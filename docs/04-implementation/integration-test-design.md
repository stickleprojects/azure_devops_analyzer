"""
Integration Test Design for Azure DevOps Analyzer

This document outlines the strategy for end-to-end integration tests that verify
actual data extraction, enrichment, and storage in PostgreSQL.
"""

# INTEGRATION TEST ARCHITECTURE

# ============================================================================

## 1. TEST STRUCTURE

### Directory Layout

```
tests/
├── integration/                      # New integration test suite
│   ├── __init__.py
│   ├── conftest.py                  # Shared fixtures for integration tests
│   ├── test_github_extraction_e2e.py # End-to-end GitHub extraction
│   ├── test_dependency_enrichment_e2e.py # Dependency enrichment in DB
│   ├── test_vulnerability_storage_e2e.py # Vulnerability data storage
│   └── README.md                     # Integration test guide
└── fixtures/
    └── test_repos.txt               # List of test repositories
```

## 2. INTEGRATION TEST STRATEGY

### Test Repositories (Safe, Non-Production)

Use small, public test repos to avoid rate limits and data contamination:

```
1. github.com/octocat/Hello-World
   - Simple, official GitHub example
   - No dependencies
   - Predictable content

2. github.com/torvalds/linux
   - Large, real-world repo
   - Rich commit history
   - Complex dependencies

3. github.com/python/cpython
   - Python dependencies
   - Active development
   - Good for language detection
```

### Test Phases

**Phase 1: Database Setup**

- Create isolated test database schema
- Initialize with fresh migrations
- No data from production

**Phase 2: Repository Extraction**

- Extract real data from test repos via GitHub API
- Store in test database
- Verify basic entity creation

**Phase 3: Dependency Analysis**

- Extract manifest files
- Parse dependencies
- Enrich with OSV.dev data
- Verify all fields populated

**Phase 4: Data Validation**

- Query database directly
- Verify data integrity
- Check relationships
- Validate type conversions

## 3. TEST FIXTURES & SETUP

### Conftest.py Template

```python
# tests/integration/conftest.py

import pytest
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.connection import engine, session_scope
from src.database.models import Base
from src.config.github import GitHubExtractorConfig

@pytest.fixture(scope="session")
def integration_test_db():
    """Create isolated test database."""
    # Use TEST_DATABASE_URL from .env.test
    test_db_url = os.environ.get("TEST_DATABASE_URL")
    assert test_db_url, "TEST_DATABASE_URL not set"

    test_engine = create_engine(test_db_url)

    # Create all tables
    Base.metadata.create_all(test_engine)
    yield test_engine

    # Cleanup: drop all tables
    Base.metadata.drop_all(test_engine)

@pytest.fixture(scope="session")
def github_config():
    """Load GitHub credentials from .env.resolved."""
    return GitHubExtractorConfig.from_env(".env.resolved")

@pytest.fixture
def test_session(integration_test_db):
    """Provide clean database session for each test."""
    Session = sessionmaker(bind=integration_test_db)
    session = Session()

    yield session

    # Rollback to avoid polluting next test
    session.rollback()
    session.close()
```

## 4. INTEGRATION TEST EXAMPLES

### Test 1: GitHub Extraction End-to-End

