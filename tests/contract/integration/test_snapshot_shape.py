"""
Integration Tests: Recorded Real-API Snapshot Shape

CONTRACT: The full extraction pipeline must handle the data shapes produced by
real GitHub and Azure DevOps APIs without raising, and the resulting database
state must satisfy all DB invariants.

Snapshots in tests/fixtures/snapshots/ are anonymised recordings of real API
responses.  They preserve production-shape quirks (case variation, whitespace
in emails, bot committer patterns, unicode in names, null fields, etc.) that
happy-path generated fixtures cannot reproduce.

Refresh snapshots quarterly via:
    bash scripts/capture-api-snapshot.sh
    python scripts/anonymise-snapshot.py
"""

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from tests.fixtures.snapshot_extractor import SnapshotExtractor
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
from src.database.models import PullRequest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_snapshot_pipeline(
    session: Session,
    platform: str,
    extractor: SnapshotExtractor,
):
    """Create org/repo rows and run the full extraction pipeline for a snapshot.

    Returns the created Repository ORM object.
    """
    org_data = sample_organization_data(
        name=f"snapshot-org-{platform}",
        platform=Platform.GITHUB if platform == "github" else Platform.AZURE_DEVOPS,
    )
    org = store_organization(session, org_data)
    project = store_project(session, org, name=f"snapshot-project-{platform}")
    repo_data = sample_repository_data(
        repo_id=f"snapshot/{platform}/fixture",
        name=f"snapshot-{platform}",
        url=f"https://fixture.example/{platform}/fixture",
    )
    repo = store_repository(session, project, repo_data)
    session.flush()

    branches = extractor.get_branches(repo.repo_id)
    default_branch = branches[0].name if branches else "main"

    for branch in branches:
        store_branch(session, repo.repo_id, branch)
    session.flush()

    for commit_data in extractor.get_commits(repo.repo_id):
        store_commit(session, repo.repo_id, default_branch, commit_data)
    session.flush()

    for pr_data in extractor.get_pull_requests(repo.repo_id):
        store_pull_request(session, repo.repo_id, pr_data)
    session.flush()

    languages = extractor.get_languages(repo.repo_id)
    if languages:
        store_languages(session, repo.repo_id, languages)
        session.flush()

    session.commit()
    return repo


# ---------------------------------------------------------------------------
# GitHub snapshot tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestGitHubSnapshot:
    """Pipeline must complete correctly on the recorded GitHub snapshot shape."""

    def test_pipeline_completes_on_real_shape(
        self, test_session, db_invariants_check
    ):
        """The pipeline must not raise on GitHub snapshot data.

        DB invariants are asserted by the db_invariants_check fixture teardown.
        """
        extractor = SnapshotExtractor("github")
        _run_snapshot_pipeline(test_session, "github", extractor)
        # db_invariants_check teardown fires here

    def test_no_orphan_pr_author_fk(self, test_session):
        """Every PR stored from the snapshot must have a valid author_id FK."""
        extractor = SnapshotExtractor("github")
        repo = _run_snapshot_pipeline(test_session, "github", extractor)

        orphans = test_session.execute(
            text("""
                SELECT count(*) FROM pull_requests
                WHERE repo_id = :rid
                  AND (author_id IS NULL
                       OR author_id NOT IN (SELECT id FROM contributors))
            """),
            {"rid": repo.repo_id},
        ).scalar()
        assert orphans == 0, f"GitHub snapshot: {orphans} PRs with NULL/dangling author_id"

    def test_no_case_variant_contributor_twins(self, test_session):
        """Case-variant emails in the snapshot must map to a single contributor row."""
        extractor = SnapshotExtractor("github")
        _run_snapshot_pipeline(test_session, "github", extractor)

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
            f"GitHub snapshot: {twin_count} normalised email(s) map to >1 contributor row"
        )


# ---------------------------------------------------------------------------
# Azure DevOps snapshot tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestAzureDevOpsSnapshot:
    """Pipeline must complete correctly on the recorded Azure DevOps snapshot shape."""

    def test_pipeline_completes_on_real_shape(
        self, test_session, db_invariants_check
    ):
        """The pipeline must not raise on Azure DevOps snapshot data.

        DB invariants are asserted by the db_invariants_check fixture teardown.
        """
        extractor = SnapshotExtractor("azure_devops")
        _run_snapshot_pipeline(test_session, "azure_devops", extractor)
        # db_invariants_check teardown fires here

    def test_no_orphan_pr_author_fk(self, test_session):
        """Every PR stored from the snapshot must have a valid author_id FK."""
        extractor = SnapshotExtractor("azure_devops")
        repo = _run_snapshot_pipeline(test_session, "azure_devops", extractor)

        orphans = test_session.execute(
            text("""
                SELECT count(*) FROM pull_requests
                WHERE repo_id = :rid
                  AND (author_id IS NULL
                       OR author_id NOT IN (SELECT id FROM contributors))
            """),
            {"rid": repo.repo_id},
        ).scalar()
        assert orphans == 0, f"Azure DevOps snapshot: {orphans} PRs with NULL/dangling author_id"

    def test_no_case_variant_contributor_twins(self, test_session):
        """Case-variant emails in the snapshot must map to a single contributor row."""
        extractor = SnapshotExtractor("azure_devops")
        _run_snapshot_pipeline(test_session, "azure_devops", extractor)

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
            f"Azure DevOps snapshot: {twin_count} normalised email(s) map to >1 contributor row"
        )
