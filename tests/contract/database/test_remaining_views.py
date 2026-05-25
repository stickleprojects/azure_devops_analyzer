"""
Contract tests: remaining uncovered SQL views

Views covered:
  Branch views:
    v_branch_metrics_latest
    v_repo_branch_rollup
  Extraction health / operational views:
    v_extraction_metrics_recent
    v_extraction_run_summary
    v_extraction_runs_active
    v_extraction_repos_per_hour_5m
  Security views:
    v_security_top_repositories_critical_vulns
    v_security_vulnerability_trend
  Per-repo drill-down views:
    v_repo_top_contributors_30d
    v_repo_top_reviewers_30d
    v_repo_total_contributors
    v_repo_pr_status_distribution
    v_repo_lines_changed_daily_trend_30d
  Contributor/global views:
    v_contributor_commits
    v_commits_daily_trend_30d
    v_repository_names
  Package views:
    v_dependency_summary
"""

import uuid
from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy import text

from src.database.models import (
    Organization,
    Project,
    Repository,
    Branch,
    Contributor,
    Commit,
    PullRequest,
    BranchMetric,
    ExtractionRun,
    ExtractionMetric,
    RepositoryDependency,
    Package,
    Vulnerability,
)


# =============================================================================
# Helpers
# =============================================================================

def _make_org_repo(db_session, suffix=None):
    """Return a minimal (org, project, repo) triple."""
    tag = suffix or uuid.uuid4().hex[:8]
    now = datetime.now(timezone.utc)

    org = Organization(
        name=f"remaining-org-{tag}",
        url="https://github.com/test",
        platform="github",
    )
    db_session.add(org)
    db_session.flush()

    project = Project(organization_id=org.organization_id, name=f"proj-{tag}")
    db_session.add(project)
    db_session.flush()

    repo = Repository(
        repo_id=f"remaining-repo-{tag}",
        name=f"repo-{tag}",
        url=f"https://github.com/test/repo-{tag}",
        project_id=project.project_id,
        is_active=True,
        last_analyzed_at=now,
    )
    db_session.add(repo)
    db_session.flush()
    return org, project, repo


# =============================================================================
# Branch views
# =============================================================================

class TestBranchViews:
    @pytest.fixture
    def branch_data(self, db_session):
        now = datetime.now(timezone.utc)
        _, _, repo = _make_org_repo(db_session, "branch")

        branch = Branch(
            repo_id=repo.repo_id,
            branch_name="main",
            latest_commit_sha="abc123",
            is_active=True,
            last_analyzed_at=now,
        )
        db_session.add(branch)
        db_session.flush()

        metric = BranchMetric(
            branch_id=branch.branch_id,
            timestamp=now,
            commit_count=42,
            unique_contributors=3,
            age_days=180,
            staleness_days=2,
            divergence_from_main=0,
        )
        db_session.add(metric)
        db_session.flush()
        return repo, branch

    def test_branch_metrics_latest_returns_row(self, branch_data, db_session):
        repo, branch = branch_data
        row = db_session.execute(text(
            "SELECT repo_id, branch_name, commit_count, unique_contributors, staleness_days "
            "FROM v_branch_metrics_latest WHERE branch_id = :bid"
        ), {"bid": branch.branch_id}).fetchone()
        assert row is not None
        assert row.commit_count == 42
        assert row.unique_contributors == 3

    def test_branch_metrics_latest_uses_most_recent_snapshot(self, branch_data, db_session):
        repo, branch = branch_data
        now = datetime.now(timezone.utc)
        # Add a newer snapshot with different commit_count
        db_session.add(BranchMetric(
            branch_id=branch.branch_id,
            timestamp=now + timedelta(seconds=1),
            commit_count=99,
            unique_contributors=5,
            age_days=181,
            staleness_days=0,
        ))
        db_session.flush()

        row = db_session.execute(text(
            "SELECT commit_count FROM v_branch_metrics_latest WHERE branch_id = :bid"
        ), {"bid": branch.branch_id}).fetchone()
        assert row.commit_count == 99

    def test_repo_branch_rollup_counts_active_branches(self, branch_data, db_session):
        repo, _ = branch_data
        row = db_session.execute(text(
            "SELECT active_branches, stale_branches FROM v_repo_branch_rollup "
            "WHERE repo_id = :rid"
        ), {"rid": repo.repo_id}).fetchone()
        assert row is not None
        assert row.active_branches >= 1

    def test_repo_branch_rollup_stale_flag(self, branch_data, db_session):
        repo, branch = branch_data
        now = datetime.now(timezone.utc)
        # Add a stale branch (staleness_days > 30)
        stale_branch = Branch(
            repo_id=repo.repo_id,
            branch_name="old-feature",
            is_active=True,
            last_analyzed_at=now,
        )
        db_session.add(stale_branch)
        db_session.flush()
        db_session.add(BranchMetric(
            branch_id=stale_branch.branch_id,
            timestamp=now,
            staleness_days=60,
        ))
        db_session.flush()

        row = db_session.execute(text(
            "SELECT stale_branches FROM v_repo_branch_rollup WHERE repo_id = :rid"
        ), {"rid": repo.repo_id}).fetchone()
        assert row.stale_branches >= 1


