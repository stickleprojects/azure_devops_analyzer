"""CONTRACT tests for database storage operations.

These tests define the business requirements for how data must be stored
and retrieved from the database. They test WHAT the system does, not HOW.

CONTRACT tests CANNOT change without documented requirement changes.
"""

import pytest
from datetime import datetime, timedelta, UTC
from sqlalchemy.exc import IntegrityError

from src.database.storage import (
    store_organization,
    store_project,
    store_repository,
    store_branch,
    store_commit,
    store_pull_request,
    get_or_create_contributor,
    get_or_create_team,
    should_scan_repository,
)
from src.database.models import (
    Organization,
    Project,
    Repository,
    Branch,
    Commit,
    PullRequest,
    Contributor,
    Team,
)
from tests.fixtures.sample_data import (
    sample_organization_data,
    sample_repository_data,
    sample_commit_data,
    sample_branch_data,
    sample_pull_request_data,
)
from src.extractors.base import Platform


class TestOrganizationStorage:
    """CONTRACT: Organization storage operations."""
    
    def test_contract_store_organization_creates_new_org(self, db_session):
        """CONTRACT: Storing an organization must create it in database."""
        org_data = sample_organization_data(name="test-org")
        
        org = store_organization(db_session, org_data)
        db_session.commit()
        
        assert org is not None
        assert org.organization_id is not None
        assert org.name == "test-org"
        assert org.url == "https://github.com/test-org"
        assert org.platform == Platform.GITHUB.value
    
    def test_contract_store_organization_idempotent(self, db_session):
        """CONTRACT: Storing same organization twice returns existing org."""
        org_data = sample_organization_data(name="test-org")
        
        org1 = store_organization(db_session, org_data)
        db_session.commit()
        org1_id = org1.organization_id
        
        org2 = store_organization(db_session, org_data)
        db_session.commit()
        
        assert org2.organization_id == org1_id
        assert db_session.query(Organization).count() == 1
    
    def test_contract_store_organization_different_platforms(self, db_session):
        """CONTRACT: Same org name on different platforms creates separate orgs."""
        org_github = sample_organization_data(
            name="test-org",
            platform=Platform.GITHUB,
        )
        org_azure = sample_organization_data(
            name="test-org",
            platform=Platform.AZURE_DEVOPS,
            url="https://dev.azure.com/test-org",
        )
        
        org1 = store_organization(db_session, org_github)
        org2 = store_organization(db_session, org_azure)
        db_session.commit()
        
        assert org1.organization_id != org2.organization_id
        assert db_session.query(Organization).count() == 2


class TestProjectStorage:
    """CONTRACT: Project storage operations."""
    
    def test_contract_store_project_creates_new_project(self, db_session):
        """CONTRACT: Storing a project must create it under organization."""
        org_data = sample_organization_data()
        org = store_organization(db_session, org_data)
        
        project = store_project(db_session, org, "test-project", "Test description")
        db_session.commit()
        
        assert project is not None
        assert project.project_id is not None
        assert project.organization_id == org.organization_id
        assert project.name == "test-project"
        assert project.description == "Test description"
    
    def test_contract_store_project_idempotent(self, db_session):
        """CONTRACT: Storing same project twice returns existing project."""
        org_data = sample_organization_data()
        org = store_organization(db_session, org_data)
        
        proj1 = store_project(db_session, org, "test-project")
        db_session.commit()
        proj1_id = proj1.project_id
        
        proj2 = store_project(db_session, org, "test-project")
        db_session.commit()
        
        assert proj2.project_id == proj1_id
        assert db_session.query(Project).count() == 1


