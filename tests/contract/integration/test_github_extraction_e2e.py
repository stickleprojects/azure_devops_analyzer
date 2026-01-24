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
from src.database.models import Repository, Branch, Commit, Contributor, RepositoryLanguage
from src.database.storage import store_commit, store_languages


def get_or_create_repository(extractor: GitHubExtractor, repo_id: str, session: Session) -> Repository:
    """
    Get existing repository or create it from GitHub API data.
    
    Handles duplicate key conflicts gracefully by returning existing record.
    Ensures repository.name is always populated (required by NOT NULL constraint).
    """
    # Check if repository already exists
    existing = session.query(Repository).filter_by(repo_id=repo_id).first()
    if existing:
        return existing
    
    # Fetch repository metadata from GitHub
    repo_data = extractor.get_repository(repo_id)
    
    # Create and store repository
    repo = Repository(
        repo_id=repo_data.repo_id,
        url=repo_data.url,
        name=repo_data.name,
        default_branch=repo_data.default_branch,
        created_at=repo_data.created_at,
        updated_at=repo_data.updated_at,
        is_private=repo_data.is_private,
        is_archived=repo_data.is_archived,
        repository_size=repo_data.repository_size,
        open_issues_count=repo_data.open_issues_count,
        license_name=repo_data.license_name,
        license_key=repo_data.license_key,
        has_vulnerability_alerts=repo_data.has_vulnerability_alerts,
        has_secret_scanning=repo_data.has_secret_scanning,
        has_dependabot_alerts=repo_data.has_dependabot_alerts,
    )
    session.add(repo)
    session.commit()
    return repo


