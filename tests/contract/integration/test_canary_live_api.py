"""Canary live-API tests for nightly monitoring (Plan 020 Component 2).

These tests exercise a small set of known-good ("canary") repositories on
each platform and assert that the extraction pipeline returns data that meets
minimum expected counts.  They are marked ``@pytest.mark.live_api`` and are
therefore **excluded from the normal CI run**; they run only under the nightly
``live-api-nightly.yml`` workflow (or on explicit ``workflow_dispatch``).

Canary baselines are lower bounds, not exact values, so the tests survive
natural repository growth without needing frequent updates.  If a count falls
significantly below the real value, refresh the constant and open a PR —
no secrets or infrastructure changes are needed.

See ``tests/fixtures/canaries/README.md`` for setup instructions and the
criteria used to select canary repositories.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import pytest
from sqlalchemy.orm import Session

from src.config.azure_devops import AzureDevOpsExtractorConfig
from src.config.github import GitHubExtractorConfig
from src.database.models import Contributor, Repository
from src.database.storage import get_or_create_contributor
from src.extractors.azure_devops.extractor import AzureDevOpsExtractor
from src.extractors.github.extractor import GitHubExtractor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_canary_github_token() -> Optional[str]:
    """Return the GitHub token from the environment, or None.

    Reads ``GITHUB_TOKEN``, which the nightly workflow populates from
    ``github.token``.
    """
    return os.environ.get("GITHUB_TOKEN")


def _get_canary_azure_pat() -> Optional[str]:
    """Return the Azure DevOps PAT from the environment, or None.

    Reads ``AZURE_DEVOPS_PAT``, the same secret used by the existing CI
    workflows.
    """
    return os.environ.get("AZURE_DEVOPS_PAT")


def _get_canary_azure_org_url() -> Optional[str]:
    """Return the Azure DevOps organisation URL from the environment, or None.

    Reads ``AZURE_DEVOPS_ORG_URL``.  If unset the test is skipped; there is
    no hardcoded default because the org URL is deployment-specific.
    """
    return os.environ.get("AZURE_DEVOPS_ORG_URL")


def _org_name_from_url(org_url: str) -> str:
    """Extract the organisation name from an Azure DevOps URL.

    Mirrors the logic in ``AzureDevOpsExtractor.get_repository`` (extractor.py:167):
    the org name is the trailing path segment of the URL.

    >>> _org_name_from_url("https://dev.azure.com/kieronwray")
    'kieronwray'
    """
    return org_url.rstrip("/").split("/")[-1]


# ---------------------------------------------------------------------------
# GitHub canary
# ---------------------------------------------------------------------------


@pytest.mark.live_api
@pytest.mark.integration
class TestGitHubCanary:
    """Canary smoke-test for GitHub extraction.

    Uses ``stickleprojects/azure_devops_analyzer`` as the canary repository —
    it is small, stable, and accessible via ``GITHUB_TOKEN``
    (populated from ``github.token`` by the nightly workflow).

    Baselines are lower bounds so they survive normal repository growth.
    If the real count drifts far above ``EXPECTED_*``, update the constant
    here and in ``tests/fixtures/canaries/README.md`` and open a PR.
    """

    CANARY = "stickleprojects/azure_devops_analyzer"
    EXPECTED_PR_COUNT = 10       # lower bound — increase if repo grows significantly
    EXPECTED_CONTRIB_COUNT = 1   # lower bound

    def test_canary_repository_is_accessible(self):
        """The canary repository can be fetched from the GitHub API."""
        token = _get_canary_github_token()
        if not token:
            pytest.skip("GITHUB_TOKEN not set")

        config = GitHubExtractorConfig(token=token)
        extractor = GitHubExtractor(config=config)
        repo_data = extractor.get_repository(self.CANARY)
        assert repo_data is not None, f"Could not fetch canary repository {self.CANARY!r}"
        assert repo_data.name, "Repository name must not be empty"
        logger.info("GitHub canary repository accessible: %s", self.CANARY)

    def test_canary_pull_request_count_meets_baseline(self):
        """At least ``EXPECTED_PR_COUNT`` pull requests exist in the canary repo."""
        token = _get_canary_github_token()
        if not token:
            pytest.skip("GITHUB_TOKEN not set")

        config = GitHubExtractorConfig(token=token)
        extractor = GitHubExtractor(config=config)

        prs = extractor.get_pull_requests(self.CANARY)
        assert len(prs) >= self.EXPECTED_PR_COUNT, (
            f"Expected >= {self.EXPECTED_PR_COUNT} PRs in {self.CANARY}, "
            f"got {len(prs)}.  If the baseline is stale, update EXPECTED_PR_COUNT."
        )
        logger.info("GitHub canary PR count OK: %d >= %d", len(prs), self.EXPECTED_PR_COUNT)

    def test_canary_contributor_identity_invariants(self, test_session: Session, db_invariants_check):
        """Stored contributor emails are normalised and identity invariants hold.

        This test verifies that:
        1. At least ``EXPECTED_CONTRIB_COUNT`` contributors are stored.
        2. Every stored email equals its own ``email.strip().lower()`` — i.e.
           normalisation has been applied and no mixed-case or padded email
           slips through to the database.

        ``db_invariants_check`` validates the full DB invariant set on teardown.
        """
        token = _get_canary_github_token()
        if not token:
            pytest.skip("GITHUB_TOKEN not set")

        config = GitHubExtractorConfig(token=token)
        extractor = GitHubExtractor(config=config)

        # Store the canary repository record, keyed by the platform repo_id.
        repo_data = extractor.get_repository(self.CANARY)
        existing = test_session.query(Repository).filter_by(repo_id=repo_data.repo_id).first()
        if existing is None:
            repo = Repository(
                repo_id=repo_data.repo_id,
                url=repo_data.url,
                name=repo_data.name,
                default_branch=repo_data.default_branch,
                created_at=repo_data.created_at,
                updated_at=repo_data.updated_at,
                is_private=repo_data.is_private,
                is_archived=repo_data.is_archived,
            )
            test_session.add(repo)
            test_session.commit()

        # Pull PRs and store contributing authors (cap at 50 to keep the test fast).
        prs = extractor.get_pull_requests(self.CANARY)
        for pr in prs[:50]:
            if pr.author_email:
                get_or_create_contributor(test_session, pr.author_email, pr.author_name or "")
        test_session.commit()

        # Baseline count check.
        all_contributors = test_session.query(Contributor).all()
        count = len(all_contributors)
        assert count >= self.EXPECTED_CONTRIB_COUNT, (
            f"Expected >= {self.EXPECTED_CONTRIB_COUNT} contributors, got {count}."
        )
        logger.info("GitHub canary contributor count OK: %d >= %d", count, self.EXPECTED_CONTRIB_COUNT)

        # Identity invariant: every stored email must already be normalised.
        non_normalised = [
            c.email for c in all_contributors
            if c.email != c.email.strip().lower()
        ]
        assert not non_normalised, (
            f"Contributor emails are not normalised in the database: {non_normalised}"
        )
        # db_invariants_check fixture validates the full DB invariant set on teardown.


# ---------------------------------------------------------------------------
# Azure DevOps canary
# ---------------------------------------------------------------------------


@pytest.mark.live_api
@pytest.mark.integration
class TestAzureDevOpsCanary:
    """Canary smoke-test for Azure DevOps extraction.

    Uses the ``azure_devops_analyzer`` project in the org identified by
    ``AZURE_DEVOPS_ORG_URL``.  Accessible via the ``AZURE_DEVOPS_PAT`` secret.

    Baselines are lower bounds; update ``EXPECTED_REPO_COUNT`` if the project
    grows significantly.
    """

    EXPECTED_REPO_COUNT = 1  # lower bound — the project must contain at least one repo

    def test_canary_organization_is_accessible(self):
        """The canary Azure DevOps organization can be reached."""
        pat = _get_canary_azure_pat()
        org_url = _get_canary_azure_org_url()
        if not pat:
            pytest.skip("AZURE_DEVOPS_PAT not set")
        if not org_url:
            pytest.skip("AZURE_DEVOPS_ORG_URL not set")

        org_name = _org_name_from_url(org_url)
        config = AzureDevOpsExtractorConfig(pat=pat, org_url=org_url)
        extractor = AzureDevOpsExtractor(config=config)
        projects = extractor.get_projects(org_name)
        assert projects is not None, "get_projects() returned None"
        logger.info(
            "Azure DevOps canary organization accessible: %s (%d project(s))",
            org_url, len(projects),
        )

    def test_canary_repo_count_meets_baseline(self):
        """At least ``EXPECTED_REPO_COUNT`` repositories exist in the canary organization."""
        pat = _get_canary_azure_pat()
        org_url = _get_canary_azure_org_url()
        if not pat:
            pytest.skip("AZURE_DEVOPS_PAT not set")
        if not org_url:
            pytest.skip("AZURE_DEVOPS_ORG_URL not set")

        org_name = _org_name_from_url(org_url)
        config = AzureDevOpsExtractorConfig(pat=pat, org_url=org_url)
        extractor = AzureDevOpsExtractor(config=config)
        projects = extractor.get_projects(org_name)
        total_repos = 0
        for project in projects:
            repos = extractor.get_repositories(organization=org_name, project=project.name)
            total_repos += len(repos)

        assert total_repos >= self.EXPECTED_REPO_COUNT, (
            f"Expected >= {self.EXPECTED_REPO_COUNT} repos across all projects, "
            f"got {total_repos}.  If the baseline is stale, update EXPECTED_REPO_COUNT."
        )
        logger.info(
            "Azure DevOps canary repo count OK: %d >= %d",
            total_repos, self.EXPECTED_REPO_COUNT,
        )
