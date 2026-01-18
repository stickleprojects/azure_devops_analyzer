"""
GitHub repository extractor implementation.
"""

from datetime import datetime
from typing import Optional

from github import GithubException
from github.Repository import Repository as GHRepository

from src.extractors.github.client import (
    get_github_client,
    get_organization_name,
    get_user_name,
)
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


class GitHubExtractor(RepositoryExtractor):
    """Extractor for GitHub repositories."""

    def __init__(self):
        self._client = None
        self._org_name = get_organization_name()
        self._user_name = get_user_name()

    @property
    def client(self):
        if self._client is None:
            self._client = get_github_client()
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
        project: Optional[str] = None
    ) -> list[RepositoryData]:
        """List repositories for an organization or user."""
        repos = []

        try:
            # Try as organization first
            org = self.client.get_organization(organization)
            gh_repos = org.get_repos()
        except GithubException:
            # Fall back to user
            user = self.client.get_user()
            gh_repos = user.get_repos( visibility="all")

        for r in gh_repos:
            repos.append(
                RepositoryData(
                    repo_id=f"{r.owner.login}/{r.name}",
                    name=r.name,
                    url=r.html_url,
                    default_branch=r.default_branch,
                    platform=Platform.GITHUB,
                    platform_repo_id=r.id,
                    project_name=organization,
                    organization_name=organization,
                    created_at=r.created_at,
                )
            )

        return repos

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
        count = 0
        for c in commits:
            if limit and count >= limit:
                break

            # Get commit stats (requires additional API call)
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
                )
            )
            count += 1

        return result

    def get_pull_requests(
        self,
        repo_id: str,
        status: Optional[str] = None,
        since: Optional[datetime] = None,
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
        for pr in prs:
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

            # Get author email (may require additional API call)
            author_email = ""
            author_name = None
            if pr.user:
                author_name = pr.user.login
                # Try to get email from user profile
                try:
                    user = self.client.get_user(pr.user.login)
                    author_email = user.email or f"{pr.user.login}@users.noreply.github.com"
                except GithubException:
                    author_email = f"{pr.user.login}@users.noreply.github.com"

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
