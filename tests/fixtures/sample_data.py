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
    FileTreeItem,
)
from src.analyzers.technology_detector import TechnologyDetection
import json
import pathlib


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
    platform: Platform = Platform.GITHUB,
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
        platform=platform,
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
    committer_email: str | None = None,
    committer_name: str | None = None,
    message: str = "Test commit",
    commit_date: datetime | None = None,
    lines_added: int = 10,
    lines_removed: int = 5,
    files_changed: int = 2,
) -> CommitData:
    """Standard commit for testing."""
    if commit_date is None:
        commit_date = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)
    # Default committer to author if not provided
    if committer_email is None:
        committer_email = author_email
    if committer_name is None:
        committer_name = author_name
    
    return CommitData(
        sha=sha,
        author_email=author_email,
        author_name=author_name,
        committer_email=committer_email,
        committer_name=committer_name,
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
    platform_pr_id: str | None = None,
    title: str = "Test Pull Request",
    status: str = "open",
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
    if platform_pr_id is None:
        platform_pr_id = f"pr-{pr_number}"
    
    return PullRequestData(
        pr_number=pr_number,
        platform_pr_id=platform_pr_id,
        title=title,
        description="Test description",
        status=status,
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


def sample_technology_detection(
    programming_languages: list[str] | None = None,
    frameworks: list[str] | None = None,
    databases: list[str] | None = None,
    deployment_platforms: list[str] | None = None,
    build_tools: list[str] | None = None,
    testing_frameworks: list[str] | None = None,
    ci_cd_platforms: list[str] | None = None,
    primary_language: str | None = "Python",
    overall_confidence: float = 0.75,
) -> TechnologyDetection:
    """Factory for TechnologyDetection with sensible defaults."""
    # Handle None values for lists
    programming_languages = programming_languages or []
    frameworks = frameworks or []
    databases = databases or []
    deployment_platforms = deployment_platforms or []
    build_tools = build_tools or []
    testing_frameworks = testing_frameworks or []
    ci_cd_platforms = ci_cd_platforms or []
    
    # Collect all technologies
    all_tech = list(set(
        programming_languages +
        frameworks +
        databases +
        deployment_platforms +
        build_tools +
        testing_frameworks +
        ci_cd_platforms
    ))
    all_tech.sort()
    
    return TechnologyDetection(
        programming_languages=programming_languages,
        frameworks=frameworks,
        databases=databases,
        deployment_platforms=deployment_platforms,
        build_tools=build_tools,
        testing_frameworks=testing_frameworks,
        ci_cd_platforms=ci_cd_platforms,
        documentation_tools=[],
        language_confidence=0.75,
        framework_confidence=0.5,
        overall_confidence=overall_confidence,
        all_technologies=all_tech,
        primary_language=primary_language,
        analyzed_at=datetime.now(UTC)
    )


def sample_file_tree(scenario_name: str) -> list[FileTreeItem]:
    """Load a named scenario and return its file tree as FileTreeItem objects."""
    scenario_path = pathlib.Path(__file__).parent / "scenarios" / f"{scenario_name}.json"
    if not scenario_path.exists():
        raise FileNotFoundError(f"Scenario file not found: {scenario_path}")
    
    with open(scenario_path, 'r') as f:
        data = json.load(f)
    
    file_names = data.get("file_names", [])
    return [FileTreeItem(path=p, is_directory=False, size=100) for p in file_names]