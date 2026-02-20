"""
Service-level analytics and metric aggregation.

Aggregates metrics across all repositories belonging to a service.

Implements FR-10.4: service-level metric aggregation.
"""

import logging
from datetime import datetime, UTC
from typing import Optional

from sqlalchemy import func, select, and_
from sqlalchemy.orm import Session

from src.database.models.contributor import ContributorMetric
from src.database.models.dependency import Dependency, Vulnerability
from src.database.models.pull_request import PullRequest
from src.database.models.quality import CodeQualityMetric
from src.database.models.service import RepositoryService, Service
from src.database.models.service_metric import ServiceMetric

logger = logging.getLogger(__name__)


def compute_service_metrics(
    session: Session,
    service_id: int,
    period_start: datetime,
    period_end: datetime,
) -> ServiceMetric:
    """
    Compute aggregated metrics for a service across all its repositories.

    Aggregates contributor metrics (commits, lines, PRs), quality metrics,
    pull request metrics, and security/dependency metrics for all repositories
    linked to the service.

    Args:
        session: Database session
        service_id: ID of the service to compute metrics for
        period_start: Start of time period (inclusive)
        period_end: End of time period (exclusive)

    Returns:
        ServiceMetric object with aggregated data (not yet persisted)

    Raises:
        ValueError: If service not found
    """
    service = session.get(Service, service_id)
    if not service:
        raise ValueError(f"Service {service_id} not found")

    repo_ids = list(
        session.execute(
            select(RepositoryService.repo_id).where(
                RepositoryService.service_id == service_id
            )
        ).scalars()
    )

    if not repo_ids:
        logger.warning("Service %d has no linked repositories", service_id)
        return _empty_service_metric(service_id, period_start, period_end)

    contributor_agg = _aggregate_contributor_metrics(
        session, repo_ids, period_start, period_end
    )
    quality_agg = _aggregate_quality_metrics(
        session, repo_ids, period_start, period_end
    )
    pr_agg = _aggregate_pr_metrics(session, repo_ids, period_start, period_end)
    security_agg = _aggregate_security_metrics(session, repo_ids)
    unique_contributors = _count_unique_contributors(
        session, repo_ids, period_start, period_end
    )
    active_repos = _count_active_repositories(
        session, repo_ids, period_start, period_end
    )

    return ServiceMetric(
        service_id=service_id,
        period_start=period_start,
        period_end=period_end,
        total_repositories=len(repo_ids),
        active_repositories=active_repos,
        unique_contributors=unique_contributors,
        computed_at=datetime.now(UTC),
        **contributor_agg,
        **quality_agg,
        **pr_agg,
        **security_agg,
    )


def get_service_metrics(
    session: Session,
    service_id: int,
    period_start: Optional[datetime] = None,
    period_end: Optional[datetime] = None,
) -> list[ServiceMetric]:
    """
    Retrieve persisted service metrics for a time range.

    Args:
        session: Database session
        service_id: Service to retrieve metrics for
        period_start: Optional start filter (inclusive)
        period_end: Optional end filter (exclusive)

    Returns:
        List of ServiceMetric objects ordered by period_start DESC
    """
    query = select(ServiceMetric).where(ServiceMetric.service_id == service_id)

    if period_start is not None:
        query = query.where(ServiceMetric.period_start >= period_start)
    if period_end is not None:
        query = query.where(ServiceMetric.period_start < period_end)

    query = query.order_by(ServiceMetric.period_start.desc())
    return list(session.execute(query).scalars())


def get_latest_service_metrics(
    session: Session,
    service_id: int,
) -> Optional[ServiceMetric]:
    """
    Get the most recently computed metrics for a service.

    Args:
        session: Database session
        service_id: Service to retrieve metrics for

    Returns:
        Most recent ServiceMetric, or None if no metrics exist
    """
    return session.execute(
        select(ServiceMetric)
        .where(ServiceMetric.service_id == service_id)
        .order_by(ServiceMetric.period_start.desc())
        .limit(1)
    ).scalar_one_or_none()


def compute_all_services_metrics(
    session: Session,
    period_start: datetime,
    period_end: datetime,
) -> list[ServiceMetric]:
    """
    Compute metrics for all services (suitable for scheduled batch jobs).

    Failures for individual services are logged and skipped so one broken
    service does not abort the entire batch.

    Args:
        session: Database session
        period_start: Start of time period
        period_end: End of time period

    Returns:
        List of computed ServiceMetric objects (not persisted)
    """
    services = list(session.execute(select(Service)).scalars())
    metrics: list[ServiceMetric] = []

    for service in services:
        try:
            metric = compute_service_metrics(
                session, service.service_id, period_start, period_end
            )
            metrics.append(metric)
        except Exception:
            logger.exception(
                "Failed to compute metrics for service %d (%s)",
                service.service_id,
                service.name,
            )

    return metrics


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _aggregate_contributor_metrics(
    session: Session,
    repo_ids: list[str],
    period_start: datetime,
    period_end: datetime,
) -> dict:
    """Sum commit and PR metrics from contributor_metrics for the period."""
    result = session.execute(
        select(
            func.sum(ContributorMetric.commit_count).label("total_commits"),
            func.sum(ContributorMetric.lines_added).label("total_lines_added"),
            func.sum(ContributorMetric.lines_removed).label("total_lines_removed"),
            func.sum(ContributorMetric.files_modified).label("total_files_modified"),
            func.sum(ContributorMetric.pr_created).label("total_prs_created"),
        ).where(
            and_(
                ContributorMetric.repo_id.in_(repo_ids),
                ContributorMetric.period_start >= period_start,
                ContributorMetric.period_start < period_end,
            )
        )
    ).one()

    return {
        "total_commits": result.total_commits or 0,
        "total_lines_added": result.total_lines_added or 0,
        "total_lines_removed": result.total_lines_removed or 0,
        "total_files_modified": result.total_files_modified or 0,
        "total_prs_created": result.total_prs_created or 0,
    }


