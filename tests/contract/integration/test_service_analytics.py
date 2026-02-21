"""
Integration tests for service-level analytics (FR-10.4).

Tests metric aggregation across multiple repositories, edge cases
(no repos, empty periods), time range filtering, and batch compute.
"""

import pytest
from datetime import datetime, timedelta, UTC
from decimal import Decimal

from src.database.models import (
    Contributor,
    ContributorMetric,
    Dependency,
    PullRequest,
    Repository,
    RepositoryService,
    Service,
    ServiceMetric,
    Vulnerability,
)
from src.database.models.quality import CodeQualityMetric
from src.database.service_analytics import (
    compute_all_services_metrics,
    compute_service_metrics,
    get_latest_service_metrics,
    get_service_metrics,
)


# ---------------------------------------------------------------------------
# Test-local fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def service(test_session):
    """Create a bare Service (no repos linked)."""
    svc = Service(name="test-service-analytics")
    test_session.add(svc)
    test_session.commit()
    return svc


@pytest.fixture
def repo_a(test_session):
    """First standalone test repository."""
    repo = Repository(
        repo_id="svc-int-repo-a",
        name="Service Integration Repo A",
        url="https://github.com/test/svc-int-repo-a",
    )
    test_session.add(repo)
    test_session.commit()
    return repo


@pytest.fixture
def repo_b(test_session):
    """Second standalone test repository."""
    repo = Repository(
        repo_id="svc-int-repo-b",
        name="Service Integration Repo B",
        url="https://github.com/test/svc-int-repo-b",
    )
    test_session.add(repo)
    test_session.commit()
    return repo


@pytest.fixture
def service_with_repos(test_session, service, repo_a, repo_b):
    """Service linked to two repositories."""
    test_session.add(
        RepositoryService(repo_id=repo_a.repo_id, service_id=service.service_id)
    )
    test_session.add(
        RepositoryService(repo_id=repo_b.repo_id, service_id=service.service_id)
    )
    test_session.commit()
    return service


@pytest.fixture
def period():
    """A one-day test period anchored on 2025-01-01 UTC."""
    start = datetime(2025, 1, 1, tzinfo=UTC)
    end = start + timedelta(days=1)
    return start, end


@pytest.fixture
def two_contributors(test_session):
    """Two distinct contributors."""
    c1 = Contributor(name="Alice Analytics", email="alice.analytics@test.com")
    c2 = Contributor(name="Bob Analytics", email="bob.analytics@test.com")
    test_session.add_all([c1, c2])
    test_session.commit()
    return c1, c2


# ---------------------------------------------------------------------------
# TestComputeEdgeCases
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestComputeEdgeCases:
    """Edge cases: missing service, service with no repos."""

    def test_raises_for_unknown_service(self, test_session, period):
        """CONTRACT: compute_service_metrics raises ValueError for non-existent service.

        Verify:
        - ValueError is raised
        - Error message includes the service ID
        """
        start, end = period
        with pytest.raises(ValueError, match="9999"):
            compute_service_metrics(test_session, 9999, start, end)

    def test_returns_zero_metric_when_no_repos(self, test_session, service, period):
        """CONTRACT: Service with no linked repos returns a zero-valued ServiceMetric.

        Verify:
        - Returned metric has correct service_id
        - All numeric fields are zero
        - No exception is raised
        """
        start, end = period
        metric = compute_service_metrics(test_session, service.service_id, start, end)

        assert metric.service_id == service.service_id
        assert metric.total_repositories == 0
        assert metric.active_repositories == 0
        assert metric.total_commits == 0
        assert metric.total_prs_created == 0
        assert metric.unique_contributors == 0
        assert metric.total_vulnerabilities == 0
        assert metric.total_dependencies == 0


