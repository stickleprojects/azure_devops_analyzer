# Test Implementation Plan

**Created**: 2026-01-23  
**Last Updated**: 2026-01-23  
**Current Coverage**: 2.01% (72/3,576 lines)  
**Target Coverage**: 80%+ for critical business logic

## Executive Summary

This document outlines a phased approach to achieving comprehensive test coverage for the Azure DevOps Analyzer project. Tests are prioritized based on business impact, architectural boundaries, and risk.

## Current Status

- ✅ **Phase 1.1 Complete**: Database Storage CONTRACT Tests (29/29 passing)
- 🔄 **Phase 1.2 In Progress**: Database Models Tests
- ⏳ **Phase 2**: Business Logic - Analyzers
- ⏳ **Phase 3**: Language Parsers

## Priority Levels

- **P0 (CRITICAL)**: Data integrity, core business logic - Must have
- **P1 (HIGH)**: Feature functionality, user-facing behavior - Should have  
- **P2 (MEDIUM)**: Integration points, orchestration - Nice to have
- **P3 (LOW)**: Platform-specific features not in active use

---

## Phase 1: Foundation - Database Layer (P0 CRITICAL)

**Status**: ✅ Phase 1.1 Complete (29/29 tests passing) | 🔄 Phase 1.2 In Progress  
**Why First**: Database is the source of truth. Corrupted data = corrupted analytics.  
**Estimated Effort**: 2-3 days  
**Target Coverage**: 80%+

### 1.1 Database Storage Tests ✅ COMPLETE

**Location**: `tests/contract/database/test_storage_contract.py`  
**Status**: ✅ **29 tests passing** (100%)  
**Completed**: 2026-01-23  
**Type**: CONTRACT tests (business requirements)

**Infrastructure**:
- ✅ PostgreSQL via Docker (TimescaleDB)
- ✅ Transaction-based test isolation with nested transactions (SAVEPOINTs)
- ✅ `.env.test` for test-specific configuration
- ✅ Comprehensive test fixtures in `tests/fixtures/sample_data.py`

```python
# Test file structure:
tests/
  contract/
    database/
      conftest.py                 # PostgreSQL fixtures with transaction isolation
      test_storage_contract.py    # ✅ 29 CONTRACT tests passing
  fixtures/
    sample_data.py                # Reusable test data fixtures
```

**CONTRACT Tests Implemented** (All Passing ✅):
- ✅ Organization storage (4 tests)
  - Create new organization
  - Update existing organization  
  - Get or create idempotency
  - Project hierarchy
- ✅ Repository storage (4 tests)
  - Create new repository with all fields
  - Update existing repository
  - Associate with team
  - Store security and quality metrics
- ✅ Branch storage (2 tests)
  - Create new branch
  - Update existing branch commit SHA
- ✅ Commit storage (5 tests)
  - Create new commit with contributor link
  - Auto-create contributor if not exists
  - Idempotent operation (returns None if exists)
  - Truncate long messages to 1000 chars
  - Handle null optional fields
- ✅ Pull request storage (2 tests)
  - Create new PR with all fields
  - Idempotent operation
- ✅ Contributor storage (2 tests)
  - Create new contributor
  - Get existing contributor (same ID)
- ✅ Team storage (2 tests)
  - Create new team
  - Get existing team
- ✅ Repository scan logic (3 tests)
  - Never analyzed → should scan
  - Recently analyzed → skip scan
  - Old analysis → should rescan
- ✅ Foreign key constraints (2 tests)
  - Commit requires valid repository
  - Repository cascade deletes commits
- ✅ Null handling (2 tests)
  - Repository optional fields
  - Commit optional fields
- ✅ Project hierarchy (1 test)
  - Organization → Project → Repository chain

**Test Data Fixtures**:
```python
@pytest.fixture
def sample_repository_data():
    """CONTRACT: Minimum valid repository data."""
    return RepositoryData(
        repo_id="test-org/test-repo",
        name="test-repo",
        platform=Platform.GITHUB,
        url="https://github.com/test-org/test-repo",
        default_branch="main",
        # ... full data structure
    )
```

**Key Implementation Details**:
- Transaction isolation ensures tests never pollute each other
- Tests can call `session.commit()` safely (rolls back automatically)
- PostgreSQL ARRAY types fully supported
- TRUNCATE CASCADE for efficient cleanup

---

### 1.2 Database Models Tests 🔄 IN PROGRESS

