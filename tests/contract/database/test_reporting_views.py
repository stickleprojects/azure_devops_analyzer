import pytest
from sqlalchemy import text
from datetime import datetime, timedelta
from src.database.storage import (
    store_organization,
    store_project,
    store_repository,
    store_commit,
    store_pull_request,
    store_languages,
)
from src.extractors.base import Platform, LanguageData
from tests.fixtures.sample_data import (
    sample_organization_data,
    sample_repository_data,
    sample_commit_data,
    sample_pull_request_data,
)

# =============================================================================
# Per-Repository Breakdown Views Tests
# =============================================================================

@pytest.mark.integration
def test_v_open_prs(db_session):
    """Test open PRs count per repository"""
    # Setup test data
    org_data = sample_organization_data(name="test-org", platform=Platform.GITHUB)
    org = store_organization(db_session, org_data)
    project = store_project(db_session, org, "test-project", "Test Project")
    repo_data = sample_repository_data(repo_id="repo1", name="test-repo")
    repo = store_repository(db_session, project, repo_data)
    
    # Create an open PR
    pr_data = sample_pull_request_data(
        pr_number=1, title="Open PR", status="open"
    )
    store_pull_request(db_session, repo.repo_id, pr_data)
    db_session.commit()

    # Query the view
    result = db_session.execute(text("SELECT repo_id, count FROM v_open_prs"))
    open_prs = result.fetchall()

    # Assert the view returns correct aggregated counts
    assert len(open_prs) == 1
    assert open_prs[0].count == 1

@pytest.mark.integration
def test_v_merged_prs_30d(db_session):
    """Test merged PRs count per repository"""
    # Setup test data
    org_data = sample_organization_data(name="test-org", platform=Platform.GITHUB)
    org = store_organization(db_session, org_data)
    project = store_project(db_session, org, "test-project", "Test Project")
    repo_data = sample_repository_data(repo_id="repo1", name="test-repo")
    repo = store_repository(db_session, project, repo_data)
    
    # Create a merged PR within 30 days
    pr_data = sample_pull_request_data(
        pr_number=1, title="Merged PR", status="merged",
        merged_at=datetime.now() - timedelta(days=20)
    )
    store_pull_request(db_session, repo.repo_id, pr_data)
    db_session.commit()

    # Query the view
    result = db_session.execute(text("SELECT repo_id, count FROM v_merged_prs_30d"))
    merged_prs_30d = result.fetchall()

    # Assert the view returns correct aggregated counts
    assert len(merged_prs_30d) == 1
    assert merged_prs_30d[0].count == 1

@pytest.mark.integration
def test_v_closed_prs_30d(db_session):
    """Test closed PRs count per repository"""
    # Setup test data
    org_data = sample_organization_data(name="test-org", platform=Platform.GITHUB)
    org = store_organization(db_session, org_data)
    project = store_project(db_session, org, "test-project", "Test Project")
    repo_data = sample_repository_data(repo_id="repo1", name="test-repo")
    repo = store_repository(db_session, project, repo_data)
    
    # Create a closed PR within 30 days
    pr_data = sample_pull_request_data(
        pr_number=1, title="Closed PR", status="closed",
        closed_at=datetime.now() - timedelta(days=10)
    )
    store_pull_request(db_session, repo.repo_id, pr_data)
    db_session.commit()

    # Query the view
    result = db_session.execute(text("SELECT repo_id, count FROM v_closed_prs_30d"))
    closed_prs_30d = result.fetchall()

    # Assert the view returns correct aggregated counts
    assert len(closed_prs_30d) == 1
    assert closed_prs_30d[0].count == 1