# =============================================================================
# Extraction operational views
# =============================================================================

class TestExtractionOperationalViews:
    @pytest.fixture
    def extraction_data(self, db_session):
        now = datetime.now(timezone.utc)
        _, _, repo = _make_org_repo(db_session, "extop")

        run = ExtractionRun(
            platform="github",
            organization_name="test-org",
            project_name="test-project",
            status="completed",
            total_repositories=5,
            processed_repositories=5,
            started_at=now - timedelta(minutes=10),
            updated_at=now,
            completed_at=now,
        )
        db_session.add(run)
        db_session.flush()

        metric = ExtractionMetric(
            run_id=run.run_id,
            repository_id=repo.repo_id,
            platform="github",
            status="completed",
            extraction_started_at=now - timedelta(minutes=5),
            extraction_completed_at=now,
            extraction_duration_seconds=300,
        )
        db_session.add(metric)
        db_session.flush()
        return run, repo

    def test_extraction_run_summary_contains_run(self, extraction_data, db_session):
        run, _ = extraction_data
        row = db_session.execute(text(
            "SELECT run_id, platform, status, total_repositories "
            "FROM v_extraction_run_summary WHERE run_id = :rid"
        ), {"rid": run.run_id}).fetchone()
        assert row is not None
        assert row.status == "completed"
        assert row.total_repositories == 5

    def test_extraction_runs_active_is_zero_when_none_running(self, extraction_data, db_session):
        row = db_session.execute(text(
            "SELECT active_runs FROM v_extraction_runs_active"
        )).fetchone()
        assert row is not None
        assert row.active_runs == 0

    def test_extraction_runs_active_counts_running(self, extraction_data, db_session):
        now = datetime.now(timezone.utc)
        db_session.add(ExtractionRun(
            platform="github",
            status="running",
            total_repositories=3,
            processed_repositories=1,
            started_at=now,
            updated_at=now,
        ))
        db_session.flush()

        row = db_session.execute(text(
            "SELECT active_runs FROM v_extraction_runs_active"
        )).fetchone()
        assert row.active_runs >= 1

    def test_extraction_metrics_recent_returns_row(self, extraction_data, db_session):
        rows = db_session.execute(text(
            "SELECT repository, platform, status, error_category, error_subcategory "
            "FROM v_extraction_metrics_recent"
        )).fetchall()
        assert len(rows) >= 1
        col_names = rows[0]._fields
        assert "error_category" in col_names
        assert "error_subcategory" in col_names

    def test_extraction_repos_per_hour_5m_queryable(self, extraction_data, db_session):
        rows = db_session.execute(text(
            "SELECT time, repos_per_hour FROM v_extraction_repos_per_hour_5m"
        )).fetchall()
        # Just must not error; may be empty if time_bucket rounds out of window
        assert isinstance(rows, list)


# =============================================================================
# Security views
# =============================================================================

class TestSecurityRemainingViews:
    @pytest.fixture
    def critical_vuln_data(self, db_session):
        now = datetime.now(timezone.utc)
        _, _, repo = _make_org_repo(db_session, "critvuln")

        pkg = Package(
            package_name="exploit-lib",
            ecosystem="pypi",
            latest_version="1.0.0",
            is_eol=False,
        )
        db_session.add(pkg)
        db_session.flush()

        vuln = Vulnerability(
            package_id=pkg.id,
            cve_id="CVE-2026-9999",
            severity="CRITICAL",
            description="Critical test vulnerability",
        )
        db_session.add(vuln)
        db_session.flush()

        dep = RepositoryDependency(
            repo_id=repo.repo_id,
            package_name="exploit-lib",
            ecosystem="pypi",
            version="0.9.0",
            has_known_vulnerabilities=True,
            last_seen_at=now,
        )
        db_session.add(dep)
        db_session.flush()
        return repo, pkg, vuln

    def test_security_top_repos_critical_vulns_shows_repo(self, critical_vuln_data, db_session):
        repo, _, _ = critical_vuln_data
        rows = db_session.execute(text(
            "SELECT repository, critical_vulns FROM v_security_top_repositories_critical_vulns"
        )).fetchall()
        assert any(r.repository == repo.name for r in rows)
        matching = [r for r in rows if r.repository == repo.name]
        assert matching[0].critical_vulns >= 1

    def test_security_vulnerability_trend_queryable(self, critical_vuln_data, db_session):
        rows = db_session.execute(text(
            "SELECT time, vulnerabilities FROM v_security_vulnerability_trend"
        )).fetchall()
        assert len(rows) >= 1
        assert all(r.vulnerabilities >= 0 for r in rows)


