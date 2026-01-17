"""
Base classes and data models for repository extractors.

All platform-specific extractors must implement the RepositoryExtractor interface
and return data using these standardized data classes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class Platform(str, Enum):
    """Supported source control platforms."""
    AZURE_DEVOPS = "azure_devops"
    GITHUB = "github"


@dataclass
class RepositoryMetadata:
    """Optional metadata from repository.json file."""
    team_name: Optional[str] = None
    service_name: Optional[str] = None


@dataclass
class OrganizationData:
    """Organization/account data from the platform."""
    name: str
    url: str
    platform: Platform


@dataclass
class ProjectData:
    """Project data (Azure DevOps concept, maps to GitHub org/user)."""
    name: str
    description: Optional[str] = None
    organization_name: Optional[str] = None


@dataclass
class ContributorData:
    """Contributor information extracted from commits and PRs."""
    email: str
    name: Optional[str] = None


@dataclass
class BranchData:
    """Branch metadata."""
    name: str
    latest_commit_sha: str
    created_at: Optional[datetime] = None


@dataclass
class FileTreeItem:
    """File or directory in the repository tree."""
    path: str
    is_directory: bool
    size: Optional[int] = None


@dataclass
class CommitData:
    """Commit information."""
    sha: str
    message: str
    author_email: str
    author_name: Optional[str]
    committer_email: str
    committer_name: Optional[str]
    commit_date: datetime
    parent_shas: list[str] = field(default_factory=list)
    files_changed: Optional[int] = None
    lines_added: Optional[int] = None
    lines_removed: Optional[int] = None


@dataclass
class PRReviewData:
    """Pull request review information."""
    reviewer_email: str
    reviewer_name: Optional[str]
    review_date: datetime
    state: str  # approved, changes_requested, commented, dismissed
    is_required: bool = False
    comment_count: int = 0


@dataclass
class PRCommentData:
    """Pull request comment/thread."""
    author_email: str
    author_name: Optional[str]
    content: str
    published_date: datetime
    thread_id: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    comment_type: str = "text"  # text, system


@dataclass
class PullRequestData:
    """Pull request metadata."""
    pr_number: int
    platform_pr_id: str  # Platform-specific unique ID
    title: str
    description: Optional[str]
    source_branch: str
    target_branch: str
    author_email: str
    author_name: Optional[str]
    status: str  # open, merged, closed
    created_at: datetime
    updated_at: Optional[datetime] = None
    merged_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    files_changed: int = 0
    lines_added: int = 0
    lines_removed: int = 0
    reviews: list[PRReviewData] = field(default_factory=list)
    comments: list[PRCommentData] = field(default_factory=list)


@dataclass
class RepositoryData:
    """Complete repository data."""
    repo_id: str  # Platform-specific identifier
    name: str
    url: str
    default_branch: Optional[str]
    platform: Platform
    platform_repo_id: Optional[int] = None  # Numeric ID (GitHub)
    project_name: Optional[str] = None
    organization_name: Optional[str] = None
    created_at: Optional[datetime] = None
    team_name: Optional[str] = None  # From repository.json
    service_name: Optional[str] = None  # From repository.json
    branches: list[BranchData] = field(default_factory=list)
    commits: list[CommitData] = field(default_factory=list)
    pull_requests: list[PullRequestData] = field(default_factory=list)
    file_tree: list[FileTreeItem] = field(default_factory=list)


class RepositoryExtractor(ABC):
    """
    Abstract base class for repository data extraction.

    Each platform (Azure DevOps, GitHub) implements this interface
    to provide a consistent API for data extraction.
    """

    @property
    @abstractmethod
    def platform(self) -> Platform:
        """Return the platform this extractor handles."""
        pass

    @abstractmethod
    def get_organizations(self) -> list[OrganizationData]:
        """
        List all accessible organizations/accounts.

        Returns:
            List of organizations the authenticated user can access.
        """
        pass

    @abstractmethod
    def get_projects(self, organization: str) -> list[ProjectData]:
        """
        List all projects within an organization.

        For GitHub, this returns a single project matching the org/user.

        Args:
            organization: Organization or account name.

        Returns:
            List of projects.
        """
        pass

    @abstractmethod
    def get_repositories(
        self,
        organization: str,
        project: Optional[str] = None
    ) -> list[RepositoryData]:
        """
        List all repositories in an organization/project.

        Args:
            organization: Organization or account name.
            project: Optional project name (Azure DevOps specific).

        Returns:
            List of repository metadata (without commits/PRs).
        """
        pass

    @abstractmethod
    def get_branches(self, repo_id: str) -> list[BranchData]:
        """
        Get all branches for a repository.

        Args:
            repo_id: Repository identifier.

        Returns:
            List of branch data.
        """
        pass

    @abstractmethod
    def get_commits(
        self,
        repo_id: str,
        branch: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> list[CommitData]:
        """
        Get commits for a repository.

        Args:
            repo_id: Repository identifier.
            branch: Optional branch to filter commits.
            since: Optional start date for commit range.
            until: Optional end date for commit range.
            limit: Maximum number of commits to return.

        Returns:
            List of commit data.
        """
        pass

    @abstractmethod
    def get_pull_requests(
        self,
        repo_id: str,
        status: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> list[PullRequestData]:
        """
        Get pull requests for a repository.

        Args:
            repo_id: Repository identifier.
            status: Filter by status (open, merged, closed, all).
            since: Only return PRs updated after this date.

        Returns:
            List of pull request data with reviews and comments.
        """
        pass

    @abstractmethod
    def get_file_tree(
        self,
        repo_id: str,
        branch: Optional[str] = None
    ) -> list[FileTreeItem]:
        """
        Get the file tree for a repository.

        Args:
            repo_id: Repository identifier.
            branch: Branch to get tree from (defaults to default branch).

        Returns:
            List of files and directories.
        """
        pass

    @abstractmethod
    def get_file_content(
        self,
        repo_id: str,
        file_path: str,
        branch: Optional[str] = None
    ) -> Optional[str]:
        """
        Get the content of a specific file.

        Args:
            repo_id: Repository identifier.
            file_path: Path to the file.
            branch: Branch to get file from (defaults to default branch).

        Returns:
            File content as string, or None if not found.
        """
        pass

    def get_repository_metadata(
        self,
        repo_id: str,
        branch: Optional[str] = None
    ) -> Optional[RepositoryMetadata]:
        """
        Get repository metadata from repository.json file.

        Args:
            repo_id: Repository identifier.
            branch: Branch to get file from (defaults to default branch).

        Returns:
            RepositoryMetadata if repository.json exists and is valid, None otherwise.
        """
        import json

        content = self.get_file_content(repo_id, "repository.json", branch)
        if content is None:
            return None

        try:
            data = json.loads(content)
            return RepositoryMetadata(
                team_name=data.get("teamname"),
                service_name=data.get("servicename"),
            )
        except (json.JSONDecodeError, TypeError):
            return None

    def extract_full_repository(
        self,
        repo_id: str,
        include_commits: bool = True,
        include_prs: bool = True,
        include_file_tree: bool = True,
        commit_limit: Optional[int] = 1000,
        commit_since_days: int = 90,
    ) -> RepositoryData:
        """
        Extract complete repository data.

        This is a convenience method that calls all extraction methods
        and returns a complete RepositoryData object.

        Args:
            repo_id: Repository identifier.
            include_commits: Whether to include commit history.
            include_prs: Whether to include pull requests.
            include_file_tree: Whether to include file tree.
            commit_limit: Maximum commits to fetch.
            commit_since_days: Only fetch commits from last N days.

        Returns:
            Complete repository data.
        """
        from datetime import timedelta

        # Get basic repo info
        repos = self.get_repositories("", None)  # Will need repo_id lookup
        repo = next((r for r in repos if r.repo_id == repo_id), None)

        if repo is None:
            raise ValueError(f"Repository not found: {repo_id}")

        # Get branches
        repo.branches = self.get_branches(repo_id)

        # Get repository metadata from repository.json
        metadata = self.get_repository_metadata(repo_id)
        if metadata:
            repo.team_name = metadata.team_name
            repo.service_name = metadata.service_name

        # Get commits
        if include_commits:
            since = datetime.utcnow() - timedelta(days=commit_since_days)
            repo.commits = self.get_commits(
                repo_id,
                since=since,
                limit=commit_limit
            )

        # Get PRs
        if include_prs:
            repo.pull_requests = self.get_pull_requests(repo_id, status="all")

        # Get file tree
        if include_file_tree:
            repo.file_tree = self.get_file_tree(repo_id)

        return repo