class TestRepositoryStorage:
    """CONTRACT: Repository storage operations."""
    
    def test_contract_store_repository_creates_new_repo(self, db_session):
        """CONTRACT: Storing a repository must create it in database."""
        org_data = sample_organization_data()
        org = store_organization(db_session, org_data)
        project = store_project(db_session, org, "test-project")
        
        repo_data = sample_repository_data()
        repo = store_repository(db_session, project, repo_data)
        db_session.commit()
        
        assert repo is not None
        assert repo.repo_id == "test-org/test-repo"
        assert repo.project_id == project.project_id
        assert repo.name == "test-repo"
        assert repo.url == "https://github.com/test-org/test-repo"
        assert repo.default_branch == "main"
        assert repo.is_active is True
    
    def test_contract_store_repository_updates_existing(self, db_session):
        """CONTRACT: Storing repository with same ID updates existing record."""
        org_data = sample_organization_data()
        org = store_organization(db_session, org_data)
        project = store_project(db_session, org, "test-project")
        
        repo_data1 = sample_repository_data(default_branch="main")
        repo1 = store_repository(db_session, project, repo_data1)
        db_session.commit()
        
        repo_data2 = sample_repository_data(
            default_branch="develop",
            url="https://github.com/test-org/test-repo-new"
        )
        repo2 = store_repository(db_session, project, repo_data2)
        db_session.commit()
        
        assert repo2.repo_id == repo1.repo_id
        assert repo2.default_branch == "develop"
        assert repo2.url == "https://github.com/test-org/test-repo-new"
        assert db_session.query(Repository).count() == 1
    
    def test_contract_store_repository_with_team(self, db_session):
        """CONTRACT: Repository can be associated with a team."""
        org_data = sample_organization_data()
        org = store_organization(db_session, org_data)
        project = store_project(db_session, org, "test-project")
        
        repo_data = sample_repository_data(team_name="backend-team")
        repo = store_repository(db_session, project, repo_data)
        db_session.commit()
        
        assert repo.team_id is not None
        team = db_session.query(Team).filter_by(team_id=repo.team_id).first()
        assert team.name == "backend-team"
    
    def test_contract_store_repository_security_fields(self, db_session):
        """CONTRACT: Repository must store security and quality metrics."""
        org_data = sample_organization_data()
        org = store_organization(db_session, org_data)
        project = store_project(db_session, org, "test-project")
        
        repo_data = sample_repository_data(
            is_private=True,
            is_archived=False,
        )
        repo = store_repository(db_session, project, repo_data)
        db_session.commit()
        
        assert repo.is_private is True
        assert repo.is_archived is False
        assert repo.repository_size == 1024
        assert repo.open_issues_count == 5
        assert repo.license_name == "MIT"
        assert repo.has_secret_scanning is True


class TestBranchStorage:
    """CONTRACT: Branch storage operations."""
    
    def test_contract_store_branch_creates_new_branch(self, db_session):
        """CONTRACT: Storing a branch must create it for repository."""
        org_data = sample_organization_data()
        org = store_organization(db_session, org_data)
        project = store_project(db_session, org, "test-project")
        repo_data = sample_repository_data()
        repo = store_repository(db_session, project, repo_data)
        db_session.commit()
        
        branch_data = sample_branch_data(name="main")
        branch = store_branch(db_session, repo.repo_id, branch_data)
        db_session.commit()
        
        assert branch is not None
        assert branch.repo_id == repo.repo_id
        assert branch.branch_name == "main"
        assert branch.latest_commit_sha == "abc123def456"
        assert branch.is_active is True
    
    def test_contract_store_branch_updates_existing(self, db_session):
        """CONTRACT: Storing branch with same name updates commit SHA."""
        org_data = sample_organization_data()
        org = store_organization(db_session, org_data)
        project = store_project(db_session, org, "test-project")
        repo_data = sample_repository_data()
        repo = store_repository(db_session, project, repo_data)
        db_session.commit()
        
        branch_data1 = sample_branch_data(name="main", latest_commit_sha="sha1")
        branch1 = store_branch(db_session, repo.repo_id, branch_data1)
        db_session.commit()
        
        branch_data2 = sample_branch_data(name="main", latest_commit_sha="sha2")
        branch2 = store_branch(db_session, repo.repo_id, branch_data2)
        db_session.commit()
        
        assert branch2.latest_commit_sha == "sha2"
        assert db_session.query(Branch).count() == 1