**Location**: `tests/contract/database/test_models_contract.py`  
**Status**: 🔄 Not yet implemented  
**Type**: CONTRACT tests (ORM behavior)

---

## Phase 2: Business Logic - Analyzers (P0 CRITICAL)

**Why Second**: Analyzers transform raw data into insights. Wrong analysis = wrong decisions.  
**Estimated Effort**: 3-4 days  
**Target Coverage**: 85%+

### 2.1 Contributor Analyzer (`tests/analyzers/test_contributor_analyzer.py`)

**CONTRACT Tests**:
- ✅ Calculate contributor statistics from commit data
- ✅ Aggregate by author email (normalize similar emails)
- ✅ Time-based metrics (commits per day/week/month)
- ✅ Activity patterns detection (active days, streak calculation)
- ✅ Code churn metrics (additions, deletions, net change)
- ✅ Handle edge cases:
  - Single commit from contributor
  - Multiple commits same day
  - Commits with no file changes
  - Authors with multiple email addresses

**Test Data**:
```python
@pytest.fixture
def sample_commits():
    """CONTRACT: Commits representing various contribution patterns."""
    return [
        {
            "author": "dev1@example.com",
            "timestamp": "2026-01-01T10:00:00Z",
            "additions": 100,
            "deletions": 20,
            "files_changed": 5
        },
        # More test data...
    ]
```

**Critical Test Cases**:
1. Empty commit list → returns empty statistics
2. Single contributor → statistics calculated correctly
3. Multiple contributors → aggregated separately
4. Contributor with email variants → normalized to single identity
5. Commits spanning multiple months → time-based metrics accurate

### 2.2 Dependency Analyzer (`tests/analyzers/test_dependency_analyzer.py`)

**CONTRACT Tests**:
- ✅ Detect dependencies from repository files
- ✅ Categorize by package manager (npm, pip, maven, etc.)
- ✅ Extract version constraints correctly
- ✅ Identify direct vs transitive dependencies
- ✅ Flag outdated dependencies
- ✅ Detect security vulnerabilities (if data available)

**Edge Cases**:
- Missing dependency files → returns empty list
- Malformed package files → logs warning, continues
- Mixed dependency managers → all detected
- Version ranges vs exact versions → both supported

### 2.3 README Analyzer (`tests/analyzers/test_readme_analyzer.py`)

**CONTRACT Tests**:
- ✅ Extract documentation quality metrics
- ✅ Detect presence of sections (Installation, Usage, Contributing)
- ✅ Count code examples
- ✅ Identify broken links
- ✅ Badge detection and validation
- ✅ Calculate readability scores

**Test Cases**:
1. No README → quality score = 0
2. Minimal README → low quality score with specific missing sections flagged
3. Comprehensive README → high quality score
4. README with broken links → detected and reported
5. Multiple README formats (README.md, README.rst) → all processed

---

## Phase 3: Language Parsers (P0-P1 CRITICAL → HIGH)

**Estimated Effort**: 4-5 days (parallel development possible)  
**Target Coverage**: 80%+ per parser

### 3.1 Python Parser (`tests/analyzers/parsers/test_python_parser.py`)

**Priority**: P0 (Most common in modern repos)

**CONTRACT Tests**:
- ✅ Parse requirements.txt correctly
- ✅ Parse setup.py dependencies
- ✅ Parse pyproject.toml (PEP 621)
- ✅ Parse Pipfile/Pipfile.lock
- ✅ Parse Poetry pyproject.toml
- ✅ Extract version constraints (==, >=, ~=, etc.)
- ✅ Handle extras/optional dependencies
- ✅ Parse environment markers (python_version, etc.)

**Test Fixtures**:
```python
@pytest.fixture
def requirements_txt_content():
    """CONTRACT: Valid requirements.txt with various version formats."""
    return """
    django==4.2.0
    requests>=2.28.0,<3.0.0
    pytest~=7.0
    black; python_version >= '3.8'
    """
```

### 3.2 Node.js Parser (`tests/analyzers/parsers/test_nodejs_parser.py`)

**Priority**: P0

**CONTRACT Tests**:
- ✅ Parse package.json dependencies
- ✅ Parse package-lock.json for exact versions
- ✅ Distinguish dependencies vs devDependencies
- ✅ Parse peerDependencies
- ✅ Handle npm, yarn, pnpm lock files
- ✅ Extract version ranges (^, ~, *, etc.)