# =============================================================================
# Per-repo drill-down views
# =============================================================================

class TestRepoDetailViews:
    @pytest.fixture
    def repo_detail_data(self, db_session):
        now = datetime.now(timezone.utc)
        _, _, repo = _make_org_repo(db_session, "detail")

        contributors = []
        for i in range(3):
            c = Contributor(email=f"eng{i}@detail.example.com", name=f"Eng {i}")
            db_session.add(c)
            contributors.append(c)
        db_session.flush()

        for i, c in enumerate(contributors):
            db_session.add(Commit(
                commit_sha=uuid.uuid4().hex,
                repo_id=repo.repo_id,
                author_id=c.id,
                commit_date=now - timedelta(days=i + 1),
                message="fix: something",
                lines_added=10,
                lines_removed=5,
            ))
            db_session.add(PullRequest(
                pr_number=200 + i,
                repo_id=repo.repo_id,
                author_id=c.id,
                title=f"PR {i}",
                status="open",
                created_at=now - timedelta(days=i + 1),
            ))
        db_session.flush()
        return repo, contributors

    def test_repo_top_contributors_30d(self, repo_detail_data, db_session):
        repo, _ = repo_detail_data
        rows = db_session.execute(text(
            "SELECT repo_id, contributor, commits FROM v_repo_top_contributors_30d "
            "WHERE repo_id = :rid"
        ), {"rid": repo.repo_id}).fetchall()
        assert len(rows) > 0
        assert all(r.commits > 0 for r in rows)

    def test_repo_total_contributors(self, repo_detail_data, db_session):
        repo, contributors = repo_detail_data
        row = db_session.execute(text(
            "SELECT contributors FROM v_repo_total_contributors WHERE repo_id = :rid"
        ), {"rid": repo.repo_id}).fetchone()
        assert row is not None
        assert row.contributors == len(contributors)

    def test_repo_pr_status_distribution(self, repo_detail_data, db_session):
        repo, _ = repo_detail_data
        rows = db_session.execute(text(
            "SELECT repo_id, status, count FROM v_repo_pr_status_distribution "
            "WHERE repo_id = :rid"
        ), {"rid": repo.repo_id}).fetchall()
        assert len(rows) > 0
        assert any(r.status == "open" for r in rows)

    def test_repo_lines_changed_daily_trend_30d(self, repo_detail_data, db_session):
        repo, _ = repo_detail_data
        rows = db_session.execute(text(
            "SELECT repo_id, time, added, removed FROM v_repo_lines_changed_daily_trend_30d "
            "WHERE repo_id = :rid"
        ), {"rid": repo.repo_id}).fetchall()
        assert len(rows) > 0
        assert all(r.added >= 0 for r in rows)

    def test_repo_top_reviewers_30d_queryable(self, repo_detail_data, db_session):
        # No reviews seeded — view must return without error
        rows = db_session.execute(text(
            "SELECT repo_id, reviewer, reviews FROM v_repo_top_reviewers_30d"
        )).fetchall()
        assert isinstance(rows, list)

    def test_repo_commits_daily_trend_30d(self, repo_detail_data, db_session):
        repo, _ = repo_detail_data
        rows = db_session.execute(text(
            "SELECT repo_id, time, commits FROM v_repo_commits_daily_trend_30d "
            "WHERE repo_id = :rid"
        ), {"rid": repo.repo_id}).fetchall()
        assert len(rows) > 0

    def test_repo_pr_size_distribution_30d(self, repo_detail_data, db_session):
        repo, _ = repo_detail_data
        rows = db_session.execute(text(
            "SELECT repo_id, size_category, count FROM v_repo_pr_size_distribution_30d "
            "WHERE repo_id = :rid"
        ), {"rid": repo.repo_id}).fetchall()
        assert len(rows) > 0

    def test_repo_pr_creation_daily_trend_30d(self, repo_detail_data, db_session):
        repo, _ = repo_detail_data
        rows = db_session.execute(text(
            "SELECT repo_id, time, created FROM v_repo_pr_creation_daily_trend_30d "
            "WHERE repo_id = :rid"
        ), {"rid": repo.repo_id}).fetchall()
        assert len(rows) > 0

    def test_repo_pr_merge_daily_trend_30d(self, repo_detail_data, db_session):
        repo, _ = repo_detail_data
        # Fixture has merged PRs for the merged test in team fixture — seed one here
        now = datetime.now(timezone.utc)
        repo2, contributors = repo_detail_data
        db_session.add(PullRequest(
            pr_number=999,
            repo_id=repo2.repo_id,
            author_id=contributors[0].id,
            title="merged PR",
            status="merged",
            created_at=now - timedelta(days=2),
            merged_at=now - timedelta(days=1),
        ))
        db_session.flush()
        rows = db_session.execute(text(
            "SELECT repo_id, time, merged FROM v_repo_pr_merge_daily_trend_30d "
            "WHERE repo_id = :rid"
        ), {"rid": repo2.repo_id}).fetchall()
        assert len(rows) > 0