class TestCommitStorage:
    """CONTRACT: Commit storage operations."""
    
    def test_contract_store_commit_creates_new_commit(self, db_session):
        """CONTRACT: Storing a commit must create it with contributor link."""
        org_data = sample_organization_data()
        org = store_organization(db_session, org_data)
        project = store_project(db_session, org, "test-project")
        repo_data = sample_repository_data()
        repo = store_repository(db_session, project, repo_data)
        db_session.commit()
        
        commit_data = sample_commit_data()
        commit = store_commit(db_session, repo.repo_id, "main", commit_data)
        db_session.commit()
        
        assert commit is not None
        assert commit.commit_sha == "abc123def456"
        assert commit.repo_id == repo.repo_id
        assert commit.branch_name == "main"
        assert commit.message == "Test commit"
        assert commit.files_changed == 2
        assert commit.lines_added == 10
        assert commit.lines_removed == 5
        assert commit.author_id is not None
    
    def test_contract_store_commit_creates_contributor(self, db_session):
        """CONTRACT: Storing commit must create contributor if not exists."""
        org_data = sample_organization_data()
        org = store_organization(db_session, org_data)
        project = store_project(db_session, org, "test-project")
        repo_data = sample_repository_data()
        repo = store_repository(db_session, project, repo_data)
        db_session.commit()
        
        commit_data = sample_commit_data(
            author_email="newdev@example.com",
            author_name="New Developer"
        )
        commit = store_commit(db_session, repo.repo_id, "main", commit_data)
        db_session.commit()
        
        contributor = db_session.query(Contributor).filter_by(
            email="newdev@example.com"
        ).first()
        assert contributor is not None
        assert contributor.name == "New Developer"
        assert commit.author_id == contributor.id
    
    def test_contract_store_commit_idempotent(self, db_session):
        """CONTRACT: Storing same commit twice returns None (already exists)."""
        org_data = sample_organization_data()
        org = store_organization(db_session, org_data)
        project = store_project(db_session, org, "test-project")
        repo_data = sample_repository_data()
        repo = store_repository(db_session, project, repo_data)
        db_session.commit()
        
        commit_data = sample_commit_data(sha="unique-sha")
        commit1 = store_commit(db_session, repo.repo_id, "main", commit_data)
        db_session.commit()
        
        commit2 = store_commit(db_session, repo.repo_id, "main", commit_data)
        
        assert commit1 is not None
        assert commit2 is None
        assert db_session.query(Commit).count() == 1
    
    def test_contract_store_commit_truncates_long_message(self, db_session):
        """CONTRACT: Commit message must be truncated to 1000 characters."""
        org_data = sample_organization_data()
        org = store_organization(db_session, org_data)
        project = store_project(db_session, org, "test-project")
        repo_data = sample_repository_data()
        repo = store_repository(db_session, project, repo_data)
        db_session.commit()
        
        long_message = "A" * 2000
        commit_data = sample_commit_data(message=long_message)
        commit = store_commit(db_session, repo.repo_id, "main", commit_data)
        db_session.commit()
        
        assert len(commit.message) == 1000


