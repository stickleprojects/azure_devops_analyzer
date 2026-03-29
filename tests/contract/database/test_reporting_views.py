import pytest
from sqlalchemy import text
from datetime import datetime, timedelta
from uuid import uuid4
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


@pytest.mark.integration
def test_v_prs_created_30d_total(db_session):
    """Test global PRs created in last 30 days"""
    org_data = sample_organization_data(name="test-org", platform=Platform.GITHUB)
    org = store_organization(db_session, org_data)
    project = store_project(db_session, org, "test-project", "Test Project")
    repo_data = sample_repository_data(repo_id="repo1", name="test-repo")
    repo = store_repository(db_session, project, repo_data)

    recent_pr = sample_pull_request_data(
        pr_number=1,
        title="Recent PR",
        status="open",
        created_at=datetime.now() - timedelta(days=5),
    )
    old_pr = sample_pull_request_data(
        pr_number=2,
        title="Old PR",
        status="open",
        created_at=datetime.now() - timedelta(days=45),
    )
    store_pull_request(db_session, repo.repo_id, recent_pr)
    store_pull_request(db_session, repo.repo_id, old_pr)
    db_session.commit()

    row = db_session.execute(text("SELECT prs FROM v_prs_created_30d_total")).fetchone()

    assert row is not None
    assert row.prs == 1


@pytest.mark.integration
def test_v_teams_total(db_session):
    """Test global teams count"""
    org_data = sample_organization_data(name="test-org", platform=Platform.GITHUB)
    org = store_organization(db_session, org_data)
    db_session.execute(
        text("INSERT INTO teams (organization_id, name, created_at) VALUES (:org_id, :name, :created_at)"),
        [
            {"org_id": org.organization_id, "name": "Team A", "created_at": datetime.now()},
            {"org_id": org.organization_id, "name": "Team B", "created_at": datetime.now()},
        ],
    )
    db_session.commit()

    row = db_session.execute(text("SELECT teams FROM v_teams_total")).fetchone()

    assert row is not None
    assert row.teams == 2


@pytest.mark.integration
def test_v_commits_total_and_contributors_total(db_session):
    """Test global all-time commit and contributor totals"""
    org_data = sample_organization_data(name="test-org", platform=Platform.GITHUB)
    org = store_organization(db_session, org_data)
    project = store_project(db_session, org, "test-project", "Test Project")
    repo_data = sample_repository_data(repo_id="repo1", name="test-repo")
    repo = store_repository(db_session, project, repo_data)

    for i, author_email in enumerate(["author1@example.com", "author2@example.com"]):
        commit_data = sample_commit_data(
            sha=f"sha{i}",
            author_email=author_email,
            commit_date=datetime.now() - timedelta(days=2),
            message=f"Commit {i}",
        )
        store_commit(db_session, repo.repo_id, "main", commit_data)
    db_session.commit()

    commits_row = db_session.execute(text("SELECT total FROM v_commits_total")).fetchone()
    contributors_row = db_session.execute(text("SELECT total FROM v_contributors_total")).fetchone()

    assert commits_row is not None
    assert contributors_row is not None
    assert commits_row.total == 2
    assert contributors_row.total == 2


@pytest.mark.integration
def test_v_repository_overview_views(db_session):
    """Test repository-overview view projections"""
    org_data = sample_organization_data(name="test-org", platform=Platform.GITHUB)
    org = store_organization(db_session, org_data)
    project = store_project(db_session, org, "test-project", "Test Project")
    repo_data = sample_repository_data(repo_id="repo1", name="test-repo")
    repo = store_repository(db_session, project, repo_data)

    for i in range(3):
        commit_data = sample_commit_data(
            sha=f"sha{i}",
            author_email="dev@example.com",
            commit_date=datetime.now() - timedelta(days=3),
            message=f"Commit {i}",
        )
        store_commit(db_session, repo.repo_id, "main", commit_data)

    pr_data = sample_pull_request_data(pr_number=1, title="PR", status="open")
    store_pull_request(db_session, repo.repo_id, pr_data)
    db_session.commit()

    top_repo = db_session.execute(
        text("SELECT repository, commits FROM v_top_repositories_by_commits_30d LIMIT 1")
    ).fetchone()
    overview_row = db_session.execute(
        text("SELECT repository, total_commits, total_prs FROM v_repository_overview_table WHERE repo_id = :rid"),
        {"rid": repo.repo_id},
    ).fetchone()

    assert top_repo is not None
    assert top_repo.repository == "test-repo"
    assert top_repo.commits == 3
    assert overview_row is not None
    assert overview_row.total_commits == 3
    assert overview_row.total_prs == 1


