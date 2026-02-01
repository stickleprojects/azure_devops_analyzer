# Environment Alignment Analysis: Local Docker vs GitHub Actions

## Executive Summary

Recent test failures reveal systematic differences between local Docker and GitHub Actions environments. These differences have manifested as:

1. **Naive timestamps from database** - GitHub Actions returns naive datetimes; local Docker returns timezone-aware
2. **Database persistence issues** - GitHub Actions uses persistent DB; local Docker uses ephemeral containers
3. **Fixture isolation failures** - Tests pass locally but fail on GitHub due to state persistence

This document identifies root causes and proposes alignment strategy.

---

## Environment Comparison

### PostgreSQL Version

| Environment    | Version     | Image                                             |
| -------------- | ----------- | ------------------------------------------------- |
| Local Docker   | 16          | `timescale/timescaledb:latest-pg16`               |
| GitHub Actions | 15          | `timescale/timescaledb:latest-pg15`               |
| **Issue**      | ⚠️ MISMATCH | Different major versions can affect type handling |

### SQLAlchemy Configuration

| Setting            | Local           | GitHub                       | Impact                              |
| ------------------ | --------------- | ---------------------------- | ----------------------------------- |
| `pool_pre_ping`    | ❌ NO           | ❌ NO                        | Connections not verified before use |
| `echo`             | `False`         | `False`                      | Same SQL logging                    |
| Connection pooling | Default         | Default                      | Same behavior                       |
| **Issue**          | ⚠️ BOTH MISSING | Missing `pool_pre_ping=True` | Stale connections can cause issues  |

### Database Type Handling

| Component               | Local             | GitHub              | Difference                         |
| ----------------------- | ----------------- | ------------------- | ---------------------------------- |
| `TIMESTAMPTZ` columns   | ✓ Timezone-aware  | ❌ Naive (stripped) | Driver or LibPQ version difference |
| TimescaleDB hypertables | ✓ Working         | ✓ Working           | Same behavior                      |
| Cleanup strategy        | DELETE + TRUNCATE | DELETE + TRUNCATE   | Same after recent fix              |

### Environment File Loading

| Stage          | Local                             | GitHub                         | Difference                    |
| -------------- | --------------------------------- | ------------------------------ | ----------------------------- |
| Pre-test setup | Loads `.env.test` from filesystem | Creates `.env.test` at runtime | Both work, but timing differs |
| Env var access | Via `os.environ.get()`            | Via `os.environ.get()`         | Same                          |
| Failure mode   | Skip if missing                   | Fail if invalid                | Local is more forgiving       |

### Test Database Isolation

| Factor             | Local                   | GitHub                     | Impact                           |
| ------------------ | ----------------------- | -------------------------- | -------------------------------- |
| DB state           | Fresh container per run | Persistent DB with cleanup | ❌ Cleanup bugs expose in GitHub |
| Schema creation    | CREATE TABLE fresh      | CREATE TABLE or ALTER      | Same                             |
| Hypertable cleanup | DELETE (works)          | DELETE (works)             | Fixed in recent commit           |

---

## Root Causes Identified

### 1. **PostgreSQL Version Mismatch (pg15 vs pg16)**

**Problem**: GitHub Actions uses `latest-pg15`, local uses `latest-pg16`

- Different pg_config defaults
- Possible differences in TIMESTAMPTZ handling
- Different libpq versions

**Evidence**:

- Naive timestamps in GitHub (suggests older driver behavior)
- Works in local pg16 (modern driver behavior)

**Severity**: 🔴 HIGH - Different major versions can behave differently

---

### 2. **Missing SQLAlchemy Connection Configuration**

**Problem**: No `pool_pre_ping=True` in integration test engine

**Why it matters**:

- Without pre-ping, stale PostgreSQL connections may be reused
- Can cause connection state inconsistencies
- Particularly problematic with persistent DB (GitHub Actions)
- Local Docker with fresh containers masks the issue

**Evidence**:

- Database conftest DOES use `pool_pre_ping=True` (line 84)
- Integration test conftest DOES NOT use it (line 111)
- Inconsistency between test suites

**Severity**: 🟡 MEDIUM - Can cause intermittent failures

---

### 3. **Timezone-Aware Datetime Handling**

**Problem**: GitHub Actions returns naive datetimes from `TIMESTAMPTZ` columns

**Root cause analysis**:

```
TIMESTAMPTZ storage: ✓ Timezone info stored in DB
        ↓
PostgreSQL libpq driver
        ↓
SQLAlchemy column type: Mapped[datetime]
        ↓
GitHub Actions: ❌ Naive datetime (tzinfo=None)
Local Docker: ✓ Timezone-aware datetime
```

**Likely causes**:

1. Different libpq/psycopg2 versions (GitHub has older)
2. Connection timezone setting not explicitly set
3. SQLAlchemy column type not specifying `asdecimal=True` style timezone handling

**Evidence**:

- pg15 (GitHub) is older than pg16 (local)
- Older drivers may not preserve timezone info by default
- We had to add `.replace(tzinfo=UTC)` workaround (commit d6c2bf8)