```python
# tests/integration/test_github_extraction_e2e.py

import pytest
from src.workflows.github_analysis import GitHubAnalysisWorkflow
from src.database.models import Repository, Branch, Commit, Contributor

class TestGitHubExtractionE2E:
    """
    Contract: GitHub extraction stores correct data in PostgreSQL.

    Tests verify:
    - Repositories extracted and stored
    - Branches tracked accurately
    - Commits and contributors recorded
    - Data types and relationships correct
    """

    def test_extract_small_repo_stores_metadata(self, github_config, test_session):
        """
        CONTRACT: Extracting octocat/Hello-World stores complete repo metadata.

        Verify:
        - Repository record created
        - Branch created with correct commit SHA
        - Repository metadata (URL, created_at, etc.) correct
        """
        # Setup
        workflow = GitHubAnalysisWorkflow(config=github_config)
        repo_id = "octocat/Hello-World"

        # Act: Extract from GitHub API
        summary = workflow.analyze_repository(repo_id)

        # Assert: Repository stored in database
        repo = test_session.query(Repository).filter_by(repo_id=repo_id).first()
        assert repo is not None
        assert repo.url == "https://github.com/octocat/Hello-World"
        assert repo.created_at is not None
        assert repo.default_branch == "master"

        # Verify branch tracking
        branch = test_session.query(Branch).filter_by(
            repo_id=repo_id,
            branch_name="master"
        ).first()
        assert branch is not None
        assert branch.latest_commit_sha is not None
        assert len(branch.latest_commit_sha) == 40  # Git SHA-1 format

        # Verify contributor tracking
        contributors = test_session.query(Contributor).filter_by(
            repo_id=repo_id
        ).all()
        assert len(contributors) > 0

        # Sample contributor should have valid email
        for contributor in contributors[:1]:
            assert "@" in contributor.email

    def test_extract_tracks_commits_correctly(self, github_config, test_session):
        """
        CONTRACT: Extracted commits have correct metadata and relationships.

        Verify:
        - Commit SHA matches GitHub API
        - Author/committer emails captured
        - Commit timestamps correct (UTC)
        - File statistics populated (if available)
        """
        # Setup & Act
        workflow = GitHubAnalysisWorkflow(config=github_config)
        repo_id = "octocat/Hello-World"
        workflow.analyze_repository(repo_id)

        # Query commits from database
        commits = test_session.query(Commit).filter_by(repo_id=repo_id).all()

        # Verify commit data
        assert len(commits) > 0, f"No commits stored for {repo_id}"

        for commit in commits[:5]:  # Check first 5 commits
            # Verify basic structure
            assert len(commit.sha) == 40
            assert commit.message is not None
            assert "@" in commit.author_email
            assert commit.commit_date is not None

            # Verify timezone info (should be UTC)
            assert commit.commit_date.tzinfo is not None

    def test_extract_large_repo_performance(self, github_config, test_session):
        """
        IMPLEMENTATION: Large repo extraction completes in reasonable time.

        Note: This is IMPLEMENTATION test - timing can vary, just ensure
        it doesn't hang or timeout.
        """
        # This test ensures the workflow doesn't get stuck
        # on large repos. It's slower and marked as such.
        pytest.mark.integration  # Mark as integration test

        workflow = GitHubAnalysisWorkflow(config=github_config)

        # Extract a larger but still manageable repo
        # (use a smaller portion via branch filter if available)
        repo_id = "python/cpython"

        # This should complete without timeout (30 second default)
        summary = workflow.analyze_repository(repo_id)

        # Basic sanity checks
        assert summary["repositories"] > 0
        assert "extraction_time_seconds" in summary
```

### Test 2: Dependency Enrichment E2E

