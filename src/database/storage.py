"""
Database storage helpers for repository extraction data.

Provides functions to persist extracted data into the database with
deduplication, upsert logic, and relationship management.
"""

from datetime import datetime, timedelta, UTC
import uuid
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
    ReadmeFile,
    Team,
    Dependency,
    RepositoryLanguage,
    ExtractionRun,
    ExtractionMetric,
)
from src.extractors.base import (
    OrganizationData,
    RepositoryData,
    BranchData,
    CommitData,
    PullRequestData,
    PRReviewData,
    PRCommentData,
    ReadmeData,
    DependencyData,
    LanguageData,
)


# Default minimum hours between scans of the same repository
DEFAULT_MIN_SCAN_INTERVAL_HOURS = 6
_UNSET = object()


def start_extraction_run(
    session: Session,
    platform: str,
    organization_name: Optional[str] = None,
    project_name: Optional[str] = None,
    total_repositories: int = 0,
) -> uuid.UUID:
    """
    Create a new extraction run record and return its run_id.
    """
    now = datetime.now(UTC)
    run = ExtractionRun(
        run_id=uuid.uuid4(),
        platform=platform,
        organization_name=organization_name,
        project_name=project_name,
        status="running",
        total_repositories=total_repositories,
        processed_repositories=0,
        started_at=now,
        updated_at=now,
    )
    session.add(run)
    session.flush()
    return run.run_id


def update_extraction_run_progress(
    session: Session,
    run_id: uuid.UUID,
    processed_repositories: Optional[int] = None,
    current_repository_id: Optional[str] | object = _UNSET,
    status: Optional[str] = None,
) -> None:
    """
    Update extraction run progress counters and current repository.
    """
    run = session.get(ExtractionRun, run_id)
    if not run:
        return

    if processed_repositories is not None:
        run.processed_repositories = processed_repositories
    if current_repository_id is not _UNSET:
        run.current_repository_id = current_repository_id
    if status is not None:
        run.status = status

    run.updated_at = datetime.now(UTC)
    session.flush()


def complete_extraction_run(session: Session, run_id: uuid.UUID) -> None:
    """
    Mark an extraction run as completed.
    """
    run = session.get(ExtractionRun, run_id)
    if not run:
        return

    now = datetime.now(UTC)
    run.status = "completed"
    run.completed_at = now
    run.updated_at = now
    run.current_repository_id = None
    session.flush()


def fail_extraction_run(
    session: Session,
    run_id: uuid.UUID,
    error_message: str,
) -> None:
    """
    Mark an extraction run as failed.
    """
    run = session.get(ExtractionRun, run_id)
    if not run:
        return

    now = datetime.now(UTC)
    run.status = "failed"
    run.completed_at = now
    run.updated_at = now
    run.error_message = error_message[:1000]
    run.current_repository_id = None
    session.flush()


def start_repository_extraction(
    session: Session,
    run_id: uuid.UUID,
    repository_id: str,
    platform: str,
    celery_task_id: Optional[str] = None,
    worker_hostname: Optional[str] = None,
) -> int:
    """
    Record a repository extraction start and return the metric id.
    """
    now = datetime.now(UTC)
    metric = ExtractionMetric(
        run_id=run_id,
        repository_id=repository_id,
        platform=platform,
        status="started",
        extraction_started_at=now,
        correlation_id=uuid.uuid4(),
        celery_task_id=celery_task_id,
        worker_hostname=worker_hostname,
    )
    session.add(metric)
    session.flush()
    return metric.id


def skip_repository_extraction(
    session: Session,
    run_id: uuid.UUID,
    repository_id: str,
    platform: str,
    reason: str,
) -> int:
    """
    Record a repository extraction skip.
    """
    now = datetime.now(UTC)
    metric = ExtractionMetric(
        run_id=run_id,
        repository_id=repository_id,
        platform=platform,
        status="skipped",
        extraction_started_at=now,
        extraction_completed_at=now,
        extraction_duration_seconds=0,
        error_message=reason[:1000],
        correlation_id=uuid.uuid4(),
    )
    session.add(metric)
    session.flush()
    return metric.id