**Severity**: 🔴 HIGH - Breaks timezone-dependent queries

---

### 4. **Database Cleanup vs Fresh Containers**

**Problem**: Local Docker creates fresh containers; GitHub Actions uses persistent DB

**Impact**:

- **Local**: Stale data bugs hidden by container recreation
- **GitHub**: Stale data bugs exposed through cleanup failures
- We fixed this, but root cause is environment difference

**Evidence**:

- Had to add deduplication to fixtures (commit 3882d81)
- Had to fix hypertable cleanup strategy (commit d6d88f6)
- These issues only surfaced on GitHub's persistent DB

**Severity**: 🟡 MEDIUM - Masks test isolation bugs locally

---

## Alignment Strategy

### Option A: Align to GitHub (Downgrade Local to pg15)

**Pros**:

- Matches exactly what tests will run on
- Exposes real issues early
- Smaller changes

**Cons**:

- pg15 is EOL next year
- Takes newer pg16 features offline

**Work**:

- Update `docker-compose.yml`: `timescale/timescaledb:latest-pg15`
- Update GitHub Actions: Use explicit `pg15` tag for consistency

---

### Option B: Align GitHub to Local (Upgrade to pg16)

**Pros**:

- Uses modern PostgreSQL version
- Better performance and features
- Newer is better principle

**Cons**:

- GitHub Actions runs may behave differently
- Need to test pg16 compatibility

**Work**:

- Update `.github/workflows/tests.yml`: Use `latest-pg16`
- Test on GitHub Actions

---

### Option C: Make Tests Version-Agnostic (Recommended)

**Pros**:

- Works on both pg15 and pg16
- Future-proof
- Doesn't require changing environments

**Cons**:

- Some configuration needed
- More complex

**Work**:

1. Add explicit connection timezone configuration
2. Ensure datetime columns have type handlers
3. Add `pool_pre_ping=True` to all engine configs
4. Test on both versions

---

## Recommended Implementation

### Step 1: Fix SQLAlchemy Configuration (All Engines)

```python
# Ensure all create_engine calls use:
engine = create_engine(
    database_url,
    echo=False,
    pool_pre_ping=True,  # ← Add this
)
```

**Files to update**:

- `tests/contract/integration/conftest.py` (line 111)
- `tests/contract/database/conftest.py` (already has it ✓)
- Check `src/` database connection code

---

### Step 2: Standardize Timezone Handling

```python
# In database connection code or conftest
# Ensure TIMESTAMPTZ columns always return timezone-aware datetimes
# Option: Use psycopg2 connection parameter
# Option: Add .replace(tzinfo=UTC) after reading (already done in tests)
```

**Files to check**:

- `src/config/database.py` - where connections are created
- Ensure `session_scope()` uses consistent config

---

### Step 3: Standardize PostgreSQL Version in GitHub Actions

```yaml
# .github/workflows/tests.yml
services:
  postgres:
    image: timescale/timescaledb:latest-pg16 # ← Upgrade from pg15
```

**Rationale**: Local uses pg16, so GitHub should too

---

### Step 4: Add Explicit Connection Timezone Settings

```python
# When creating engine or connection
# Set timezone to UTC explicitly for consistency
set timezone = 'UTC';
```

---

## Implementation Priority

| Priority | Action                                        | Impact                        | Effort    |
| -------- | --------------------------------------------- | ----------------------------- | --------- |
| 1️⃣       | Add `pool_pre_ping=True` to integration tests | Fixes connection state issues | ⚡ 5 min  |
| 2️⃣       | Align PostgreSQL to pg16 in GitHub Actions    | Matches local environment     | ⚡ 5 min  |
| 3️⃣       | Add explicit timezone in connection strings   | Ensures consistency           | ⏱️ 15 min |
| 4️⃣       | Add connection tests for timezone behavior    | Prevents regression           | ⏱️ 20 min |

---

## Testing Verification

After alignment, verify with:

```bash
# Run tests locally with both outcomes should match:
bash scripts/run-tests-docker.sh

# Verify postgres version
docker exec analyzer-timescaledb psql -U postgres -c "SELECT version();"

# Verify timezone handling in tests
pytest tests/contract/integration/test_github_extraction_e2e.py::TestGitHubLanguageDetection::test_extract_languages_from_repo -v

# Verify database cleanup
pytest tests/contract/integration/test_azure_devops_extraction_e2e.py::TestAzureDevOpsLanguageDetection::test_language_storage_time_series -v
```

---

## Summary

**Primary issue**: PostgreSQL version mismatch (pg15 vs pg16) causing timezone-aware datetime stripping

**Secondary issues**:

- Missing `pool_pre_ping=True` in integration test config
- Cleanup bugs expose on persistent DB (GitHub), hidden by fresh containers (local)

**Recommended fix**:

1. Align PostgreSQL to pg16 across all environments
2. Add `pool_pre_ping=True` to integration test engine
3. Add explicit UTC timezone configuration

**Expected outcome**: Tests behave identically locally and on GitHub Actions
