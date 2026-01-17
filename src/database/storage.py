"""
Database storage helpers for repository extraction data.

Provides functions to persist extracted data into the database with
deduplication, upsert logic, and relationship management.
"""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from src.database.models import (
    Organization,
    Project,
    Repository,
    Branch,
    Contributor,
    Commit,
    PullRequest,
    PRReview,
    PRComment,
)
from src.extractors.base import (
    OrganizationData,
    RepositoryData,
    BranchData,
    CommitData,
    PullRequestData,
    PRReviewData,
    PRCommentData,
)


# Default minimum hours between scans of the same repository
DEFAULT_MIN_SCAN_INTERVAL_HOURS = 6


def should_scan_repository(
    session: Session,
    repo_id: str,
    min_hours: int = DEFAULT_MIN_SCAN_INTERVAL_HOURS,
) -> bool:
    """
    Check if a repository should be scanned based on last_analyzed_at.

    Args:
        session: Database session.
        repo_id: Repository identifier.
        min_hours: Minimum hours between scans.

    Returns:
        True if repository should be scanned, False otherwise.
    """
    repo = session.query(Repository).filter_by(repo_id=repo_id).first()
    if not repo or not repo.last_analyzed_at:
        return True

    threshold = datetime.utcnow() - timedelta(hours=min_hours)
    return repo.last_analyzed_at < threshold


def get_or_create_contributor(
    session: Session,
    email: str,
    name: Optional[str] = None,
) -> Contributor:
    """
    Get existing contributor or create a new one.

    Args:
        session: Database session.
        email: Contributor email address.
        name: Contributor display name.

    Returns:
        Contributor instance.
    """
    contributor = session.query(Contributor).filter_by(email=email).first()
    if not contributor:
        contributor = Contributor(email=email, name=name)
        session.add(contributor)
        session.flush()
    return contributor


def store_organization(
    session: Session,
    org_data: OrganizationData,
) -> Organization:
    """
    Store or update an organization.

    Args:
        session: Database session.
        org_data: Organization data from extractor.

    Returns:
        Organization instance.
    """
    org = session.query(Organization).filter_by(
        platform=org_data.platform.value,
        name=org_data.name,
    ).first()

    if not org:
        org = Organization(
            name=org_data.name,
            url=org_data.url,
            platform=org_data.platform.value,
        )
        session.add(org)
        session.flush()

    return org


def store_project(
    session: Session,
    organization: Organization,
    name: str,
    description: Optional[str] = None,
) -> Project:
    """
    Store or update a project.

    Args:
        session: Database session.
        organization: Parent organization.
        name: Project name.
        description: Project description.

    Returns:
        Project instance.
    """
    project = session.query(Project).filter_by(
        organization_id=organization.organization_id,
        name=name,
    ).first()

    if not project:
        project = Project(
            organization_id=organization.organization_id,
            name=name,
            description=description or f"Repositories for {name}",
        )
        session.add(project)
        session.flush()

    return project


def store_repository(
    session: Session,
    project: Project,
    repo_data: RepositoryData,
) -> Repository:
    """
    Store or update a repository.

    Args:
        session: Database session.
        project: Parent project.
        repo_data: Repository data from extractor.

    Returns:
        Repository instance (created=True if new).
    """
    repo = session.query(Repository).filter_by(repo_id=repo_data.repo_id).first()

    if not repo:
        repo = Repository(
            repo_id=repo_data.repo_id,
            project_id=project.project_id,
            name=repo_data.name,
            url=repo_data.url,
            default_branch=repo_data.default_branch,
            platform_repo_id=repo_data.platform_repo_id,
            created_at=repo_data.created_at,
            is_active=True,
        )
        session.add(repo)
        session.flush()
    else:
        repo.url = repo_data.url
        repo.default_branch = repo_data.default_branch

    return repo


def store_branch(
    session: Session,
    repo_id: str,
    branch_data: BranchData,
) -> Branch:
    """
    Store or update a branch.

    Args:
        session: Database session.
        repo_id: Parent repository ID.
        branch_data: Branch data from extractor.

    Returns:
        Branch instance.
    """
    branch = session.query(Branch).filter_by(
        repo_id=repo_id,
        branch_name=branch_data.name,
    ).first()

    if not branch:
        branch = Branch(
            repo_id=repo_id,
            branch_name=branch_data.name,
            latest_commit_sha=branch_data.latest_commit_sha,
            is_active=True,
        )
        session.add(branch)
    else:
        branch.latest_commit_sha = branch_data.latest_commit_sha

    return branch


def store_commit(
    session: Session,
    repo_id: str,
    branch_name: str,
    commit_data: CommitData,
) -> Optional[Commit]:
    """
    Store a commit if it doesn't exist.

    Args:
        session: Database session.
        repo_id: Repository ID.
        branch_name: Branch name.
        commit_data: Commit data from extractor.

    Returns:
        Commit instance or None if already exists.
    """
    existing = session.query(Commit).filter_by(commit_sha=commit_data.sha).first()
    if existing:
        return None

    contributor = get_or_create_contributor(
        session,
        commit_data.author_email,
        commit_data.author_name,
    )

    commit = Commit(
        commit_sha=commit_data.sha,
        repo_id=repo_id,
        branch_name=branch_name,
        author_id=contributor.id,
        committer_id=contributor.id,
        message=commit_data.message[:1000] if commit_data.message else "",
        commit_date=commit_data.commit_date,
        files_changed=commit_data.files_changed,
        lines_added=commit_data.lines_added,
        lines_removed=commit_data.lines_removed,
    )
    session.add(commit)
    return commit