# ---------------------------------------------------------------------------
# TestAggregateContributorMetrics
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestAggregateContributorMetrics:
    """Contributor metric aggregation across repos."""

    def test_sums_commits_across_repos(
        self,
        test_session,
        service_with_repos,
        repo_a,
        repo_b,
        two_contributors,
        period,
    ):
        """CONTRACT: commit_count, lines, and PRs are summed across both repos.

        Verify:
        - total_commits = sum of both repos
        - total_prs_created = sum of both repos
        - total_lines_added / removed / files_modified also summed
        """
        start, end = period
        c1, c2 = two_contributors

        test_session.add(
            ContributorMetric(
                repo_id=repo_a.repo_id,
                contributor_id=c1.id,
                period_start=start,
                period_end=end,
                commit_count=10,
                pr_created=2,
                lines_added=100,
                lines_removed=50,
                files_modified=5,
            )
        )
        test_session.add(
            ContributorMetric(
                repo_id=repo_b.repo_id,
                contributor_id=c2.id,
                period_start=start,
                period_end=end,
                commit_count=20,
                pr_created=3,
                lines_added=200,
                lines_removed=80,
                files_modified=8,
            )
        )
        test_session.commit()

        metric = compute_service_metrics(
            test_session, service_with_repos.service_id, start, end
        )

        assert metric.total_commits == 30
        assert metric.total_prs_created == 5
        assert metric.total_lines_added == 300
        assert metric.total_lines_removed == 130
        assert metric.total_files_modified == 13

    def test_excludes_metrics_outside_period(
        self,
        test_session,
        service_with_repos,
        repo_a,
        two_contributors,
        period,
    ):
        """CONTRACT: Contributor metrics outside the period window are excluded.

        Verify:
        - Only metrics within [period_start, period_end) contribute
        - Metrics from a prior period are ignored
        """
        start, end = period
        c1, _ = two_contributors

        # Inside period
        test_session.add(
            ContributorMetric(
                repo_id=repo_a.repo_id,
                contributor_id=c1.id,
                period_start=start,
                period_end=end,
                commit_count=5,
                pr_created=1,
                lines_added=10,
                lines_removed=0,
                files_modified=1,
            )
        )
        # Outside period — one month earlier
        test_session.add(
            ContributorMetric(
                repo_id=repo_a.repo_id,
                contributor_id=c1.id,
                period_start=start - timedelta(days=30),
                period_end=start,
                commit_count=999,
                pr_created=999,
                lines_added=999,
                lines_removed=999,
                files_modified=999,
            )
        )
        test_session.commit()

        metric = compute_service_metrics(
            test_session, service_with_repos.service_id, start, end
        )

        assert metric.total_commits == 5
        assert metric.total_prs_created == 1

    def test_total_repositories_counts_linked_repos(
        self, test_session, service_with_repos, period
    ):
        """CONTRACT: total_repositories reflects the number of linked repos.

        Verify:
        - total_repositories matches the count of RepositoryService rows
        """
        start, end = period
        metric = compute_service_metrics(
            test_session, service_with_repos.service_id, start, end
        )
        assert metric.total_repositories == 2


# ---------------------------------------------------------------------------
# TestAggregateQualityMetrics
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestAggregateQualityMetrics:
    """Quality metric aggregation."""

    def test_averages_test_coverage_across_repos(
        self, test_session, service_with_repos, repo_a, repo_b, period
    ):
        """CONTRACT: avg_test_coverage is the mean of all quality rows in the period.

        Verify:
        - avg_test_coverage = (80 + 60) / 2 = 70
        - total_quality_issues = sum of all repos
        """
        start, end = period
        mid = start + timedelta(hours=6)

        test_session.add(
            CodeQualityMetric(
                repo_id=repo_a.repo_id,
                timestamp=mid,
                test_coverage=Decimal("80.00"),
                maintainability_index=Decimal("70.00"),
                total_issues=10,
            )
        )
        test_session.add(
            CodeQualityMetric(
                repo_id=repo_b.repo_id,
                timestamp=mid + timedelta(hours=1),
                test_coverage=Decimal("60.00"),
                maintainability_index=Decimal("50.00"),
                total_issues=5,
            )
        )
        test_session.commit()

        metric = compute_service_metrics(
            test_session, service_with_repos.service_id, start, end
        )

        assert float(metric.avg_test_coverage) == pytest.approx(70.0, abs=1.0)
        assert metric.total_quality_issues == 15

    def test_quality_nulls_when_no_data(
        self, test_session, service_with_repos, period
    ):
        """CONTRACT: avg_test_coverage is None when no quality records exist.

        Verify:
        - avg_test_coverage is None
        - avg_maintainability_index is None
        - total_quality_issues is 0
        """
        start, end = period
        metric = compute_service_metrics(
            test_session, service_with_repos.service_id, start, end
        )

        assert metric.avg_test_coverage is None
        assert metric.avg_maintainability_index is None
        assert metric.total_quality_issues == 0


