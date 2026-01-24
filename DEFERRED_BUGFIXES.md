# Deferred Bug Fixes - Integration Test Findings

## Overview

Integration tests executed successfully on 2026-01-24 and identified **3 production bugs** that need to be fixed. These bugs are documented here for prioritized implementation.

---

## 🔴 HIGH PRIORITY: Bug #1 - Repository Name Not Extracted

**Severity**: HIGH (blocks all repository extraction)  
**Estimated Effort**: 30 minutes  
**Status**: NOT STARTED

### Problem
GitHubExtractor is not extracting the repository `name` field from the GitHub API, causing NOT NULL constraint violations when writing to the database.

### Error Message
```
psycopg2.errors.NotNullViolation: null value in column "name" of relation "repositories" violates not-null constraint
```

### Root Cause
The `_convert_to_repository()` method in GitHubExtractor doesn't populate the `name` field, which is required by the database schema.

### Impact
- **Production**: All repository extraction fails on database commit
- **Missing Data**: Repository names not stored, breaking UI/dashboards
- **Blocking**: 5 integration tests failing

### Files to Fix
- `src/extractors/github/extractor.py`
  - Likely: `_convert_to_repository()` method
  - Need to extract `repo.name` from GitHub API response

### Fix Steps
1. Locate the GitHub API response object in extractor
2. Extract `name` field: `repo_data.get('name')` or `repo.name`
3. Add to Repository object creation: `name=repo_name`
4. Verify GitHub API documentation for field name
5. Run unit tests: `pytest tests/contract/extractors/github/`
6. Run integration tests: `pytest tests/contract/integration/test_github_extraction_e2e.py`

### Acceptance Criteria
- [ ] Repository.name is populated from GitHub API
- [ ] Database constraint satisfied (no NULL values)
- [ ] 5 failing integration tests now pass
- [ ] Unit tests still pass

### Related Tests
- `test_extract_small_repo_stores_metadata` ❌
- `test_extract_tracks_commits` ❌
- `test_extract_tracks_contributors` ❌
- `test_foreign_key_relationships` ❌
- `test_dependencies_extracted_and_stored` (dependency tests) ❌

---

## 🟡 MEDIUM PRIORITY: Bug #2 - Timezone Information Lost

**Severity**: MEDIUM (data integrity, datetime comparison failures)  
**Estimated Effort**: 60 minutes  
**Status**: NOT STARTED

### Problem
SQLAlchemy models define datetime columns without `timezone=True`, causing PostgreSQL TIMESTAMPTZ data to lose timezone information when retrieved from the database.

### Error Message
```python
assert stored_repo.created_at.tzinfo is not None  # FAILS
# tzinfo is None after retrieval, even though saved as UTC
```

### Root Cause
Models use `mapped_column()` without specifying `DateTime(timezone=True)`, so SQLAlchemy treats timestamps as naive datetimes.

### Code Example

**Current (WRONG)**:
```python
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column

class Repository(Base):
    created_at: Mapped[Optional[datetime]] = mapped_column()
```

**Correct**:
```python
from datetime import datetime
from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column

class Repository(Base):
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
```

### Impact
- **Data Integrity**: Timezone-aware datetimes become naive on retrieval
- **Comparison Failures**: `datetime.now(UTC)` comparisons fail
- **Historical Issue**: May affect existing code with timezone bugs
- **Blocking**: 1 integration test failing explicitly checking this

### Files to Fix

All model files with datetime columns:

1. **High Priority (Core Entities)**:
   - `src/database/models/repository.py`
     - `created_at`, `last_analyzed_at`, `pushed_at`, `updated_at`
   - `src/database/models/commit.py`
     - `commit_date`
   - `src/database/models/branch.py`
     - `created_at`, `last_analyzed_at`
   - `src/database/models/pull_request.py`
     - `created_at`, `updated_at`, `closed_at`, `merged_at`

2. **Medium Priority (Analysis Data)**:
   - `src/database/models/contributor.py`
     - `created_at`, `last_commit_date`
   - `src/database/models/dependency.py`
     - `first_detected_at`, `latest_version_date`
   - `src/database/models/vulnerability.py`
     - `published_date`, `first_detected_at`, `resolved_at`

3. **Lower Priority (Metadata)**:
   - `src/database/models/organization.py`
   - `src/database/models/project.py`
   - `src/database/models/team.py`

### Fix Steps

**Option A: Individual Fix (Safe)**
1. Add import: `from sqlalchemy import DateTime`
2. For each datetime field, change:
   ```python
   field: Mapped[Optional[datetime]] = mapped_column()
   # TO:
   field: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
   ```
3. Run tests after each model file updated

**Option B: Create Helper Type (Better Long-term)**
1. Create `src/database/types.py`:
   ```python
   from sqlalchemy import DateTime
   from typing import TypeVar
   
   # Timezone-aware datetime type
   TZDateTime = DateTime(timezone=True)
   ```
2. Use in models:
   ```python
   from src.database.types import TZDateTime
   
   field: Mapped[Optional[datetime]] = mapped_column(TZDateTime)
   ```

### Validation Steps
1. Run timezone test: `pytest tests/contract/integration/test_github_extraction_e2e.py::TestGitHubExtractionDataIntegrity::test_timezone_handling`
2. Verify datetime comparisons work: `pytest tests/contract/extractors/`
3. Check existing code for datetime comparison bugs
4. Run full integration test suite

### Acceptance Criteria
- [ ] All datetime fields use `DateTime(timezone=True)`
- [ ] `test_timezone_handling` passes
- [ ] DateTime comparisons work correctly
- [ ] No regression in existing tests