### 3.3 Java/Maven Parser (`tests/analyzers/parsers/test_java_parser.py`)

**Priority**: P1

**CONTRACT Tests**:
- ✅ Parse pom.xml dependencies
- ✅ Parse Gradle build files (build.gradle, build.gradle.kts)
- ✅ Extract groupId:artifactId:version
- ✅ Handle dependency scopes (compile, test, provided)
- ✅ Parse parent POM references

### 3.4 .NET Parser (`tests/analyzers/parsers/test_dotnet_parser.py`)

**Priority**: P1

**CONTRACT Tests**:
- ✅ Parse .csproj files
- ✅ Parse packages.config
- ✅ Parse Directory.Build.props
- ✅ Extract NuGet package references
- ✅ Handle TargetFramework variations

### 3.5 Go Parser (`tests/analyzers/parsers/test_go_parser.py`)

**Priority**: P1

**CONTRACT Tests**:
- ✅ Parse go.mod files
- ✅ Parse go.sum for checksums
- ✅ Extract module paths and versions
- ✅ Handle replace directives
- ✅ Parse pseudo-versions

### 3.6 Ruby/Rust Parsers

**Priority**: P2 (Lower frequency)

**CONTRACT Tests**:
- Ruby: Parse Gemfile/Gemfile.lock
- Rust: Parse Cargo.toml/Cargo.lock

---

## Phase 4: Platform Extractors (P1 HIGH)

**Estimated Effort**: 3-4 days  
**Target Coverage**: 75%+

### 4.1 GitHub Extractor (`tests/extractors/github/test_github_extractor.py`)

**Current State**: Minimal tests exist  
**Expand to Include**:

**CONTRACT Tests**:
- ✅ Fetch repositories for user/organization
- ✅ Fetch commits with pagination
- ✅ Fetch pull requests with all fields
- ✅ Fetch contributors list
- ✅ Rate limit handling (wait and retry)
- ✅ Authentication token validation
- ✅ Handle API errors gracefully (404, 403, 500)

**IMPLEMENTATION Tests**:
- Pagination cursor management
- GraphQL query optimization
- Response caching strategies
- Retry logic with exponential backoff

**Mock Strategy**:
```python
@pytest.fixture
def mock_github_api(mocker):
    """IMPLEMENTATION: Mock GitHub API responses."""
    mock_response = {
        "data": {
            "repository": {
                "name": "test-repo",
                "defaultBranchRef": {"name": "main"},
                # ...
            }
        }
    }
    mocker.patch("requests.post", return_value=mock_response)
```

### 4.2 GitHub Client (`tests/extractors/github/test_github_client.py`)

**CONTRACT Tests**:
- ✅ GraphQL query construction
- ✅ Response parsing and transformation
- ✅ Error response handling
- ✅ Retry on transient failures
- ✅ Token refresh mechanism

### 4.3 Base Extractor (`tests/extractors/test_base_extractor.py`)

**CONTRACT Tests** (Abstract base class behavior):
- ✅ Rate limiting enforcement
- ✅ Logging standardization
- ✅ Error propagation
- ✅ Configuration validation

---

## Phase 5: Workflows (P2 MEDIUM)

**Estimated Effort**: 2-3 days  
**Target Coverage**: 70%+

### 5.1 GitHub Analysis Workflow (`tests/workflows/test_github_analysis.py`)

**CONTRACT Tests**:
- ✅ End-to-end repository analysis orchestration
- ✅ Extractor → Analyzer → Storage pipeline
- ✅ Error handling at each stage
- ✅ Partial success scenarios (some steps fail)
- ✅ Progress tracking and reporting

**Integration Test Structure**:
```python
class TestGitHubAnalysisWorkflow:
    """CONTRACT: End-to-end analysis workflow behavior."""
    
    def test_full_repository_analysis_pipeline(self, mock_github, mock_db):
        """CONTRACT: Complete analysis stores all expected data."""
        workflow = GitHubAnalysisWorkflow()
        result = workflow.analyze_repository("owner/repo")
        
        assert result.commits_stored > 0
        assert result.contributors_analyzed > 0
        assert result.dependencies_found >= 0  # May be 0 for some repos
```

**Test Scenarios**:
1. Happy path: All steps succeed
2. Extractor failure: Workflow fails gracefully, no partial data stored
3. Analyzer failure: Raw data stored, analysis marked as failed
4. Storage failure: Transaction rolled back, no corrupted data
5. Retry on transient failure: Workflow resumes from checkpoint