def complete_repository_extraction(
    session: Session,
    metric_id: int,
    commits_extracted: int = 0,
    pull_requests_extracted: int = 0,
    branches_extracted: int = 0,
    contributors_extracted: int = 0,
    cache_hits: int = 0,
    cache_misses: int = 0,
) -> None:
    """
    Record a successful repository extraction completion.
    """
    metric = session.get(ExtractionMetric, metric_id)
    if not metric:
        return

    now = datetime.now(UTC)
    metric.extraction_completed_at = now
    metric.extraction_duration_seconds = int(
        (now - metric.extraction_started_at).total_seconds()
    )
    metric.status = "completed"
    metric.commits_extracted = commits_extracted
    metric.pull_requests_extracted = pull_requests_extracted
    metric.branches_extracted = branches_extracted
    metric.contributors_extracted = contributors_extracted
    metric.cache_hits = cache_hits
    metric.cache_misses = cache_misses
    session.flush()


def fail_repository_extraction(
    session: Session,
    metric_id: int,
    error_message: str,
) -> None:
    """
    Record a repository extraction failure.
    """
    metric = session.get(ExtractionMetric, metric_id)
    if not metric:
        return

    now = datetime.now(UTC)
    metric.extraction_completed_at = now
    metric.extraction_duration_seconds = int(
        (now - metric.extraction_started_at).total_seconds()
    )
    metric.status = "failed"
    metric.error_message = error_message[:1000]
    session.flush()


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

    threshold = datetime.now(UTC) - timedelta(hours=min_hours)
    # Ensure last_analyzed_at is timezone-aware (assume UTC if naive)
    last_analyzed = repo.last_analyzed_at
    if last_analyzed.tzinfo is None:
        last_analyzed = last_analyzed.replace(tzinfo=UTC)
    return last_analyzed < threshold


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


def get_or_create_team(
    session: Session,
    organization: Organization,
    team_name: str,
    description: Optional[str] = None,
) -> Team:
    """
    Get existing team or create a new one.

    Args:
        session: Database session.
        organization: Parent organization.
        team_name: Team name.
        description: Team description.

    Returns:
        Team instance.
    """
    team = session.query(Team).filter_by(
        organization_id=organization.organization_id,
        name=team_name,
    ).first()
    if not team:
        team = Team(
            organization_id=organization.organization_id,
            name=team_name,
            description=description,
            created_at=datetime.now(UTC),
        )
        session.add(team)
        session.flush()
    return team


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

    # Get or create team if team_name is provided
    team_id = None
    if repo_data.team_name:
        # Get the organization from the project
        organization = session.query(Organization).filter_by(
            organization_id=project.organization_id
        ).first()
        if organization:
            team = get_or_create_team(
                session,
                organization,
                repo_data.team_name,
            )
            team_id = team.team_id

    if not repo:
        repo = Repository(
            repo_id=repo_data.repo_id,
            project_id=project.project_id,
            team_id=team_id,
            name=repo_data.name,
            url=repo_data.url,
            default_branch=repo_data.default_branch,
            platform_repo_id=repo_data.platform_repo_id,
            created_at=repo_data.created_at,
            is_active=True,
            # Security and code quality metrics
            is_private=repo_data.is_private,
            is_archived=repo_data.is_archived,
            repository_size=repo_data.repository_size,
            open_issues_count=repo_data.open_issues_count,
            license_name=repo_data.license_name,
            license_key=repo_data.license_key,
            has_vulnerability_alerts=repo_data.has_vulnerability_alerts,
            has_secret_scanning=repo_data.has_secret_scanning,
            has_dependabot_alerts=repo_data.has_dependabot_alerts,
            pushed_at=repo_data.pushed_at,
            updated_at=repo_data.updated_at,
        )
        session.add(repo)
        session.flush()
    else:
        repo.url = repo_data.url
        repo.default_branch = repo_data.default_branch
        repo.team_id = team_id  # Update team if changed
        # Update security and code quality metrics
        repo.is_private = repo_data.is_private
        repo.is_archived = repo_data.is_archived
        repo.repository_size = repo_data.repository_size
        repo.open_issues_count = repo_data.open_issues_count
        repo.license_name = repo_data.license_name
        repo.license_key = repo_data.license_key
        repo.has_vulnerability_alerts = repo_data.has_vulnerability_alerts
        repo.has_secret_scanning = repo_data.has_secret_scanning
        repo.has_dependabot_alerts = repo_data.has_dependabot_alerts
        repo.pushed_at = repo_data.pushed_at
        repo.updated_at = repo_data.updated_at

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


