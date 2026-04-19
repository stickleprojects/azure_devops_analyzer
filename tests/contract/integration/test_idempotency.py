"""
Integration Tests: Extraction Idempotency

CONTRACT: Running the full extraction pipeline twice against the same repository
must produce stable database state — identical row counts and primary key sets.
Idempotency is critical because scheduled re-scans and retries are routine
production events.

Gap 3 from Plan 019: re-extraction producing duplicates or orphans would only
surface in production without this harness.
"""

import hashlib
import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from tests.fixtures.fixture_extractor import FixtureExtractor
from tests.fixtures.sample_data import sample_organization_data, sample_repository_data
from src.database.storage import (
    store_organization,
    store_project,
    store_repository,
    store_branch,
    store_commit,
    store_pull_request,
    store_languages,
)
from src.extractors.base import Platform
from src.database.models import Commit, PullRequest, PRReview, Contributor

# ---------------------------------------------------------------------------
# Scenarios to exercise idempotency.
# Must include at least two happy-path + one adversarial (mixed-case-emails).
# ---------------------------------------------------------------------------
IDEMPOTENCY_SCENARIOS = [
    "go-microservice",
    "fullstack-monorepo",
    "mixed-case-emails",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _setup_repo(session: Session, scenario_name: str):
    """Create org → project → repo for an idempotency test."""
    org_data = sample_organization_data(
        name=f"idempotency-org-{scenario_name}",
        platform=Platform.GITHUB,
    )
    org = store_organization(session, org_data)
    project = store_project(session, org, name=f"idempotency-project-{scenario_name}")
    repo_data = sample_repository_data(
        repo_id=f"idempotency/{scenario_name}",
        name=scenario_name,
        url=f"https://example.com/idempotency/{scenario_name}",
    )
    repo = store_repository(session, project, repo_data)
    session.commit()
    return repo


def _run_pipeline(session: Session, repo_id: str, extractor: FixtureExtractor):
    """Run branches → commits → PRs → languages for a single repo."""
    branches = extractor.get_branches(repo_id)
    default_branch = branches[0].name if branches else "main"

    for branch in branches:
        store_branch(session, repo_id, branch)
    session.flush()

    for commit_data in extractor.get_commits(repo_id):
        store_commit(session, repo_id, default_branch, commit_data)
    session.flush()

    for pr_data in extractor.get_pull_requests(repo_id):
        store_pull_request(session, repo_id, pr_data)
    session.flush()

    languages = extractor.get_languages(repo_id)
    if languages:
        store_languages(session, repo_id, languages)
        session.flush()

    session.commit()


def _capture_state(session: Session, repo_id: str) -> dict:
    """Capture a stable snapshot of the DB state for a given repo.

    Returns a dict with:
        row_counts: {table: count}  scoped to repo_id where possible
        id_hashes:  {table: hex}   stable hash of the sorted set of PKs
    """
    tables_scoped = {
        "commits": "SELECT id FROM commits WHERE repo_id = :rid ORDER BY id",
        "pull_requests": "SELECT id FROM pull_requests WHERE repo_id = :rid ORDER BY id",
    }
    tables_via_pr = {
        "pr_reviews": (
            "SELECT r.id FROM pr_reviews r "
            "JOIN pull_requests pr ON r.pr_id = pr.id "
            "WHERE pr.repo_id = :rid ORDER BY r.id"
        ),
    }

    row_counts = {}
    id_hashes = {}

    for table, sql in {**tables_scoped, **tables_via_pr}.items():
        rows = session.execute(text(sql), {"rid": repo_id}).fetchall()
        row_counts[table] = len(rows)
        id_str = ",".join(str(r[0]) for r in rows)
        id_hashes[table] = hashlib.md5(id_str.encode()).hexdigest()

    # contributors — scoped by email appearing in this repo's commits/PRs
    contributor_ids = session.execute(
        text("""
            SELECT DISTINCT c.id
            FROM contributors c
            WHERE c.id IN (
                SELECT author_id FROM commits WHERE repo_id = :rid
                UNION
                SELECT author_id FROM pull_requests WHERE repo_id = :rid
                UNION
                SELECT r.reviewer_id FROM pr_reviews r
                JOIN pull_requests pr ON r.pr_id = pr.id
                WHERE pr.repo_id = :rid
            )
            ORDER BY c.id
        """),
        {"rid": repo_id},
    ).fetchall()
    row_counts["contributors"] = len(contributor_ids)
    id_hashes["contributors"] = hashlib.md5(
        ",".join(str(r[0]) for r in contributor_ids).encode()
    ).hexdigest()

    return {"row_counts": row_counts, "id_hashes": id_hashes}


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.parametrize("scenario", IDEMPOTENCY_SCENARIOS)
class TestExtractionIdempotency:
    """
    CONTRACT: Running the pipeline twice against the same repository must
    produce identical row counts and primary-key sets.
    """

    def test_reextraction_produces_stable_state(
        self, scenario, test_session, db_invariants_check
    ):
        """Two pipeline passes over the same data must yield identical DB state.

        Also asserts DB invariants via the db_invariants_check fixture.
        """
        extractor = FixtureExtractor(scenario)
        repo = _setup_repo(test_session, scenario)

        # Pass 1
        _run_pipeline(test_session, repo.repo_id, extractor)
        snapshot_1 = _capture_state(test_session, repo.repo_id)

        # Pass 2 — same extractor, same target repo
        _run_pipeline(test_session, repo.repo_id, extractor)
        snapshot_2 = _capture_state(test_session, repo.repo_id)

        assert snapshot_1 == snapshot_2, (
            f"Re-extraction changed DB state for scenario '{scenario}':\n"
            f"  pass-1: {snapshot_1}\n"
            f"  pass-2: {snapshot_2}"
        )
        # db_invariants_check teardown runs here automatically