---

## Phase 6: Azure DevOps Extractor (P3 LOW)

**Estimated Effort**: 2 days  
**Target Coverage**: 60%+ (minimal for now)

**Why Low Priority**: Not actively used based on codebase analysis

### 6.1 Azure DevOps Extractor (`tests/extractors/azure_devops/test_azure_devops_extractor.py`)

**CONTRACT Tests**:
- ✅ Fetch projects and repositories
- ✅ Fetch commits and work items
- ✅ Authentication with PAT tokens
- ✅ API version compatibility

**Note**: Expand when Azure DevOps support becomes active requirement

---

## Test Infrastructure & Tooling

### Test Organization Structure

```
tests/
├── contract/              # Business requirement tests (STRICT)
│   ├── database/
│   │   ├── test_storage_contract.py
│   │   └── test_models_contract.py
│   ├── analyzers/
│   │   ├── test_contributor_analyzer_contract.py
│   │   ├── test_dependency_analyzer_contract.py
│   │   └── parsers/
│   ├── extractors/
│   │   ├── github/
│   │   └── azure_devops/
│   └── workflows/
│
├── implementation/        # Technical detail tests (FLEXIBLE)
│   ├── database/
│   │   └── test_storage_impl.py
│   ├── extractors/
│   │   └── github/
│   │       └── test_github_client_impl.py
│   └── ...
│
├── integration/          # Cross-component tests
│   ├── test_end_to_end_github_analysis.py
│   └── test_database_with_real_schema.py
│
├── fixtures/             # Shared test data
│   ├── sample_repositories.py
│   ├── sample_commits.py
│   └── sample_github_responses.py
│
└── conftest.py          # Global pytest configuration
```

### Required pytest Plugins

```bash
# Install additional test dependencies
pip install pytest-cov pytest-mock pytest-asyncio pytest-timeout freezegun
```

### Fixtures to Create

#### Global Fixtures (`tests/conftest.py`)

```python
import pytest
from pathlib import Path

@pytest.fixture(scope="session")
def test_data_dir():
    """Path to test data directory."""
    return Path(__file__).parent / "fixtures" / "data"

@pytest.fixture
def clean_database(db_connection):
    """Provide clean database for each test."""
    # Setup: Clear all tables
    yield db_connection
    # Teardown: Clear again

@pytest.fixture
def sample_repository():
    """Standard test repository data."""
    return {
        "name": "test-repo",
        "platform": "github",
        "url": "https://github.com/test-org/test-repo",
        "default_branch": "main"
    }
```

#### Module-Specific Fixtures

Each test module should have focused fixtures for its domain.

### Test Naming Conventions

**CONTRACT Tests**:
- `test_contract_<behavior>` - e.g., `test_contract_repository_must_have_unique_url`
- Docstring starts with: `"""CONTRACT: <requirement>"""`

**IMPLEMENTATION Tests**:
- `test_impl_<mechanism>` - e.g., `test_impl_batch_insert_uses_single_transaction`
- Docstring starts with: `"""IMPLEMENTATION: <technical detail>"""`

### Coverage Reporting

```bash
# Run tests with coverage
pytest --cov=src --cov-report=html --cov-report=term

# Coverage thresholds in pytest.ini or pyproject.toml
[tool.pytest.ini_options]
addopts = "--cov=src --cov-report=term-missing --cov-fail-under=80"
```

---

## Implementation Timeline

### Week 1: Foundation
- **Day 1-2**: Database storage tests (P0)
- **Day 3**: Database models tests (P0)
- **Day 4-5**: Contributor analyzer tests (P0)

### Week 2: Core Business Logic
- **Day 6-7**: Dependency analyzer tests (P0)
- **Day 8-9**: Python & Node.js parser tests (P0)
- **Day 10**: README analyzer tests (P1)

### Week 3: Language Parsers
- **Day 11-12**: Java/Maven parser tests (P1)
- **Day 13**: .NET parser tests (P1)
- **Day 14**: Go parser tests (P1)
- **Day 15**: Ruby/Rust parser tests (P2)

### Week 4: Integration & Platform
- **Day 16-17**: GitHub extractor expansion (P1)
- **Day 18-19**: Workflow orchestration tests (P2)
- **Day 20**: Integration tests, cleanup, documentation

