# Integration Tests (CONTRACT Tests)

End-to-end tests that verify actual data flows through the complete pipeline.

**Location:** `tests/contract/integration/`

These tests are CONTRACT tests (not IMPLEMENTATION tests) because they validate **business requirements**:
- ✅ Data must reach PostgreSQL correctly
- ✅ Enrichment must populate specific fields
- ✅ Timestamps must be UTC-aware
- ✅ Foreign keys must be enforced

**Test Guardian Protection:** These tests are protected by the Test Guardian agent. Changes to test assertions require documented business requirement changes. See [Test Guardian](../../../agents/04a-test-guardian.md) for details.

## What These Tests Do

✅ **Real GitHub API Calls** - Uses your GitHub credentials
✅ **Real Database Operations** - Writes to test PostgreSQL  
✅ **Real Enrichment** - Calls OSV.dev and endoflife.date APIs
✅ **Data Validation** - Verifies database schema and constraints
✅ **No Silent Failures** - Catches data corruption early

## Prerequisites

1. **Test Database Setup**

   ```bash
   createdb analyzer_test
   ```

2. **Environment Configuration**

   ```bash
   # Copy your .env to .env.resolved (or create one)
   cp .env .env.resolved

   # Ensure these are set:
   export TEST_DATABASE_URL="postgresql://user:password@localhost/analyzer_test"
   export GITHUB_TOKEN="your_github_token"
   ```

3. **Dependencies Installed**
   ```bash
   pip install -r requirements.txt pytest pytest-cov
   ```

## Running Tests

### Run All Integration Tests

```bash
pytest tests/integration/ -v
```

### Run Specific Test File

```bash
pytest tests/integration/test_github_extraction_e2e.py -v
```

### Run Only Data Integrity Tests

```bash
pytest tests/integration/ -k "integrity" -v
```

### Run with Live API Calls (May Hit Rate Limits)

```bash
pytest tests/integration/ -m live_api -v
```

### Run Without Live API Tests (Skip API-dependent tests)

```bash
pytest tests/integration/ -m "not live_api" -v
```

### Run with Coverage Report

```bash
pytest tests/integration/ --cov=src --cov-report=html -v
```

### Run in Parallel (Multiple Workers)

```bash
pytest tests/integration/ -n auto -v
```

## Test Markers

| Marker                     | Purpose             | When to Use                         |
| -------------------------- | ------------------- | ----------------------------------- |
| `@pytest.mark.integration` | Integration test    | All integration tests               |
| `@pytest.mark.slow`        | Slow test (30+ sec) | Disable with `-m "not slow"`        |
| `@pytest.mark.live_api`    | Uses live APIs      | Skip in CI with `-m "not live_api"` |

## Test Organization

### `test_github_extraction_e2e.py`

Tests GitHub extraction pipeline:

- Repository metadata extraction
- Branch tracking
- Commit history
- Contributor analysis
- Database constraints
- Timezone handling

### `test_dependency_enrichment_e2e.py`

Tests dependency enrichment pipeline:

- Manifest parsing
- Dependency extraction
- OSV.dev enrichment
- EOL detection
- Vulnerability storage

## Important Notes

### Rate Limits

- GitHub API: 5000 requests/hour (authenticated)
- OSV.dev: Generous limits, but best effort
- endoflife.date: Rate limited, use sparingly

To avoid hitting limits:

- Run without `-m live_api` in CI
- Use small test repositories
- Run enrichment tests sequentially

### Test Data Cleanup

- Each test gets a clean database session
- Test data automatically deleted after each test
- No pollution between tests
- Safe to run in production-like environments

### CI/CD Integration

See `.github/workflows/integration-tests.yml` for GitHub Actions configuration:

- Runs on PR creation
- Skips live API tests (use mocks)
- Uses test PostgreSQL service container
- Reports coverage

## Debugging Failed Tests

### Test Fails: "TEST_DATABASE_URL not configured"

```bash
export TEST_DATABASE_URL="postgresql://user:pass@localhost/analyzer_test"
```

### Test Fails: "Database connection failed"

```bash
# Ensure PostgreSQL is running
psql -U user -d analyzer_test -c "SELECT 1"

# If fails, create database
createdb analyzer_test
```

### Test Fails: "API rate limit exceeded"

```bash
# Run without live API tests
pytest tests/integration/ -m "not live_api" -v
```

### Test Hangs or Times Out

- Use smaller test repositories
- Run with `-m "not slow"` to skip long tests
- Check API status pages (GitHub, OSV.dev)

## Test Naming Convention

- `test_<feature>_<scenario>` - Feature being tested + scenario
- Example: `test_extract_small_repo_stores_metadata`

All tests follow CONTRACT pattern:

```python
def test_something(self, github_config, test_session):
    """
    CONTRACT: [What should happen]

    Verify:
    - [Assertion 1]
    - [Assertion 2]
    """
```

## Adding New Tests

### Template

```python
@pytest.mark.integration
def test_new_feature(self, github_config, test_session):
    """
    CONTRACT: [Clear statement of expected behavior]

    Verify:
    - [What should be true]
    """
    # Setup

    # Act

    # Assert
```

### Best Practices

1. Each test should be independent
2. Use descriptive names
3. Include CONTRACT comment
4. Verify both success and edge cases
5. Clean up after yourself (auto-handled)

## Fixtures Available

From `conftest.py`:

- `github_config` - GitHub API configuration with credentials
- `test_session` - Clean database session for test
- `integration_test_engine` - Database engine instance
- `mock_osv_client` - Mocked OSV.dev client
- `mock_eol_client` - Mocked endoflife.date client

## Performance

Typical test execution:

- Basic extraction: 10-30 seconds (API dependent)
- Enrichment: 30-60 seconds (multiple API calls)
- Data validation: < 5 seconds
- Total suite: 5-10 minutes (without live API tests)

## Troubleshooting

### Table "xxx" doesn't exist

- Database schema not created
- Run migrations: `alembic upgrade head`
- Or let conftest create tables (automatic)

### Foreign key constraint fails

- Test data cleanup incomplete
- Check `conftest.py` cleanup_database fixture
- May need to delete in different order

### Tests pass locally but fail in CI

- Check environment variables
- Verify .env.resolved is generated
- Check GitHub Actions service container config

## Contributing

When adding new features:

1. Add contract test first (TDD)
2. Implement feature
3. Verify test passes with real data
4. Document in this README
5. Update PROGRESS.md

## References

- [Integration Test Design](../integration-test-design.md) - Architecture details
- [Priority Assessment](../integration-testing-priority-assessment.md) - Strategic value
- [Test Organization](../test-organization.md) - Contract vs Implementation tests