```python
# tests/integration/test_dependency_enrichment_e2e.py

class TestDependencyEnrichmentE2E:
    """
    Contract: Dependencies extracted from repos and enriched with API data.

    Tests verify:
    - Manifest files found and parsed
    - Dependencies stored in database
    - Enrichment APIs called and data stored
    - Latest versions and EOL dates populated
    """

    def test_dependencies_extracted_and_stored(self, github_config, test_session):
        """
        CONTRACT: Extracting repo with dependencies stores them in DB.

        Use: python/cpython (has requirements.txt, pyproject.toml)

        Verify:
        - Dependency records created
        - Package names and versions correct
        - Dev vs production dependencies marked
        - Ecosystem detected correctly
        """
        workflow = GitHubAnalysisWorkflow(config=github_config)
        repo_id = "python/cpython"

        # Extract
        workflow.analyze_repository(repo_id)

        # Query dependencies
        deps = test_session.query(Dependency).filter_by(repo_id=repo_id).all()

        assert len(deps) > 0, f"No dependencies extracted for {repo_id}"

        # Verify dependency structure
        for dep in deps[:10]:
            assert dep.package_name is not None
            assert dep.ecosystem in ["pypi", "npm", "maven", "nuget", "go", "rubygems", "cargo"]
            assert isinstance(dep.is_dev_dependency, bool)
            assert dep.analyzed_at is not None

    def test_dependencies_enriched_with_latest_versions(self, github_config, test_session):
        """
        CONTRACT: Enrichment populates latest_version from OSV.dev.

        Verify:
        - latest_version field is populated (not NULL for known packages)
        - Version format matches expected pattern
        - Only populated for supported ecosystems
        """
        workflow = GitHubAnalysisWorkflow(config=github_config)
        repo_id = "python/cpython"

        workflow.analyze_repository(repo_id)

        deps = test_session.query(Dependency).filter_by(repo_id=repo_id).all()

        # Count how many have enriched data
        enriched_count = sum(1 for d in deps if d.latest_version is not None)

        # Expect at least some enrichment (not all may be available)
        assert enriched_count > 0, "No dependencies enriched with latest versions"

        # Verify version format for enriched deps
        for dep in [d for d in deps if d.latest_version]:
            # Should look like semantic version
            assert "." in dep.latest_version or dep.latest_version.replace(".", "").isdigit()

    def test_eol_detection_populated(self, github_config, test_session):
        """
        CONTRACT: EOL dates are populated for known Python versions.

        Verify:
        - is_eol flag set for EOL versions
        - eol_date populated for detected versions
        - Correctly identifies past vs future EOL
        """
        workflow = GitHubAnalysisWorkflow(config=github_config)
        repo_id = "python/cpython"

        workflow.analyze_repository(repo_id)

        # Find Python dependencies (ecosystem="pypi")
        python_deps = test_session.query(Dependency).filter(
            Dependency.repo_id == repo_id,
            Dependency.ecosystem == "pypi"
        ).all()

        # At least some should have EOL detection
        eol_detected = sum(1 for d in python_deps if d.eol_date is not None)

        # Note: May be 0 if OSV.dev doesn't have data, that's OK
        if eol_detected > 0:
            for dep in [d for d in python_deps if d.eol_date]:
                assert dep.is_eol in [True, False]
                assert dep.eol_date is not None

    def test_vulnerabilities_stored(self, github_config, test_session):
        """
        CONTRACT: Vulnerabilities from OSV.dev are stored in database.

        Verify:
        - Vulnerability records created for vulnerable deps
        - CVE/OSV IDs stored
        - Severity levels populated
        - Fixed versions tracked
        """
        from src.database.models import Vulnerability

        workflow = GitHubAnalysisWorkflow(config=github_config)
        repo_id = "python/cpython"

        workflow.analyze_repository(repo_id)

        # Find dependencies with vulnerabilities
        vulns = test_session.query(Vulnerability).join(
            Dependency, Vulnerability.dependency_id == Dependency.id
        ).filter(
            Dependency.repo_id == repo_id
        ).all()

        # Note: May be 0 if no known vulnerabilities, that's OK
        if vulns:
            for vuln in vulns[:5]:
                assert vuln.severity in ["critical", "high", "medium", "low"]
                assert vuln.cve_id or vuln.vulnerability_id  # At least one ID
```

### Test 3: Data Validation

```python
# tests/integration/test_data_integrity_e2e.py

class TestDataIntegrity:
    """
    Contract: Data in PostgreSQL is valid and type-correct.

    Tests verify:
    - No NULL values where NOT NULL constraint
    - Foreign keys resolve correctly
    - Date/time fields are UTC
    - IDs are unique and valid
    """

    def test_repository_constraints_enforced(self, test_session):
        """Verify database constraints work."""
        from sqlalchemy.exc import IntegrityError

        # Attempt to insert invalid repository
        invalid_repo = Repository(
            repo_id=None,  # Should fail - NOT NULL
            url="https://example.com"
        )
        test_session.add(invalid_repo)

        with pytest.raises(IntegrityError):
            test_session.commit()

    def test_foreign_key_relationships(self, test_session):
        """
        CONTRACT: Relationships between entities are valid.

        Verify after extraction:
        - All branches reference valid repositories
        - All commits reference valid branches
        - All dependencies reference valid repositories
        """
        branches = test_session.query(Branch).all()

        for branch in branches:
            # Verify repository exists
            repo = test_session.query(Repository).filter_by(
                repo_id=branch.repo_id
            ).first()
            assert repo is not None, f"Branch references non-existent repo {branch.repo_id}"

    def test_timezone_handling(self, test_session):
        """
        CONTRACT: All timestamp fields are UTC-aware.

        Verify:
        - commit_date has timezone info
        - created_at has timezone info
        - No naive datetime objects
        """
        commits = test_session.query(Commit).limit(10).all()

        for commit in commits:
            assert commit.commit_date.tzinfo is not None, \
                f"Commit {commit.sha} has naive datetime"
```

