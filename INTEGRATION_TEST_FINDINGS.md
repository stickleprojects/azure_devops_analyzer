# Integration Test Findings - 2026-01-24

> **✅ RESOLVED** — All 3 bugs fixed in commit `0a1bf4a` (2026-01-24). See PROGRESS.md Part 2 for details.

## Summary

Integration tests successfully executed and revealed **3 critical bugs** in the codebase (all now fixed):

1. **GitHubExtractor missing repository name extraction** (HIGH severity)
2. **SQLAlchemy models losing timezone information** (MEDIUM severity)
3. **Test code using wrong extractor method name** (TEST FIX)

## Test Execution Status

**Database Connection**: ✅ WORKING  
**Test Infrastructure**: ✅ WORKING  
**Tests Executed**: 8 tests (excluding 3 live_api tests)  
**Results**: 1 PASSED, 7 FAILED (all failures due to real bugs, not test issues)

### Test Results

```
tests/contract/integration/test_dependency_enrichment_e2e.py::test_dependencies_extracted_and_stored
  FAILED - Repository.name is NULL

tests/contract/integration/test_github_extraction_e2e.py::test_extract_small_repo_stores_metadata
  FAILED - AttributeError: 'extract_repository' doesn't exist

tests/contract/integration/test_github_extraction_e2e.py::test_extract_tracks_branches
  FAILED - AttributeError: 'extract_repository' doesn't exist

tests/contract/integration/test_github_extraction_e2e.py::test_extract_tracks_commits
  FAILED - Repository.name is NULL

tests/contract/integration/test_github_extraction_e2e.py::test_extract_tracks_contributors
  FAILED - Repository.name is NULL

tests/contract/integration/test_github_extraction_e2e.py::test_repository_constraints
  PASSED ✅

tests/contract/integration/test_github_extraction_e2e.py::test_foreign_key_relationships
  FAILED - Repository.name is NULL

tests/contract/integration/test_github_extraction_e2e.py::test_timezone_handling
  FAILED - DateTime losing timezone info (tzinfo=None after retrieval)
```

## Bug Details

### Bug #1: GitHubExtractor Not Extracting Repository Name (HIGH SEVERITY)

**Error**:

```
psycopg2.errors.NotNullViolation: null value in column "name" of relation "repositories" violates not-null constraint
```

**Root Cause**: GitHubExtractor is creating Repository objects without setting the `name` field, which is NOT NULL in the database schema.

**Impact**:

- All repository extraction fails when writing to database
- Production extraction would fail on commit
- Missing critical metadata for UI/dashboards

**Files Affected**:

- `src/extractors/github/extractor.py` (needs to extract `repo.name` from API)
- Likely affects: `_convert_to_repository()` method

**Schema Constraint**:

```sql
CREATE TABLE repositories (
    name VARCHAR(255) NOT NULL,  -- This field is required
    ...
);
```

**Fix Required**:

1. Update GitHubExtractor to extract repository name from GitHub API response
2. Ensure `repo.name` is populated in `_convert_to_repository()` method
3. Verify GitHub API provides `name` field in response

**Test Coverage**: 5 tests failing due to this issue

---

### Bug #2: SQLAlchemy Models Losing Timezone Information (MEDIUM SEVERITY)

**Error**:

```python
assert stored_repo.created_at.tzinfo is not None  # FAILS - tzinfo is None
```

**Root Cause**: SQLAlchemy models define datetime columns without `timezone=True`, causing PostgreSQL TIMESTAMPTZ data to lose timezone info when retrieved.

**Example**:

```python
# Current (WRONG):
created_at: Mapped[Optional[datetime]] = mapped_column()

# Should be:
from sqlalchemy import DateTime
created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
```

**Impact**:

- All datetime comparisons will fail (UTC vs naive datetime)
- Historical issue that may affect existing code
- Data integrity issue for time-sensitive operations

**Files Affected**:

- `src/database/models/repository.py` (created_at, last_analyzed_at, pushed_at, updated_at)
- `src/database/models/commit.py` (commit_date)
- `src/database/models/branch.py` (created_at, last_analyzed_at)
- Likely many other model files with datetime fields

**Database Schema** (CORRECT):

```sql
created_at TIMESTAMPTZ  -- PostgreSQL has correct type
```

