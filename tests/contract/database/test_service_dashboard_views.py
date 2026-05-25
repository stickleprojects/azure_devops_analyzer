"""
Contract tests: Service dashboard SQL views

CONTRACT: All v_service_* views are queryable and return structurally correct
results when services with linked repositories and metrics exist.

Views covered:
  v_service_metrics_latest
  v_service_metrics_trend
  v_service_repository_breakdown
  v_service_vulnerabilities_by_severity
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from sqlalchemy import text

from src.database.models import Organization, Project, Repository
from src.database.models.service import Service, RepositoryService
from src.database.models.service_metric import ServiceMetric


# =============================================================================
# Fixture — one service with two repos and two metric periods
# =============================================================================

@pytest.fixture
def service_dataset(db_session):
    """Seed a service with two repos and two time-series metric periods."""
    now = datetime.now(timezone.utc)

    org = Organization(
        name=f"svc-test-org-{uuid4().hex[:8]}",
        url="https://dev.azure.com/test",
        platform="azure_devops",
    )
    db_session.add(org)
    db_session.flush()

    project = Project(organization_id=org.organization_id, name="svc-project")
    db_session.add(project)
    db_session.flush()

    repos = []
    for i in range(2):
        repo = Repository(
            repo_id=f"svc-repo-{uuid4().hex[:8]}",
            name=f"payment-service-{i}",
            url=f"https://github.com/test/payment-{i}",
            project_id=project.project_id,
            is_active=True,
            last_analyzed_at=now - timedelta(hours=1),
        )
        db_session.add(repo)
        repos.append(repo)
    db_session.flush()

    svc = Service(
        name=f"payment-platform-{uuid4().hex[:8]}",
        purpose="Handles all payment processing",
    )
    db_session.add(svc)
    db_session.flush()

    for repo in repos:
        db_session.add(RepositoryService(repo_id=repo.repo_id, service_id=svc.service_id))

    # Two time-series metric rows (latest + one prior period)
    for offset_days in (0, 30):
        db_session.add(ServiceMetric(
            service_id=svc.service_id,
            period_start=now - timedelta(days=offset_days + 30),
            period_end=now - timedelta(days=offset_days),
            total_repositories=2,
            active_repositories=2,
            total_commits=100 - offset_days,
            total_prs_created=20,
            total_prs_merged=18,
            total_vulnerabilities=3,
            critical_vulnerabilities=1,
            high_vulnerabilities=2,
            eol_dependencies=1,
            total_dependencies=50,
        ))

    db_session.flush()
    return {"service": svc, "repos": repos}


# =============================================================================
# Tests
# =============================================================================

class TestServiceMetricsLatest:
    def test_returns_one_row_per_service(self, service_dataset, db_session):
        svc_name = service_dataset["service"].name
        rows = db_session.execute(text(
            "SELECT service, total_repositories, total_commits, total_vulnerabilities "
            "FROM v_service_metrics_latest WHERE service = :name"
        ), {"name": svc_name}).fetchall()
        assert len(rows) == 1

    def test_latest_picks_most_recent_period(self, service_dataset, db_session):
        svc_name = service_dataset["service"].name
        row = db_session.execute(text(
            "SELECT total_commits FROM v_service_metrics_latest WHERE service = :name"
        ), {"name": svc_name}).fetchone()
        # Most recent period has commits=100 (offset_days=0)
        assert row is not None
        assert row.total_commits == 100

    def test_expected_columns_present(self, service_dataset, db_session):
        svc_name = service_dataset["service"].name
        row = db_session.execute(text(
            "SELECT service, total_repositories, active_repositories, "
            "unique_contributors, total_commits, total_prs_created, total_prs_merged, "
            "total_vulnerabilities, critical_vulnerabilities, eol_dependencies "
            "FROM v_service_metrics_latest WHERE service = :name"
        ), {"name": svc_name}).fetchone()
        assert row is not None
        assert row.total_repositories == 2


class TestServiceMetricsTrend:
    def test_returns_multiple_time_periods(self, service_dataset, db_session):
        svc_name = service_dataset["service"].name
        rows = db_session.execute(text(
            "SELECT service, time, commits FROM v_service_metrics_trend "
            "WHERE service = :name ORDER BY time"
        ), {"name": svc_name}).fetchall()
        assert len(rows) == 2

    def test_trend_columns_present(self, service_dataset, db_session):
        svc_name = service_dataset["service"].name
        row = db_session.execute(text(
            "SELECT service, time, commits, prs_created, prs_merged, "
            "vulnerabilities, critical "
            "FROM v_service_metrics_trend WHERE service = :name LIMIT 1"
        ), {"name": svc_name}).fetchone()
        assert row is not None
        assert row.commits > 0


class TestServiceRepositoryBreakdown:
    def test_both_repos_appear(self, service_dataset, db_session):
        svc_name = service_dataset["service"].name
        rows = db_session.execute(text(
            "SELECT repository, service, commits_30d, open_prs "
            "FROM v_service_repository_breakdown WHERE service = :name"
        ), {"name": svc_name}).fetchall()
        assert len(rows) == 2
        assert all(r.service == svc_name for r in rows)

    def test_columns_structurally_correct(self, service_dataset, db_session):
        svc_name = service_dataset["service"].name
        row = db_session.execute(text(
            "SELECT repo_id, repository, service, commits_30d, contributors_30d, "
            "open_prs, merged_prs_30d, vulnerabilities "
            "FROM v_service_repository_breakdown WHERE service = :name LIMIT 1"
        ), {"name": svc_name}).fetchone()
        assert row is not None
        assert row.commits_30d >= 0
        assert row.vulnerabilities >= 0


class TestServiceVulnerabilitiesBySeverity:
    def test_view_queryable_without_error(self, service_dataset, db_session):
        # No vulnerabilities seeded — view must return without error
        rows = db_session.execute(text(
            "SELECT service, severity, count FROM v_service_vulnerabilities_by_severity"
        )).fetchall()
        assert isinstance(rows, list)

    def test_returns_empty_when_no_vulns(self, service_dataset, db_session):
        svc_name = service_dataset["service"].name
        rows = db_session.execute(text(
            "SELECT service, severity, count FROM v_service_vulnerabilities_by_severity "
            "WHERE service = :name"
        ), {"name": svc_name}).fetchall()
        # No dependency vulnerabilities seeded → expect empty, not error
        assert rows == []
