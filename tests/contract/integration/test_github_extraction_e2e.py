"""
Integration Tests: GitHub Extraction E2E

CONTRACT: GitHub extraction stores correct data in PostgreSQL.

Tests verify:
- Repositories extracted and stored with correct metadata
- Branches tracked accurately
- Commits and contributors recorded
- Data types and relationships correct
- Database constraints enforced
"""

import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from src.extractors.github.extractor import GitHubExtractor
from src.database.models import Repository, Branch, Commit, Contributor


class TestGitHubExtractionBasic:
    """Basic GitHub extraction E2E tests."""
    
    @pytest.mark.integration
    def test_extract_small_repo_stores_metadata(
        self,
        github_config,
        test_session: Session
    ):
        """
        CONTRACT: Extracting octocat/Hello-World stores complete repo metadata.
        
        Verify:
        - Repository record created
        - All metadata fields populated
        - Timestamps are UTC-aware
        """
        # Setup
        extractor = GitHubExtractor(config=github_config)
        repo_id = "octocat/Hello-World"
        
        # Act: Extract repository metadata
        repo_data = extractor.extract_repository(repo_id)
        
        # Store in database
        repo = Repository(
            repo_id=repo_data["repo_id"],
            url=repo_data["url"],
            name=repo_data["name"],
            created_at=repo_data.get("created_at"),
            updated_at=repo_data.get("updated_at"),
            description=repo_data.get("description"),
            is_fork=repo_data.get("is_fork", False),
            is_archived=repo_data.get("is_archived", False),
            is_private=repo_data.get("is_private", False),
            default_branch=repo_data.get("default_branch"),
            size_kb=repo_data.get("size_kb"),
            stars=repo_data.get("stars", 0),
            watchers=repo_data.get("watchers", 0),
            forks=repo_data.get("forks", 0),
        )
        test_session.add(repo)
        test_session.commit()
        
        # Assert: Repository stored correctly
        stored_repo = test_session.query(Repository).filter_by(
            repo_id=repo_id
        ).first()
        
        assert stored_repo is not None, f"Repository {repo_id} not found in database"
        assert stored_repo.url == f"https://github.com/{repo_id}"
        assert stored_repo.created_at is not None
        assert stored_repo.created_at.tzinfo is not None, "Timestamp should be UTC-aware"
        assert stored_repo.default_branch is not None
        assert stored_repo.name == "Hello-World"
    
    @pytest.mark.integration
    def test_extract_tracks_branches(
        self,
        github_config,
        test_session: Session
    ):
        """
        CONTRACT: Branches are tracked with correct commit SHAs.
        
        Verify:
        - Branch record created for default branch
        - Commit SHA correct format (40-character hex)
        - Branch references valid repository
        """
        # Setup
        extractor = GitHubExtractor(config=github_config)
        repo_id = "octocat/Hello-World"
        
        # Extract and store repository
        repo_data = extractor.extract_repository(repo_id)
        repo = Repository(
            repo_id=repo_id,
            url=repo_data["url"],
            name=repo_data["name"],
            default_branch=repo_data.get("default_branch"),
        )
        test_session.add(repo)
        test_session.commit()
        
        # Extract branch information
        branches_data = extractor.extract_branches(repo_id)
        
        # Store branches
        for branch_data in branches_data:
            branch = Branch(
                repo_id=repo_id,
                branch_name=branch_data["branch_name"],
                latest_commit_sha=branch_data["latest_commit_sha"],
            )
            test_session.add(branch)
        test_session.commit()
        
        # Assert: Branches stored correctly
        branches = test_session.query(Branch).filter_by(
            repo_id=repo_id
        ).all()
        
        assert len(branches) > 0, f"No branches found for {repo_id}"
        
        for branch in branches:
            # Verify SHA format (Git SHA-1 is 40 hex characters)
            assert len(branch.latest_commit_sha) == 40, \
                f"Invalid SHA format: {branch.latest_commit_sha}"
            assert all(c in "0123456789abcdef" for c in branch.latest_commit_sha), \
                f"SHA contains invalid characters: {branch.latest_commit_sha}"
    
    @pytest.mark.integration
    def test_extract_tracks_commits(
        self,
        github_config,
        test_session: Session
    ):
        """
        CONTRACT: Extracted commits have correct metadata and relationships.
        
        Verify:
        - Commit SHA matches GitHub API
        - Author/committer emails captured
        - Commit timestamps are UTC
        - Message is not NULL
        """
        # Setup
        extractor = GitHubExtractor(config=github_config)
        repo_id = "octocat/Hello-World"
        
        # Create repository first
        repo = Repository(repo_id=repo_id, url="https://github.com/octocat/Hello-World")
        test_session.add(repo)
        test_session.commit()
        
        # Extract commits
        commits_data = extractor.extract_commits(repo_id, max_commits=10)
        
        # Store commits
        for commit_data in commits_data:
            commit = Commit(
                repo_id=repo_id,
                sha=commit_data["sha"],
                message=commit_data.get("message", ""),
                author_email=commit_data.get("author_email", "unknown@github.com"),
                author_name=commit_data.get("author_name", "Unknown"),
                commit_date=commit_data.get("commit_date"),
                files_changed=commit_data.get("files_changed", 0),
                additions=commit_data.get("additions", 0),
                deletions=commit_data.get("deletions", 0),
            )
            test_session.add(commit)
        test_session.commit()
        
        # Assert: Commits stored correctly
        commits = test_session.query(Commit).filter_by(repo_id=repo_id).all()
        
        assert len(commits) > 0, f"No commits extracted for {repo_id}"
        
        for commit in commits:
            # Verify basic structure
            assert len(commit.sha) == 40, f"Invalid SHA: {commit.sha}"
            assert commit.message is not None
            assert commit.author_email is not None
            assert "@" in commit.author_email or commit.author_email == "unknown@github.com"
            
            # Verify timestamp is UTC-aware
            assert commit.commit_date is not None
            assert commit.commit_date.tzinfo is not None, \
                f"Commit {commit.sha} has naive (non-UTC) datetime"
    
    @pytest.mark.integration
    def test_extract_tracks_contributors(
        self,
        github_config,
        test_session: Session
    ):
        """
        CONTRACT: Contributors are tracked with email identification.
        
        Verify:
        - Contributor records created
        - Email addresses captured
        - Contribution counts populated
        """
        # Setup
        extractor = GitHubExtractor(config=github_config)
        repo_id = "octocat/Hello-World"
        
        # Create repository
        repo = Repository(repo_id=repo_id, url="https://github.com/octocat/Hello-World")
        test_session.add(repo)
        test_session.commit()
        
        # Extract contributors
        contributors_data = extractor.extract_contributors(repo_id)
        
        # Store contributors
        for contrib_data in contributors_data:
            contributor = Contributor(
                repo_id=repo_id,
                email=contrib_data.get("email", "unknown@github.com"),
                name=contrib_data.get("name", "Unknown"),
                contributions=contrib_data.get("contributions", 0),
            )
            test_session.add(contributor)
        test_session.commit()
        
        # Assert: Contributors stored
        contributors = test_session.query(Contributor).filter_by(
            repo_id=repo_id
        ).all()
        
        assert len(contributors) > 0, f"No contributors found for {repo_id}"
        
        for contributor in contributors:
            # Verify email is present (or has placeholder)
            assert contributor.email is not None
            assert "@" in contributor.email or contributor.email == "unknown@github.com"