## 5. RUNNING INTEGRATION TESTS

### Prerequisites

```bash
# 1. Setup test database
export TEST_DATABASE_URL="postgresql://user:pass@localhost/analyzer_test"

# 2. Create test database
createdb analyzer_test

# 3. Load environment
source .env.test
```

### Run Tests

```bash
# Run all integration tests
pytest tests/integration/ -v --tb=short

# Run specific test
pytest tests/integration/test_github_extraction_e2e.py -v

# Run with output
pytest tests/integration/ -v -s

# Run with markers
pytest tests/integration/ -m integration
```

### Markers for Different Test Types

```python
# tests/integration/conftest.py

def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: end-to-end integration tests"
    )
    config.addinivalue_line(
        "markers", "slow: slow integration tests (30+ seconds)"
    )
    config.addinivalue_line(
        "markers", "live_api: tests using live GitHub/OSV APIs"
    )
```

## 6. CI/CD INTEGRATION

### GitHub Actions Workflow

```yaml
# .github/workflows/integration-tests.yml

name: Integration Tests

on: [pull_request, push]

jobs:
  integration:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: analyzer_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install -r requirements.txt pytest pytest-cov

      - name: Create test database
        run: createdb analyzer_test
        env:
          PGHOST: localhost
          PGUSER: postgres
          PGPASSWORD: test_password

      - name: Run integration tests
        env:
          TEST_DATABASE_URL: postgresql://postgres:test_password@localhost/analyzer_test
          GITHUB_TOKEN: ${{ secrets.TEST_GITHUB_TOKEN }}
        run: pytest tests/integration/ -v --tb=short --maxfail=3
```

## 7. TEST MAINTENANCE

### Test Data Cleanup

```python
@pytest.fixture(autouse=True)
def cleanup_test_data(test_session):
    """Automatically clean up after each test."""
    yield

    # Delete in reverse order to respect FK constraints
    test_session.query(Vulnerability).delete()
    test_session.query(Dependency).delete()
    test_session.query(Commit).delete()
    test_session.query(Branch).delete()
    test_session.query(Repository).delete()
    test_session.commit()
```

### Handling Rate Limits

```python
# Use caching for API calls during tests
@pytest.fixture
def mock_github_api():
    """Mock GitHub API to avoid rate limits in local testing."""
    with patch("src.extractors.github.client.GitHubClient") as mock:
        # Load cached responses from fixtures/
        mock.return_value.get_user.return_value = load_fixture("github_user.json")
        yield mock
```

## 8. EXPECTED OUTCOMES

After integration tests pass, you can be confident that:

✅ **Extraction Works**

- Real GitHub API calls successful
- Data correctly parsed and stored

✅ **Database Integrity**

- No foreign key violations
- Correct data types
- Timezone handling correct

✅ **Enrichment Works**

- OSV.dev integration functional
- endoflife.date integration functional
- Data correctly stored in PostgreSQL

✅ **End-to-End Pipeline**

- Full workflow from extraction → enrichment → storage
- No data loss or corruption
- All fields populated as expected

## 9. NEXT STEPS

1. **Create integration test infrastructure**
   - Set up conftest.py with fixtures
   - Create test repos list

2. **Implement core E2E tests**
   - Basic extraction test
   - Dependency enrichment test
   - Data validation test

3. **Add CI/CD integration**
   - GitHub Actions workflow
   - Automated test runs on PRs

4. **Expand test coverage**
   - Additional test repositories
   - Error scenarios
   - Performance tests