@pytest.mark.integration
def test_v_active_contributors_30d(db_session):
    """Test active contributors count per repository"""
    # Setup test data
    org_data = sample_organization_data(name="test-org", platform=Platform.GITHUB)
    org = store_organization(db_session, org_data)
    project = store_project(db_session, org, "test-project", "Test Project")
    repo_data = sample_repository_data(repo_id="repo1", name="test-repo")
    repo = store_repository(db_session, project, repo_data)
    
    # Create commits from multiple authors
    for i, author_email in enumerate(["author1@example.com", "author2@example.com", "author3@example.com"]):
        commit_data = sample_commit_data(
            sha=f"sha{i}",
            author_email=author_email,
            commit_date=datetime.now() - timedelta(days=5),
            message=f"Commit by {author_email}"
        )
        store_commit(db_session, repo.repo_id, "main", commit_data)
    db_session.commit()

    # Query the view
    result = db_session.execute(text("SELECT repo_id, count FROM v_active_contributors_30d"))
    active_contributors_30d = result.fetchall()

    # Assert the view returns correct aggregated counts
    assert len(active_contributors_30d) == 1
    assert active_contributors_30d[0].count == 3

@pytest.mark.integration
def test_v_commits_30d(db_session):
    """Test commits count per repository"""
    # Setup test data
    org_data = sample_organization_data(name="test-org", platform=Platform.GITHUB)
    org = store_organization(db_session, org_data)
    project = store_project(db_session, org, "test-project", "Test Project")
    repo_data = sample_repository_data(repo_id="repo1", name="test-repo")
    repo = store_repository(db_session, project, repo_data)
    
    # Create multiple commits
    for i in range(5):
        commit_data = sample_commit_data(
            sha=f"sha{i}",
            author_email="developer@example.com",
            commit_date=datetime.now() - timedelta(days=5),
            message=f"Commit {i}"
        )
        store_commit(db_session, repo.repo_id, "main", commit_data)
    db_session.commit()

    # Query the view
    result = db_session.execute(text("SELECT repo_id, count FROM v_commits_30d"))
    commits_30d = result.fetchall()

    # Assert the view returns correct aggregated counts
    assert len(commits_30d) == 1
    assert commits_30d[0].count == 5

@pytest.mark.integration
def test_v_repository_summary(db_session):
    """Test repository summary view"""
    # Setup test data
    org_data = sample_organization_data(name="test-org", platform=Platform.GITHUB)
    org = store_organization(db_session, org_data)
    project = store_project(db_session, org, "test-project", "Test Project")
    repo_data = sample_repository_data(repo_id="repo1", name="test-repo")
    repo = store_repository(db_session, project, repo_data)
    
    # Create a commit
    commit_data = sample_commit_data(
        sha="abc123",
        author_email="developer@example.com",
        commit_date=datetime.now(),
        message="test"
    )
    store_commit(db_session, repo.repo_id, "main", commit_data)
    db_session.commit()

    # Query the view
    result = db_session.execute(text("SELECT repo_id, name FROM v_repository_summary"))
    repository_summary = result.fetchall()

    # Assert the view returns correct data
    assert len(repository_summary) == 1
    assert repository_summary[0].name == "test-repo"

@pytest.mark.integration
def test_v_language_summary(db_session):
    """Test language summary view"""
    # Setup test data
    org_data = sample_organization_data(name="test-org", platform=Platform.GITHUB)
    org = store_organization(db_session, org_data)
    project = store_project(db_session, org, "test-project", "Test Project")
    repo_data = sample_repository_data(repo_id="repo1", name="test-repo")
    repo = store_repository(db_session, project, repo_data)
    
    # Store languages for the repository
    languages_data = [LanguageData(language="Python", percentage=90, byte_count=50000)]
    store_languages(db_session, repo.repo_id, languages_data)
    db_session.commit()

    # Query the view
    result = db_session.execute(text("SELECT repo_id, language FROM v_language_summary"))
    language_summary = result.fetchall()

    # Assert the view returns correct aggregated counts
    assert len(language_summary) == 1
    assert language_summary[0].language == "Python"


# =============================================================================
# Global Summary Views (Dashboard Top-Level Metrics)
# =============================================================================