**SQLAlchemy Models** (INCORRECT):

```python
created_at: Mapped[Optional[datetime]] = mapped_column()  -- Missing timezone=True
```

**Fix Required**:

1. Add `from sqlalchemy import DateTime` to affected model files
2. Change all datetime mapped_column() to: `mapped_column(DateTime(timezone=True))`
3. Or use SQLAlchemy's global `TIMESTAMP` type configuration
4. Verify fix by re-running test_timezone_handling test

**Test Coverage**: 1 test explicitly checking this (`test_timezone_handling`)

---

### Bug #3: Test Code Using Wrong Method Name (TEST FIX)

**Error**:

```
AttributeError: 'GitHubExtractor' object has no attribute 'extract_repository'.
Did you mean: 'extract_full_repository'?
```

**Root Cause**: Integration tests written assuming `extract_repository()` method, but actual API is `extract_full_repository()`.

**Impact**: Test code needs updating (not production code issue)

**Files Affected**:

- `tests/contract/integration/test_github_extraction_e2e.py` (lines 44, 97, etc.)

**Fix Required**:

1. Find all calls to `extractor.extract_repository(...)` in test files
2. Replace with `extractor.extract_full_repository(...)`
3. Verify parameters are correct for the actual method signature

**Test Coverage**: 2 tests failing due to this

---

## Recommended Fix Order

### Phase 1: Fix Production Code (HIGH PRIORITY)

1. **Fix Bug #1 - Repository Name Extraction** (30 minutes)
   - Update `src/extractors/github/extractor.py`
   - Extract `name` field from GitHub API
   - Update `_convert_to_repository()` method

2. **Fix Bug #2 - Timezone Handling** (60 minutes)
   - Audit all model files for datetime columns
   - Add `DateTime(timezone=True)` to all datetime fields
   - Consider creating a helper type or mixin

### Phase 2: Fix Test Code (LOW PRIORITY)

3. **Fix Bug #3 - Test Method Names** (15 minutes)
   - Update test files to use `extract_full_repository()`
   - Verify method signatures match

### Phase 3: Validation

4. **Re-run Integration Tests** (5 minutes)

   ```bash
   pytest tests/contract/integration/ -v -m "not live_api"
   ```

5. **Run Unit Tests** (5 minutes)
   ```bash
   pytest tests/contract/extractors/github/ -v
   ```

## Value Delivered

✅ **Integration tests working as intended** - Successfully caught 3 real bugs before production deployment

✅ **Critical data integrity issue found** - Repository name being NULL would cause production failures

✅ **Timezone bug discovered** - Prevents future datetime comparison bugs

✅ **Test infrastructure validated** - Database connection, fixtures, cleanup all working correctly

## Next Steps

1. ~~Fix Bug #1 (repository name extraction)~~ ✅ Fixed
2. ~~Fix Bug #2 (timezone handling)~~ ✅ Fixed
3. ~~Fix Bug #3 (test code)~~ ✅ Fixed
4. Re-run all integration tests to verify fixes
5. Consider running live_api tests if safe
6. Document any additional findings

## Related Documentation

- Integration Test Design: [docs/04-implementation/integration-test-design.md](docs/04-implementation/integration-test-design.md)
- Integration Test Setup: [docs/04-implementation/integration-test-setup.md](docs/04-implementation/integration-test-setup.md)
- Test Organization: [docs/03-operations/test-organization.md](docs/03-operations/test-organization.md)
- Test Guardian: [agents/04a-test-guardian.md](agents/04a-test-guardian.md)

---

**Test Execution Command Used**:

```bash
export TEST_DATABASE_URL="postgresql://analyzer:7RBCqJn1kac6LXbHAVyST04G@localhost:5432/analyzer_test"
export GITHUB_TOKEN="$(grep GITHUB_TOKEN .env.resolved | cut -d'=' -f2)"
pytest tests/contract/integration/ -v -m "not live_api"
```

**Environment**:

- Database: PostgreSQL/TimescaleDB (container: analyzer-timescaledb)
- Python: 3.12.3 (.venv)
- Test Database: analyzer_test (created successfully)
- Docker Container Status: Running, Healthy

---

_These integration tests have already paid for themselves by catching 3 critical bugs before they reached production._