---

## Success Metrics

### Coverage Targets
- **Overall**: 80%+ line coverage
- **Critical Path** (database, analyzers): 85%+
- **Extractors**: 75%+
- **Workflows**: 70%+

### Quality Metrics
- All tests pass consistently
- No flaky tests (tests that intermittently fail)
- Test suite runs in < 5 minutes
- Clear separation between CONTRACT and IMPLEMENTATION tests

### Documentation
- Each test has descriptive docstring explaining WHAT is tested
- CONTRACT tests document business requirements
- Complex test setups have inline comments explaining WHY

---

## Quick Start Guide (For Tomorrow)

### Step 1: Set Up Test Structure

```bash
# Create test directory structure
mkdir -p tests/contract/{database,analyzers/parsers,extractors/github,workflows}
mkdir -p tests/implementation/{database,extractors/github}
mkdir -p tests/integration
mkdir -p tests/fixtures/data
```

### Step 2: Start with Database Tests (Highest Priority)

```bash
# Create first test file
touch tests/contract/database/test_storage_contract.py
```

**First test to write**:
```python
"""CONTRACT tests for database storage operations."""

import pytest
from src.database.storage import DatabaseStorage

class TestRepositoryStorage:
    """CONTRACT: Repository storage operations."""
    
    def test_contract_create_repository_returns_id(self, clean_database):
        """CONTRACT: Creating a repository must return its ID."""
        storage = DatabaseStorage()
        repo_data = {
            "name": "test-repo",
            "platform": "github",
            "url": "https://github.com/test/repo",
            "default_branch": "main"
        }
        
        repo_id = storage.create_repository(repo_data)
        
        assert repo_id is not None
        assert isinstance(repo_id, int)
        assert repo_id > 0
```

### Step 3: Run Your First Test

```bash
# Activate Python environment
source venv/bin/activate

# Run single test
pytest tests/contract/database/test_storage_contract.py::TestRepositoryStorage::test_contract_create_repository_returns_id -v

# Run with coverage
pytest tests/contract/database/ --cov=src/database --cov-report=term
```

### Step 4: Build Test Fixtures

Create reusable test data in `tests/fixtures/sample_data.py`:

```python
"""Shared test data fixtures."""

def sample_repository_data():
    """Standard repository for testing."""
    return {
        "name": "test-repo",
        "platform": "github",
        "url": "https://github.com/test-org/test-repo",
        "default_branch": "main",
        "organization": "test-org"
    }

def sample_commit_data(repository_id=1):
    """Standard commit for testing."""
    return {
        "repository_id": repository_id,
        "sha": "abc123def456",
        "author": "developer@example.com",
        "timestamp": "2026-01-01T10:00:00Z",
        "message": "Test commit",
        "additions": 10,
        "deletions": 5,
        "files_changed": 2
    }
```

---

## Notes & Considerations

### Database Testing Strategy
- Use in-memory SQLite for unit tests (fast)
- Use PostgreSQL Docker container for integration tests (realistic)
- Always clean database between tests
- Use transactions that rollback for faster tests

### Mocking Strategy
- Mock external APIs (GitHub, Azure DevOps) in extractor tests
- Use real database for storage tests (not mocked)
- Mock file system for parser tests (use in-memory strings)

### Test Data Management
- Keep test data small and focused
- Use factories/builders for complex objects
- Store large sample files in `tests/fixtures/data/`
- Version control test data files

### Common Pitfalls to Avoid
1. **Don't test implementation details** in CONTRACT tests
2. **Don't mock what you don't own** - test actual behavior
3. **Don't write assertion-less tests** - each test must verify something
4. **Don't ignore test failures** - fix immediately or tests become noise
5. **Don't couple tests** - each test should be independent

### Architecture Guardian Integration
Before implementing any test that touches architectural boundaries:
1. Check if test setup crosses component boundaries
2. Ensure mocks respect layer isolation
3. Verify test doesn't bypass architectural constraints
4. Document any intentional boundary crossings

---

## References

- [Test Organization Guide](./test-organization.md)
- [Architecture Guardian](../../agents/02a-architecture-guardian.md)
- [Test Guardian](../../agents/04a-test-guardian.md)
- [pytest Documentation](https://docs.pytest.org/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)

---

**Last Updated**: 2026-01-23  
**Next Review**: After Phase 1 completion  
**Owner**: Development Team
