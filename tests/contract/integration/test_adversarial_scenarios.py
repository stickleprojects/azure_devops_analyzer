"""
Integration Tests: Adversarial Fixture Scenarios

CONTRACT: Each adversarial scenario must flow through the full extraction →
storage pipeline without raising, and the resulting database state must satisfy
all invariants defined in tests/db_invariants.sql.

Adversarial scenarios model real-world edge cases that happy-path generated
fixtures deliberately omit: case-variant emails, whitespace emails, ghost
authors, unicode names, force-pushed PRs, bot committers, self-reviews,
dismissed reviews, future-dated commits, and same-second commits.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from tests.fixtures.fixture_extractor import FixtureExtractor
from tests.fixtures.sample_data import sample_repository_data
from tests.contract.integration._pipeline_helpers import run_pipeline
from src.database.storage import (
    store_project,
    store_repository,
)
from src.database.models import Commit, Contributor, PullRequest, PRReview

# ---------------------------------------------------------------------------
# Scenario registry
# ---------------------------------------------------------------------------

ADVERSARIAL_SCENARIOS = [
    "mixed-case-emails",
    "whitespace-emails",
    "ghost-author",
    "unicode-names",
    "force-pushed-pr",
    "bot-committer",
    "self-review",
    "dismissed-review",
    "future-dated-commit",
    "same-second-commits",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_fixture_repo(session: Session, organization, scenario_name: str):
    """Create a project + repository row for a given fixture scenario."""
    project = store_project(session, organization, name=f"adversarial-project-{scenario_name}", description="")
    repo_data = sample_repository_data(
        repo_id=f"adversarial/{scenario_name}",
        name=scenario_name,
        url=f"https://example.com/adversarial/{scenario_name}",
    )
    repo = store_repository(session, project, repo_data)
    session.commit()
    return repo


def _run_full_pipeline(session: Session, repo_id: str, extractor: FixtureExtractor):
    """Run the extraction pipeline for a single repo (delegates to shared helper)."""
    run_pipeline(session, repo_id, extractor)


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.parametrize("scenario", ADVERSARIAL_SCENARIOS)
class TestAdversarialScenarios:
    """
    CONTRACT: Every adversarial scenario must complete the full pipeline
    without error, and the resulting DB state must satisfy all invariants.
    """

    def test_pipeline_completes_without_error(self, scenario, test_session, organization):
        """The extraction pipeline must not raise for this edge-case scenario."""
        extractor = FixtureExtractor(scenario)
        repo = _create_fixture_repo(test_session, organization, scenario)
        # Must not raise
        _run_full_pipeline(test_session, repo.repo_id, extractor)

    def test_db_invariants_hold(self, scenario, test_session, organization, db_invariants_check):
        """All DB invariants defined in tests/db_invariants.sql must hold.

        The db_invariants_check fixture runs the invariant queries as a
        post-condition after the test body commits data.
        """
        extractor = FixtureExtractor(scenario)
        repo = _create_fixture_repo(test_session, organization, scenario)
        _run_full_pipeline(test_session, repo.repo_id, extractor)
        # db_invariants_check teardown fires here

    def test_no_orphan_pr_author_fk(self, scenario, test_session, organization):
        """No pull_requests row may have a null or dangling author_id."""
        extractor = FixtureExtractor(scenario)
        repo = _create_fixture_repo(test_session, organization, scenario)
        _run_full_pipeline(test_session, repo.repo_id, extractor)

        orphan_count = test_session.execute(
            text("""
                SELECT count(*) FROM pull_requests
                WHERE repo_id = :repo_id
                  AND (author_id IS NULL
                       OR author_id NOT IN (SELECT id FROM contributors))
            """),
            {"repo_id": repo.repo_id},
        ).scalar()
        assert orphan_count == 0, (
            f"Adversarial scenario '{scenario}': found {orphan_count} PRs with "
            "NULL or dangling author_id"
        )

    def test_no_orphan_pr_reviewer_fk(self, scenario, test_session, organization):
        """No pr_reviews row may have a null or dangling reviewer_id."""
        extractor = FixtureExtractor(scenario)
        repo = _create_fixture_repo(test_session, organization, scenario)
        _run_full_pipeline(test_session, repo.repo_id, extractor)

        stored_prs = test_session.query(PullRequest).filter_by(repo_id=repo.repo_id).all()
        pr_ids = [p.id for p in stored_prs]

        if pr_ids:
            orphan_count = test_session.execute(
                text("""
                    SELECT count(*) FROM pr_reviews
                    WHERE pr_id = ANY(:pr_ids)
                      AND (reviewer_id IS NULL
                           OR reviewer_id NOT IN (SELECT id FROM contributors))
                """),
                {"pr_ids": pr_ids},
            ).scalar()
            assert orphan_count == 0, (
                f"Adversarial scenario '{scenario}': found {orphan_count} reviews with "
                "NULL or dangling reviewer_id"
            )

    def test_no_case_variant_contributor_twins(self, scenario, test_session, organization):
        """No two contributors rows may share the same normalised email."""
        extractor = FixtureExtractor(scenario)
        repo = _create_fixture_repo(test_session, organization, scenario)
        _run_full_pipeline(test_session, repo.repo_id, extractor)

        twin_count = test_session.execute(
            text("""
                SELECT count(*) FROM (
                    SELECT lower(trim(email)) AS norm_email
                    FROM contributors
                    GROUP BY lower(trim(email))
                    HAVING count(*) > 1
                ) dupes
            """)
        ).scalar()
        assert twin_count == 0, (
            f"Adversarial scenario '{scenario}': found {twin_count} email(s) with "
            "multiple contributors rows (case-variant twin)"
        )