@pytest.mark.integration
def test_v_repo_summary_latest(db_session):
    """Latest repository summary view should return only the newest summary per repo"""
    org_data = sample_organization_data(name="test-org", platform=Platform.GITHUB)
    org = store_organization(db_session, org_data)
    project = store_project(db_session, org, "test-project", "Test Project")
    repo_data = sample_repository_data(repo_id="repo1", name="test-repo")
    repo = store_repository(db_session, project, repo_data)

    db_session.execute(
        text(
            """
            INSERT INTO repository_summaries (repo_id, summary_text, purpose, key_technologies, generated_at)
            VALUES
            (:repo_id, :old_summary, :purpose, :tech, :old_generated),
            (:repo_id, :new_summary, :purpose, :tech, :new_generated)
            """
        ),
        {
            "repo_id": repo.repo_id,
            "old_summary": "Older summary",
            "new_summary": "Latest summary",
            "purpose": "Testing",
            "tech": ["Python", "PostgreSQL"],
            "old_generated": datetime.now() - timedelta(days=2),
            "new_generated": datetime.now() - timedelta(hours=1),
        },
    )
    db_session.commit()

    row = db_session.execute(
        text("SELECT summary_text FROM v_repo_summary_latest WHERE repo_id = :rid"),
        {"rid": repo.repo_id},
    ).fetchone()

    assert row is not None
    assert row.summary_text == "Latest summary"


@pytest.mark.integration
def test_v_pr_reviews_30d_total(db_session):
    """Test global PR reviews count in last 30 days"""
    org_data = sample_organization_data(name="test-org", platform=Platform.GITHUB)
    org = store_organization(db_session, org_data)
    project = store_project(db_session, org, "test-project", "Test Project")
    repo_data = sample_repository_data(repo_id="repo1", name="test-repo")
    repo = store_repository(db_session, project, repo_data)

    pr_data = sample_pull_request_data(pr_number=1, title="PR 1", status="open")
    pr = store_pull_request(db_session, repo.repo_id, pr_data)

    reviewer_id = pr.author_id
    db_session.execute(
        text(
            """
            INSERT INTO pr_reviews (pr_id, reviewer_id, review_date, vote, is_required, comment_count)
            VALUES (:pr_id, :reviewer_id, :review_date, :vote, :is_required, :comment_count)
            """
        ),
        {
            "pr_id": pr.id,
            "reviewer_id": reviewer_id,
            "review_date": datetime.now() - timedelta(days=1),
            "vote": 10,
            "is_required": False,
            "comment_count": 0,
        },
    )
    db_session.commit()

    row = db_session.execute(text("SELECT reviews FROM v_pr_reviews_30d_total")).fetchone()

    assert row is not None
    assert row.reviews == 1


@pytest.mark.integration
def test_v_top_contributor_and_reviewer_views(db_session):
    """Test contributor and reviewer ranking views"""
    org_data = sample_organization_data(name="test-org", platform=Platform.GITHUB)
    org = store_organization(db_session, org_data)
    project = store_project(db_session, org, "test-project", "Test Project")
    repo_data = sample_repository_data(repo_id="repo1", name="test-repo")
    repo = store_repository(db_session, project, repo_data)

    commit_data = sample_commit_data(
        sha="sha1",
        author_email="dev@example.com",
        commit_date=datetime.now() - timedelta(days=2),
        message="Commit 1",
    )
    store_commit(db_session, repo.repo_id, "main", commit_data)

    pr_data = sample_pull_request_data(pr_number=1, title="PR 1", status="open")
    pr = store_pull_request(db_session, repo.repo_id, pr_data)
    db_session.execute(
        text(
            """
            INSERT INTO pr_reviews (pr_id, reviewer_id, review_date, vote, is_required, comment_count)
            VALUES (:pr_id, :reviewer_id, :review_date, :vote, :is_required, :comment_count)
            """
        ),
        {
            "pr_id": pr.id,
            "reviewer_id": pr.author_id,
            "review_date": datetime.now() - timedelta(days=1),
            "vote": 10,
            "is_required": False,
            "comment_count": 0,
        },
    )
    db_session.commit()

    top_contributor = db_session.execute(
        text("SELECT contributor, commits FROM v_top_contributors_30d LIMIT 1")
    ).fetchone()
    top_reviewer = db_session.execute(
        text("SELECT reviewer, reviews FROM v_top_reviewers_30d LIMIT 1")
    ).fetchone()

    assert top_contributor is not None
    assert top_contributor.commits >= 1
    assert top_reviewer is not None
    assert top_reviewer.reviews >= 1