# =============================================================================
# Code quality views (queryable checks — no quality data seeded)
# =============================================================================

class TestCodeQualityViews:
    def test_repo_code_quality_latest_queryable(self, db_session):
        rows = db_session.execute(text(
            "SELECT repo_id, branch_id, overall_score FROM v_repo_code_quality_latest"
        )).fetchall()
        assert isinstance(rows, list)

    def test_repo_code_quality_trend_90d_queryable(self, db_session):
        rows = db_session.execute(text(
            "SELECT repo_id, time, overall_score FROM v_repo_code_quality_trend_90d"
        )).fetchall()
        assert isinstance(rows, list)

    def test_repo_issue_severity_latest_queryable(self, db_session):
        rows = db_session.execute(text(
            "SELECT repo_id, severity, count FROM v_repo_issue_severity_latest"
        )).fetchall()
        assert isinstance(rows, list)


# =============================================================================
# Contributor / global views
# =============================================================================

class TestGlobalViews:
    @pytest.fixture
    def global_data(self, db_session):
        now = datetime.now(timezone.utc)
        _, _, repo = _make_org_repo(db_session, "global")
        c = Contributor(email="global@example.com", name="Global Dev")
        db_session.add(c)
        db_session.flush()
        db_session.add(Commit(
            commit_sha=uuid.uuid4().hex,
            repo_id=repo.repo_id,
            author_id=c.id,
            commit_date=now - timedelta(days=1),
            message="chore: update",
        ))
        db_session.flush()
        return repo, c

    def test_contributor_commits_has_row(self, global_data, db_session):
        _, c = global_data
        rows = db_session.execute(text(
            "SELECT author_id, commit_count FROM v_contributor_commits "
            "WHERE author_id = :aid"
        ), {"aid": c.id}).fetchall()
        assert len(rows) >= 1
        assert rows[0].commit_count >= 1

    def test_commits_daily_trend_30d_has_row(self, global_data, db_session):
        rows = db_session.execute(text(
            "SELECT time, commits FROM v_commits_daily_trend_30d"
        )).fetchall()
        assert len(rows) >= 1
        assert all(r.commits > 0 for r in rows)

    def test_repository_names_contains_active_repo(self, global_data, db_session):
        repo, _ = global_data
        row = db_session.execute(text(
            "SELECT repo_id, repository FROM v_repository_names WHERE repo_id = :rid"
        ), {"rid": repo.repo_id}).fetchone()
        assert row is not None
        assert row.repository == repo.name


# =============================================================================
# Package / dependency views
# =============================================================================

class TestDependencySummaryView:
    def test_dependency_summary_queryable(self, db_session):
        rows = db_session.execute(text(
            "SELECT repo_id, package_name, ecosystem, version, "
            "has_known_vulnerabilities, is_eol "
            "FROM v_dependency_summary"
        )).fetchall()
        assert isinstance(rows, list)

    def test_dependency_summary_includes_eol_flag(self, db_session):
        now = datetime.now(timezone.utc)
        _, _, repo = _make_org_repo(db_session, "depsumm")
        pkg = Package(
            package_name="old-lib",
            ecosystem="npm",
            latest_version="5.0.0",
            is_eol=True,
            eol_date=now - timedelta(days=365),
        )
        db_session.add(pkg)
        db_session.flush()
        db_session.add(RepositoryDependency(
            repo_id=repo.repo_id,
            package_name="old-lib",
            ecosystem="npm",
            version="4.0.0",
            has_known_vulnerabilities=False,
            last_seen_at=now,
        ))
        db_session.flush()

        row = db_session.execute(text(
            "SELECT is_eol FROM v_dependency_summary "
            "WHERE repo_id = :rid AND package_name = 'old-lib'"
        ), {"rid": repo.repo_id}).fetchone()
        assert row is not None
        assert row.is_eol is True
