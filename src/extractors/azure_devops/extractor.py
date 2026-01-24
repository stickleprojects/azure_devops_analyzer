"""
Azure DevOps repository extractor implementation.
"""

import os
from datetime import datetime
from typing import Optional

from azure.devops.v7_1.git.models import (
    GitPullRequestSearchCriteria,
    GitQueryCommitsCriteria,
)

from src.config.azure_devops import AzureDevOpsExtractorConfig
from src.extractors.azure_devops.client import get_git_client, get_core_client
from src.extractors.base import (
    Platform,
    RepositoryExtractor,
    OrganizationData,
    ProjectData,
    RepositoryData,
    BranchData,
    CommitData,
    PullRequestData,
    PRReviewData,
    PRCommentData,
    ContributorData,
    FileTreeItem,
)


class AzureDevOpsExtractor(RepositoryExtractor):
    """Extractor for Azure DevOps repositories."""

    def __init__(self, config: Optional[AzureDevOpsExtractorConfig] = None):
        self.config = config or AzureDevOpsExtractorConfig.from_env()
        self._git_client = None
        self._core_client = None
        self._org_url = self.config.org_url or ""

    @property
    def git_client(self):
        if self._git_client is None:
            self._git_client = get_git_client(self.config)
        return self._git_client

    @property
    def core_client(self):
        if self._core_client is None:
            self._core_client = get_core_client(self.config)
        return self._core_client

    @property
    def platform(self) -> Platform:
        return Platform.AZURE_DEVOPS

    def get_organizations(self) -> list[OrganizationData]:
        """Return the configured organization."""
        org_name = self._org_url.rstrip("/").split("/")[-1]
        return [
            OrganizationData(
                name=org_name,
                url=self._org_url,
                platform=Platform.AZURE_DEVOPS,
            )
        ]

    def get_projects(self, organization: str) -> list[ProjectData]:
        """List all projects in the organization."""
        projects = self.core_client.get_projects()
        return [
            ProjectData(
                name=p.name,
                description=p.description,
                organization_name=organization,
            )
            for p in projects
        ]

    def get_repositories(
        self,
        organization: str,
        project: Optional[str] = None
    ) -> list[RepositoryData]:
        """List repositories, optionally filtered by project."""
        if project:
            repos = self.git_client.get_repositories(project=project)
        else:
            # Get repos from all projects
            repos = []
            projects = self.core_client.get_projects()
            for p in projects:
                project_repos = self.git_client.get_repositories(project=p.name)
                repos.extend(project_repos)

        return [
            RepositoryData(
                repo_id=str(r.id),
                name=r.name,
                url=r.web_url or r.remote_url,
                default_branch=self._normalize_branch(r.default_branch),
                platform=Platform.AZURE_DEVOPS,
                project_name=r.project.name if r.project else None,
                organization_name=organization,
                created_at=None,  # Azure DevOps doesn't expose this directly
            )
            for r in repos
        ]

    def get_branches(self, repo_id: str) -> list[BranchData]:
        """Get all branches for a repository."""
        branches = self.git_client.get_branches(repository_id=repo_id)
        return [
            BranchData(
                name=self._normalize_branch(b.name),
                latest_commit_sha=b.commit.commit_id if b.commit else "",
                created_at=None,
            )
            for b in branches
        ]

    def get_languages(self, repo_id: str) -> list["LanguageData"]:
        """
        Get programming language statistics for a repository.
        
        Note: Azure DevOps REST API does not provide built-in language statistics.
        This implementation uses heuristics based on common project files and
        file extensions to estimate language usage.
        """
        from src.extractors.base import LanguageData
        
        # Get file tree
        files = self.get_file_tree(repo_id)
        if not files:
            return []
        
        # Count files by language
        language_counts: dict[str, int] = {}
        
        for file_item in files:
            if file_item.is_directory:
                continue
            
            path = file_item.path.lower()
            filename = os.path.basename(path)
            
            # Check for project/configuration files (weighted higher)
            if filename in self._PROJECT_FILE_MAP:
                lang = self._PROJECT_FILE_MAP[filename]
                language_counts[lang] = language_counts.get(lang, 0) + 10
            
            # Check file extensions
            elif "." in filename:
                ext = filename.rsplit(".", 1)[-1]
                if ext in self._EXTENSION_MAP:
                    lang = self._EXTENSION_MAP[ext]
                    language_counts[lang] = language_counts.get(lang, 0) + 1
        
        if not language_counts:
            return []
        
        # Convert counts to LanguageData with percentages
        total_count = sum(language_counts.values())
        languages = []
        
        for lang, count in language_counts.items():
            # Estimate byte count (rough approximation)
            byte_count = count * 1000  # Assume average file size
            percentage = round((count / total_count) * 100, 2)
            
            languages.append(
                LanguageData(
                    language=lang,
                    byte_count=byte_count,
                    percentage=percentage,
                )
            )
        
        # Sort by byte count descending
        languages.sort(key=lambda x: x.byte_count, reverse=True)
        return languages
    
    # Language detection mappings
    _PROJECT_FILE_MAP = {
        # .NET
        ".csproj": "C#",
        ".vbproj": "Visual Basic .NET",
        ".fsproj": "F#",
        "packages.config": "C#",
        
        # Python
        "requirements.txt": "Python",
        "setup.py": "Python",
        "pyproject.toml": "Python",
        "pipfile": "Python",
        "poetry.lock": "Python",
        
        # JavaScript/TypeScript
        "package.json": "JavaScript",
        "tsconfig.json": "TypeScript",
        "yarn.lock": "JavaScript",
        "package-lock.json": "JavaScript",
        
        # Java
        "pom.xml": "Java",
        "build.gradle": "Java",
        "build.gradle.kts": "Kotlin",
        "settings.gradle": "Java",
        
        # Ruby
        "gemfile": "Ruby",
        "gemfile.lock": "Ruby",
        
        # Go
        "go.mod": "Go",
        "go.sum": "Go",
        
        # Rust
        "cargo.toml": "Rust",
        "cargo.lock": "Rust",
        
        # PHP
        "composer.json": "PHP",
        "composer.lock": "PHP",
        
        # Others
        "makefile": "Makefile",
        "dockerfile": "Dockerfile",
        "vagrantfile": "Ruby",
    }
    
    _EXTENSION_MAP = {
        # Programming languages
        "cs": "C#",
        "vb": "Visual Basic .NET",
        "fs": "F#",
        "py": "Python",
        "js": "JavaScript",
        "jsx": "JavaScript",
        "ts": "TypeScript",
        "tsx": "TypeScript",
        "java": "Java",
        "kt": "Kotlin",
        "rb": "Ruby",
        "go": "Go",
        "rs": "Rust",
        "php": "PHP",
        "c": "C",
        "cpp": "C++",
        "cc": "C++",
        "cxx": "C++",
        "h": "C",
        "hpp": "C++",
        "swift": "Swift",
        "m": "Objective-C",
        "mm": "Objective-C++",
        "scala": "Scala",
        "clj": "Clojure",
        "ex": "Elixir",
        "exs": "Elixir",
        "erl": "Erlang",
        "hrl": "Erlang",
        "hs": "Haskell",
        "lua": "Lua",
        "pl": "Perl",
        "r": "R",
        "dart": "Dart",
        
        # Web/Markup
        "html": "HTML",
        "htm": "HTML",
        "css": "CSS",
        "scss": "SCSS",
        "sass": "Sass",
        "less": "Less",
        "vue": "Vue",
        
        # Data/Config
        "json": "JSON",
        "xml": "XML",
        "yaml": "YAML",
        "yml": "YAML",
        "toml": "TOML",
        
        # Shell
        "sh": "Shell",
        "bash": "Shell",
        "ps1": "PowerShell",
        "psm1": "PowerShell",
        
        # SQL
        "sql": "SQL",
    }

    def get_commits(
        self,
        repo_id: str,
        branch: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> list[CommitData]:
        """Get commits for a repository."""
        search_criteria = GitQueryCommitsCriteria()

        if branch:
            search_criteria.item_version = {"version": branch, "versionType": "branch"}
        if since:
            search_criteria.from_date = since.isoformat()
        if until:
            search_criteria.to_date = until.isoformat()
        if limit:
            search_criteria.top = limit

        commits = self.git_client.get_commits(
            repository_id=repo_id,
            search_criteria=search_criteria,
        )

        return [
            CommitData(
                sha=c.commit_id,
                message=c.comment or "",
                author_email=c.author.email if c.author else "",
                author_name=c.author.name if c.author else None,
                committer_email=c.committer.email if c.committer else "",
                committer_name=c.committer.name if c.committer else None,
                commit_date=c.author.date if c.author else datetime.utcnow(),
                parent_shas=[p for p in (c.parents or [])],
                files_changed=c.change_counts.get("Edit", 0) if c.change_counts else None,
                lines_added=None,  # Requires additional API call
                lines_removed=None,
            )
            for c in commits
        ]

    def get_pull_requests(
        self,
        repo_id: str,
        status: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> list[PullRequestData]:
        """Get pull requests with reviews and comments."""
        search_criteria = GitPullRequestSearchCriteria()

        if status == "open":
            search_criteria.status = "active"
        elif status == "merged":
            search_criteria.status = "completed"
        elif status == "closed":
            search_criteria.status = "abandoned"
        # "all" or None returns all statuses

        prs = self.git_client.get_pull_requests(
            repository_id=repo_id,
            search_criteria=search_criteria,
        )

        result = []
        for pr in prs:
            # Get reviews (votes)
            reviews = self._get_pr_reviews(repo_id, pr.pull_request_id)

            # Get comments
            comments = self._get_pr_comments(repo_id, pr.pull_request_id)

            # Map Azure status to standard status
            pr_status = self._map_pr_status(pr.status)

            result.append(
                PullRequestData(
                    pr_number=pr.pull_request_id,
                    platform_pr_id=str(pr.pull_request_id),
                    title=pr.title or "",
                    description=pr.description,
                    source_branch=self._normalize_branch(pr.source_ref_name),
                    target_branch=self._normalize_branch(pr.target_ref_name),
                    author_email=pr.created_by.unique_name if pr.created_by else "",
                    author_name=pr.created_by.display_name if pr.created_by else None,
                    status=pr_status,
                    created_at=pr.creation_date or datetime.utcnow(),
                    updated_at=None,
                    merged_at=pr.closed_date if pr_status == "merged" else None,
                    closed_at=pr.closed_date,
                    reviews=reviews,
                    comments=comments,
                )
            )

        return result

    def _get_pr_reviews(self, repo_id: str, pr_id: int) -> list[PRReviewData]:
        """Get reviews (votes) for a pull request."""
        try:
            reviewers = self.git_client.get_pull_request_reviewers(
                repository_id=repo_id,
                pull_request_id=pr_id,
            )
        except Exception:
            return []

        reviews = []
        for r in reviewers:
            if r.vote != 0:  # Only include actual votes
                state = self._map_vote_to_state(r.vote)
                reviews.append(
                    PRReviewData(
                        reviewer_email=r.unique_name or "",
                        reviewer_name=r.display_name,
                        review_date=datetime.utcnow(),  # Azure doesn't expose vote date
                        state=state,
                        is_required=r.is_required or False,
                    )
                )

        return reviews

    def _get_pr_comments(self, repo_id: str, pr_id: int) -> list[PRCommentData]:
        """Get comments for a pull request."""
        try:
            threads = self.git_client.get_threads(
                repository_id=repo_id,
                pull_request_id=pr_id,
            )
        except Exception:
            return []

        comments = []
        for thread in threads:
            for c in (thread.comments or []):
                if c.comment_type == "system":
                    continue  # Skip system comments

                comments.append(
                    PRCommentData(
                        author_email=c.author.unique_name if c.author else "",
                        author_name=c.author.display_name if c.author else None,
                        content=c.content or "",
                        published_date=c.published_date or datetime.utcnow(),
                        thread_id=str(thread.id) if thread.id else None,
                        file_path=thread.thread_context.file_path if thread.thread_context else None,
                        line_number=thread.thread_context.right_file_start.line if thread.thread_context and thread.thread_context.right_file_start else None,
                        comment_type="text",
                    )
                )

        return comments

    def get_file_tree(
        self,
        repo_id: str,
        branch: Optional[str] = None
    ) -> list[FileTreeItem]:
        """Get the file tree for a repository."""
        version_descriptor = None
        if branch:
            version_descriptor = {"version": branch, "versionType": "branch"}

        try:
            items = self.git_client.get_items(
                repository_id=repo_id,
                scope_path="/",
                recursion_level="full",
                version_descriptor=version_descriptor,
            )
        except Exception:
            return []

        return [
            FileTreeItem(
                path=item.path,
                is_directory=item.is_folder or False,
                size=item.size if hasattr(item, 'size') else None,
            )
            for item in items
            if item.path != "/"
        ]

    def get_file_content(
        self,
        repo_id: str,
        file_path: str,
        branch: Optional[str] = None
    ) -> Optional[str]:
        """Get the content of a specific file."""
        version_descriptor = None
        if branch:
            version_descriptor = {"version": branch, "versionType": "branch"}

        try:
            stream = self.git_client.get_item_content(
                repository_id=repo_id,
                path=file_path,
                version_descriptor=version_descriptor,
            )
            content = b"".join(stream).decode("utf-8")
            return content
        except Exception:
            return None

    @staticmethod
    def _normalize_branch(ref_name: Optional[str]) -> str:
        """Remove refs/heads/ prefix from branch name."""
        if not ref_name:
            return ""
        return ref_name.replace("refs/heads/", "")

    @staticmethod
    def _map_pr_status(azure_status: str) -> str:
        """Map Azure DevOps PR status to standard status."""
        mapping = {
            "active": "open",
            "completed": "merged",
            "abandoned": "closed",
        }
        return mapping.get(azure_status, azure_status)

    @staticmethod
    def _map_vote_to_state(vote: int) -> str:
        """Map Azure DevOps vote to review state."""
        if vote == 10:
            return "approved"
        elif vote == 5:
            return "commented"  # Approved with suggestions
        elif vote == -5:
            return "changes_requested"  # Wait for author
        elif vote == -10:
            return "changes_requested"  # Rejected
        else:
            return "commented"
