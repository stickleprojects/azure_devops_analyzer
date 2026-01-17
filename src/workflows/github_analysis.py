"""
GitHub repository analysis workflow.

Orchestrates the extraction and storage of GitHub repository data
including organizations, repositories, branches, commits, and pull requests.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from src.database.connection import session_scope
from src.database.models import Organization, Project
from src.database.storage import (
    should_scan_repository,
    store_organization,
    store_project,
    store_repository,
    store_branch,
    store_commit,
    store_pull_request,
    update_repository_analyzed_timestamp,
    get_extraction_summary,
)
from src.extractors.github.extractor import GitHubExtractor

logger = logging.getLogger(__name__)


@dataclass
class ExtractionLimits:
    """Configuration for limiting extraction scope."""

    max_branches: int = 10
    max_commits: int = 50
    max_pull_requests: int = 20
    min_scan_interval_hours: int = 6


class GitHubAnalysisWorkflow:
    """
    Workflow for extracting and storing GitHub repository data.

    This class orchestrates the full extraction process:
    1. Fetch organizations/users
    2. Create organization and project records
    3. Fetch repositories for each org/user
    4. For each repository:
       - Store repository metadata
       - Fetch and store branches
       - Fetch and store commits
       - Fetch and store pull requests with reviews and comments
    """

    def __init__(
        self,
        extractor: Optional[GitHubExtractor] = None,
        limits: Optional[ExtractionLimits] = None,
    ):
        """
        Initialize the workflow.

        Args:
            extractor: GitHubExtractor instance (created if not provided).
            limits: Extraction limits configuration.
        """
        self.extractor = extractor or GitHubExtractor()
        self.limits = limits or ExtractionLimits()

    def run(self) -> dict:
        """
        Execute the full GitHub analysis workflow.

        Returns:
            Summary dictionary with extraction counts.
        """
        logger.info("Starting GitHub analysis workflow")

        orgs = self._fetch_organizations()

        for org_data in orgs:
            self._process_organization(org_data)

        logger.info("Extraction complete")
        return self._get_summary()

    def _fetch_organizations(self):
        """Fetch organizations/users from GitHub."""
        logger.info("Fetching organizations/users...")
        orgs = self.extractor.get_organizations()
        logger.info("Found %d organizations/users", len(orgs))
        return orgs

    def _process_organization(self, org_data):
        """Process a single organization and its repositories."""
        logger.info("Processing: %s", org_data.name)

        with session_scope() as session:
            org = store_organization(session, org_data)
            created = org.organization_id is not None
            if created:
                logger.info("  Created organization: %s", org_data.name)
            else:
                logger.info("  Organization exists: %s", org_data.name)

            project = store_project(
                session,
                org,
                org_data.name,
                f"GitHub repositories for {org_data.name}",
            )

        self._process_repositories(org_data)

    def _process_repositories(self, org_data):
        """Fetch and process all repositories for an organization."""
        logger.info("  Fetching repositories for %s...", org_data.name)
        repos = self.extractor.get_repositories(org_data.name)
        logger.info("  Found %d repositories", len(repos))

        for repo_data in repos:
            self._process_repository(org_data, repo_data)

    def _process_repository(self, org_data, repo_data):
        """Process a single repository."""
        logger.info("    Processing repo: %s", repo_data.name)

        # Check if repo was recently scanned
        with session_scope() as session:
            if not should_scan_repository(
                session,
                repo_data.repo_id,
                self.limits.min_scan_interval_hours,
            ):
                logger.info(
                    "      Skipping %s - scanned within last %d hours",
                    repo_data.name,
                    self.limits.min_scan_interval_hours,
                )
                return

        # Store repository
        with session_scope() as session:
            project = (
                session.query(Project)
                .join(Organization)
                .filter(
                    Organization.name == org_data.name,
                    Organization.platform == org_data.platform.value,
                )
                .first()
            )

            repo = store_repository(session, project, repo_data)
            logger.info("      Stored repository: %s", repo_data.name)

        # Process repository contents
        self._process_branches(repo_data)
        self._process_commits(repo_data)
        self._process_pull_requests(repo_data)

        # Update timestamp
        with session_scope() as session:
            update_repository_analyzed_timestamp(session, repo_data.repo_id)
            logger.info("      Updated last_analyzed_at for %s", repo_data.name)

    def _process_branches(self, repo_data):
        """Fetch and store branches for a repository."""
        try:
            branches = self.extractor.get_branches(repo_data.repo_id)
            logger.info("      Found %d branches", len(branches))

            with session_scope() as session:
                for branch_data in branches[: self.limits.max_branches]:
                    store_branch(session, repo_data.repo_id, branch_data)

        except Exception as e:
            logger.warning("      Failed to fetch branches: %s", e)

    def _process_commits(self, repo_data):
        """Fetch and store commits for a repository."""
        try:
            commits = self.extractor.get_commits(
                repo_data.repo_id,
                limit=self.limits.max_commits,
            )
            logger.info("      Found %d recent commits", len(commits))

            with session_scope() as session:
                stored_count = 0
                for commit_data in commits:
                    result = store_commit(
                        session,
                        repo_data.repo_id,
                        repo_data.default_branch,
                        commit_data,
                    )
                    if result:
                        stored_count += 1

                if stored_count > 0:
                    logger.info("      Stored %d new commits", stored_count)

        except Exception as e:
            logger.warning("      Failed to fetch commits: %s", e)

    def _process_pull_requests(self, repo_data):
        """Fetch and store pull requests for a repository."""
        try:
            prs = self.extractor.get_pull_requests(repo_data.repo_id)
            prs = prs[: self.limits.max_pull_requests]
            logger.info("      Found %d pull requests", len(prs))

            with session_scope() as session:
                stored_count = 0
                for pr_data in prs:
                    result = store_pull_request(session, repo_data.repo_id, pr_data)
                    if result:
                        stored_count += 1

                if stored_count > 0:
                    logger.info("      Stored %d new pull requests", stored_count)

        except Exception as e:
            logger.warning("      Failed to fetch PRs: %s", e)

    def _get_summary(self) -> dict:
        """Get extraction summary counts."""
        with session_scope() as session:
            return get_extraction_summary(session)


def run_github_extraction() -> dict:
    """
    Convenience function to run GitHub extraction workflow.

    Returns:
        Summary dictionary with extraction counts.
    """
    workflow = GitHubAnalysisWorkflow()
    return workflow.run()


def print_extraction_summary(summary: dict) -> None:
    """
    Print extraction summary to console.

    Args:
        summary: Dictionary with entity counts.
    """
    print("\n" + "=" * 50)
    print("EXTRACTION SUMMARY")
    print("=" * 50)
    print(f"Organizations:  {summary['organizations']}")
    print(f"Repositories:   {summary['repositories']}")
    print(f"Branches:       {summary['branches']}")
    print(f"Commits:        {summary['commits']}")
    print(f"Pull Requests:  {summary['pull_requests']}")
    print(f"Contributors:   {summary['contributors']}")
    print("=" * 50)