# ---------------------------------------------------------------------------
# TestAggregatePRMetrics
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestAggregatePRMetrics:
    """PR metric aggregation."""

    def test_counts_merged_prs_in_period(
        self, test_session, service_with_repos, repo_a, period
    ):
        """CONTRACT: Only merged PRs whose created_at falls in the period are counted.

        Verify:
        - Open PR not counted
        - PR merged before period not counted
        - Merged PR in period counted once
        """
        start, end = period

        pr_merged = PullRequest(
            repo_id=repo_a.repo_id,
            pr_number=101,
            title="Merged in period",
            created_at=start + timedelta(hours=1),
            merged_at=start + timedelta(hours=5),
        )
        pr_open = PullRequest(
            repo_id=repo_a.repo_id,
            pr_number=102,
            title="Still open",
            created_at=start + timedelta(hours=2),
        )
        pr_old = PullRequest(
            repo_id=repo_a.repo_id,
            pr_number=103,
            title="Merged before period",
            created_at=start - timedelta(days=2),
            merged_at=start - timedelta(days=1),
        )
        test_session.add_all([pr_merged, pr_open, pr_old])
        test_session.commit()

        metric = compute_service_metrics(
            test_session, service_with_repos.service_id, start, end
        )

        assert metric.total_prs_merged == 1

    def test_avg_pr_review_time_computed(
        self, test_session, service_with_repos, repo_a, period
    ):
        """CONTRACT: avg_pr_review_time_hours is (merged_at - created_at) in hours.

        Verify:
        - A 4-hour turnaround yields avg_pr_review_time_hours ≈ 4.0
        """
        start, end = period

        pr = PullRequest(
            repo_id=repo_a.repo_id,
            pr_number=200,
            title="PR with known review time",
            created_at=start + timedelta(hours=1),
            merged_at=start + timedelta(hours=5),  # exactly 4 hours
        )
        test_session.add(pr)
        test_session.commit()

        metric = compute_service_metrics(
            test_session, service_with_repos.service_id, start, end
        )

        assert float(metric.avg_pr_review_time_hours) == pytest.approx(4.0, abs=0.1)


# ---------------------------------------------------------------------------
# TestAggregateSecurityMetrics
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestAggregateSecurityMetrics:
    """Security and dependency metric aggregation (point-in-time, no period filter)."""

    def test_counts_vulnerabilities_by_severity(
        self, test_session, service_with_repos, repo_a, repo_b, period
    ):
        """CONTRACT: vulnerable dependency count and severity breakdowns are correct.

        Verify:
        - total_vulnerabilities = distinct deps that have vulnerabilities
        - critical_vulnerabilities = count of CRITICAL vuln rows
        - high_vulnerabilities = count of HIGH vuln rows
        """
        now = datetime.now(UTC)
        start, end = period

        dep_a = Dependency(
            repo_id=repo_a.repo_id,
            package_name="pkg-critical",
            ecosystem="PyPI",
            first_seen_at=now,
            last_seen_at=now,
        )
        dep_b = Dependency(
            repo_id=repo_b.repo_id,
            package_name="pkg-high",
            ecosystem="npm",
            first_seen_at=now,
            last_seen_at=now,
        )
        test_session.add_all([dep_a, dep_b])
        test_session.commit()

        test_session.add(
            Vulnerability(dependency_id=dep_a.id, severity="CRITICAL", summary="critical vuln")
        )
        test_session.add(
            Vulnerability(dependency_id=dep_b.id, severity="HIGH", summary="high vuln 1")
        )
        test_session.add(
            Vulnerability(dependency_id=dep_b.id, severity="HIGH", summary="high vuln 2")
        )
        test_session.commit()

        metric = compute_service_metrics(
            test_session, service_with_repos.service_id, start, end
        )

        # total_vulnerabilities = distinct vulnerable deps (dep_a + dep_b = 2)
        assert metric.total_vulnerabilities == 2
        assert metric.critical_vulnerabilities == 1
        assert metric.high_vulnerabilities == 2

    def test_counts_eol_dependencies(
        self, test_session, service_with_repos, repo_a, repo_b, period
    ):
        """CONTRACT: eol_dependencies counts is_eol=True deps across all repos.

        Verify:
        - eol_dependencies = count of EOL deps across both repos
        - total_dependencies = count of all deps across both repos
        """
        now = datetime.now(UTC)
        start, end = period

        test_session.add(
            Dependency(
                repo_id=repo_a.repo_id,
                package_name="eol-pkg",
                ecosystem="PyPI",
                is_eol=True,
                first_seen_at=now,
                last_seen_at=now,
            )
        )
        test_session.add(
            Dependency(
                repo_id=repo_a.repo_id,
                package_name="current-pkg",
                ecosystem="PyPI",
                is_eol=False,
                first_seen_at=now,
                last_seen_at=now,
            )
        )
        test_session.add(
            Dependency(
                repo_id=repo_b.repo_id,
                package_name="another-eol-pkg",
                ecosystem="npm",
                is_eol=True,
                first_seen_at=now,
                last_seen_at=now,
            )
        )
        test_session.commit()

        metric = compute_service_metrics(
            test_session, service_with_repos.service_id, start, end
        )

        assert metric.eol_dependencies == 2
        assert metric.total_dependencies == 3


