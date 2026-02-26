# Testing Guide

## Quick Start

### 1. Start PostgreSQL

```bash
# Start PostgreSQL container
docker compose up -d postgres

# Verify it's running
docker compose ps postgres
```

### 2. Configure Test Environment

When running tests on your host machine (outside Docker), PostgreSQL needs to connect to localhost:

```bash
# Create a test environment file (tests will use this if present)
echo "POSTGRES_HOST=localhost" > .env.test

# Or set inline when running tests
export POSTGRES_HOST=localhost
```

### 3. Run Tests

```bash
# Run all tests (after setting POSTGRES_HOST=localhost)
POSTGRES_HOST=localhost pytest

# Run specific test file
POSTGRES_HOST=localhost pytest tests/contract/database/test_storage_contract.py

# Run with verbose output
POSTGRES_HOST=localhost pytest -v

# Run with coverage
POSTGRES_HOST=localhost pytest --cov=src --cov-report=html

# Or create .env.test file to avoid repeating:
echo "POSTGRES_HOST=localhost" > .env.test
pytest  # Will automatically use .env.test
```

## Test Fixtures & Scenarios

### Generating Test Scenarios with Ollama

This project uses local LLM (Ollama) to generate realistic test fixture scenarios. Test scenarios are JSON files that define repository structures, dependencies, commits, branches, and pull requests for testing.

**Quick Start (config-driven, Plan 014):**

```bash
# Validate config structure
python scripts/validate-fixture-config.py

# Generate the seed generator script
python scripts/ollama-generate.py \
  --model qwen2.5-coder:14b \
  --prompt .ai/ollama-prompts/fixture-repo-seeds.md \
  --output scripts/generated/generate-repo-seeds.py \
  --context tests/fixtures/scenarios/config.json

# Create seed JSON files
python scripts/generated/generate-repo-seeds.py

# Enrich a seed (repeat per repo)
python scripts/ollama-generate.py \
  --model qwen2.5-coder:14b \
  --prompt .ai/ollama-prompts/fixture-repo-enrichment.md \
  --output scripts/generated/enrich-python-docker.py \
  --context tests/fixtures/scenarios/config.json \
  --context tests/fixtures/scenarios/generated/python-docker.json

python scripts/generated/enrich-python-docker.py \
  tests/fixtures/scenarios/generated/python-docker.json
```

**Legacy (Plan 013, monolithic):**

```bash
# Generates scenarios + extractor + factories using fixture-scenarios.md
bash scripts/generate-test-fixtures.sh
```

**What gets generated:**

- N scenario JSON files in `tests/fixtures/scenarios/generated/` (N derived from `repo_sets`)
- Python script (`generate-repo-seeds.py`) that creates seed scenarios
- Per-repo enrichment scripts (`enrich-<name>.py`) that add commits/PRs
- `FixtureExtractor` class for loading scenarios in tests (unchanged)
- Factory functions for test data construction (unchanged)

**Scenarios include:**

- Various tech stacks (Python/Docker, React/TypeScript, Java/Maven, .NET, Go)
- Different CI/CD platforms (GitHub Actions, Jenkins, Azure Pipelines)
- Edge cases (dual dependencies, nested manifests, empty repos)
- Commit history, branches, and pull requests for workflow testing

**See:** [.ai/patterns/ollama-fixture-and-code-generation.md](.ai/patterns/ollama-fixture-and-code-generation.md) for the generation pattern.

### Using Scenarios in Tests

```python
from tests.fixtures.fixture_extractor import FixtureExtractor

# Load a scenario
extractor = FixtureExtractor("python-docker")  # Loads from generated/ first, then scenarios/

# Use in tests
files = extractor.get_file_tree("test-repo")
commits = extractor.get_commits("test-repo")
branches = extractor.get_branches("test-repo")
prs = extractor.get_pull_requests("test-repo")
```

## Test Organization

