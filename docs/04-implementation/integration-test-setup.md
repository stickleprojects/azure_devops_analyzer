# Integration Test Setup Guide

## Quick Start (5 minutes)

### 1. Create Test Database
```bash
# On Windows (PowerShell)
# First, connect to PostgreSQL default database
psql -U postgres -d postgres -c "CREATE DATABASE analyzer_test;"

# On macOS/Linux
createdb analyzer_test
```

### 2. Set Environment Variables
```bash
# Option A: Update .env.resolved
echo "TEST_DATABASE_URL=postgresql://postgres:password@localhost/analyzer_test" >> .env.resolved

# Option B: Export directly (temporary)
export TEST_DATABASE_URL="postgresql://postgres:password@localhost/analyzer_test"
export GITHUB_TOKEN="ghp_your_github_token_here"
```

### 3. Run Integration Tests
```bash
# Run all tests
pytest tests/integration/ -v

# Or specific test
pytest tests/integration/test_github_extraction_e2e.py::TestGitHubExtractionBasic::test_extract_small_repo_stores_metadata -v
```

## Detailed Setup

### Step 1: PostgreSQL Test Database

**Windows (using PostgreSQL installed locally):**
```powershell
# Open PowerShell as Administrator
psql -U postgres

# In psql shell
CREATE DATABASE analyzer_test;
\q
```

**macOS (using Homebrew):**
```bash
brew services start postgresql
createdb analyzer_test
```

**Linux (Debian/Ubuntu):**
```bash
sudo -u postgres createdb analyzer_test
```

**Docker (if using PostgreSQL container):**
```bash
docker exec postgres_container createdb -U postgres analyzer_test
```

### Step 2: Configure Test Database URL

Choose one approach:

**Approach A: .env.resolved (Recommended)**
```bash
# This file has resolved environment variables (no $ references)
echo "TEST_DATABASE_URL=postgresql://postgres:password@localhost/analyzer_test" >> .env.resolved

# Verify
cat .env.resolved | grep TEST_DATABASE_URL
```

**Approach B: .env (Alternative)**
```bash
# Edit .env directly
echo "TEST_DATABASE_URL=postgresql://postgres:password@localhost/analyzer_test" >> .env

# Load it
source .env  # or in PowerShell: . .env
```

**Approach C: Environment Variable (Temporary)**
```bash
# For current session only
export TEST_DATABASE_URL="postgresql://postgres:password@localhost/analyzer_test"
```

### Step 3: Configure GitHub Token

**Required for live API tests**

```bash
# Get your token from https://github.com/settings/tokens
# Create Personal Access Token with:
#   - repo (full control of private repositories)
#   - public_repo (access to public repositories)

# Add to .env.resolved or .env
echo "GITHUB_TOKEN=ghp_your_token_here" >> .env.resolved

# Or export
export GITHUB_TOKEN="ghp_your_token_here"
```

### Step 4: Verify Setup

```bash
# Test database connection
psql -U postgres -d analyzer_test -c "SELECT version();"

# Test environment variables
python -c "import os; print(f'DB URL: {os.getenv(\"TEST_DATABASE_URL\")}'); print(f'GitHub Token: {os.getenv(\"GITHUB_TOKEN\", \"NOT SET\")}')"

# Test imports
pytest tests/test_imports_and_structure.py -v
```

## Running Tests

### All Integration Tests
```bash
pytest tests/integration/ -v
```

### Only Quick Tests (Skip Slow Tests)
```bash
pytest tests/integration/ -m "not slow" -v
```

### Only Safe Tests (Skip Live API Tests)
```bash
pytest tests/integration/ -m "not live_api" -v
```

### Specific Test Class
```bash
pytest tests/integration/test_github_extraction_e2e.py::TestGitHubExtractionBasic -v
```

### With Detailed Output
```bash
pytest tests/integration/ -vv -s --tb=short
```

### With Coverage Report
```bash
pytest tests/integration/ --cov=src --cov-report=html
# Open htmlcov/index.html
```

## Troubleshooting

### Error: "TEST_DATABASE_URL not configured"

