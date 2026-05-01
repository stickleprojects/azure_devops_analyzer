# GitHub Actions - Tests Workflow

## Overview

Automated test execution on every push and pull request using GitHub Actions. Tests run in a clean Ubuntu environment with a managed PostgreSQL database.

## Workflow Details

### Triggers

- **Push**: `main` and `develop`
- **Pull Request**: main and develop branches
- **Manual**: Can be triggered via GitHub Actions UI

### Environment

- **OS**: Ubuntu latest (Linux)
- **Python**: 3.12.x
- **Database**: TimescaleDB (latest) with PostgreSQL 15
- **Timeout**: 30 minutes per test run

## Test Execution

### Step 1: Documentation Validation

- Runs `bash scripts/validate-documentation.sh README.md`
- Runs `bash scripts/validate-documentation.sh docs`
- Executes as a dedicated PR status check: **Documentation Validation**
- Fails the workflow only on documentation violations; warnings are reported but do not fail the job

### Step 2: Setup

- Checks out code
- Sets up Python 3.12 with pip caching
- Installs all dependencies from requirements.txt

### Step 3: Configuration

- Creates `.env.test` with database connection details
- PostgreSQL automatically available via service container
- No need for Docker Compose locally in CI

### Step 4: Database Migrations

- Runs migrations to set up schema
- Creates tables, indexes, and hypertables
- Safe to run multiple times (idempotent)

### Step 5: Tests

**Unit Tests** (`tests/unit/`):

- Fast, isolated, no external dependencies
- Tests individual components and functions
- ~5-10 seconds typically

**Integration Tests** (`tests/contract/integration/`):

- Uses PostgreSQL database
- Tests workflows and data persistence
- May include external API calls (with mocks where possible)
- ~15-25 seconds typically

### Step 6: Coverage & Reports

- Generates coverage report (lines/branches covered)
- Reports to Codecov if token available
- Continues even if Codecov upload fails

## GitHub Status Checks

### What This Means for PRs

✅ **PR can merge only if**:

- Documentation validation completes without violations
- All unit tests pass
- All integration tests pass
- Build completes without errors

❌ **PR cannot merge if**:

- Documentation validation finds violations
- Any test fails
- Workflow times out (> 30 min)
- Environment setup fails

### Viewing Results

1. Go to your PR on GitHub
2. Scroll to "Checks" section
3. Click the relevant check:
   - `Documentation Validation` for docs validation output
   - `CI Tests` for unit/integration/coverage output
4. See detailed output, logs, and failures

## GitHub Actions Capabilities vs Requirements

| Requirement          | Supported   | Notes                                   |
| -------------------- | ----------- | --------------------------------------- |
| **Python venv**      | ✅ Yes      | Automatically created per job           |
| **PostgreSQL**       | ✅ Yes      | Via service containers                  |
| **TimescaleDB**      | ✅ Yes      | Official timescale/timescaledb image    |
| **pip install**      | ✅ Yes      | Works identically to local              |
| **Environment vars** | ✅ Yes      | Via .env.test or secrets                |
| **External APIs**    | ✅ Yes      | GITHUB_TOKEN via secrets (rate-limited) |
| **Docker Compose**   | ✅ Optional | Can use, but services are simpler       |
| **File system**      | ✅ Yes      | Clean disk per run, ephemeral           |

## Database Connectivity

### In CI (GitHub Actions)

```
Test Process
    ↓
postgres service (localhost:5432)
    ↓
TimescaleDB
    ↓
test_azure_devops database
```

**Connection String**:

```
postgresql://postgres:postgres@localhost:5432/test_azure_devops
```

### Health Checks

PostgreSQL service has automatic health checks:

- Runs `pg_isready` every 10 seconds
- Must pass health check before tests start
- Waits up to 50 seconds (5 retries × 10 second interval)
- Ensures database is ready before tests run

## Troubleshooting

### Tests Fail Locally but Pass in CI

1. Check Python version matches (3.12)
2. Verify database is running locally
3. Check `.env` or `.env.test` has correct settings
4. Run: `pip install -r requirements.txt --force-reinstall`

### Tests Pass Locally but Fail in CI

1. Check for hardcoded paths (use pathlib/relative paths)
2. Check for timezone assumptions (CI uses UTC)
3. Check for network/API dependencies (may need mocks)
4. Review workflow logs for full error details

### Timeout (> 30 minutes)

1. Check if tests have infinite loops
2. Check if API calls are hanging (add timeouts)
3. Increase timeout in `.github/workflows/tests.yml` if needed
4. Consider skipping slow integration tests for quick feedback

## Secrets Required

### GITHUB_TOKEN

- **Provided by**: GitHub automatically
- **Used for**: API calls with proper rate limiting
- **No action needed**: Already configured

### Optional: Codecov Token

- Only needed if uploading coverage reports
- Not required for workflow to pass
- Can be added later if desired

## Future Enhancements

1. **Linting**: Add flake8/ruff checks
2. **Type Checking**: Add mypy validation
3. **Coverage Threshold**: Require minimum % coverage
4. **Performance Tests**: Track test duration trends
5. **Matrix Testing**: Test against multiple Python versions
6. **Scheduled Runs**: Nightly full test suite
7. **Artifact Storage**: Store test reports/logs

## Current Check Names

- `Documentation Validation` — validates `README.md` and the `docs/` tree
- `CI Tests` — runs the Python and shell test paths based on changed files

## Related Documentation

- [Testing Strategy](../../agents/04-testing.md)
- [Pre-commit Validation](../../agents/06-pre-commit-validation.md)
- [Branch Protection](./branch-protection-setup.md)
- [Development Workflow](./feature-development-workflow.md)

---

**Last Updated**: 2026-04-05
**Status**: ✅ Active - documentation validation and tests run on PRs