@pytest.mark.integration
def test_v_open_prs_total(db_session):
    """Test global open PRs count"""
    # Setup: Create org->project->repo hierarchy
    org_data = sample_organization_data(name="test-org", platform=Platform.GITHUB)
    org = store_organization(db_session, org_data)
    project = store_project(db_session, org, "test-project", "Test Project")
    repo_data = sample_repository_data(repo_id="repo1", name="test-repo")
    repo = store_repository(db_session, project, repo_data)

    for i in range(3):
        pr_data = sample_pull_request_data(pr_number=i+1, title=f"Open PR {i}", status="open")
        store_pull_request(db_session, repo.repo_id, pr_data)
    db_session.commit()

    result = db_session.execute(text("SELECT open_prs FROM v_open_prs_total"))
    row = result.fetchone()

    assert row is not None
    assert row.open_prs == 3


@pytest.mark.integration
def test_v_merged_prs_30d_total(db_session):
    """Test global merged PRs count in last 30 days"""
    org_data = sample_organization_data(name="test-org", platform=Platform.GITHUB)
    org = store_organization(db_session, org_data)
    project = store_project(db_session, org, "test-project", "Test Project")
    repo_data = sample_repository_data(repo_id="repo1", name="test-repo")
    repo = store_repository(db_session, project, repo_data)

    pr_data = sample_pull_request_data(pr_number=1, title="Merged PR", status="merged", 
                                       merged_at=datetime.now() - timedelta(days=15))
    store_pull_request(db_session, repo.repo_id, pr_data)
    db_session.commit()

    result = db_session.execute(text("SELECT merged_prs FROM v_merged_prs_30d_total"))
    row = result.fetchone()

    assert row is not None
    assert row.merged_prs == 1


@pytest.mark.integration
def test_v_closed_prs_30d_total(db_session):
    """Test global closed PRs count in last 30 days"""
    org_data = sample_organization_data(name="test-org", platform=Platform.GITHUB)
    org = store_organization(db_session, org_data)
    project = store_project(db_session, org, "test-project", "Test Project")
    repo_data = sample_repository_data(repo_id="repo1", name="test-repo")
    repo = store_repository(db_session, project, repo_data)

    pr_data = sample_pull_request_data(pr_number=1, title="Closed PR", status="closed",
                                       closed_at=datetime.now() - timedelta(days=10))
    store_pull_request(db_session, repo.repo_id, pr_data)
    db_session.commit()

    result = db_session.execute(text("SELECT closed_prs FROM v_closed_prs_30d_total"))
    row = result.fetchone()

    assert row is not None
    assert row.closed_prs == 1


@pytest.mark.integration
def test_v_pr_status_distribution(db_session):
    """Test PR status distribution (all statuses)"""
    org_data = sample_organization_data(name="test-org", platform=Platform.GITHUB)
    org = store_organization(db_session, org_data)
    project = store_project(db_session, org, "test-project", "Test Project")
    repo_data = sample_repository_data(repo_id="repo1", name="test-repo")
    repo = store_repository(db_session, project, repo_data)

    for i, status in enumerate(["open", "merged", "closed"]):
        pr_data = sample_pull_request_data(pr_number=i+1, title=f"{status} PR", status=status)
        store_pull_request(db_session, repo.repo_id, pr_data)
    db_session.commit()

    result = db_session.execute(text("SELECT status, count FROM v_pr_status_distribution ORDER BY status"))
    rows = result.fetchall()

    assert len(rows) == 3
    statuses = {row.status: row.count for row in rows}
    assert statuses.get("open") == 1
    assert statuses.get("merged") == 1
    assert statuses.get("closed") == 1


