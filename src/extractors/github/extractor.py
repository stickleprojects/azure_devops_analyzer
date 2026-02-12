"""
GitHub repository extractor implementation.

Key API Behavior Note:
    When fetching repositories via GitHub's REST API, there is a critical distinction:
    
    - Authenticated user endpoint (client.get_user() with no args):
      Returns ALL accessible repos including private ones.
      Use visibility="all" parameter.
      
    - Named user endpoint (client.get_user('username')):
      Returns ONLY public repos, even if the username matches the authenticated user.
      Use type="all" parameter (but still only gets public repos).
    
    This implementation detects when the requested username matches the authenticated user
    and automatically uses the authenticated endpoint to ensure private repositories are
    included in the results.
"""

import logging
import time
from datetime import datetime
from typing import Optional

from github import GithubException
from github.Repository import Repository as GHRepository

from src.extractors.github.client import (
    get_github_client,
    get_organization_name,
    get_user_name,
)
from src.config.github import GitHubExtractorConfig
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
)
from src.extractors.cache import cached


class GitHubExtractor(RepositoryExtractor):
    """Extractor for GitHub repositories."""

    def __init__(
        self,
        config: Optional[GitHubExtractorConfig] = None,
    ):
        super().__init__()
        self.config = config or GitHubExtractorConfig.from_env()
        self._client = None
        self._org_name = self.config.organization
        self._user_name = self.config.user
        self._user_email_cache: dict[str, str] = {}
        self._logger = logging.getLogger(__name__)

    @property
    def client(self):
        if self._client is None:
            self._client = get_github_client(config=self.config)
            # Ensure paginated calls use the configured page size
            try:
                self._client.per_page = self.config.page_size
            except Exception:
                pass
        return self._client

    @property
    def platform(self) -> Platform:
        return Platform.GITHUB

    def get_organizations(self) -> list[OrganizationData]:
        """Return accessible organizations."""
        orgs = []

        # Add configured organization
        if self._org_name:
            try:
                org = self.client.get_organization(self._org_name)
                orgs.append(
                    OrganizationData(
                        name=org.login,
                        url=org.html_url,
                        platform=Platform.GITHUB,
                    )
                )
            except GithubException:
                pass

        # Add authenticated user
        if self._user_name:
            try:
                user = self.client.get_user(self._user_name)
                orgs.append(
                    OrganizationData(
                        name=user.login,
                        url=user.html_url,
                        platform=Platform.GITHUB,
                    )
                )
            except GithubException:
                pass

        # If nothing configured, get current user
        if not orgs:
            user = self.client.get_user()
            orgs.append(
                OrganizationData(
                    name=user.login,
                    url=user.html_url,
                    platform=Platform.GITHUB,
                )
            )

        return orgs

    def get_projects(self, organization: str) -> list[ProjectData]:
        """
        GitHub doesn't have projects in the Azure DevOps sense.
        Return a single project representing the org/user.
        """
        return [
            ProjectData(
                name=organization,
                description=None,
                organization_name=organization,
            )
        ]

    def get_repositories(
        self,
        organization: str,
        project: Optional[str] = None,
    ) -> list[RepositoryData]:
        """List repositories for an organization or user with pagination and rate limiting."""
        repos: list[RepositoryData] = []

        gh_repos = None
        org_name = organization

        try:
            org = self.client.get_organization(organization)
            gh_repos = org.get_repos(type="all")
        except GithubException as exc:
            # Fall back to a user with the provided name
            # CRITICAL: GitHub API behavior for private repos
            # - Authenticated endpoint: client.get_user() returns ALL repos (public + private)
            # - Named user endpoint: client.get_user('name') returns ONLY public repos
            # We must detect if 'organization' is the authenticated user and use the right endpoint
            try:
                if organization:
                    # Check if requested user is the authenticated user
                    auth_user = self.client.get_user()
                    if auth_user.login.lower() == organization.lower():
                        # Use authenticated user endpoint to get ALL repos including private
                        user = auth_user
                        gh_repos = user.get_repos(visibility="all")
                    else:
                        # Different user - can only see public repos
                        user = self.client.get_user(organization)
                        gh_repos = user.get_repos(type="all")
                else:
                    # No organization specified - get authenticated user's repos
                    user = self.client.get_user()
                    gh_repos = user.get_repos(visibility="all")
                org_name = user.login
            except GithubException as inner_exc:
                self._logger.warning("Failed to list repos for %s: %s", organization, inner_exc)
                return []
            else:
                self._logger.info("Falling back to user scope for %s (%s)", organization, exc)

        paginated_repos = self._safe_paginated_list(gh_repos, limit=self.config.max_items_per_list)

        for r in paginated_repos:
            repos.append(
                RepositoryData(
                    repo_id=f"{r.owner.login}/{r.name}",
                    name=r.name,
                    url=r.html_url,
                    default_branch=r.default_branch,
                    platform=Platform.GITHUB,
                    platform_repo_id=r.id,
                    project_name=org_name,
                    organization_name=org_name,
                    created_at=r.created_at,
                    # Security and code quality metrics
                    is_private=r.private,
                    is_archived=r.archived,
                    repository_size=r.size,
                    open_issues_count=r.open_issues_count,
                    license_name=r.license.name if r.license else None,
                    license_key=r.license.key if r.license else None,
                    has_vulnerability_alerts=getattr(r.security_and_analysis, 'vulnerability_alerts', {}).get('enabled', False) if hasattr(r, 'security_and_analysis') else None,
                    has_secret_scanning=getattr(r.security_and_analysis, 'secret_scanning', {}).get('enabled', False) if hasattr(r, 'security_and_analysis') else None,
                    has_dependabot_alerts=getattr(r.security_and_analysis, 'dependabot_security_updates', {}).get('enabled', False) if hasattr(r, 'security_and_analysis') else None,
                    pushed_at=r.pushed_at,
                    updated_at=r.updated_at,
                )
            )

        return repos

    def get_repository(self, repo_id: str) -> RepositoryData:
        """
        Get a specific repository by ID.

        Args:
            repo_id: Repository identifier in format 'owner/name'.

        Returns:
            Repository metadata for the specified repository.

        Raises:
            ValueError: If repository not found.
        """
        try:
            gh_repo = self.client.get_repo(repo_id)
            
            return RepositoryData(
                repo_id=repo_id,
                name=gh_repo.name,
                url=gh_repo.html_url,
                default_branch=gh_repo.default_branch,
                platform=Platform.GITHUB,
                platform_repo_id=gh_repo.id,
                project_name=gh_repo.owner.login,
                organization_name=gh_repo.owner.login,
                created_at=gh_repo.created_at,
                is_private=gh_repo.private,
                is_archived=gh_repo.archived,
                repository_size=gh_repo.size,
                open_issues_count=gh_repo.open_issues_count,
                license_name=gh_repo.license.name if gh_repo.license else None,
                license_key=gh_repo.license.key if gh_repo.license else None,
                has_vulnerability_alerts=getattr(gh_repo.security_and_analysis, 'vulnerability_alerts', {}).get('enabled', False) if hasattr(gh_repo, 'security_and_analysis') else None,
                has_secret_scanning=getattr(gh_repo.security_and_analysis, 'secret_scanning', {}).get('enabled', False) if hasattr(gh_repo, 'security_and_analysis') else None,
                has_dependabot_alerts=getattr(gh_repo.security_and_analysis, 'dependabot_security_updates', {}).get('enabled', False) if hasattr(gh_repo, 'security_and_analysis') else None,
                pushed_at=gh_repo.pushed_at,
                updated_at=gh_repo.updated_at,
            )
        except GithubException as exc:
            raise ValueError(f"Repository not found: {repo_id}") from exc

    @cached
    def get_branches(self, repo_id: str) -> list[BranchData]:
        """Get all branches for a repository."""
        repo = self._get_repo(repo_id)
        branches = repo.get_branches()

        return [
            BranchData(
                name=b.name,
                latest_commit_sha=b.commit.sha,
                created_at=None,  # GitHub API doesn't expose branch creation date
            )
            for b in branches
        ]

    @cached
    def get_languages(self, repo_id: str) -> list["LanguageData"]:
        """
        Get programming language statistics for a repository.

        Returns language data with byte counts and percentages.
        GitHub API returns a dict of {language_name: byte_count}.
        """
        from src.extractors.base import LanguageData
        
        repo = self._get_repo(repo_id)
        
        try:
            # GitHub returns dict of {language: byte_count}
            languages_dict = repo.get_languages()
            
            if not languages_dict:
                return []
            
            # Calculate total bytes for percentage calculation
            total_bytes = sum(languages_dict.values())
            
            # Convert to list of LanguageData objects
            result = []
            for language, byte_count in languages_dict.items():
                percentage = (byte_count / total_bytes * 100) if total_bytes > 0 else 0
                result.append(
                    LanguageData(
                        language=language,
                        byte_count=byte_count,
                        percentage=round(percentage, 2)
                    )
                )
            
            # Sort by byte count descending
            result.sort(key=lambda x: x.byte_count, reverse=True)
            
            return result
            
        except Exception as e:
            self._logger.warning("Failed to get languages for %s: %s", repo_id, e)
            return []

    def get_commits(
        self,
        repo_id: str,
        branch: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> list[CommitData]:
        """Get commits for a repository."""
        repo = self._get_repo(repo_id)

        kwargs = {}
        if branch:
            kwargs["sha"] = branch
        if since:
            kwargs["since"] = since
        if until:
            kwargs["until"] = until

        commits = repo.get_commits(**kwargs)

        result = []
        for c in self._safe_paginated_list(commits, limit=limit or self.config.max_items_per_list):
            stats = c.stats if c.stats else None

            result.append(
                CommitData(
                    sha=c.sha,
                    message=c.commit.message or "",
                    author_email=c.commit.author.email if c.commit.author else "",
                    author_name=c.commit.author.name if c.commit.author else None,
                    committer_email=c.commit.committer.email if c.commit.committer else "",
                    committer_name=c.commit.committer.name if c.commit.committer else None,
                    commit_date=c.commit.author.date if c.commit.author else datetime.utcnow(),
                    parent_shas=[p.sha for p in c.parents],
                    files_changed=stats.total if stats else None,
                    lines_added=stats.additions if stats else None,
                    lines_removed=stats.deletions if stats else None,
                    is_verified=c.commit.verification.verified if c.commit.verification else None,
                    verification_reason=c.commit.verification.reason if c.commit.verification else None,
                )
            )

        return result

    def get_pull_requests(
        self,
        repo_id: str,
        status: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> list[PullRequestData]:
        """Get pull requests with reviews and comments."""
        repo = self._get_repo(repo_id)

        # Map status to GitHub state
        state = "all"
        if status == "open":
            state = "open"
        elif status in ("merged", "closed"):
            state = "closed"

        prs = repo.get_pulls(state=state, sort="updated", direction="desc")

        result = []
        for pr in self._safe_paginated_list(prs, limit=limit or self.config.max_items_per_list):
            # Filter merged vs closed if needed
            if status == "merged" and not pr.merged:
                continue
            if status == "closed" and pr.merged:
                continue

            # Get reviews
            reviews = self._get_pr_reviews(pr)

            # Get comments
            comments = self._get_pr_comments(pr)

            # Determine status
            if pr.merged:
                pr_status = "merged"
            elif pr.state == "open":
                pr_status = "open"
            else:
                pr_status = "closed"

            # Get author email (cached to avoid redundant API calls)
            author_email = ""
            author_name = None
            if pr.user:
                author_name = pr.user.login
                login = pr.user.login
                if login in self._user_email_cache:
                    author_email = self._user_email_cache[login]
                else:
                    try:
                        user = self.client.get_user(login)
                        author_email = user.email or f"{login}@users.noreply.github.com"
                    except GithubException:
                        author_email = f"{login}@users.noreply.github.com"
                    self._user_email_cache[login] = author_email

            result.append(
                PullRequestData(
                    pr_number=pr.number,
                    platform_pr_id=str(pr.id),
                    title=pr.title or "",
                    description=pr.body,
                    source_branch=pr.head.ref if pr.head else "",
                    target_branch=pr.base.ref if pr.base else "",
                    author_email=author_email,
                    author_name=author_name,
                    status=pr_status,
                    created_at=pr.created_at or datetime.utcnow(),
                    updated_at=pr.updated_at,
                    merged_at=pr.merged_at,
                    closed_at=pr.closed_at,
                    files_changed=pr.changed_files or 0,
                    lines_added=pr.additions or 0,
                    lines_removed=pr.deletions or 0,
                    reviews=reviews,
                    comments=comments,
                )
            )

        return result

    def _get_pr_reviews(self, pr) -> list[PRReviewData]:
        """Get reviews for a pull request."""
        reviews = []

        try:
            gh_reviews = pr.get_reviews()
            for r in gh_reviews:
                reviewer_email = ""
                reviewer_name = None
                if r.user:
                    reviewer_name = r.user.login
                    reviewer_email = f"{r.user.login}@users.noreply.github.com"

                reviews.append(
                    PRReviewData(
                        reviewer_email=reviewer_email,
                        reviewer_name=reviewer_name,
                        review_date=r.submitted_at or datetime.utcnow(),
                        state=self._map_review_state(r.state),
                        is_required=False,
                        comment_count=0,
                    )
                )
        except GithubException:
            pass

        return reviews

    def _get_pr_comments(self, pr) -> list[PRCommentData]:
        """Get comments for a pull request."""
        comments = []

        try:
            # Get review comments (on code)
            review_comments = pr.get_review_comments()
            for c in review_comments:
                author_email = ""
                author_name = None
                if c.user:
                    author_name = c.user.login
                    author_email = f"{c.user.login}@users.noreply.github.com"

                comments.append(
                    PRCommentData(
                        author_email=author_email,
                        author_name=author_name,
                        content=c.body or "",
                        published_date=c.created_at or datetime.utcnow(),
                        thread_id=str(c.id),
                        file_path=c.path,
                        line_number=c.line,
                        comment_type="text",
                    )
                )

            # Get issue comments (general discussion)
            issue_comments = pr.get_issue_comments()
            for c in issue_comments:
                author_email = ""
                author_name = None
                if c.user:
                    author_name = c.user.login
                    author_email = f"{c.user.login}@users.noreply.github.com"

                comments.append(
                    PRCommentData(
                        author_email=author_email,
                        author_name=author_name,
                        content=c.body or "",
                        published_date=c.created_at or datetime.utcnow(),
                        thread_id=str(c.id),
                        file_path=None,
                        line_number=None,
                        comment_type="text",
                    )
                )

        except GithubException:
            pass

        return comments

    def _safe_paginated_list(self, paginated, limit: Optional[int] = None):
        """Iterate a PyGithub PaginatedList with basic rate-limit backoff and bounds."""
        items = []
        max_items = limit or self.config.max_items_per_list
        retries = 0

        iterator = iter(paginated)
        while True:
            try:
                item = next(iterator)
            except StopIteration:
                break
            except GithubException as exc:
                if self._is_rate_limited(exc) and retries < self.config.max_retries:
                    sleep_for = self._rate_limit_sleep_seconds(exc)
                    self._logger.info("Hit GitHub rate limit, sleeping %.1fs before retry", sleep_for)
                    time.sleep(sleep_for)
                    retries += 1
                    continue
                raise

            items.append(item)
            if max_items and len(items) >= max_items:
                break

        return items

    @staticmethod
    def _is_rate_limited(exc: GithubException) -> bool:
        """Detect GitHub rate limit responses (HTTP 403 with rate-limit headers)."""
        try:
            return getattr(exc, "status", None) == 403
        except Exception:
            return False

    def _rate_limit_sleep_seconds(self, exc: GithubException) -> float:
        """Compute a backoff duration using X-RateLimit-Reset when available."""
        headers = getattr(exc, "headers", {}) or {}
        reset_raw = headers.get("X-RateLimit-Reset") or headers.get("x-ratelimit-reset")
        if reset_raw:
            try:
                reset_epoch = int(reset_raw)
                now = int(time.time())
                wait = max(reset_epoch - now, self.backoff_seconds)
                return min(wait, self.max_backoff_seconds)
            except Exception:
                pass
        return min(self.config.backoff_seconds, self.config.max_backoff_seconds)

    @cached
    def get_file_tree(
        self,
        repo_id: str,
        branch: Optional[str] = None
    ) -> list[FileTreeItem]:
        """Get the file tree for a repository."""
        repo = self._get_repo(repo_id)

        ref = branch or repo.default_branch
        try:
            tree = repo.get_git_tree(sha=ref, recursive=True)
        except GithubException:
            return []

        return [
            FileTreeItem(
                path=item.path,
                is_directory=item.type == "tree",
                size=item.size if item.type == "blob" else None,
            )
            for item in tree.tree
        ]

    @cached
    def get_file_content(
        self,
        repo_id: str,
        file_path: str,
        branch: Optional[str] = None
    ) -> Optional[str]:
        """Get the content of a specific file."""
        repo = self._get_repo(repo_id)

        ref = branch or repo.default_branch
        try:
            content = repo.get_contents(file_path, ref=ref)
            if isinstance(content, list):
                return None  # It's a directory
            return content.decoded_content.decode("utf-8")
        except GithubException:
            return None

    @cached
    def _get_repo(self, repo_id: str) -> GHRepository:
        """Get a repository by ID (owner/name format)."""
        return self.client.get_repo(repo_id)

    @staticmethod
    def _map_review_state(gh_state: str) -> str:
        """Map GitHub review state to standard state."""
        mapping = {
            "APPROVED": "approved",
            "CHANGES_REQUESTED": "changes_requested",
            "COMMENTED": "commented",
            "DISMISSED": "dismissed",
            "PENDING": "commented",
        }
        return mapping.get(gh_state, "commented")
