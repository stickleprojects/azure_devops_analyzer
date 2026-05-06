"""
Azure DevOps repository extractor implementation.

API Limitations (vs GitHub):
- CommitData.lines_added/lines_removed: Not available. The Azure DevOps API only
  provides file change type counts (Edit/Add/Delete), not line-level statistics.
  Getting line counts would require fetching full diffs per commit.
- PullRequestData.lines_added/lines_removed: Not available from the iterations API.
  Only file count can be determined from iteration changes.
- PRReviewData.review_date: Azure DevOps does not expose vote timestamps on reviewers.
  As a defensible fallback the PR's merged/closed/created date is used so that stale
  reviews from old PRs do not appear as current activity.
"""

import logging
import os
import time
from datetime import datetime
from typing import Optional

from azure.devops.exceptions import AzureDevOpsServiceError
from azure.devops.v7_1.git.models import (
    GitPullRequestSearchCriteria,
    GitQueryCommitsCriteria,
    GitVersionDescriptor,
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
    FileTreeItem,
    LanguageData,
)
from src.extractors.cache import cached


class AzureDevOpsExtractor(RepositoryExtractor):
    """Extractor for Azure DevOps repositories."""

    def __init__(self, config: Optional[AzureDevOpsExtractorConfig] = None):
        super().__init__()
        self.config = config or AzureDevOpsExtractorConfig.from_env()
        self._git_client = None
        self._core_client = None
        self._org_url = self.config.org_url or ""
        self._logger = logging.getLogger(__name__)

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

    # ── Rate Limiting ─────────────────────────────────────────────────

    def _api_call_with_retry(self, api_callable, *args, **kwargs):
        """
        Execute an Azure DevOps API call with retry and exponential backoff.

        Retries on HTTP 429 (throttled) responses up to config.max_retries times.
        """
        last_exception = None
        for attempt in range(self.config.max_retries + 1):
            try:
                return api_callable(*args, **kwargs)
            except AzureDevOpsServiceError as e:
                last_exception = e
                if self._is_throttled(e) and attempt < self.config.max_retries:
                    sleep_time = min(
                        self.config.backoff_seconds * (2 ** attempt),
                        self.config.max_backoff_seconds,
                    )
                    self._logger.warning(
                        "Azure DevOps API throttled (attempt %d/%d), sleeping %.1fs",
                        attempt + 1, self.config.max_retries, sleep_time,
                    )
                    time.sleep(sleep_time)
                else:
                    raise
        raise last_exception

    @staticmethod
    def _is_throttled(exc: AzureDevOpsServiceError) -> bool:
        """Detect Azure DevOps rate limit (HTTP 429) responses."""
        status_code = getattr(exc, "status_code", None)
        if status_code == 429:
            return True
        inner = getattr(exc, "inner_exception", None)
        if inner and getattr(inner, "status_code", None) == 429:
            return True
        return False

    # ── Organizations & Projects ──────────────────────────────────────

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
        projects = self._api_call_with_retry(self.core_client.get_projects)
        return [
            ProjectData(
                name=p.name,
                description=p.description,
                organization_name=organization,
            )
            for p in projects
        ]

    # ── Repositories ──────────────────────────────────────────────────

    def get_repositories(
        self,
        organization: str,
        project: Optional[str] = None
    ) -> list[RepositoryData]:
        """List repositories, optionally filtered by project."""
        if project:
            repos = self._api_call_with_retry(
                self.git_client.get_repositories, project=project
            )
        else:
            repos = []
            projects = self._api_call_with_retry(self.core_client.get_projects)
            for p in projects:
                project_repos = self._api_call_with_retry(
                    self.git_client.get_repositories, project=p.name
                )
                repos.extend(project_repos)

        return [self._build_repository_data(r, organization) for r in repos]

    def get_repository(self, repo_id: str) -> RepositoryData:
        """Get a specific repository by ID."""
        try:
            repo = self._api_call_with_retry(
                self.git_client.get_repository, repository_id=repo_id
            )
            org_name = self._org_url.rstrip("/").split("/")[-1]
            return self._build_repository_data(repo, org_name)
        except Exception as e:
            raise ValueError(f"Repository {repo_id} not found: {e}")

    def _build_repository_data(self, repo, organization: str) -> RepositoryData:
        """Build RepositoryData from an Azure DevOps GitRepository object."""
        return RepositoryData(
            repo_id=str(repo.id),
            name=repo.name,
            url=repo.web_url or repo.remote_url,
            default_branch=self._normalize_branch(repo.default_branch),
            platform=Platform.AZURE_DEVOPS,
            platform_repo_id=None,
            project_name=repo.project.name if repo.project else None,
            organization_name=organization,
            created_at=None,
            is_private=self._infer_visibility(repo),
            is_archived=getattr(repo, "is_disabled", None),
            repository_size=getattr(repo, "size", None),
            open_issues_count=None,  # Requires WorkItem API (different client)
            license_name=None,  # Not available in Azure DevOps API
            license_key=None,
            has_vulnerability_alerts=None,  # GitHub-specific
            has_secret_scanning=None,  # GitHub-specific
            has_dependabot_alerts=None,  # GitHub-specific
            pushed_at=None,  # Not directly available
            updated_at=None,  # Not directly available
        )

    @staticmethod
    def _infer_visibility(repo) -> Optional[bool]:
        """
        Infer repository privacy from project visibility.

        Azure DevOps repos inherit visibility from their project.
        Project visibility: 0=private, 1=organization, 2=public.
        """
        if repo.project:
            visibility = getattr(repo.project, "visibility", None)
            if visibility is not None:
                return visibility != 2  # True if not public
        return None

    # ── Branches ──────────────────────────────────────────────────────

    @cached
    def get_branches(self, repo_id: str) -> list[BranchData]:
        """Get all branches for a repository."""
        branches = self._api_call_with_retry(
            self.git_client.get_branches, repository_id=repo_id
        )
        return [
            BranchData(
                name=self._normalize_branch(b.name),
                latest_commit_sha=b.commit.commit_id if b.commit else "",
                created_at=None,
            )
            for b in branches
        ]

    # ── Languages ─────────────────────────────────────────────────────

    @cached
    def get_languages(self, repo_id: str) -> list[LanguageData]:
        """
        Get programming language statistics for a repository.

        Note: Azure DevOps REST API does not provide built-in language statistics.
        This implementation uses heuristics based on common project files and
        file extensions to estimate language usage.
        """
        files = self.get_file_tree(repo_id)
        if not files:
            return []

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

        total_count = sum(language_counts.values())
        languages = []

        for lang, count in language_counts.items():
            byte_count = count * 1000  # Rough approximation
            percentage = round((count / total_count) * 100, 2)
            languages.append(
                LanguageData(
                    language=lang,
                    byte_count=byte_count,
                    percentage=percentage,
                )
            )

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

    # ── Commits ───────────────────────────────────────────────────────

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
            search_criteria.item_version = GitVersionDescriptor(
                version=branch, version_type="branch"
            )
        if since:
            search_criteria.from_date = since.isoformat()
        if until:
            search_criteria.to_date = until.isoformat()
        if limit:
            search_criteria.top = limit

        commits = self._api_call_with_retry(
            self.git_client.get_commits,
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
                files_changed=(
                    sum(c.change_counts.values()) if c.change_counts else None
                ),
                lines_added=None,  # Not available from Azure DevOps API
                lines_removed=None,  # Would require fetching full diffs
            )
            for c in commits
        ]

    # ── Pull Requests ─────────────────────────────────────────────────

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

        prs = self._api_call_with_retry(
            self.git_client.get_pull_requests,
            repository_id=repo_id,
            search_criteria=search_criteria,
        )

        result = []
        for pr in prs:
            pr_status = self._map_pr_status(pr.status)

            # Determine timestamps first so they can be used as review_date fallback
            created_at = pr.creation_date or datetime.utcnow()
            closed_date = pr.closed_date

            if pr_status == "merged":
                merged_at = (
                    getattr(pr, "completion_queue_time", None) or closed_date
                )
                closed_at = closed_date
            elif pr_status == "closed":
                merged_at = None
                closed_at = closed_date
            else:
                merged_at = None
                closed_at = None

            updated_at = closed_date or created_at

            # Use the most precise available PR date as a fallback for review_date.
            # Azure DevOps does not expose per-reviewer vote timestamps, so we use
            # merged_at > closed_at > created_at to avoid assigning "now" to old PRs.
            review_date_fallback = merged_at or closed_at or created_at

            # Get reviews and comments in one pass (avoids duplicate get_threads call)
            reviews, comments = self._get_pr_reviews_and_comments(
                repo_id, pr.pull_request_id, review_date_fallback
            )

            # Get file metrics if enabled
            files_changed, lines_added, lines_removed = self._get_pr_file_metrics(
                repo_id, pr.pull_request_id
            )

            result.append(
                PullRequestData(
                    pr_number=pr.pull_request_id,
                    platform_pr_id=str(pr.pull_request_id),
                    title=pr.title or "",
                    description=pr.description,
                    source_branch=self._normalize_branch(pr.source_ref_name),
                    target_branch=self._normalize_branch(pr.target_ref_name),
                    author_email=(
                        pr.created_by.unique_name if pr.created_by else ""
                    ),
                    author_name=(
                        pr.created_by.display_name if pr.created_by else None
                    ),
                    status=pr_status,
                    created_at=created_at,
                    updated_at=updated_at,
                    merged_at=merged_at,
                    closed_at=closed_at,
                    files_changed=files_changed,
                    lines_added=lines_added,
                    lines_removed=lines_removed,
                    reviews=reviews,
                    comments=comments,
                )
            )

        return result

    def _get_pr_file_metrics(
        self, repo_id: str, pr_id: int
    ) -> tuple[int, int, int]:
        """
        Get file change count for a pull request via the iterations API.

        Returns (files_changed, lines_added, lines_removed).
        lines_added/lines_removed are always 0 (not available from this API).
        """
        if not self.config.fetch_pr_file_metrics:
            return (0, 0, 0)

        try:
            iterations = self._api_call_with_retry(
                self.git_client.get_pull_request_iterations,
                repository_id=repo_id,
                pull_request_id=pr_id,
            )

            if not iterations:
                return (0, 0, 0)

            last_iteration_id = iterations[-1].id

            changes = self._api_call_with_retry(
                self.git_client.get_pull_request_iteration_changes,
                repository_id=repo_id,
                pull_request_id=pr_id,
                iteration_id=last_iteration_id,
            )

            files_changed = 0
            if changes and hasattr(changes, "change_entries") and changes.change_entries:
                files_changed = len(changes.change_entries)

            return (files_changed, 0, 0)

        except Exception as e:
            self._logger.debug("Failed to get PR %d file metrics: %s", pr_id, e)
            return (0, 0, 0)

    def _get_pr_reviews_and_comments(
        self, repo_id: str, pr_id: int, review_date_fallback: Optional[datetime] = None
    ) -> tuple[list[PRReviewData], list[PRCommentData]]:
        """
        Get reviews and comments for a PR in one pass.

        Fetches threads once, counts comments per reviewer, then builds
        both PRReviewData (with comment_count) and PRCommentData lists.
        """
        # Fetch threads (used for both comments and reviewer comment counts)
        try:
            threads = self._api_call_with_retry(
                self.git_client.get_threads,
                repository_id=repo_id,
                pull_request_id=pr_id,
            )
        except Exception:
            threads = []

        # Build comments and count per reviewer
        comments = []
        reviewer_comment_counts: dict[str, int] = {}

        for thread in threads:
            for c in (thread.comments or []):
                if c.comment_type == "system":
                    continue

                author_email = c.author.unique_name if c.author else ""
                if author_email:
                    reviewer_comment_counts[author_email] = (
                        reviewer_comment_counts.get(author_email, 0) + 1
                    )

                comments.append(
                    PRCommentData(
                        author_email=author_email,
                        author_name=(
                            c.author.display_name if c.author else None
                        ),
                        content=c.content or "",
                        published_date=c.published_date or datetime.utcnow(),
                        thread_id=str(thread.id) if thread.id else None,
                        file_path=(
                            thread.thread_context.file_path
                            if thread.thread_context else None
                        ),
                        line_number=(
                            thread.thread_context.right_file_start.line
                            if thread.thread_context
                            and thread.thread_context.right_file_start
                            else None
                        ),
                        comment_type="text",
                    )
                )

        # Build reviews with comment counts
        reviews = self._build_reviews_with_counts(
            repo_id, pr_id, reviewer_comment_counts, review_date_fallback
        )

        return reviews, comments

    def _build_reviews_with_counts(
        self,
        repo_id: str,
        pr_id: int,
        comment_counts: dict[str, int],
        review_date_fallback: Optional[datetime] = None,
    ) -> list[PRReviewData]:
        """Build review data with per-reviewer comment counts.

        Azure DevOps does not expose per-reviewer vote timestamps.
        ``review_date_fallback`` should be the most precise PR date available
        (merged_at > closed_at > created_at) so that reviews for old PRs are
        not assigned the current wall-clock time and therefore do not appear as
        recent activity in 30-day reporting views.
        """
        try:
            reviewers = self._api_call_with_retry(
                self.git_client.get_pull_request_reviewers,
                repository_id=repo_id,
                pull_request_id=pr_id,
            )
        except Exception:
            return []

        # Use the provided PR date as the review date when a real timestamp is
        # unavailable.  Fall back to utcnow() only as a last resort (e.g. for
        # open PRs that have no closed/merged date yet).
        effective_review_date = review_date_fallback or datetime.utcnow()

        reviews = []
        for r in reviewers:
            if r.vote != 0:  # Only include actual votes
                state = self._map_vote_to_state(r.vote)
                reviewer_email = r.unique_name or ""
                reviews.append(
                    PRReviewData(
                        reviewer_email=reviewer_email,
                        reviewer_name=r.display_name,
                        review_date=effective_review_date,
                        state=state,
                        is_required=r.is_required or False,
                        comment_count=comment_counts.get(reviewer_email, 0),
                    )
                )

        return reviews

    # ── File Operations ───────────────────────────────────────────────

    @cached
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
            items = self._api_call_with_retry(
                self.git_client.get_items,
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
                size=item.size if hasattr(item, "size") else None,
            )
            for item in items
            if item.path != "/"
        ]

    @cached
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
            stream = self._api_call_with_retry(
                self.git_client.get_item_content,
                repository_id=repo_id,
                path=file_path,
                version_descriptor=version_descriptor,
            )
            content = b"".join(stream).decode("utf-8")
            return content
        except Exception:
            return None

    # ── Helpers ───────────────────────────────────────────────────────

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