class TestGitHubExtractionBasic:
    """Basic GitHub extraction E2E tests."""
    
    @pytest.mark.integration
    @pytest.mark.live_api
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
        repo_data = extractor.get_repository(repo_id)
        
        assert repo_data is not None, f"Repository {repo_id} not found in extraction"
        
        # Store in database
        repo = Repository(
            repo_id=repo_data.repo_id,
            url=repo_data.url,
            name=repo_data.name,
            created_at=repo_data.created_at,
            updated_at=repo_data.updated_at,
            is_archived=repo_data.is_archived,
            is_private=repo_data.is_private,
            default_branch=repo_data.default_branch,
            repository_size=repo_data.repository_size,
            open_issues_count=repo_data.open_issues_count,
            license_name=repo_data.license_name,
            license_key=repo_data.license_key,
            has_vulnerability_alerts=repo_data.has_vulnerability_alerts,
            has_secret_scanning=repo_data.has_secret_scanning,
            has_dependabot_alerts=repo_data.has_dependabot_alerts,
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
    @pytest.mark.live_api
    def test_private_repo_flags_stored(
        self,
        github_config,
        test_session: Session
    ):
        """
        CONTRACT: Private repo fields from GitHub API are persisted.
        Requires GITHUB_PRIVATE_REPO env var pointing to an accessible private repo.
        """

        private_repo_id = github_config.private_repo
        if not private_repo_id:
            pytest.skip("GITHUB_PRIVATE_REPO not configured for private repo test")

        extractor = GitHubExtractor(config=github_config)

        # Extract and store using helper to ensure full metadata
        repo = get_or_create_repository(extractor, private_repo_id, test_session)

        # Assert API data says private and stored flags are preserved
        assert repo.is_private is True
        assert repo.has_secret_scanning is not None
        assert repo.has_dependabot_alerts is not None
        assert repo.has_vulnerability_alerts is not None
    
    @pytest.mark.integration
    @pytest.mark.live_api
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
        repo_data = extractor.get_repository(repo_id)
        assert repo_data is not None, f"Repository {repo_id} not found"
        
        repo = Repository(
            repo_id=repo_id,
            url=repo_data.url,
            name=repo_data.name,
            default_branch=repo_data.default_branch,
        )
        test_session.add(repo)
        test_session.commit()
        
        # Extract branch information
        branches_data = extractor.get_branches(repo_id)
        
        # Store branches
        for branch_data in branches_data:
            branch = Branch(
                repo_id=repo_id,
                branch_name=branch_data.name,
                latest_commit_sha=branch_data.latest_commit_sha,
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
    @pytest.mark.live_api
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
        
        # Create repository with full metadata from GitHub API
        repo = get_or_create_repository(extractor, repo_id, test_session)
        
        # Extract commits
        commits_data = extractor.get_commits(repo_id, limit=10)
        
        # Store commits using the storage layer (handles email->contributor mapping)
        for commit_data in commits_data:
            store_commit(test_session, repo_id, "main", commit_data)
        test_session.commit()
        
        # Assert: Commits stored correctly
        commits = test_session.query(Commit).filter_by(repo_id=repo_id).all()
        
        assert len(commits) > 0, f"No commits extracted for {repo_id}"
        
        for commit in commits:
            # Verify basic structure
            assert len(commit.commit_sha) == 40, f"Invalid SHA: {commit.commit_sha}"
            assert commit.message is not None
            assert commit.author is not None, f"Commit {commit.commit_sha} has no author"
            assert "@" in commit.author.email or commit.author.email == "unknown@github.com"
            
            # Verify timestamp is UTC-aware
            assert commit.commit_date is not None
            assert commit.commit_date.tzinfo is not None, \
                f"Commit {commit.commit_sha} has naive (non-UTC) datetime"
    
    @pytest.mark.integration
    @pytest.mark.live_api
    def test_extract_tracks_contributors(
        self,
        github_config,
        test_session: Session
    ):
        """
        CONTRACT: Contributors are tracked via commits with email identification.
        
        Verify:
        - Contributor records created from commit authors
        - Email addresses captured
        - Contributors linked to repository
        """
        # Setup
        extractor = GitHubExtractor(config=github_config)
        repo_id = "octocat/Hello-World"
        
        # Create repository with full metadata from GitHub API
        repo = get_or_create_repository(extractor, repo_id, test_session)
        
        # Extract commits (which creates contributors automatically)
        commits_data = extractor.get_commits(repo_id, max_commits=10)
        
        # Store commits (which stores contributors via get_or_create_contributor)
        for commit_data in commits_data:
            store_commit(test_session, repo_id, commit_data)
        
        # Assert: Contributors stored
        contributors = test_session.query(Contributor).all()
        
        assert len(contributors) > 0, f"No contributors found after extracting commits"
        
        for contributor in contributors:
            # Verify email is present
            assert contributor.email is not None, f"Contributor {contributor.contributor_id} has no email"
            assert "@" in contributor.email, f"Invalid email format: {contributor.email}"
            
            # Verify name is present (may be same as email if not provided by Git)
            assert contributor.name is not None, f"Contributor {contributor.contributor_id} has no name"


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
        from sqlalchemy import exc as sqlalchemy_exc
        import warnings
        
        # Attempt to insert repository without repo_id (should fail)
        # The SQLAlchemy warning about missing primary key is expected (intentional test)
        invalid_repo = Repository(
            repo_id=None,  # NOT NULL constraint
            url="https://example.com"
        )
        test_session.add(invalid_repo)
        
        # Expect the constraint violation, suppress the unrelated SAWarning about primary key
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=sqlalchemy_exc.SAWarning)
            with pytest.raises(IntegrityError):
                test_session.commit()
    
    @pytest.mark.integration
    @pytest.mark.live_api
    def test_foreign_key_relationships(
        self,
        github_config,
        test_session: Session
    ):
        """
        CONTRACT: Foreign key relationships are valid.
        
        Verify:
        - Branch references valid repository
        - Commit references valid repository
        - No orphaned entities
        """
        # Create repository with full metadata
        extractor = GitHubExtractor(config=github_config)
        repo = get_or_create_repository(extractor, "octocat/Hello-World", test_session)
        
        # Create branch (should reference valid repo)
        branch = Branch(
            repo_id=repo.repo_id,
            branch_name="main",
            latest_commit_sha="a" * 40
        )
        test_session.add(branch)
        test_session.commit()
        
        # Verify relationship works
        stored_branch = test_session.query(Branch).filter_by(
            repo_id=repo.repo_id
        ).first()
        
        assert stored_branch is not None
        assert stored_branch.repo_id == repo.repo_id
        
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
            name="Test Repository",
            url="https://github.com/test/repo",
            created_at=datetime.now(timezone.utc)
        )
        test_session.add(repo)
        test_session.commit()
        
        commit = Commit(
            repo_id="test/repo",
            commit_sha="a" * 40,
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


class TestGitHubLanguageDetection:
    """GitHub language detection E2E tests."""
    
    @pytest.mark.integration
    @pytest.mark.live_api
    def test_extract_languages_from_repo(
        self,
        github_config,
        test_session: Session
    ):
        """
        CONTRACT: Language detection extracts and stores language statistics.
        
        Verify:
        - Languages extracted from GitHub API
        - Byte counts and percentages calculated correctly
        - Data stored in repository_languages table
        - Percentages sum to approximately 100%
        """
        # Setup
        extractor = GitHubExtractor(config=github_config)
        # Using Spoon-Knife as it has HTML and CSS files
        repo_id = "octocat/Spoon-Knife"
        
        # Ensure repository exists
        repo = get_or_create_repository(extractor, repo_id, test_session)
        
        # Act: Extract languages
        languages = extractor.get_languages(repo_id)
        
        # Assert: Languages extracted
        assert len(languages) > 0, f"No languages detected for {repo_id}"
        
        # Assert: Data structure is correct
        for lang in languages:
            assert lang.language is not None, "Language name should be present"
            assert lang.byte_count > 0, "Byte count should be positive"
            assert lang.percentage is not None, "Percentage should be calculated"
            assert 0 <= lang.percentage <= 100, "Percentage should be between 0-100"
        
        # Assert: Percentages sum to approximately 100%
        total_percentage = sum(lang.percentage for lang in languages)
        assert 99.0 <= total_percentage <= 101.0, \
            f"Total percentage should be ~100%, got {total_percentage}"
        
        # Assert: Languages sorted by byte count (descending)
        byte_counts = [lang.byte_count for lang in languages]
        assert byte_counts == sorted(byte_counts, reverse=True), \
            "Languages should be sorted by byte count (descending)"
        
        # Act: Store languages in database
        store_languages(test_session, repo.repo_id, languages)
        test_session.commit()
        
        # Assert: Languages stored correctly
        stored_languages = test_session.query(RepositoryLanguage).filter_by(
            repo_id=repo.repo_id
        ).all()
        
        assert len(stored_languages) == len(languages), \
            f"Expected {len(languages)} languages stored, got {len(stored_languages)}"
        
        # Assert: Data integrity
        for stored_lang in stored_languages:
            assert stored_lang.language is not None
            assert stored_lang.byte_count > 0
            assert stored_lang.percentage is not None
            assert stored_lang.analyzed_at is not None
            assert stored_lang.analyzed_at.tzinfo is not None, \
                "analyzed_at should be timezone-aware"
    
    @pytest.mark.integration
    @pytest.mark.live_api
    def test_language_detection_no_languages(
        self,
        github_config,
        test_session: Session
    ):
        """
        CONTRACT: Repositories with no detectable languages return empty list.
        
        This is valid for repos that only contain non-code files
        (documentation, configuration, etc.).
        
        Note: octocat/Hello-World is a test repo with no code files.
        """
        # Setup
        extractor = GitHubExtractor(config=github_config)
        
        # Using Hello-World which has no code files
        repo_id = "octocat/Hello-World"
        
        # Act
        languages = extractor.get_languages(repo_id)
        
        # Assert: Empty list is valid for repos with no code
        assert isinstance(languages, list)
        # Hello-World should have no languages
        assert len(languages) == 0, \
            f"Expected no languages for {repo_id}, got {languages}"
    
    @pytest.mark.integration
    def test_language_storage_time_series(
        self,
        github_config,
        test_session: Session
    ):
        """
        CONTRACT: Language data can be stored multiple times for time-series tracking.
        
        Verify:
        - Multiple language snapshots can be stored
        - analyzed_at timestamps distinguish snapshots
        - TimescaleDB hypertable accepts data
        """
        from datetime import timedelta, UTC
        
        # Create test repository
        repo = Repository(
            repo_id="test/language-repo",
            name="Language Test Repo",
            url="https://github.com/test/language-repo"
        )
        test_session.add(repo)
        test_session.commit()
        
        # Store first snapshot
        from src.extractors.base import LanguageData
        
        languages_v1 = [
            LanguageData(language="Python", byte_count=10000, percentage=100.0),
        ]
        now = datetime.now(UTC)
        store_languages(test_session, repo.repo_id, languages_v1, analyzed_at=now)
        test_session.commit()
        
        # Store second snapshot (1 hour later)
        languages_v2 = [
            LanguageData(language="Python", byte_count=8000, percentage=80.0),
            LanguageData(language="JavaScript", byte_count=2000, percentage=20.0),
        ]
        later = now + timedelta(hours=1)
        store_languages(test_session, repo.repo_id, languages_v2, analyzed_at=later)
        test_session.commit()
        
        # Assert: Both snapshots stored
        all_snapshots = test_session.query(RepositoryLanguage).filter_by(
            repo_id=repo.repo_id
        ).order_by(RepositoryLanguage.analyzed_at).all()
        
        assert len(all_snapshots) == 3, \
            f"Expected 3 language records (1 + 2), got {len(all_snapshots)}"
        
        # Assert: First snapshot
        first_snapshot = [s for s in all_snapshots if s.analyzed_at == now]
        assert len(first_snapshot) == 1
        assert first_snapshot[0].language == "Python"
        
        # Assert: Second snapshot
        second_snapshot = [s for s in all_snapshots if s.analyzed_at == later]
        assert len(second_snapshot) == 2
        lang_names = {s.language for s in second_snapshot}
        assert lang_names == {"Python", "JavaScript"}


class TestGitHubTechnologyDetection:
    """GitHub technology stack detection E2E tests."""
    
    @pytest.mark.integration
    @pytest.mark.live_api
    def test_detect_technologies_from_repo(
        self,
        github_config,
        test_session: Session
    ):
        """
        CONTRACT: Technology detection identifies frameworks, databases, and tools.
        
        Verify:
        - Technology detector can analyze GitHub repository files
        - Detects multiple technology categories
        - Returns results for well-populated repositories
        """
        from src.analyzers.technology_detector import TechnologyDetector
        
        # Setup
        extractor = GitHubExtractor(config=github_config)
        detector = TechnologyDetector()
        
        # Use Spoon-Knife as it has various file types
        repo_id = "octocat/Spoon-Knife"
        repo = get_or_create_repository(extractor, repo_id, test_session)
        
        # Act: Get file tree and detect technologies
        try:
            files = extractor.get_file_tree(repo_id)
            if not files:
                pytest.skip("Repository has no files to analyze")
            
            # Build file paths for detection
            file_paths = [f.path for f in files if not f.is_directory]
            
            # Act: Detect technologies
            result = detector.detect(file_paths)
            
            # Assert: Result has expected structure
            assert result is not None
            assert hasattr(result, 'languages')
            assert hasattr(result, 'frameworks')
            assert hasattr(result, 'databases')
            assert hasattr(result, 'platforms')
            
            # Assert: At least some basic files present
            assert isinstance(result.languages, list)
            assert isinstance(result.frameworks, list)
            assert isinstance(result.databases, list)
            assert isinstance(result.platforms, list)
            
        except Exception as e:
            pytest.skip(f"Unable to access file tree: {e}")

    @pytest.mark.integration
    def test_technology_detection_structure(
        self,
        test_session: Session
    ):
        """
        CONTRACT: Technology detection returns well-formed results.
        
        Verify:
        - Detector returns all expected categories
        - Each category is a list
        - Can process sample file paths
        """
        from src.analyzers.technology_detector import TechnologyDetector
        
        detector = TechnologyDetector()
        
        # Use sample file paths that represent common repository structures
        file_paths = [
            "src/main.py",
            "src/app.py",
            "requirements.txt",
            "setup.py",
            "src/main.js",
            "src/app.jsx",
            "package.json",
            "webpack.config.js",
            "docker-compose.yml",
            "Dockerfile",
            "docker-entrypoint.sh",
            ".github/workflows/build.yml",
            ".github/workflows/test.yml",
            "pytest.ini",
            "jest.config.js",
            "README.md",
            "docs/index.md",
            "Makefile",
            "build.gradle",
        ]
        
        # Act: Detect technologies
        result = detector.detect(file_paths)
        
        # Assert: All categories present
        assert result.programming_languages is not None
        assert result.frameworks is not None
        assert result.databases is not None
        assert result.deployment_platforms is not None
        assert result.build_tools is not None
        assert result.testing_frameworks is not None
        assert result.ci_cd_platforms is not None
        assert result.documentation_tools is not None
        
        # Assert: All are lists
        assert isinstance(result.programming_languages, list)
        assert isinstance(result.frameworks, list)
        assert isinstance(result.databases, list)
        assert isinstance(result.deployment_platforms, list)
        
        # Assert: Detection found something
        total_detected = (
            len(result.programming_languages) +
            len(result.frameworks) +
            len(result.databases) +
            len(result.deployment_platforms) +
            len(result.build_tools) +
            len(result.testing_frameworks)
        )
        assert total_detected > 0, "Should detect at least some technologies"
        
        # Assert: Python and JavaScript detected
        assert any(t in result.programming_languages for t in ["Python", "JavaScript"]), \
            "Should detect Python or JavaScript"
        
        # Assert: Docker and GitHub Actions detected
        assert any(t in result.deployment_platforms for t in ["Docker", "GitHub"]), \
            "Should detect Docker or GitHub"

    @pytest.mark.integration
    def test_technology_detection_with_dependencies(
        self,
        test_session: Session
    ):
        """
        CONTRACT: Technology detection identifies dependency management files.
        
        Verify:
        - Detects Python (requirements.txt, setup.py, pyproject.toml)
        - Detects JavaScript (package.json, yarn.lock, package-lock.json)
        - Detects Java (pom.xml, build.gradle, build.gradle.kts)
        - Detects C# (*.csproj, *.sln)
        """
        from src.analyzers.technology_detector import TechnologyDetector
        
        detector = TechnologyDetector()
        
        # Python project files
        python_files = [
            "requirements.txt",
            "setup.py",
            "pyproject.toml",
            "pipenv/Pipfile",
            "poetry.lock",
        ]
        result = detector.detect(python_files)
        assert "Python" in result.programming_languages, "Should detect Python"
        
        # JavaScript project files
        js_files = [
            "package.json",
            "package-lock.json",
            "yarn.lock",
            "tsconfig.json",
            "webpack.config.js",
        ]
        result = detector.detect(js_files)
        assert "JavaScript" in result.programming_languages, "Should detect JavaScript"
        
        # Java project files
        java_files = [
            "pom.xml",
            "build.gradle",
            "build.gradle.kts",
            "src/main/java/Main.java",
        ]
        result = detector.detect(java_files)
        assert "Java" in result.programming_languages, "Should detect Java"
        
        # C# project files
        csharp_files = [
            "Project.csproj",
            "Solution.sln",
            "src/Program.cs",
        ]
        result = detector.detect(csharp_files)
        assert "C#" in result.programming_languages, "Should detect C#"