@pytest.mark.integration
def test_stale_reviews_excluded_from_top_reviewers_30d(db_session):
    """Regression test for DASH-REVIEW-003.

    Reviews older than 30 days must NOT appear in v_top_reviewers_30d.
    This guards against synthetic review timestamps (e.g. from Azure DevOps
    ingestion) causing inactive contributors to appear as recent reviewers.
    """
    org_data = sample_organization_data(name="test-org", platform=Platform.GITHUB)
    org = store_organization(db_session, org_data)
    project = store_project(db_session, org, "test-project", "Test Project")
    repo_data = sample_repository_data(repo_id="repo1", name="test-repo")
    repo = store_repository(db_session, project, repo_data)

    pr_data = sample_pull_request_data(pr_number=1, title="Old PR", status="merged")
    pr = store_pull_request(db_session, repo.repo_id, pr_data)

    # Insert a review that is 60 days old (stale — outside the 30-day window)
    db_session.execute(
        text(
            """
            INSERT INTO pr_reviews (pr_id, reviewer_id, review_date, vote, is_required, comment_count)
            VALUES (:pr_id, :reviewer_id, :review_date, :vote, :is_required, :comment_count)
            """
        ),
        {
            "pr_id": pr.id,
            "reviewer_id": pr.author_id,
            "review_date": datetime.now() - timedelta(days=60),
            "vote": 10,
            "is_required": False,
            "comment_count": 0,
        },
    )
    db_session.commit()

    top_reviewer = db_session.execute(
        text("SELECT reviewer, reviews FROM v_top_reviewers_30d LIMIT 1")
    ).fetchone()

    # The stale reviewer must NOT appear in the 30-day view
    assert top_reviewer is None, (
        f"Stale reviewer '{top_reviewer.reviewer}' incorrectly appears in "
        "v_top_reviewers_30d — review timestamp may be synthetic/incorrect"
    )



    """Test contributor activity rollup view"""
    org_data = sample_organization_data(name="test-org", platform=Platform.GITHUB)
    org = store_organization(db_session, org_data)
    project = store_project(db_session, org, "test-project", "Test Project")
    repo_data = sample_repository_data(repo_id="repo1", name="test-repo")
    repo = store_repository(db_session, project, repo_data)

    commit_data = sample_commit_data(
        sha="sha1",
        author_email="dev@example.com",
        commit_date=datetime.now() - timedelta(days=2),
        message="Commit 1",
    )
    commit_data.lines_added = 25
    commit_data.lines_removed = 10
    store_commit(db_session, repo.repo_id, "main", commit_data)

    pr_data = sample_pull_request_data(
        pr_number=1,
        title="PR 1",
        status="open",
        created_at=datetime.now() - timedelta(days=1),
    )
    pr = store_pull_request(db_session, repo.repo_id, pr_data)
    db_session.execute(
        text(
            """
            INSERT INTO pr_reviews (pr_id, reviewer_id, review_date, vote, is_required, comment_count)
            VALUES (:pr_id, :reviewer_id, :review_date, :vote, :is_required, :comment_count)
            """
        ),
        {
            "pr_id": pr.id,
            "reviewer_id": pr.author_id,
            "review_date": datetime.now() - timedelta(days=1),
            "vote": 10,
            "is_required": False,
            "comment_count": 0,
        },
    )
    db_session.commit()

    row = db_session.execute(
        text(
            """
            SELECT
                COALESCE(SUM(commits), 0) AS commits,
                COALESCE(SUM(prs_authored), 0) AS prs_authored,
                COALESCE(SUM(reviews_given), 0) AS reviews_given
            FROM v_contributor_activity_30d
            """
        )
    ).fetchone()

    assert row is not None
    assert row.commits >= 1
    assert row.prs_authored >= 1
    assert row.reviews_given >= 1


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