@pytest.mark.integration
def test_v_pr_size_distribution_30d(db_session):
    """Test PR size distribution for last 30 days"""
    org_data = sample_organization_data(name="test-org", platform=Platform.GITHUB)
    org = store_organization(db_session, org_data)
    project = store_project(db_session, org, "test-project", "Test Project")
    repo_data = sample_repository_data(repo_id="repo1", name="test-repo")
    repo = store_repository(db_session, project, repo_data)

    for i, (size, lines_added, lines_removed) in enumerate([
        ("small", 20, 10),  # total 30 < 50 = small
        ("medium", 100, 50),  # total 150, 50-199 = medium
        ("large", 300, 100)  # total 400, 200-499 = large
    ]):
        pr_data = sample_pull_request_data(
            pr_number=i+1, title=f"{size} PR", status="open",
            created_at=datetime.now() - timedelta(days=5)
        )
        # Override lines to match expected size
        pr_data.lines_added = lines_added
        pr_data.lines_removed = lines_removed
        store_pull_request(db_session, repo.repo_id, pr_data)
    db_session.commit()

    result = db_session.execute(text("SELECT size_category, count FROM v_pr_size_distribution_30d ORDER BY size_category"))
    rows = result.fetchall()

    assert len(rows) > 0


@pytest.mark.integration
def test_v_pr_avg_changes_30d(db_session):
    """Test average PR change volume in last 30 days"""
    org_data = sample_organization_data(name="test-org", platform=Platform.GITHUB)
    org = store_organization(db_session, org_data)
    project = store_project(db_session, org, "test-project", "Test Project")
    repo_data = sample_repository_data(repo_id="repo1", name="test-repo")
    repo = store_repository(db_session, project, repo_data)

    pr_data_1 = sample_pull_request_data(pr_number=1, title="PR 1", status="open")
    pr_data_2 = sample_pull_request_data(pr_number=2, title="PR 2", status="open")
    store_pull_request(db_session, repo.repo_id, pr_data_1)
    store_pull_request(db_session, repo.repo_id, pr_data_2)
    db_session.commit()

    result = db_session.execute(text("SELECT avg_changes FROM v_pr_avg_changes_30d"))
    row = result.fetchone()

    assert row is not None
    assert row.avg_changes >= 0


@pytest.mark.integration
def test_v_active_contributors_30d_total(db_session):
    """Test global active contributors count in last 30 days"""
    org_data = sample_organization_data(name="test-org", platform=Platform.GITHUB)
    org = store_organization(db_session, org_data)
    project = store_project(db_session, org, "test-project", "Test Project")
    repo_data = sample_repository_data(repo_id="repo1", name="test-repo")
    repo = store_repository(db_session, project, repo_data)

    for i, author_email in enumerate(["author1@example.com", "author2@example.com", "author3@example.com"]):
        commit_data = sample_commit_data(sha=f"sha{i}", author_email=author_email,
                                        commit_date=datetime.now() - timedelta(days=5), message=f"Commit by {author_email}")
        store_commit(db_session, repo.repo_id, "main", commit_data)
    db_session.commit()

    result = db_session.execute(text("SELECT contributors FROM v_active_contributors_30d_total"))
    row = result.fetchone()

    assert row is not None
    assert row.contributors >= 1


@pytest.mark.integration
def test_v_commits_30d_total(db_session):
    """Test global commits count in last 30 days"""
    org_data = sample_organization_data(name="test-org", platform=Platform.GITHUB)
    org = store_organization(db_session, org_data)
    project = store_project(db_session, org, "test-project", "Test Project")
    repo_data = sample_repository_data(repo_id="repo1", name="test-repo")
    repo = store_repository(db_session, project, repo_data)

    for i in range(5):
        commit_data = sample_commit_data(sha=f"sha{i}", author_email="developer@example.com",
                                        commit_date=datetime.now() - timedelta(days=5), message=f"Commit {i}")
        store_commit(db_session, repo.repo_id, "main", commit_data)
    db_session.commit()

    result = db_session.execute(text("SELECT commits FROM v_commits_30d_total"))
    row = result.fetchone()

    assert row is not None
    assert row.commits == 5


@pytest.mark.integration
def test_v_active_repositories_total(db_session):
    """Test active repositories count"""
    org_data = sample_organization_data(name="test-org", platform=Platform.GITHUB)
    org = store_organization(db_session, org_data)
    project = store_project(db_session, org, "test-project", "Test Project")

    for i in range(3):
        repo_data = sample_repository_data(repo_id=f"repo{i}", name=f"test-repo-{i}")
        store_repository(db_session, project, repo_data)
    db_session.commit()

    result = db_session.execute(text("SELECT total FROM v_active_repositories_total"))
    row = result.fetchone()

    assert row is not None
    assert row.total >= 3