# ---------------------------------------------------------------------------
# TestUniqueContributorsAndActiveRepos
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestUniqueContributorsAndActiveRepos:
    """Cross-repo deduplication of contributors and active repository counting."""

    def test_unique_contributors_deduped_across_repos(
        self,
        test_session,
        service_with_repos,
        repo_a,
        repo_b,
        two_contributors,
        period,
    ):
        """CONTRACT: The same contributor in two repos counts as one unique contributor.

        Verify:
        - c1 committed to both repos → still counts as 1
        - c2 committed to one repo → adds 1
        - unique_contributors == 2 (not 3)
        """
        start, end = period
        c1, c2 = two_contributors

        # c1 contributed to both repos
        test_session.add(
            ContributorMetric(
                repo_id=repo_a.repo_id,
                contributor_id=c1.id,
                period_start=start,
                period_end=end,
                commit_count=5,
                pr_created=0,
                lines_added=0,
                lines_removed=0,
                files_modified=0,
            )
        )
        test_session.add(
            ContributorMetric(
                repo_id=repo_b.repo_id,
                contributor_id=c1.id,
                period_start=start,
                period_end=end,
                commit_count=3,
                pr_created=0,
                lines_added=0,
                lines_removed=0,
                files_modified=0,
            )
        )
        # c2 contributed to repo_a only
        test_session.add(
            ContributorMetric(
                repo_id=repo_a.repo_id,
                contributor_id=c2.id,
                period_start=start,
                period_end=end,
                commit_count=1,
                pr_created=0,
                lines_added=0,
                lines_removed=0,
                files_modified=0,
            )
        )
        test_session.commit()

        metric = compute_service_metrics(
            test_session, service_with_repos.service_id, start, end
        )

        assert metric.unique_contributors == 2

    def test_active_repos_excludes_zero_commit_repos(
        self,
        test_session,
        service_with_repos,
        repo_a,
        repo_b,
        two_contributors,
        period,
    ):
        """CONTRACT: active_repositories counts only repos with commit_count > 0.

        Verify:
        - repo_a with commits is counted
        - repo_b with commit_count=0 is NOT counted
        - active_repositories == 1
        """
        start, end = period
        c1, _ = two_contributors

        test_session.add(
            ContributorMetric(
                repo_id=repo_a.repo_id,
                contributor_id=c1.id,
                period_start=start,
                period_end=end,
                commit_count=5,
                pr_created=0,
                lines_added=0,
                lines_removed=0,
                files_modified=0,
            )
        )
        test_session.add(
            ContributorMetric(
                repo_id=repo_b.repo_id,
                contributor_id=c1.id,
                period_start=start,
                period_end=end,
                commit_count=0,  # inactive
                pr_created=0,
                lines_added=0,
                lines_removed=0,
                files_modified=0,
            )
        )
        test_session.commit()

        metric = compute_service_metrics(
            test_session, service_with_repos.service_id, start, end
        )

        assert metric.active_repositories == 1


