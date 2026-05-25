"""
Contract tests: Team dashboard SQL views

CONTRACT: All v_team_* views are queryable and return structurally correct
results when team-assigned repositories, commits, and pull requests exist.

Views covered:
  v_repository_team_labels        (foundation used by all team views)
  v_team_commits_daily_trend_30d
  v_team_pr_creation_daily_trend_30d
  v_team_pr_merge_daily_trend_30d
  v_team_active_contributors_daily_30d
  v_team_lines_changed_daily_trend_30d
  v_team_repository_health_matrix
  v_team_pr_health_summary_30d
  v_team_vulnerabilities_total_latest
  v_team_pr_size_distribution_30d
  v_team_vulnerabilities_by_severity_latest
  v_team_language_distribution_latest
  v_team_top_contributors_30d
  v_team_top_reviewers_30d
  v_team_performance_summary
  v_team_recent_prs_7d
  v_team_metrics_summary
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from sqlalchemy import text

from src.database.models import (
    Organization,
    Project,
    Repository,
    Team,
    TeamMetric,
    Contributor,
    Commit,
    PullRequest,
    RepositoryStack,
)


# =============================================================================
# Shared fixture — seeds one team with two repos, commits, PRs, languages
# =============================================================================

@pytest.fixture
def team_dataset(db_session):
    """Seed a team with two repos, recent commits, recent PRs, and languages."""
    now = datetime.now(timezone.utc)

    org = Organization(
        name=f"team-test-org-{uuid4().hex[:8]}",
        url="https://dev.azure.com/test",
        platform="azure_devops",
    )
    db_session.add(org)
    db_session.flush()

    team = Team(
        organization_id=org.organization_id,
        name="Platform Team",
        description="Platform infrastructure",
        created_at=now,
    )
    db_session.add(team)
    db_session.flush()

    project = Project(
        organization_id=org.organization_id,
        name="platform-project",
    )
    db_session.add(project)
    db_session.flush()

    repos = []
    for i in range(2):
        repo = Repository(
            repo_id=f"team-test-repo-{uuid4().hex[:8]}",
            name=f"platform-service-{i}",
            url=f"https://github.com/test/platform-service-{i}",
            team_id=team.team_id,
            project_id=project.project_id,
            is_active=True,
            last_analyzed_at=now - timedelta(hours=1),
        )
        db_session.add(repo)
        repos.append(repo)
    db_session.flush()

    # Contributors
    contributors = []
    for i in range(3):
        c = Contributor(email=f"dev{i}@platform.example.com", name=f"Dev {i}")
        db_session.add(c)
        contributors.append(c)
    db_session.flush()

    # Recent commits (within 30d)
    for repo in repos:
        for i, contrib in enumerate(contributors):
            commit = Commit(
                commit_sha=uuid4().hex,
                repo_id=repo.repo_id,
                author_id=contrib.id,
                commit_date=now - timedelta(days=i + 1),
                message=f"feat: change {i}",
                lines_added=10 * (i + 1),
                lines_removed=5 * i,
                files_changed=i + 1,
            )
            db_session.add(commit)

    # Recent PRs (within 30d and 7d)
    for repo in repos:
        for i, contrib in enumerate(contributors):
            merged_at = now - timedelta(days=i + 1)
            pr = PullRequest(
                pr_number=1000 + i,
                repo_id=repo.repo_id,
                author_id=contrib.id,
                title=f"PR {i}",
                status="merged",
                created_at=now - timedelta(days=i + 2),
                merged_at=merged_at,
                files_changed=i + 1,
                lines_added=20,
                lines_removed=5,
                approval_count=1,
                size_category="small",
            )
            db_session.add(pr)

    # Language stack
    for repo in repos:
        db_session.add(RepositoryStack(
            repo_id=repo.repo_id,
            name="Python",
            category="language",
            line_count=5000,
            last_seen_at=now,
        ))

    # TeamMetric row for v_team_metrics_summary
    db_session.add(TeamMetric(
        team_id=team.team_id,
        period_start=now - timedelta(days=30),
        period_end=now,
        total_commits=50,
        total_prs_created=10,
        active_contributors=3,
    ))

    db_session.flush()
    return {"org": org, "team": team, "repos": repos, "contributors": contributors}


# =============================================================================
# Tests
# =============================================================================

class TestRepositoryTeamLabels:
    def test_repos_appear_with_team_name(self, team_dataset, db_session):
        rows = db_session.execute(text(
            "SELECT repo_id, repository, team FROM v_repository_team_labels "
            "WHERE team = 'Platform Team'"
        )).fetchall()
        assert len(rows) == 2
        assert all(r.team == "Platform Team" for r in rows)

    def test_repos_without_team_show_no_team(self, db_session):
        org = Organization(
            name=f"lonely-org-{uuid4().hex[:8]}",
            url="https://example.com",
            platform="github",
        )
        db_session.add(org)
        db_session.flush()
        project = Project(organization_id=org.organization_id, name="p")
        db_session.add(project)
        db_session.flush()
        repo = Repository(
            repo_id=f"teamless-{uuid4().hex[:8]}",
            name="teamless-repo",
            url="https://github.com/test/teamless",
            project_id=project.project_id,
            team_id=None,
            is_active=True,
        )
        db_session.add(repo)
        db_session.flush()

        row = db_session.execute(text(
            "SELECT team FROM v_repository_team_labels WHERE repo_id = :rid"
        ), {"rid": repo.repo_id}).fetchone()
        assert row is not None
        assert row.team == "No Team"


class TestTeamTrendViews:
    """Daily-trend views return rows when data exists within the window."""

    def test_commits_daily_trend_queryable(self, team_dataset, db_session):
        rows = db_session.execute(text(
            "SELECT time, team, commits FROM v_team_commits_daily_trend_30d "
            "WHERE team = 'Platform Team'"
        )).fetchall()
        assert len(rows) > 0
        assert all(r.commits > 0 for r in rows)

    def test_pr_creation_daily_trend_queryable(self, team_dataset, db_session):
        rows = db_session.execute(text(
            "SELECT time, team, created FROM v_team_pr_creation_daily_trend_30d "
            "WHERE team = 'Platform Team'"
        )).fetchall()
        assert len(rows) > 0

    def test_pr_merge_daily_trend_queryable(self, team_dataset, db_session):
        rows = db_session.execute(text(
            "SELECT time, team, merged FROM v_team_pr_merge_daily_trend_30d "
            "WHERE team = 'Platform Team'"
        )).fetchall()
        assert len(rows) > 0

    def test_active_contributors_daily_trend_queryable(self, team_dataset, db_session):
        rows = db_session.execute(text(
            "SELECT time, team, contributors FROM v_team_active_contributors_daily_30d "
            "WHERE team = 'Platform Team'"
        )).fetchall()
        assert len(rows) > 0

    def test_lines_changed_daily_trend_queryable(self, team_dataset, db_session):
        rows = db_session.execute(text(
            "SELECT time, team, added, removed FROM v_team_lines_changed_daily_trend_30d "
            "WHERE team = 'Platform Team'"
        )).fetchall()
        assert len(rows) > 0
        assert all(r.added >= 0 and r.removed >= 0 for r in rows)

    def test_pr_size_distribution_queryable(self, team_dataset, db_session):
        rows = db_session.execute(text(
            "SELECT team, size, count FROM v_team_pr_size_distribution_30d "
            "WHERE team = 'Platform Team'"
        )).fetchall()
        assert len(rows) > 0


class TestTeamAggregateViews:
    def test_repository_health_matrix_has_both_repos(self, team_dataset, db_session):
        rows = db_session.execute(text(
            "SELECT repo_id, repository, team, commits_30d, open_prs "
            "FROM v_team_repository_health_matrix WHERE team = 'Platform Team'"
        )).fetchall()
        assert len(rows) == 2
        col_names = rows[0]._fields
        assert "commits_30d" in col_names
        assert "open_prs" in col_names

    def test_pr_health_summary_has_team_row(self, team_dataset, db_session):
        rows = db_session.execute(text(
            "SELECT team, avg_merge_time_days, avg_approvals "
            "FROM v_team_pr_health_summary_30d WHERE team = 'Platform Team'"
        )).fetchall()
        assert len(rows) == 1
        assert rows[0].avg_merge_time_days >= 0

    def test_performance_summary_counts_correct(self, team_dataset, db_session):
        row = db_session.execute(text(
            "SELECT team, repositories, contributors, commits_30d "
            "FROM v_team_performance_summary WHERE team = 'Platform Team'"
        )).fetchone()
        assert row is not None
        assert row.repositories == 2
        assert row.commits_30d > 0

    def test_top_contributors_lists_devs(self, team_dataset, db_session):
        rows = db_session.execute(text(
            "SELECT team, contributor, commits FROM v_team_top_contributors_30d "
            "WHERE team = 'Platform Team'"
        )).fetchall()
        assert len(rows) > 0
        assert all(r.commits > 0 for r in rows)

    def test_language_distribution_shows_python(self, team_dataset, db_session):
        rows = db_session.execute(text(
            "SELECT team, language, lines FROM v_team_language_distribution_latest "
            "WHERE team = 'Platform Team'"
        )).fetchall()
        assert len(rows) > 0
        assert any(r.language == "Python" for r in rows)

    def test_recent_prs_7d_returns_rows(self, team_dataset, db_session):
        rows = db_session.execute(text(
            "SELECT team, pr_number, status FROM v_team_recent_prs_7d "
            "WHERE team = 'Platform Team'"
        )).fetchall()
        assert len(rows) > 0

    def test_vulnerabilities_total_queryable(self, team_dataset, db_session):
        rows = db_session.execute(text(
            "SELECT team, total_vulnerabilities FROM v_team_vulnerabilities_total_latest "
            "WHERE team = 'Platform Team'"
        )).fetchall()
        # May be 0 (no vulns seeded) but must not error and must have the team row
        assert len(rows) == 1
        assert rows[0].total_vulnerabilities >= 0

    def test_vulnerabilities_by_severity_queryable(self, team_dataset, db_session):
        # No vulns seeded — view should return empty without error
        rows = db_session.execute(text(
            "SELECT team, severity, count FROM v_team_vulnerabilities_by_severity_latest"
        )).fetchall()
        assert isinstance(rows, list)


class TestTeamMetricsSummary:
    def test_metrics_summary_aggregates_team(self, team_dataset, db_session):
        row = db_session.execute(text(
            "SELECT team_name, total_commits, total_prs_created "
            "FROM v_team_metrics_summary WHERE team_name = 'Platform Team'"
        )).fetchone()
        assert row is not None
        assert row.total_commits == 50
        assert row.total_prs_created == 10


class TestTeamTopReviewers:
    def test_top_reviewers_queryable(self, team_dataset, db_session):
        # No PR reviews seeded — view must return without error
        rows = db_session.execute(text(
            "SELECT team, reviewer, reviews FROM v_team_top_reviewers_30d"
        )).fetchall()
        assert isinstance(rows, list)