# =============================================================================
# Time Series Views (Trend Charts)
# =============================================================================

@pytest.mark.integration
def test_v_pr_creation_daily_trend(db_session):
    """Test PR creation daily trend"""
    org_data = sample_organization_data(name="test-org", platform=Platform.GITHUB)
    org = store_organization(db_session, org_data)
    project = store_project(db_session, org, "test-project", "Test Project")
    repo_data = sample_repository_data(repo_id="repo1", name="test-repo")
    repo = store_repository(db_session, project, repo_data)

    for i in range(3):
        pr_data = sample_pull_request_data(pr_number=i+1, title=f"PR {i}", status="open",
                                          created_at=datetime.now() - timedelta(days=3-i))
        store_pull_request(db_session, repo.repo_id, pr_data)
    db_session.commit()

    result = db_session.execute(text("SELECT time, created FROM v_pr_creation_daily_trend ORDER BY time"))
    rows = result.fetchall()

    assert len(rows) > 0
    assert all(hasattr(row, 'time') and hasattr(row, 'created') for row in rows)


@pytest.mark.integration
def test_v_pr_merge_daily_trend(db_session):
    """Test PR merge daily trend"""
    org_data = sample_organization_data(name="test-org", platform=Platform.GITHUB)
    org = store_organization(db_session, org_data)
    project = store_project(db_session, org, "test-project", "Test Project")
    repo_data = sample_repository_data(repo_id="repo1", name="test-repo")
    repo = store_repository(db_session, project, repo_data)

    for i in range(2):
        pr_data = sample_pull_request_data(pr_number=i+1, title=f"Merged PR {i}", status="merged",
                                          merged_at=datetime.now() - timedelta(days=2-i))
        store_pull_request(db_session, repo.repo_id, pr_data)
    db_session.commit()

    result = db_session.execute(text("SELECT time, merged FROM v_pr_merge_daily_trend ORDER BY time"))
    rows = result.fetchall()

    assert len(rows) > 0
    assert all(hasattr(row, 'time') and hasattr(row, 'merged') for row in rows)


@pytest.mark.integration
def test_v_pr_recent_details(db_session):
    """Test recent PR details view"""
    org_data = sample_organization_data(name="test-org", platform=Platform.GITHUB)
    org = store_organization(db_session, org_data)
    project = store_project(db_session, org, "test-project", "Test Project")
    repo_data = sample_repository_data(repo_id="repo1", name="test-repo")
    repo = store_repository(db_session, project, repo_data)

    pr_data = sample_pull_request_data(pr_number=1, title="Test PR", status="open",
                                      created_at=datetime.now() - timedelta(days=5))
    store_pull_request(db_session, repo.repo_id, pr_data)
    db_session.commit()

    result = db_session.execute(text("SELECT * FROM v_pr_recent_details LIMIT 1"))
    row = result.fetchone()

    assert row is not None
    assert row.title == "Test PR"
    assert row.status == "open"


# =============================================================================
# Extraction Operation Views
# =============================================================================

@pytest.mark.integration
def test_v_extraction_run_latest_progress(db_session):
    """Test latest extraction run progress"""
    result = db_session.execute(text("SELECT progress_pct FROM v_extraction_run_latest_progress"))
    row = result.fetchone()
    
    if row is not None:
        assert row.progress_pct >= 0 and row.progress_pct <= 100


@pytest.mark.integration
def test_v_stale_repositories(db_session):
    """Test stale repositories view (7+ days without analysis)"""
    result = db_session.execute(text("SELECT * FROM v_stale_repositories"))
    rows = result.fetchall()
    
    assert isinstance(rows, list)


@pytest.mark.integration
def test_v_unanalyzed_repositories(db_session):
    """Test never-analyzed repositories view"""
    result = db_session.execute(text("SELECT * FROM v_unanalyzed_repositories"))
    rows = result.fetchall()
    
    assert isinstance(rows, list)