def store_languages(
    session: Session,
    repo_id: str,
    languages: list[LanguageData],
    branch_id: Optional[int] = None,
) -> list[RepositoryLanguage]:
    """
    Upsert language statistics for a repository.

    Uses (repo_id, language) as the natural key. On first insert sets
    first_seen_at; on every run updates last_seen_at and stats.

    Args:
        session: Database session.
        repo_id: Repository ID.
        languages: List of language data from extractor.
        branch_id: Optional branch ID (None for repository-wide stats).

    Returns:
        List of upserted RepositoryLanguage instances.
    """
    now = datetime.now(UTC)
    results = []
    for lang_data in languages:
        existing = (
            session.query(RepositoryLanguage)
            .filter_by(repo_id=repo_id, language=lang_data.language)
            .first()
        )
        if existing:
            existing.percentage = lang_data.percentage
            existing.byte_count = lang_data.byte_count
            existing.branch_id = branch_id
            existing.last_seen_at = now
            results.append(existing)
        else:
            lang = RepositoryLanguage(
                repo_id=repo_id,
                branch_id=branch_id,
                language=lang_data.language,
                percentage=lang_data.percentage,
                line_count=None,
                byte_count=lang_data.byte_count,
                first_seen_at=now,
                last_seen_at=now,
            )
            session.add(lang)
            results.append(lang)

    return results


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
        is_verified=commit_data.is_verified,
        verification_reason=commit_data.verification_reason,
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
        repo.last_analyzed_at = datetime.now(UTC)


def store_readme(
    session: Session,
    repo_id: str,
    readme_data: ReadmeData,
) -> ReadmeFile:
    """
    Store a README file with scope context.

    Args:
        session: Database session.
        repo_id: Repository identifier.
        readme_data: README data from extractor.

    Returns:
        ReadmeFile instance.
    """
    # Get repository
    repo = session.query(Repository).filter_by(repo_id=repo_id).first()
    if not repo:
        raise ValueError(f"Repository {repo_id} not found")

    # Find branch if specified
    branch_id = None
    if readme_data.branch:
        branch = (
            session.query(Branch)
            .filter_by(repo_id=repo_id, branch_name=readme_data.branch)
            .first()
        )
        if branch:
            branch_id = branch.branch_id

    # Find parent README if specified
    parent_readme_id = None
    if readme_data.parent_readme_path:
        parent_readme = (
            session.query(ReadmeFile)
            .filter_by(
                repo_id=repo_id,
                branch_id=branch_id,
                file_path=readme_data.parent_readme_path
            )
            .first()
        )
        if parent_readme:
            parent_readme_id = parent_readme.id

    # Check if README already exists
    existing = (
        session.query(ReadmeFile)
        .filter_by(
            repo_id=repo_id,
            branch_id=branch_id,
            file_path=readme_data.file_path
        )
        .first()
    )

    if existing:
        # Update existing README
        existing.content = readme_data.content
        existing.word_count = readme_data.word_count
        existing.analyzed_at = readme_data.analyzed_at
        existing.scope_type = readme_data.scope_type
        existing.scope_path = readme_data.scope_path
        existing.parent_readme_id = parent_readme_id
        existing.affects_paths = readme_data.affects_paths
        return existing
    else:
        # Create new README
        readme_file = ReadmeFile(
            repo_id=repo_id,
            branch_id=branch_id,
            file_path=readme_data.file_path,
            content=readme_data.content,
            word_count=readme_data.word_count,
            analyzed_at=readme_data.analyzed_at,
            scope_type=readme_data.scope_type,
            scope_path=readme_data.scope_path,
            parent_readme_id=parent_readme_id,
            affects_paths=readme_data.affects_paths,
        )
        session.add(readme_file)
        return readme_file


