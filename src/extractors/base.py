"""
Base classes and data models for repository extractors.

All platform-specific extractors must implement the RepositoryExtractor interface
and return data using these standardized data classes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, UTC
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
class DependencyData:
    """Dependency information extracted from manifest files."""
    package_name: str
    ecosystem: str  # pypi, npm, maven, nuget, go, rubygems, cargo
    version: Optional[str] = None
    is_dev_dependency: bool = False
    source_file: str = ""
    version_constraint: Optional[str] = None


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
class LanguageData:
    """Programming language statistics for a repository."""
    language: str
    byte_count: int
    percentage: Optional[float] = None


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
    is_verified: Optional[bool] = None  # GPG signature verification
    verification_reason: Optional[str] = None  # Reason if verification failed


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
    author_email: Optional[str]
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
class ManifestFileData:
    """Manifest file content and metadata for dependency analysis."""
    file_path: str  # Path within repository (e.g., "requirements.txt", "src/package.json")
    content: str  # File content with normalized line endings (LF)
    ecosystem: Optional[str] = None  # Ecosystem hint (pypi, npm, maven, etc.)


@dataclass
class ReadmeData:
    """README file content and metadata."""
    file_path: str
    content: str
    branch: Optional[str] = None
    word_count: Optional[int] = None
    analyzed_at: Optional[datetime] = None

    # Scope and context information
    scope_type: Optional[str] = None  # repository, module, package, component
    scope_path: Optional[str] = None  # directory path this README covers
    parent_readme_path: Optional[str] = None  # path to parent README
    affects_paths: Optional[list[str]] = None  # paths this README documents


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
    
    # Security and code quality metrics
    is_private: Optional[bool] = None
    is_archived: Optional[bool] = None
    repository_size: Optional[int] = None  # Size in KB
    open_issues_count: Optional[int] = None
    license_name: Optional[str] = None
    license_key: Optional[str] = None
    has_vulnerability_alerts: Optional[bool] = None
    has_secret_scanning: Optional[bool] = None
    has_dependabot_alerts: Optional[bool] = None
    pushed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    branches: list[BranchData] = field(default_factory=list)
    commits: list[CommitData] = field(default_factory=list)
    pull_requests: list[PullRequestData] = field(default_factory=list)
    file_tree: list[FileTreeItem] = field(default_factory=list)
    readme_files: list[ReadmeData] = field(default_factory=list)


class RepositoryExtractor(ABC):
    """
    Abstract base class for repository data extraction.

    Each platform (Azure DevOps, GitHub) implements this interface
    to provide a consistent API for data extraction.
    """

    def __init__(self):
        self._cache: dict = {}
        self._cache_hits: int = 0
        self._cache_misses: int = 0
        self._cache_method_stats: dict[str, dict[str, int]] = {}

    def clear_cache(self) -> None:
        """Reset the instance cache and counters."""
        self._cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        self._cache_method_stats.clear()

    @property
    def cache_stats(self) -> dict:
        """Return cache hit/miss/size statistics."""
        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "size": len(self._cache),
            "methods": dict(self._cache_method_stats),
        }

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
    def get_repository(self, repo_id: str) -> RepositoryData:
        """
        Get a specific repository by ID.

        Args:
            repo_id: Repository identifier (e.g., 'owner/name' for GitHub).

        Returns:
            Repository metadata for the specified repository.

        Raises:
            ValueError: If repository not found.
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
    def get_languages(self, repo_id: str) -> list[LanguageData]:
        """
        Get programming language statistics for a repository.

        Args:
            repo_id: Repository identifier.

        Returns:
            List of language data with byte counts and percentages.
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

    def extract_manifests(
        self,
        repo_id: str,
        branch: Optional[str] = None
    ) -> list[ManifestFileData]:
        """
        Extract manifest files from a repository for dependency analysis.
        
        Searches the repository file tree for known dependency manifest files
        (requirements.txt, package.json, pom.xml, *.csproj, etc.) and retrieves
        their contents with normalized line endings (LF).
        
        Args:
            repo_id: Repository identifier.
            branch: Branch to scan (defaults to default branch).
        
        Returns:
            List of manifest files with content and metadata.
        """
        from fnmatch import fnmatch
        
        # Known manifest file patterns
        # These match the SUPPORTED_FILES from all parsers
        manifest_patterns = [
            # Python
            "requirements.txt",
            "*requirements*.txt",  # requirements-dev.txt, dev-requirements.txt, etc.
            "pyproject.toml",
            "Pipfile",
            "Pipfile.lock",
            # Node.js
            "package.json",
            "package-lock.json",
            "yarn.lock",
            # Java
            "pom.xml",
            "build.gradle",
            "build.gradle.kts",
            # .NET
            "*.csproj",
            "*.vbproj",
            "*.fsproj",
            "packages.config",
            # Go
            "go.mod",
            "go.sum",
            # Ruby
            "Gemfile",
            "Gemfile.lock",
            # Rust
            "Cargo.toml",
            "Cargo.lock",
        ]
        
        file_tree = self.get_file_tree(repo_id, branch)
        manifest_files = []
        
        for item in file_tree:
            if item.is_directory:
                continue
            
            file_name = item.path.split('/')[-1]
            
            # Check if this file matches any manifest pattern
            is_manifest = any(
                fnmatch(file_name, pattern)
                for pattern in manifest_patterns
            )
            
            if is_manifest:
                content = self.get_file_content(repo_id, item.path, branch)
                if content:
                    # Normalize line endings to LF (Unix style)
                    # This ensures consistent parsing across Windows/Linux environments
                    normalized_content = content.replace('\r\n', '\n').replace('\r', '\n')
                    
                    manifest_files.append(
                        ManifestFileData(
                            file_path=item.path,
                            content=normalized_content,
                            ecosystem=self._infer_ecosystem(file_name)
                        )
                    )
        
        return manifest_files

    @staticmethod
    def _infer_ecosystem(file_name: str) -> Optional[str]:
        """
        Infer the ecosystem from the manifest file name.
        
        Args:
            file_name: Name of the manifest file.
        
        Returns:
            Ecosystem identifier (pypi, npm, maven, etc.) or None.
        """
        ecosystem_map = {
            "requirements.txt": "pypi",
            "pyproject.toml": "pypi",
            "Pipfile": "pypi",
            "package.json": "npm",
            "pom.xml": "maven",
            ".csproj": "nuget",
            ".vbproj": "nuget",
            ".fsproj": "nuget",
            "packages.config": "nuget",
            "go.mod": "go",
            "Gemfile": "rubygems",
            "Cargo.toml": "cargo",
        }
        
        # Exact match
        if file_name in ecosystem_map:
            return ecosystem_map[file_name]
        
        # Check file extensions
        if file_name.endswith((".csproj", ".vbproj", ".fsproj")):
            return "nuget"
        
        # Check patterns for Python requirements
        if "requirements" in file_name.lower() and file_name.endswith(".txt"):
            return "pypi"
        
        return None

    def get_readme_files(
        self,
        repo_id: str,
        branch: Optional[str] = None
    ) -> list[ReadmeData]:
        """
        Find and extract README files from a repository with scope detection.

        Args:
            repo_id: Repository identifier.
            branch: Branch to scan (defaults to default branch).

        Returns:
            List of README files found with scope context.
        """
        readme_patterns = [
            "README.md", "README.rst", "README.txt", "README",
            "readme.md", "readme.rst", "readme.txt", "readme",
            "Readme.md", "Readme.rst", "Readme.txt", "Readme"
        ]

        file_tree = self.get_file_tree(repo_id, branch)
        readme_files = []

        # First pass: collect all README files
        for item in file_tree:
            if not item.is_directory:
                file_name = item.path.split('/')[-1]
                if file_name in readme_patterns:
                    content = self.get_file_content(repo_id, item.path, branch)
                    if content:
                        readme_files.append(
                            ReadmeData(
                                file_path=item.path,
                                content=content,
                                branch=branch,
                                word_count=len(content.split()),
                                analyzed_at=datetime.now(UTC)
                            )
                        )

        # Second pass: analyze scope and relationships
        self._analyze_readme_scopes(readme_files, file_tree)

        return readme_files

    def _analyze_readme_scopes(
        self,
        readme_files: list[ReadmeData],
        file_tree: list[FileTreeItem]
    ) -> None:
        """
        Analyze scope and hierarchical relationships between README files.

        Args:
            readme_files: List of README files to analyze.
            file_tree: Complete file tree for context.
        """
        # Create directory structure map
        directories = set()
        for item in file_tree:
            if item.is_directory:
                directories.add(item.path)
            else:
                # Add all parent directories
                path_parts = item.path.split('/')[:-1]
                for i in range(len(path_parts)):
                    dir_path = '/'.join(path_parts[:i+1])
                    if dir_path:
                        directories.add(dir_path)

        # Sort README files by path depth (root first)
        readme_files.sort(key=lambda r: len(r.file_path.split('/')))

        # Analyze each README file
        for readme in readme_files:
            self._determine_readme_scope(readme, readme_files, directories)

    def _determine_readme_scope(
        self,
        readme: ReadmeData,
        all_readmes: list[ReadmeData],
        directories: set[str]
    ) -> None:
        """
        Determine the scope and context for a single README file.

        Args:
            readme: README file to analyze.
            all_readmes: All README files for context.
            directories: Set of all directories in the repository.
        """
        path = readme.file_path
        path_parts = path.split('/')

        # Determine scope path (directory containing the README)
        if len(path_parts) == 1:
            # Root README
            readme.scope_path = "/"
            readme.scope_type = "repository"
        else:
            # README in subdirectory
            readme.scope_path = '/'.join(path_parts[:-1])
            readme.scope_type = self._classify_scope_type(readme.scope_path, directories)

        # Find parent README (closest README in parent directories)
        readme.parent_readme_path = self._find_parent_readme(readme, all_readmes)

        # Determine affected paths (what this README documents)
        readme.affects_paths = self._calculate_affected_paths(readme, directories)

    def _classify_scope_type(self, scope_path: str, directories: set[str]) -> str:
        """
        Classify the type of scope based on directory structure.

        Args:
            scope_path: Directory path of the README.
            directories: Set of all directories.

        Returns:
            Scope type: repository, module, package, or component.
        """
        path_parts = scope_path.split('/')
        path_lower = scope_path.lower()

        # Package patterns (usually have multiple subdirectories)
        package_indicators = ['packages', 'libs', 'modules', 'components']
        if any(indicator in path_lower for indicator in package_indicators):
            return "package"

        # Module patterns (organized by functionality)
        module_indicators = ['src', 'lib', 'app', 'core', 'services', 'api', 'web', 'backend', 'frontend']
        if any(indicator in path_lower for indicator in module_indicators):
            return "module"

        # Component patterns (specific features or utilities)
        component_indicators = ['utils', 'helpers', 'tools', 'scripts', 'configs', 'tests', 'docs']
        if any(indicator in path_lower for indicator in component_indicators):
            return "component"

        # Depth-based classification
        if len(path_parts) >= 3:
            return "component"
        elif len(path_parts) == 2:
            return "module"
        else:
            return "repository"

    def _find_parent_readme(self, readme: ReadmeData, all_readmes: list[ReadmeData]) -> Optional[str]:
        """
        Find the parent README file (in a parent directory).

        Args:
            readme: Current README file.
            all_readmes: All README files to search.

        Returns:
            Path to parent README, or None if no parent found.
        """
        current_parts = readme.file_path.split('/')[:-1]  # Remove filename

        # Search for README in parent directories
        while len(current_parts) > 0:
            current_parts.pop()  # Move up one directory
            parent_dir = '/'.join(current_parts) if current_parts else ''

            # Look for README in this parent directory
            for other_readme in all_readmes:
                if other_readme.file_path == readme.file_path:
                    continue  # Skip self

                other_dir = '/'.join(other_readme.file_path.split('/')[:-1])
                if other_dir == parent_dir:
                    return other_readme.file_path

        return None

    def _calculate_affected_paths(self, readme: ReadmeData, directories: set[str]) -> list[str]:
        """
        Calculate which paths/directories this README documents.

        Args:
            readme: README file to analyze.
            directories: Set of all directories.

        Returns:
            List of paths this README covers.
        """
        if readme.scope_type == "repository":
            return ["/"]

        scope_path = readme.scope_path
        affected_paths = [scope_path]

        # Add all subdirectories under the scope path
        for directory in directories:
            if directory.startswith(scope_path + '/'):
                affected_paths.append(directory)

        return affected_paths

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