**Solution:**
```bash
# Verify database URL is set
echo $TEST_DATABASE_URL  # On Linux/macOS
echo %TEST_DATABASE_URL%  # On Windows PowerShell

# If empty, set it
export TEST_DATABASE_URL="postgresql://postgres:password@localhost/analyzer_test"

# Verify database exists
psql -U postgres -d analyzer_test -c "SELECT 1;"
```

### Error: "Database connection refused"

**Check PostgreSQL is running:**
```bash
# Windows
tasklist | findstr postgres

# macOS
brew services list | grep postgres

# Linux
systemctl status postgresql

# If not running, start it
# Windows: Start PostgreSQL service
# macOS: brew services start postgresql
# Linux: sudo systemctl start postgresql
```

### Error: "Database 'analyzer_test' does not exist"

**Create it:**
```bash
# macOS/Linux
createdb analyzer_test

# Windows (PowerShell)
psql -U postgres -c "CREATE DATABASE analyzer_test;"

# Docker
docker exec postgres_container createdb -U postgres analyzer_test
```

### Error: "GITHUB_TOKEN not configured"

**Solution (optional - skip live API tests instead):**
```bash
# Skip tests that need GitHub token
pytest tests/integration/ -m "not live_api" -v

# Or, add your token
export GITHUB_TOKEN="ghp_your_token"
```

### Error: "Connection refused on localhost:5432"

**PostgreSQL not running. Start it:**
```bash
# macOS
brew services start postgresql

# Linux
sudo systemctl start postgresql

# Windows: Ensure PostgreSQL service is running in Services.msc
```

## CI/CD Integration (GitHub Actions)

Create `.github/workflows/integration-tests.yml`:

```yaml
name: Integration Tests

on: [pull_request, push]

jobs:
  integration:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: analyzer_test
          POSTGRES_PASSWORD: test_password
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
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-xdist
      
      - name: Run integration tests
        env:
          TEST_DATABASE_URL: postgresql://postgres:test_password@localhost/analyzer_test
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          pytest tests/integration/ -m "not live_api" -v --tb=short
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

## Manual Testing Workflow

### For Local Development

1. **Start session**
   ```bash
   cd azure-devops-analyzer
   export TEST_DATABASE_URL="postgresql://postgres:password@localhost/analyzer_test"
   export GITHUB_TOKEN="your_token"
   ```

2. **Run quick tests**
   ```bash
   pytest tests/integration/ -m "not slow" -v
   ```

3. **Make code changes**

4. **Run affected tests**
   ```bash
   pytest tests/integration/test_github_extraction_e2e.py -v
   ```

5. **Commit changes**
   ```bash
   git add -A
   git commit -m "feat: add integration tests for X"
   ```

### For CI/CD Pipeline

- Automatic on PR creation
- Uses PostgreSQL service container
- Skips live API tests (uses GITHUB_TOKEN from secrets)
- Reports coverage

## Performance Optimization

### Parallel Test Execution
```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel
pytest tests/integration/ -n auto -v
```

### Skip Slow Tests in Development
```bash
# During development
pytest tests/integration/ -m "not slow" -v

# Before commit, run full suite
pytest tests/integration/ -v
```

### Run Only Affected Tests
```bash
# After modifying GitHub extraction
pytest tests/integration/test_github_extraction_e2e.py -v

# After modifying enrichment
pytest tests/integration/test_dependency_enrichment_e2e.py -v
```

## Database Cleanup

### Manual Cleanup (if needed)
```bash
# If tests leave data behind
psql -U postgres -d analyzer_test -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# Or drop and recreate database
dropdb analyzer_test
createdb analyzer_test
```

### Reset Between Test Runs
```bash
# Tests auto-cleanup, but if needed:
pytest tests/integration/ --create-db -v
```

## Next Steps

1. ✅ Database setup complete
2. ✅ Environment variables configured
3. Run tests: `pytest tests/integration/ -v`
4. Review results
5. Commit: `git commit -m "test: run integration tests"`
6. Create PR

## Reference

- See [Integration Tests README](tests/integration/README.md) for test documentation
- See [Integration Test Design](docs/04-implementation/integration-test-design.md) for architecture
- GitHub API docs: https://docs.github.com/en/rest
- SQLAlchemy docs: https://docs.sqlalchemy.org/