### Related Tests
- `test_timezone_handling` ❌ (explicitly tests this)
- Potentially affects any test comparing datetimes

---

## 🟢 LOW PRIORITY: Bug #3 - Test Method Name Wrong

**Severity**: LOW (test code only, not production)  
**Estimated Effort**: 15 minutes  
**Status**: NOT STARTED

### Problem
Integration tests call `extractor.extract_repository()` but the actual method name is `extract_full_repository()`.

### Error Message
```
AttributeError: 'GitHubExtractor' object has no attribute 'extract_repository'. 
Did you mean: 'extract_full_repository'?
```

### Root Cause
Test code written with assumed API that doesn't match actual implementation.

### Impact
- **Production**: No impact (test code only)
- **Blocking**: 2 integration tests failing

### Files to Fix
- `tests/contract/integration/test_github_extraction_e2e.py`
  - Lines calling `extractor.extract_repository(...)`

### Fix Steps
1. Search test file for all occurrences of `extract_repository`
2. Replace with `extract_full_repository`
3. Verify method signature matches:
   ```python
   # Check actual method signature:
   def extract_full_repository(self, repo_identifier: str, session) -> Repository:
   ```
4. Update test calls to match parameters
5. Run affected tests

### Acceptance Criteria
- [ ] All test calls use correct method name
- [ ] Method parameters correct
- [ ] 2 failing tests now pass

### Related Tests
- `test_extract_small_repo_stores_metadata` ❌
- `test_extract_tracks_branches` ❌

---

## Fix Sequence Recommendation

### Phase 1: Unblock Tests (1 hour)
1. **Fix Bug #3 first** (15 min) - Quick win, unblocks 2 tests
2. **Fix Bug #1** (30 min) - Unblocks 5 tests, critical for extraction

### Phase 2: Data Integrity (1 hour)
3. **Fix Bug #2** (60 min) - Ensures datetime handling correct

### Phase 3: Validation (15 min)
4. **Run full integration test suite**:
   ```bash
   export TEST_DATABASE_URL="postgresql://analyzer:7RBCqJn1kac6LXbHAVyST04G@localhost:5432/analyzer_test"
   export GITHUB_TOKEN="$(grep GITHUB_TOKEN .env.resolved | cut -d'=' -f2)"
   pytest tests/contract/integration/ -v -m "not live_api"
   ```
5. **Run unit tests**:
   ```bash
   pytest tests/contract/extractors/github/ -v
   ```
6. **Consider live_api tests** (if all pass and safe)

### Total Estimated Time
- **Minimum**: 1 hour 45 minutes (all 3 bugs)
- **With validation**: 2 hours
- **With documentation**: 2.5 hours

---

## Testing Commands

### Run All Integration Tests (Excluding Live API)
```bash
cd /d/code/tyl/azure-devops-analyzer
export TEST_DATABASE_URL="postgresql://analyzer:7RBCqJn1kac6LXbHAVyST04G@localhost:5432/analyzer_test"
export GITHUB_TOKEN="$(grep GITHUB_TOKEN .env.resolved | cut -d'=' -f2)"
D:/code/tyl/azure-devops-analyzer/.venv/Scripts/python.exe -m pytest tests/contract/integration/ -v -m "not live_api"
```

### Run Single Test (For Quick Validation)
```bash
pytest tests/contract/integration/test_github_extraction_e2e.py::TestGitHubExtractionDataIntegrity::test_repository_constraints -v
```

### Run Live API Tests (After Safe Tests Pass)
```bash
pytest tests/contract/integration/ -v -m "live_api"
```

---

## Current Test Status

| Test File | Test Name | Status | Blocked By |
|-----------|-----------|--------|------------|
| `test_github_extraction_e2e.py` | `test_extract_small_repo_stores_metadata` | ❌ FAIL | Bug #3 |
| `test_github_extraction_e2e.py` | `test_extract_tracks_branches` | ❌ FAIL | Bug #3 |
| `test_github_extraction_e2e.py` | `test_extract_tracks_commits` | ❌ FAIL | Bug #1 |
| `test_github_extraction_e2e.py` | `test_extract_tracks_contributors` | ❌ FAIL | Bug #1 |
| `test_github_extraction_e2e.py` | `test_repository_constraints` | ✅ PASS | - |
| `test_github_extraction_e2e.py` | `test_foreign_key_relationships` | ❌ FAIL | Bug #1 |
| `test_github_extraction_e2e.py` | `test_timezone_handling` | ❌ FAIL | Bug #2 |
| `test_dependency_enrichment_e2e.py` | `test_dependencies_extracted_and_stored` | ❌ FAIL | Bug #1 |

**Total**: 1/8 passing (12.5% pass rate)  
**Expected after fixes**: 8/8 passing (100% pass rate)

---

## Additional Notes

### Environment Setup (For Reference)
- **Database**: PostgreSQL/TimescaleDB (container: analyzer-timescaledb)
- **Test Database**: analyzer_test
- **Correct Password**: 7RBCqJn1kac6LXbHAVyST04G (from container, not .env.resolved)
- **Python**: 3.12.3 (.venv/Scripts/python.exe)

### .env.resolved Password Mismatch
The .env.resolved file contains an outdated password. Current workaround is to export TEST_DATABASE_URL directly with the correct container password. Consider updating .env.resolved or documenting this discrepancy.

---

## Success Metrics

When all bugs are fixed:

✅ 8/8 integration tests passing (excluding live_api)  
✅ Repository name populated in database  
✅ Timezone information preserved  
✅ Full E2E pipeline validated  
✅ Ready for live API testing  

---

*Integration tests have already proven their value by catching these bugs before production deployment. The test infrastructure is solid and working correctly.*