# ---------------------------------------------------------------------------
# TestGetServiceMetrics
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestGetServiceMetrics:
    """Retrieval functions: get_service_metrics and get_latest_service_metrics."""

    def test_get_service_metrics_returns_desc_order(self, test_session, service):
        """CONTRACT: get_service_metrics returns records ordered by period_start DESC.

        Verify:
        - Three metrics stored with different months
        - Results ordered newest-first
        """
        jan = datetime(2025, 1, 1, tzinfo=UTC)
        feb = datetime(2025, 2, 1, tzinfo=UTC)
        mar = datetime(2025, 3, 1, tzinfo=UTC)

        for start in [jan, feb, mar]:
            test_session.add(
                ServiceMetric(
                    service_id=service.service_id,
                    period_start=start,
                    period_end=start + timedelta(days=28),
                    computed_at=datetime.now(UTC),
                )
            )
        test_session.commit()

        results = get_service_metrics(test_session, service.service_id)

        assert len(results) == 3
        assert results[0].period_start >= results[1].period_start
        assert results[1].period_start >= results[2].period_start

    def test_get_service_metrics_time_range_filter(self, test_session, service):
        """CONTRACT: period_start/end arguments restrict which metrics are returned.

        Verify:
        - Only the February record is returned when filtered to [feb, mar)
        """
        jan = datetime(2025, 1, 1, tzinfo=UTC)
        feb = datetime(2025, 2, 1, tzinfo=UTC)
        mar = datetime(2025, 3, 1, tzinfo=UTC)

        for start in [jan, feb, mar]:
            test_session.add(
                ServiceMetric(
                    service_id=service.service_id,
                    period_start=start,
                    period_end=start + timedelta(days=28),
                    computed_at=datetime.now(UTC),
                )
            )
        test_session.commit()

        results = get_service_metrics(
            test_session,
            service.service_id,
            period_start=feb,
            period_end=mar,
        )

        assert len(results) == 1
        assert results[0].period_start == feb

    def test_get_latest_returns_most_recent_metric(self, test_session, service):
        """CONTRACT: get_latest_service_metrics returns the highest period_start record.

        Verify:
        - Two metrics stored (January, March)
        - Returns the March one
        """
        jan = datetime(2025, 1, 1, tzinfo=UTC)
        mar = datetime(2025, 3, 1, tzinfo=UTC)

        test_session.add(
            ServiceMetric(
                service_id=service.service_id,
                period_start=jan,
                period_end=jan + timedelta(days=31),
                computed_at=datetime.now(UTC),
            )
        )
        test_session.add(
            ServiceMetric(
                service_id=service.service_id,
                period_start=mar,
                period_end=mar + timedelta(days=31),
                computed_at=datetime.now(UTC),
            )
        )
        test_session.commit()

        latest = get_latest_service_metrics(test_session, service.service_id)

        assert latest is not None
        assert latest.period_start == mar

    def test_get_latest_returns_none_when_no_metrics(self, test_session, service):
        """CONTRACT: get_latest_service_metrics returns None when no metrics exist.

        Verify:
        - Fresh service with no stored metrics → None returned
        """
        result = get_latest_service_metrics(test_session, service.service_id)

        assert result is None


# ---------------------------------------------------------------------------
# TestBatchCompute
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestBatchCompute:
    """Batch metric computation via compute_all_services_metrics."""

    def test_batch_computes_for_all_services(self, test_session, period):
        """CONTRACT: compute_all_services_metrics returns one metric per service.

        Verify:
        - Two services created
        - Both appear in the results
        """
        start, end = period
        svc1 = Service(name="batch-analytics-svc-1")
        svc2 = Service(name="batch-analytics-svc-2")
        test_session.add_all([svc1, svc2])
        test_session.commit()

        results = compute_all_services_metrics(test_session, start, end)

        service_ids = {m.service_id for m in results}
        assert svc1.service_id in service_ids
        assert svc2.service_id in service_ids

    def test_batch_skips_failing_service(self, test_session, period, monkeypatch):
        """CONTRACT: A failure for one service does not abort the batch.

        Verify:
        - compute_service_metrics is called for both services
        - The failing service is skipped and not in results
        - The passing service is returned
        """
        start, end = period
        svc_ok = Service(name="batch-ok-svc-analytics")
        svc_fail = Service(name="batch-fail-svc-analytics")
        test_session.add_all([svc_ok, svc_fail])
        test_session.commit()

        call_count = 0
        original_compute = compute_service_metrics

        def patched_compute(session, service_id, p_start, p_end):
            nonlocal call_count
            call_count += 1
            if service_id == svc_fail.service_id:
                raise RuntimeError("Simulated per-service failure")
            return original_compute(session, service_id, p_start, p_end)

        monkeypatch.setattr(
            "src.database.service_analytics.compute_service_metrics",
            patched_compute,
        )

        results = compute_all_services_metrics(test_session, start, end)

        assert call_count == 2
        result_ids = {m.service_id for m in results}
        assert svc_ok.service_id in result_ids
        assert svc_fail.service_id not in result_ids