Our tests follow a two-tier architecture:

### CONTRACT Tests (`tests/contract/`)

- **Purpose**: Define business requirements and expected behavior
- **Protection**: CANNOT be changed without documented requirement change
- **Naming**: Files named `test_contract_*.py`, docstrings start with `CONTRACT:`
- **Example**: "CONTRACT: Storing an organization must create it in database"
- **Rule**: If implementation changes, fix implementation to match contract

### IMPLEMENTATION Tests (`tests/implementation/`)

- **Purpose**: Validate technical implementation details
- **Protection**: CAN change with implementation (if contracts still pass)
- **Naming**: Files named `test_impl_*.py`, docstrings start with `IMPLEMENTATION:`
- **Example**: "IMPLEMENTATION: Pagination returns 50 items per page"
- **Rule**: Can update test if implementation strategy changes

**See [docs/03-operations/test-organization.md](../docs/03-operations/test-organization.md) for complete guide.**

## Database Tests

### Prerequisites

- Docker and Docker Compose
- PostgreSQL container running (via `docker compose up -d postgres`)

### Configuration

The test database is automatically created and managed:

- **Default**: Uses `repo_analyzer_test` database on localhost:5432
- **Custom**: Set `TEST_DATABASE_URL` environment variable

```bash
# Use custom test database
export TEST_DATABASE_URL="postgresql://user:password@host:port/testdb"
pytest tests/contract/database/
```

### Environment Variables

The tests read from your environment or `.env.resolved`:

- `POSTGRES_HOST` (default: localhost)
- `POSTGRES_PORT` (default: 5432)
- `POSTGRES_USER` (default: postgres)
- `POSTGRES_PASSWORD` (default: postgres)

### Test Database Management

- **Created**: Automatically on first test run
- **Tables**: Created/dropped for each test session
- **Data**: Cleaned between test functions
- **Isolation**: Each test runs in a transaction

## Running Tests in CI/CD

```yaml
# Example GitHub Actions workflow
- name: Start PostgreSQL
  run: docker compose up -d postgres

- name: Wait for PostgreSQL
  run: |
    timeout 30 bash -c 'until docker compose exec -T postgres pg_isready; do sleep 1; done'

- name: Run Tests
  run: |
    pytest --cov=src --cov-report=xml --cov-report=html
```

## Test Fixtures

### Database Fixtures

- `test_database_url`: Returns test database URL
- `test_engine`: SQLAlchemy engine (session scope)
- `db_session`: Clean database session per test (function scope)
- `clean_database`: Explicitly truncated database

### Sample Data Fixtures

Located in `tests/fixtures/sample_data.py`:

- `sample_organization_data()`
- `sample_repository_data()`
- `sample_commit_data()`
- `sample_pull_request_data()`
- And more...

## Troubleshooting

### "Could not connect to database"

```bash
# Check if PostgreSQL is running
docker compose ps postgres

# View logs
docker compose logs postgres

# Restart PostgreSQL
docker compose restart postgres
```

### "Database does not exist"

The test database is created automatically. If you see this error:

```bash
# Manually create test database (usually not needed)
docker compose exec postgres createdb -U postgres repo_analyzer_test
```

### "ARRAY type not supported"

This means tests are using SQLite instead of PostgreSQL. Ensure:

1. PostgreSQL container is running
2. `test_database_url` fixture returns PostgreSQL URL
3. No `TEST_DATABASE_URL` env var pointing to SQLite

## Coverage Reports

```bash
# Generate HTML coverage report
pytest --cov=src --cov-report=html

# Open report
xdg-open htmlcov/index.html  # Linux
open htmlcov/index.html      # macOS
```

## Test Implementation Plan

Follow [docs/03-operations/test-implementation-plan.md](../docs/03-operations/test-implementation-plan.md) for:

- 6-phase testing roadmap
- Priority matrix
- Test examples
- Coverage goals
