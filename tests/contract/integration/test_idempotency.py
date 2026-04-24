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
from tests.contract.integration._pipeline_helpers import run_pipeline
from src.database.storage import (
    store_organization,
    store_project,
    store_repository,
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
    """Run the extraction pipeline for a single repo (delegates to shared helper)."""
    run_pipeline(session, repo_id, extractor)


def _capture_state(session: Session, repo_id: str) -> dict:
    """Capture a stable snapshot of the DB state for a given repo.

    Returns a dict with:
        row_counts: {table: count}  scoped to repo_id where possible
        id_hashes:  {table: hex}   stable hash of the sorted set of *content* keys

    Hashing strategy — content keys rather than surrogate PKs:
        commits       – commit_sha  (content-addressed, stable across re-inserts)
        pull_requests – pr_number   (business key; unique per repo)
        pr_reviews    – (pr_number, reviewer_id, vote) tuple
        contributors  – normalised email (what the dedup logic actually stores)

    Using content keys means the hash detects genuine duplication or omission
    even if autoincrement sequences reset between test runs.  It does NOT detect
    field-level mutations (e.g. a title change) — that is out of scope for the
    current "insert-once" idempotency guarantee (see TODO below).

    TODO: extend once store_pull_request gains upsert semantics.  At that point
    the snapshot should capture (pr_number, status, review_count) tuples so that
    field-level convergence is also verified.
    """
    # commits — hash sorted commit_sha values (already content-addressed)
    commit_rows = session.execute(
        text("SELECT commit_sha FROM commits WHERE repo_id = :rid ORDER BY commit_sha"),
        {"rid": repo_id},
    ).fetchall()

    # pull_requests — hash sorted pr_number values (natural business key)
    pr_rows = session.execute(
        text("SELECT pr_number FROM pull_requests WHERE repo_id = :rid ORDER BY pr_number"),
        {"rid": repo_id},
    ).fetchall()

    # pr_reviews — hash sorted (pr_number, reviewer_id, vote) tuples
    # pr_reviews has no `state` column; the verdict is stored as `vote` (integer).
    review_rows = session.execute(
        text("""
            SELECT pr.pr_number, r.reviewer_id, r.vote
            FROM pr_reviews r
            JOIN pull_requests pr ON r.pr_id = pr.id
            WHERE pr.repo_id = :rid
            ORDER BY pr.pr_number, r.reviewer_id, r.vote
        """),
        {"rid": repo_id},
    ).fetchall()

    # contributors — hash sorted normalised emails
    contributor_rows = session.execute(
        text("""
            SELECT DISTINCT c.email
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
            ORDER BY c.email
        """),
        {"rid": repo_id},
    ).fetchall()

    def _hash(rows) -> str:
        return hashlib.sha256("|".join(str(r) for r in rows).encode()).hexdigest()

    return {
        "row_counts": {
            "commits": len(commit_rows),
            "pull_requests": len(pr_rows),
            "pr_reviews": len(review_rows),
            "contributors": len(contributor_rows),
        },
        "id_hashes": {
            "commits": _hash(commit_rows),
            "pull_requests": _hash(pr_rows),
            "pr_reviews": _hash(review_rows),
            "contributors": _hash(contributor_rows),
        },
    }


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

        Idempotency guarantee — current semantics are **insert-once at the PR
        level**: ``store_pull_request`` is a no-op when the (repo_id, pr_number)
        row already exists and does not update reviews or any other field.  Pass
        2 therefore produces the same row set as pass 1.

        This harness catches regressions *away* from the insert-once behaviour
        (e.g. a code change that accidentally inserts duplicate rows on re-run).
        It does not verify genuine re-convergence / upsert semantics — that is
        a TODO for when ``store_pull_request`` gains explicit upsert semantics.

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