def classify_pr_size(lines_added: int, lines_removed: int) -> str:
    """
    Classify pull request size based on total changes.

    Args:
        lines_added: Number of lines added.
        lines_removed: Number of lines removed.

    Returns:
        Size category: 'small', 'medium', 'large', or 'extra_large'.
    """
    total_changes = lines_added + lines_removed
    if total_changes < 50:
        return "small"
    elif total_changes < 200:
        return "medium"
    elif total_changes < 500:
        return "large"
    return "extra_large"


def map_review_state_to_vote(state: str) -> int:
    """
    Map review state string to numeric vote value.

    Args:
        state: Review state string.

    Returns:
        Vote value: 10 (approved), -10 (changes_requested), 0 (other).
    """
    vote_map = {
        "approved": 10,
        "changes_requested": -10,
        "commented": 0,
        "dismissed": 0,
    }
    return vote_map.get(state, 0)


def store_pull_request(
    session: Session,
    repo_id: str,
    pr_data: PullRequestData,
) -> Optional[PullRequest]:
    """
    Store a pull request with reviews and comments if it doesn't exist.

    Args:
        session: Database session.
        repo_id: Repository ID.
        pr_data: Pull request data from extractor.

    Returns:
        PullRequest instance or None if already exists.
    """
    existing = session.query(PullRequest).filter_by(
        repo_id=repo_id,
        pr_number=pr_data.pr_number,
    ).first()

    if existing:
        return None

    author = get_or_create_contributor(
        session,
        pr_data.author_email,
        pr_data.author_name,
    )

    size = classify_pr_size(pr_data.lines_added, pr_data.lines_removed)

    pr = PullRequest(
        repo_id=repo_id,
        pr_number=pr_data.pr_number,
        platform_pr_id=pr_data.platform_pr_id,
        title=pr_data.title[:500] if pr_data.title else "",
        description=pr_data.description[:2000] if pr_data.description else None,
        source_branch=pr_data.source_branch,
        target_branch=pr_data.target_branch,
        author_id=author.id,
        status=pr_data.status,
        created_at=pr_data.created_at,
        updated_at=pr_data.updated_at,
        merged_at=pr_data.merged_at,
        closed_at=pr_data.closed_at,
        files_changed=pr_data.files_changed,
        lines_added=pr_data.lines_added,
        lines_removed=pr_data.lines_removed,
        size_category=size,
    )
    session.add(pr)
    session.flush()

    # Store reviews
    for review_data in pr_data.reviews:
        store_pr_review(session, pr.id, review_data)

    # Store comments (limit to 50)
    for comment_data in pr_data.comments[:50]:
        store_pr_comment(session, pr.id, comment_data)

    return pr


def store_pr_review(
    session: Session,
    pr_id: int,
    review_data: PRReviewData,
) -> PRReview:
    """
    Store a pull request review.

    Args:
        session: Database session.
        pr_id: Pull request ID.
        review_data: Review data from extractor.

    Returns:
        PRReview instance.
    """
    reviewer = get_or_create_contributor(
        session,
        review_data.reviewer_email,
        review_data.reviewer_name,
    )

    review = PRReview(
        pr_id=pr_id,
        reviewer_id=reviewer.id,
        review_date=review_data.review_date,
        vote=map_review_state_to_vote(review_data.state),
        is_required=review_data.is_required,
    )
    session.add(review)
    return review


def store_pr_comment(
    session: Session,
    pr_id: int,
    comment_data: PRCommentData,
) -> PRComment:
    """
    Store a pull request comment.

    Args:
        session: Database session.
        pr_id: Pull request ID.
        comment_data: Comment data from extractor.

    Returns:
        PRComment instance.
    """
    commenter = get_or_create_contributor(
        session,
        comment_data.author_email,
        comment_data.author_name,
    )

    comment = PRComment(
        pr_id=pr_id,
        author_id=commenter.id,
        content=comment_data.content[:2000] if comment_data.content else "",
        published_date=comment_data.published_date,
        thread_id=comment_data.thread_id,
        file_path=comment_data.file_path,
        line_number=comment_data.line_number,
        comment_type=comment_data.comment_type,
    )
    session.add(comment)
    return comment


def update_repository_analyzed_timestamp(session: Session, repo_id: str) -> None:
    """
    Update the last_analyzed_at timestamp for a repository.

    Args:
        session: Database session.
        repo_id: Repository ID.
    """
    repo = session.query(Repository).filter_by(repo_id=repo_id).first()
    if repo:
        repo.last_analyzed_at = datetime.utcnow()


def get_extraction_summary(session: Session) -> dict:
    """
    Get summary counts of all extracted data.

    Args:
        session: Database session.

    Returns:
        Dictionary with counts for each entity type.
    """
    return {
        "organizations": session.query(Organization).count(),
        "repositories": session.query(Repository).count(),
        "branches": session.query(Branch).count(),
        "commits": session.query(Commit).count(),
        "pull_requests": session.query(PullRequest).count(),
        "contributors": session.query(Contributor).count(),
    }