def _resolve_branch_id(
    session: Session, repo_id: str, branch_name: Optional[str]
) -> Optional[int]:
    """Resolve a branch name to its ID."""
    if not branch_name:
        return None
    branch = (
        session.query(Branch)
        .filter_by(repo_id=repo_id, branch_name=branch_name)
        .first()
    )
    return branch.branch_id if branch else None


def store_dependencies(
    session: Session,
    repo_id: str,
    dependencies: list[DependencyData],
    branch_name: Optional[str] = None,
) -> list[Dependency]:
    """
    Upsert dependencies for a repository.

    Uses (repo_id, package_name, ecosystem) as the natural key.
    On first insert sets first_seen_at; on every run updates last_seen_at.

    Args:
        session: Database session.
        repo_id: Repository identifier.
        dependencies: List of DependencyData to store.
        branch_name: Branch name (optional).

    Returns:
        List of stored Dependency instances.
    """
    now = datetime.now(UTC)
    branch_id = _resolve_branch_id(session, repo_id, branch_name)

    stored_deps = []
    for dep_data in dependencies:
        existing = (
            session.query(Dependency)
            .filter_by(
                repo_id=repo_id,
                package_name=dep_data.package_name,
                ecosystem=dep_data.ecosystem,
            )
            .first()
        )
        if existing:
            existing.version = dep_data.version
            existing.is_dev_dependency = dep_data.is_dev_dependency
            existing.branch_id = branch_id
            existing.last_seen_at = now
            stored_deps.append(existing)
        else:
            dep = Dependency(
                repo_id=repo_id,
                branch_id=branch_id,
                package_name=dep_data.package_name,
                version=dep_data.version,
                ecosystem=dep_data.ecosystem,
                is_dev_dependency=dep_data.is_dev_dependency,
                first_seen_at=now,
                last_seen_at=now,
            )
            session.add(dep)
            stored_deps.append(dep)

    return stored_deps


def store_enriched_dependencies(
    session: Session,
    repo_id: str,
    enriched_dependencies: list,
    branch_name: Optional[str] = None,
) -> list[Dependency]:
    """
    Upsert enriched dependencies for a repository.

    Uses (repo_id, package_name, ecosystem) as the natural key.
    Includes enrichment fields from OSV.dev and endoflife.date.

    Args:
        session: Database session.
        repo_id: Repository identifier.
        enriched_dependencies: List of EnrichedDependency objects.
        branch_name: Branch name (optional).

    Returns:
        List of stored Dependency instances.
    """
    now = datetime.now(UTC)
    branch_id = _resolve_branch_id(session, repo_id, branch_name)

    stored_deps = []
    for enriched_dep in enriched_dependencies:
        existing = (
            session.query(Dependency)
            .filter_by(
                repo_id=repo_id,
                package_name=enriched_dep.package_name,
                ecosystem=enriched_dep.ecosystem,
            )
            .first()
        )
        if existing:
            existing.version = enriched_dep.version
            existing.latest_version = enriched_dep.latest_version
            existing.is_dev_dependency = enriched_dep.is_dev_dependency
            existing.has_vulnerabilities = enriched_dep.has_vulnerabilities
            existing.is_eol = enriched_dep.is_eol
            existing.eol_date = enriched_dep.eol_date
            existing.branch_id = branch_id
            existing.last_seen_at = now
            stored_deps.append(existing)
        else:
            dep = Dependency(
                repo_id=repo_id,
                branch_id=branch_id,
                package_name=enriched_dep.package_name,
                version=enriched_dep.version,
                ecosystem=enriched_dep.ecosystem,
                latest_version=enriched_dep.latest_version,
                is_dev_dependency=enriched_dep.is_dev_dependency,
                has_vulnerabilities=enriched_dep.has_vulnerabilities,
                is_eol=enriched_dep.is_eol,
                eol_date=enriched_dep.eol_date,
                first_seen_at=now,
                last_seen_at=now,
            )
            session.add(dep)
            stored_deps.append(dep)

    return stored_deps


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
        "readme_files": session.query(ReadmeFile).count(),
        "dependencies": session.query(Dependency).count(),
    }