class TestPullRequestStorage:
    """CONTRACT: Pull request storage operations."""
    
    def test_contract_store_pull_request_creates_new_pr(self, db_session):
        """CONTRACT: Storing a pull request must create it in database."""
        org_data = sample_organization_data()
        org = store_organization(db_session, org_data)
        project = store_project(db_session, org, "test-project")
        repo_data = sample_repository_data()
        repo = store_repository(db_session, project, repo_data)
        db_session.commit()
        
        pr_data = sample_pull_request_data()
        pr = store_pull_request(db_session, repo.repo_id, pr_data)
        db_session.commit()
        
        assert pr is not None
        assert pr.repo_id == repo.repo_id
        assert pr.pr_number == 1
        assert pr.title == "Test Pull Request"
        assert pr.state == "open"
        assert pr.source_branch == "feature-branch"
        assert pr.target_branch == "main"
        assert pr.author_id is not None
    
    def test_contract_store_pull_request_idempotent(self, db_session):
        """CONTRACT: Storing same PR twice returns None (already exists)."""
        org_data = sample_organization_data()
        org = store_organization(db_session, org_data)
        project = store_project(db_session, org, "test-project")
        repo_data = sample_repository_data()
        repo = store_repository(db_session, project, repo_data)
        db_session.commit()
        
        pr_data = sample_pull_request_data(pr_number=42)
        pr1 = store_pull_request(db_session, repo.repo_id, pr_data)
        db_session.commit()
        
        pr2 = store_pull_request(db_session, repo.repo_id, pr_data)
        
        assert pr1 is not None
        assert pr2 is None
        assert db_session.query(PullRequest).count() == 1


class TestContributorStorage:
    """CONTRACT: Contributor storage and retrieval."""
    
    def test_contract_get_or_create_contributor_creates_new(self, db_session):
        """CONTRACT: Getting nonexistent contributor creates it."""
        contributor = get_or_create_contributor(
            db_session,
            email="dev@example.com",
            name="Developer"
        )
        db_session.commit()
        
        assert contributor is not None
        assert contributor.id is not None
        assert contributor.email == "dev@example.com"
        assert contributor.name == "Developer"
    
    def test_contract_get_or_create_contributor_returns_existing(self, db_session):
        """CONTRACT: Getting existing contributor returns same instance."""
        contrib1 = get_or_create_contributor(
            db_session,
            email="dev@example.com",
            name="Developer"
        )
        db_session.commit()
        contrib1_id = contrib1.id
        
        contrib2 = get_or_create_contributor(
            db_session,
            email="dev@example.com",
            name="Developer Updated"
        )
        db_session.commit()
        
        assert contrib2.id == contrib1_id
        assert contrib2.name == "Developer"  # Original name preserved
        assert db_session.query(Contributor).count() == 1


class TestTeamStorage:
    """CONTRACT: Team storage and retrieval."""
    
    def test_contract_get_or_create_team_creates_new(self, db_session):
        """CONTRACT: Getting nonexistent team creates it."""
        org_data = sample_organization_data()
        org = store_organization(db_session, org_data)
        
        team = get_or_create_team(
            db_session,
            org,
            "backend-team",
            "Backend development team"
        )
        db_session.commit()
        
        assert team is not None
        assert team.team_id is not None
        assert team.organization_id == org.organization_id
        assert team.name == "backend-team"
        assert team.description == "Backend development team"
    
    def test_contract_get_or_create_team_returns_existing(self, db_session):
        """CONTRACT: Getting existing team returns same instance."""
        org_data = sample_organization_data()
        org = store_organization(db_session, org_data)
        
        team1 = get_or_create_team(db_session, org, "backend-team")
        db_session.commit()
        team1_id = team1.team_id
        
        team2 = get_or_create_team(db_session, org, "backend-team")
        db_session.commit()
        
        assert team2.team_id == team1_id
        assert db_session.query(Team).count() == 1