def _aggregate_quality_metrics(
    session: Session,
    repo_ids: list[str],
    period_start: datetime,
    period_end: datetime,
) -> dict:
    """Average quality scores and sum issue counts across repos for the period."""
    result = session.execute(
        select(
            func.avg(CodeQualityMetric.test_coverage).label("avg_test_coverage"),
            func.avg(CodeQualityMetric.maintainability_index).label(
                "avg_maintainability_index"
            ),
            func.sum(CodeQualityMetric.total_issues).label("total_quality_issues"),
        ).where(
            and_(
                CodeQualityMetric.repo_id.in_(repo_ids),
                CodeQualityMetric.timestamp >= period_start,
                CodeQualityMetric.timestamp < period_end,
            )
        )
    ).one()

    return {
        "avg_test_coverage": result.avg_test_coverage,
        "avg_maintainability_index": result.avg_maintainability_index,
        "total_quality_issues": result.total_quality_issues or 0,
    }


def _aggregate_pr_metrics(
    session: Session,
    repo_ids: list[str],
    period_start: datetime,
    period_end: datetime,
) -> dict:
    """Count merged PRs and compute average review time for the period."""
    result = session.execute(
        select(
            func.count(PullRequest.id).label("total_prs_merged"),
            func.avg(
                func.extract("epoch", PullRequest.merged_at - PullRequest.created_at)
                / 3600
            ).label("avg_pr_review_time_hours"),
        ).where(
            and_(
                PullRequest.repo_id.in_(repo_ids),
                PullRequest.created_at >= period_start,
                PullRequest.created_at < period_end,
                PullRequest.merged_at.isnot(None),
            )
        )
    ).one()

    return {
        "total_prs_merged": result.total_prs_merged or 0,
        "avg_pr_review_time_hours": result.avg_pr_review_time_hours,
    }


def _aggregate_security_metrics(
    session: Session,
    repo_ids: list[str],
) -> dict:
    """
    Aggregate security and dependency metrics (point-in-time).

    Dependencies represent current state rather than time-series data,
    so no period filter is applied here.
    """
    # Vulnerability counts by severity (via join to Vulnerability)
    vuln_result = session.execute(
        select(
            func.count(func.distinct(Dependency.id)).label("total_vulnerable_deps"),
            func.sum(
                func.case((Vulnerability.severity == "CRITICAL", 1), else_=0)
            ).label("critical_vulns"),
            func.sum(
                func.case((Vulnerability.severity == "HIGH", 1), else_=0)
            ).label("high_vulns"),
        )
        .select_from(Dependency)
        .join(Vulnerability, Vulnerability.dependency_id == Dependency.id)
        .where(Dependency.repo_id.in_(repo_ids))
    ).one()

    # Total dependency counts including EOL
    dep_result = session.execute(
        select(
            func.count(Dependency.id).label("total_deps"),
            func.sum(
                func.case((Dependency.is_eol.is_(True), 1), else_=0)
            ).label("eol_deps"),
        ).where(Dependency.repo_id.in_(repo_ids))
    ).one()

    return {
        "total_vulnerabilities": vuln_result.total_vulnerable_deps or 0,
        "critical_vulnerabilities": vuln_result.critical_vulns or 0,
        "high_vulnerabilities": vuln_result.high_vulns or 0,
        "total_dependencies": dep_result.total_deps or 0,
        "eol_dependencies": dep_result.eol_deps or 0,
    }


def _count_unique_contributors(
    session: Session,
    repo_ids: list[str],
    period_start: datetime,
    period_end: datetime,
) -> int:
    """Count distinct contributors across all service repos for the period."""
    result = session.execute(
        select(func.count(func.distinct(ContributorMetric.contributor_id))).where(
            and_(
                ContributorMetric.repo_id.in_(repo_ids),
                ContributorMetric.period_start >= period_start,
                ContributorMetric.period_start < period_end,
            )
        )
    ).scalar()

    return result or 0


def _count_active_repositories(
    session: Session,
    repo_ids: list[str],
    period_start: datetime,
    period_end: datetime,
) -> int:
    """Count repos with at least one commit recorded in the period."""
    result = session.execute(
        select(func.count(func.distinct(ContributorMetric.repo_id))).where(
            and_(
                ContributorMetric.repo_id.in_(repo_ids),
                ContributorMetric.period_start >= period_start,
                ContributorMetric.period_start < period_end,
                ContributorMetric.commit_count > 0,
            )
        )
    ).scalar()

    return result or 0


def _empty_service_metric(
    service_id: int,
    period_start: datetime,
    period_end: datetime,
) -> ServiceMetric:
    """Return zero-valued ServiceMetric for a service with no linked repositories."""
    return ServiceMetric(
        service_id=service_id,
        period_start=period_start,
        period_end=period_end,
        computed_at=datetime.now(UTC),
    )