@pytest.mark.integration
def test_v_auth_errors_by_platform_and_total(db_session):
    """Auth failures should be grouped by platform and counted in 24h total"""
    now = datetime.now()
    run_gh = uuid4()
    run_ado = uuid4()
    run_other = uuid4()

    db_session.execute(
        text(
            """
            INSERT INTO extraction_runs
            (run_id, platform, organization_name, project_name, status, total_repositories, processed_repositories, started_at, updated_at, completed_at, error_message)
            VALUES
            (:run_gh, 'github', 'org', NULL, 'failed', 1, 0, :now, :now, :now, '401 Bad credentials'),
            (:run_ado, 'azure_devops', 'org', NULL, 'failed', 1, 0, :now, :now, :now, 'The requested resource requires user authentication'),
            (:run_other, 'github', 'org', NULL, 'failed', 1, 0, :now, :now, :now, 'network timeout')
            """
        ),
        {"run_gh": str(run_gh), "run_ado": str(run_ado), "run_other": str(run_other), "now": now},
    )
    db_session.commit()

    rows = db_session.execute(text("SELECT platform, error_count FROM v_auth_errors_by_platform ORDER BY platform")).fetchall()
    total = db_session.execute(text("SELECT auth_errors FROM v_auth_errors_24h_total")).scalar_one()

    assert len(rows) == 2
    assert total == 2


@pytest.mark.integration
def test_v_extraction_metrics_with_errors_categories(db_session):
    """Extraction metrics view should normalize auth and non-auth error categories"""
    now = datetime.now()
    run_id = uuid4()

    db_session.execute(
        text(
            """
            INSERT INTO extraction_runs
            (run_id, platform, organization_name, project_name, status, total_repositories, processed_repositories, started_at, updated_at, completed_at, error_message)
            VALUES
            (:run_id, 'github', 'org', NULL, 'failed', 3, 1, :now, :now, :now, 'mixed failures')
            """
        ),
        {"run_id": str(run_id), "now": now},
    )

    db_session.execute(
        text(
            """
            INSERT INTO extraction_metrics
            (
                id,
                run_id,
                repository_id,
                platform,
                status,
                extraction_started_at,
                extraction_completed_at,
                extraction_duration_seconds,
                error_message,
                commits_extracted,
                pull_requests_extracted,
                branches_extracted,
                contributors_extracted,
                cache_hits,
                cache_misses,
                correlation_id
            )
            VALUES
            (:id1, :run_id, 'repo/a', 'github', 'failed', :now, :now, 3, '401 unauthorized', 0, 0, 0, 0, 0, 0, :c1),
            (:id2, :run_id, 'repo/b', 'github', 'failed', :now, :now, 3, 'bad credentials', 0, 0, 0, 0, 0, 0, :c2),
            (:id3, :run_id, 'repo/c', 'github', 'failed', :now, :now, 3, 'unexpected parser failure', 0, 0, 0, 0, 0, 0, :c3)
            """
        ),
        {
            "id1": 900001,
            "id2": 900002,
            "id3": 900003,
            "run_id": str(run_id),
            "now": now,
            "c1": str(uuid4()),
            "c2": str(uuid4()),
            "c3": str(uuid4()),
        },
    )
    db_session.commit()

    categories = db_session.execute(
        text("SELECT error_message, error_category FROM v_extraction_metrics_with_errors WHERE run_id = :run_id"),
        {"run_id": str(run_id)},
    ).fetchall()

    category_map = {row.error_message: row.error_category for row in categories}
    assert category_map["401 unauthorized"] == "AUTH_401_UNAUTHORIZED"
    assert category_map["bad credentials"] == "BAD_CREDENTIALS"
    assert category_map["unexpected parser failure"] == "OTHER_ERROR"


@pytest.mark.integration
def test_v_extraction_runs_recent_includes_error_category(db_session):
    """Recent runs view should expose normalized run-level error categories"""
    now = datetime.now()
    run_id = uuid4()
    db_session.execute(
        text(
            """
            INSERT INTO extraction_runs
            (run_id, platform, organization_name, project_name, status, total_repositories, processed_repositories, started_at, updated_at, completed_at, error_message)
            VALUES
            (:run_id, 'github', 'org', NULL, 'failed', 1, 0, :now, :now, :now, '401 bad credentials')
            """
        ),
        {"run_id": str(run_id), "now": now},
    )
    db_session.commit()

    row = db_session.execute(
        text("SELECT error_category FROM v_extraction_runs_recent WHERE run_id = :run_id"),
        {"run_id": str(run_id)},
    ).fetchone()

    assert row is not None
    assert row.error_category == "AUTH_401_UNAUTHORIZED"