class TestRepositoryScanLogic:
    """CONTRACT: Repository scan timing logic."""
    
    def test_contract_should_scan_repository_new_repo(self, db_session):
        """CONTRACT: New repository should always be scanned."""
        # Repository doesn't exist yet
        should_scan = should_scan_repository(db_session, "nonexistent/repo")
        
        assert should_scan is True
    
    def test_contract_should_scan_repository_never_analyzed(self, db_session):
        """CONTRACT: Repository never analyzed should be scanned."""
        org_data = sample_organization_data()
        org = store_organization(db_session, org_data)
        project = store_project(db_session, org, "test-project")
        repo_data = sample_repository_data()
        repo = store_repository(db_session, project, repo_data)
        # Don't set last_analyzed_at
        db_session.commit()
        
        should_scan = should_scan_repository(db_session, repo.repo_id)
        
        assert should_scan is True
    
    def test_contract_should_scan_repository_recently_analyzed(self, db_session):
        """CONTRACT: Recently analyzed repository should not be scanned."""
        org_data = sample_organization_data()
        org = store_organization(db_session, org_data)
        project = store_project(db_session, org, "test-project")
        repo_data = sample_repository_data()
        repo = store_repository(db_session, project, repo_data)
        
        # Set last_analyzed_at to 2 hours ago
        repo.last_analyzed_at = datetime.now(UTC) - timedelta(hours=2)
        db_session.commit()
        
        should_scan = should_scan_repository(db_session, repo.repo_id, min_hours=6)
        
        assert should_scan is False
    
    def test_contract_should_scan_repository_old_analysis(self, db_session):
        """CONTRACT: Repository with old analysis should be rescanned."""
        org_data = sample_organization_data()
        org = store_organization(db_session, org_data)
        project = store_project(db_session, org, "test-project")
        repo_data = sample_repository_data()
        repo = store_repository(db_session, project, repo_data)
        
        # Set last_analyzed_at to 10 hours ago
        repo.last_analyzed_at = datetime.now(UTC) - timedelta(hours=10)
        db_session.commit()
        
        should_scan = should_scan_repository(db_session, repo.repo_id, min_hours=6)
        
        assert should_scan is True


class TestForeignKeyConstraints:
    """CONTRACT: Foreign key relationships must be enforced."""
    
    def test_contract_commit_requires_valid_repository(self, db_session):
        """CONTRACT: Cannot create commit without valid repository."""
        commit_data = sample_commit_data()
        
        # Try to store commit for nonexistent repository
        commit = store_commit(db_session, "nonexistent/repo", "main", commit_data)
        
        if commit:  # Only test if commit was created
            with pytest.raises(IntegrityError):
                db_session.commit()
    
    def test_contract_repository_cascade_delete_commits(self, db_session):
        """CONTRACT: Deleting repository must cascade delete commits."""
        org_data = sample_organization_data()
        org = store_organization(db_session, org_data)
        project = store_project(db_session, org, "test-project")
        repo_data = sample_repository_data()
        repo = store_repository(db_session, project, repo_data)
        
        commit_data = sample_commit_data()
        store_commit(db_session, repo.repo_id, "main", commit_data)
        db_session.commit()
        
        assert db_session.query(Commit).count() == 1
        
        # Delete repository
        db_session.delete(repo)
        db_session.commit()
        
        # Commits should be deleted too
        assert db_session.query(Commit).count() == 0


class TestNullHandling:
    """CONTRACT: Optional fields must handle null values correctly."""
    
    def test_contract_repository_optional_fields_can_be_null(self, db_session):
        """CONTRACT: Repository optional fields accept null values."""
        org_data = sample_organization_data()
        org = store_organization(db_session, org_data)
        project = store_project(db_session, org, "test-project")
        
        repo_data = sample_repository_data()
        # Override with None values
        repo_data.license_name = None
        repo_data.license_key = None
        repo_data.pushed_at = None
        
        repo = store_repository(db_session, project, repo_data)
        db_session.commit()
        
        assert repo.license_name is None
        assert repo.license_key is None
        assert repo.pushed_at is None
    
    def test_contract_commit_optional_fields_can_be_null(self, db_session):
        """CONTRACT: Commit optional fields accept null values."""
        org_data = sample_organization_data()
        org = store_organization(db_session, org_data)
        project = store_project(db_session, org, "test-project")
        repo_data = sample_repository_data()
        repo = store_repository(db_session, project, repo_data)
        db_session.commit()
        
        commit_data = sample_commit_data()
        commit_data.files_changed = None
        commit_data.lines_added = None
        commit_data.lines_removed = None
        
        commit = store_commit(db_session, repo.repo_id, "main", commit_data)
        db_session.commit()
        
        assert commit.files_changed is None
        assert commit.lines_added is None
        assert commit.lines_removed is None
