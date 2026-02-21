"""Unit tests for ServiceMetric model."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.database.models.service_metric import ServiceMetric


class TestServiceMetric:
    """Test ServiceMetric model creation and field validation."""

    def test_create_service_metric_minimal(self):
        """Test creating a ServiceMetric with minimal required fields."""
        period_start = datetime(2026, 2, 1, tzinfo=timezone.utc)
        period_end = datetime(2026, 3, 1, tzinfo=timezone.utc)
        
        metric = ServiceMetric(
            service_id=1,
            period_start=period_start,
            period_end=period_end,
        )
        
        assert metric.service_id == 1
        assert metric.period_start == period_start
        assert metric.period_end == period_end
        
        # Note: Default values are only applied when object is persisted to database
        # For non-persisted instances, unset fields are None

    def test_create_service_metric_with_defaults(self):
        """Test creating a ServiceMetric with explicit default values."""
        period_start = datetime(2026, 2, 1, tzinfo=timezone.utc)
        period_end = datetime(2026, 3, 1, tzinfo=timezone.utc)
        
        metric = ServiceMetric(
            service_id=1,
            period_start=period_start,
            period_end=period_end,
            total_repositories=0,
            active_repositories=0,
            total_commits=0,
            total_lines_added=0,
            total_lines_removed=0,
            total_files_modified=0,
            total_prs_created=0,
            total_prs_merged=0,
            total_quality_issues=0,
            total_vulnerabilities=0,
            critical_vulnerabilities=0,
            high_vulnerabilities=0,
            total_dependencies=0,
            eol_dependencies=0,
            unique_contributors=0,
        )
        
        # Verify explicitly set defaults
        assert metric.total_repositories == 0
        assert metric.active_repositories == 0
        assert metric.total_commits == 0
        assert metric.total_lines_added == 0
        assert metric.total_lines_removed == 0
        assert metric.total_files_modified == 0
        assert metric.total_prs_created == 0
        assert metric.total_prs_merged == 0
        assert metric.total_quality_issues == 0
        assert metric.total_vulnerabilities == 0
        assert metric.critical_vulnerabilities == 0
        assert metric.high_vulnerabilities == 0
        assert metric.total_dependencies == 0
        assert metric.eol_dependencies == 0
        assert metric.unique_contributors == 0

    def test_create_service_metric_with_all_fields(self):
        """Test creating a ServiceMetric with all fields populated."""
        period_start = datetime(2026, 2, 1, tzinfo=timezone.utc)
        period_end = datetime(2026, 3, 1, tzinfo=timezone.utc)
        computed = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        metric = ServiceMetric(
            service_id=1,
            period_start=period_start,
            period_end=period_end,
            total_repositories=10,
            active_repositories=8,
            total_commits=150,
            total_lines_added=5000,
            total_lines_removed=2000,
            total_files_modified=300,
            total_prs_created=25,
            total_prs_merged=20,
            avg_pr_review_time_hours=Decimal("24.5"),
            avg_test_coverage=Decimal("85.50"),
            avg_maintainability_index=Decimal("72.30"),
            total_quality_issues=45,
            total_vulnerabilities=5,
            critical_vulnerabilities=1,
            high_vulnerabilities=2,
            total_dependencies=120,
            eol_dependencies=3,
            unique_contributors=15,
            computed_at=computed,
        )
        
        # Repository counts
        assert metric.total_repositories == 10
        assert metric.active_repositories == 8
        
        # Commit metrics
        assert metric.total_commits == 150
        assert metric.total_lines_added == 5000
        assert metric.total_lines_removed == 2000
        assert metric.total_files_modified == 300
        
        # PR metrics
        assert metric.total_prs_created == 25
        assert metric.total_prs_merged == 20
        assert metric.avg_pr_review_time_hours == Decimal("24.5")
        
        # Quality metrics
        assert metric.avg_test_coverage == Decimal("85.50")
        assert metric.avg_maintainability_index == Decimal("72.30")
        assert metric.total_quality_issues == 45
        
        # Security metrics
        assert metric.total_vulnerabilities == 5
        assert metric.critical_vulnerabilities == 1
        assert metric.high_vulnerabilities == 2
        
        # Dependency health
        assert metric.total_dependencies == 120
        assert metric.eol_dependencies == 3
        
        # Activity
        assert metric.unique_contributors == 15
        
        # Audit
        assert metric.computed_at == computed

    def test_service_metric_nullable_fields(self):
        """Test that certain fields can be None."""
        period_start = datetime(2026, 2, 1, tzinfo=timezone.utc)
        period_end = datetime(2026, 3, 1, tzinfo=timezone.utc)
        
        metric = ServiceMetric(
            service_id=1,
            period_start=period_start,
            period_end=period_end,
            avg_pr_review_time_hours=None,
            avg_test_coverage=None,
            avg_maintainability_index=None,
        )
        
        assert metric.avg_pr_review_time_hours is None
        assert metric.avg_test_coverage is None
        assert metric.avg_maintainability_index is None

    def test_service_metric_decimal_precision(self):
        """Test decimal field precision."""
        period_start = datetime(2026, 2, 1, tzinfo=timezone.utc)
        period_end = datetime(2026, 3, 1, tzinfo=timezone.utc)
        
        metric = ServiceMetric(
            service_id=1,
            period_start=period_start,
            period_end=period_end,
            avg_pr_review_time_hours=Decimal("123.45"),
            avg_test_coverage=Decimal("99.99"),
            avg_maintainability_index=Decimal("88.75"),
        )
        
        # Verify decimal values preserved
        assert metric.avg_pr_review_time_hours == Decimal("123.45")
        assert metric.avg_test_coverage == Decimal("99.99")
        assert metric.avg_maintainability_index == Decimal("88.75")

    def test_service_metric_table_name(self):
        """Test that table name is correctly set."""
        assert ServiceMetric.__tablename__ == "service_metrics"

    def test_service_metric_period_range(self):
        """Test period_start and period_end can represent different time ranges."""
        # Monthly range
        monthly_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        monthly_end = datetime(2026, 2, 1, tzinfo=timezone.utc)
        
        metric_monthly = ServiceMetric(
            service_id=1,
            period_start=monthly_start,
            period_end=monthly_end,
        )
        
        assert metric_monthly.period_start == monthly_start
        assert metric_monthly.period_end == monthly_end
        
        # Weekly range
        weekly_start = datetime(2026, 2, 1, tzinfo=timezone.utc)
        weekly_end = datetime(2026, 2, 8, tzinfo=timezone.utc)
        
        metric_weekly = ServiceMetric(
            service_id=2,
            period_start=weekly_start,
            period_end=weekly_end,
        )
        
        assert metric_weekly.period_start == weekly_start
        assert metric_weekly.period_end == weekly_end