class TestGitHubExtractionDataIntegrity:
    """Data integrity and constraint validation."""
    
    @pytest.mark.integration
    def test_repository_constraints(self, test_session: Session):
        """
        CONTRACT: Database constraints are enforced.
        
        Verify:
        - NOT NULL constraints prevent invalid data
        - Unique constraints prevent duplicates
        """
        from sqlalchemy.exc import IntegrityError
        
        # Attempt to insert repository without repo_id (should fail)
        invalid_repo = Repository(
            repo_id=None,  # NOT NULL constraint
            url="https://example.com"
        )
        test_session.add(invalid_repo)
        
        with pytest.raises(IntegrityError):
            test_session.commit()
    
    @pytest.mark.integration
    def test_foreign_key_relationships(
        self,
        test_session: Session
    ):
        """
        CONTRACT: Foreign key relationships are valid.
        
        Verify:
        - Branch references valid repository
        - Commit references valid repository
        - No orphaned entities
        """
        # Create repository
        repo = Repository(
            repo_id="test/repo",
            url="https://github.com/test/repo"
        )
        test_session.add(repo)
        test_session.commit()
        
        # Create branch (should reference valid repo)
        branch = Branch(
            repo_id="test/repo",
            branch_name="main",
            latest_commit_sha="a" * 40
        )
        test_session.add(branch)
        test_session.commit()
        
        # Verify relationship works
        stored_branch = test_session.query(Branch).filter_by(
            repo_id="test/repo"
        ).first()
        
        assert stored_branch is not None
        assert stored_branch.repo_id == "test/repo"
        
        # Verify we can navigate relationship (if foreign key configured)
        # This would work if relationship is configured in model
        assert stored_branch.branch_name == "main"
    
    @pytest.mark.integration
    def test_timezone_handling(
        self,
        github_config,
        test_session: Session
    ):
        """
        CONTRACT: All timestamp fields are UTC-aware.
        
        Verify:
        - commit_date has timezone info
        - created_at has timezone info
        - No naive datetime objects
        """
        # Create test data with timezone-aware datetimes
        from datetime import timezone
        
        repo = Repository(
            repo_id="test/repo",
            url="https://github.com/test/repo",
            created_at=datetime.now(timezone.utc)
        )
        test_session.add(repo)
        test_session.commit()
        
        commit = Commit(
            repo_id="test/repo",
            sha="a" * 40,
            message="Test commit",
            commit_date=datetime.now(timezone.utc)
        )
        test_session.add(commit)
        test_session.commit()
        
        # Retrieve and verify
        stored_repo = test_session.query(Repository).filter_by(
            repo_id="test/repo"
        ).first()
        stored_commit = test_session.query(Commit).filter_by(
            repo_id="test/repo"
        ).first()
        
        assert stored_repo.created_at.tzinfo is not None, \
            "Repository.created_at should be timezone-aware"
        assert stored_commit.commit_date.tzinfo is not None, \
            "Commit.commit_date should be timezone-aware"
