"""Shared test data fixtures for database tests.

This module provides reusable test data fixtures that represent
valid business data structures for testing.
"""

from datetime import datetime, UTC
from src.extractors.base import (
    OrganizationData,
    RepositoryData,
    CommitData,
    PullRequestData,
    BranchData,
    DependencyData,
    ReadmeData,
    Platform,
)


def sample_organization_data(
    name: str = "test-org",
    platform: Platform = Platform.GITHUB,
    url: str = "https://github.com/test-org",
) -> OrganizationData:
    """Standard organization for testing."""
    return OrganizationData(
        name=name,
        url=url,
        platform=platform,
    )


def sample_repository_data(
    repo_id: str = "test-org/test-repo",
    name: str = "test-repo",
    url: str = "https://github.com/test-org/test-repo",
    default_branch: str = "main",
    team_name: str | None = None,
    is_private: bool = False,
    is_archived: bool = False,
) -> RepositoryData:
    """Standard repository for testing."""
    return RepositoryData(
        repo_id=repo_id,
        name=name,
        url=url,
        default_branch=default_branch,
        team_name=team_name,
        platform_repo_id=12345,
        created_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        is_private=is_private,
        is_archived=is_archived,
        repository_size=1024,
        open_issues_count=5,
        license_name="MIT",
        license_key="mit",
        has_vulnerability_alerts=False,
        has_secret_scanning=True,
        has_dependabot_alerts=False,
        pushed_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
        updated_at=datetime(2026, 1, 15, 0, 0, 0, tzinfo=UTC),
    )


def sample_commit_data(
    sha: str = "abc123def456",
    author_email: str = "developer@example.com",
    author_name: str = "Developer",
    message: str = "Test commit",
    commit_date: datetime | None = None,
    lines_added: int = 10,
    lines_removed: int = 5,
    files_changed: int = 2,
) -> CommitData:
    """Standard commit for testing."""
    if commit_date is None:
        commit_date = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)
    
    return CommitData(
        sha=sha,
        author_email=author_email,
        author_name=author_name,
        message=message,
        commit_date=commit_date,
        lines_added=lines_added,
        lines_removed=lines_removed,
        files_changed=files_changed,
        is_verified=False,
        verification_reason=None,
    )


def sample_branch_data(
    name: str = "main",
    latest_commit_sha: str = "abc123def456",
) -> BranchData:
    """Standard branch for testing."""
    return BranchData(
        name=name,
        latest_commit_sha=latest_commit_sha,
    )


def sample_pull_request_data(
    pr_number: int = 1,
    title: str = "Test Pull Request",
    state: str = "open",
    author_email: str = "developer@example.com",
    author_name: str = "Developer",
    source_branch: str = "feature-branch",
    target_branch: str = "main",
    created_at: datetime | None = None,
    merged_at: datetime | None = None,
    closed_at: datetime | None = None,
) -> PullRequestData:
    """Standard pull request for testing."""
    if created_at is None:
        created_at = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)
    
    return PullRequestData(
        pr_number=pr_number,
        title=title,
        description="Test description",
        state=state,
        author_email=author_email,
        author_name=author_name,
        source_branch=source_branch,
        target_branch=target_branch,
        created_at=created_at,
        updated_at=created_at,
        merged_at=merged_at,
        closed_at=closed_at,
        lines_added=50,
        lines_removed=20,
        commits_count=3,
        comments_count=2,
        review_comments_count=1,
        is_draft=False,
    )


def sample_dependency_data(
    name: str = "pytest",
    version: str = "7.4.0",
    package_manager: str = "pip",
    dependency_type: str = "dev",
) -> DependencyData:
    """Standard dependency for testing."""
    return DependencyData(
        name=name,
        version=version,
        package_manager=package_manager,
        dependency_type=dependency_type,
    )


def sample_readme_data(
    content: str = "# Test Repository\n\nThis is a test repository.",
    file_path: str = "README.md",
) -> ReadmeData:
    """Standard README for testing."""
    return ReadmeData(
        content=content,
        file_path=file_path,
    )
