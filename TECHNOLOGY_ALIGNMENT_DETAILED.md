# Comprehensive Technology Alignment Review - Local vs GitHub Actions

## Critical Differences Found

### 1. **PostgreSQL Credentials Mismatch** 🔴 HIGH PRIORITY

| Component      | Local Docker                                                              | GitHub Actions                                                    | Issue       |
| -------------- | ------------------------------------------------------------------------- | ----------------------------------------------------------------- | ----------- |
| Username       | `test_analyzer`                                                           | `postgres`                                                        | ❌ MISMATCH |
| Password       | `test_password_123`                                                       | `postgres`                                                        | ❌ MISMATCH |
| Database       | `analyzer_test`                                                           | `test_azure_devops`                                               | ❌ MISMATCH |
| Connection URL | `postgresql://test_analyzer:test_password_123@test-db:5432/analyzer_test` | `postgresql://postgres:postgres@localhost:5432/test_azure_devops` | ❌ MISMATCH |

**Impact**: If tests are environment-sensitive (checking credentials, connection strings in logs, etc.), they could behave differently

**Recommendation**: Use identical credentials in both environments for consistency

---

### 2. **Test Command Differences** 🟡 MEDIUM PRIORITY

#### GitHub Actions (tests.yml)

```bash
# Unit tests
pytest tests/unit/ -v --tb=short

# Integration tests
pytest tests/contract/integration/ -v --tb=short --durations=10 -m "not live_api"

# Coverage
pytest tests/ --cov=src --cov-report=xml --cov-report=term-missing -m "not live_api"
```

#### Local Docker (docker-compose.test.yml)

```bash
# Specific test files only
pytest tests/contract/integration/test_github_extraction_e2e.py \
       tests/contract/integration/test_azure_devops_extraction_e2e.py \
       -v \
       -m 'not live_api' \
       --junit-xml=/app/test-results/junit.xml \
       -p no:cacheprovider \
       --tb=short
```

**Differences**:

- ❌ Local SKIPS unit tests (doesn't run `tests/unit/`)
- ❌ Local uses `-p no:cacheprovider` (disables cache)
- ❌ GitHub has `--durations=10` (shows slow tests)
- ❌ Local doesn't run coverage
- ✅ Both use `--tb=short` and `-m "not live_api"`

**Impact**: Local Docker doesn't test unit tests at all! Coverage isn't generated locally.

**Recommendation**: Align docker-compose.test.yml to run same test suite as GitHub

---

### 3. **Environment Variables** 🟡 MEDIUM PRIORITY

#### GitHub Actions sets

```yaml
PYTHONPATH: ${{ github.workspace }}
GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
AZURE_DEVOPS_PAT: ${{ secrets.AZURE_DEVOPS_PAT }}
DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_azure_devops
```

#### Local Docker sets

```yaml
TEST_DATABASE_URL: postgresql://test_analyzer:test_password_123@test-db:5432/analyzer_test
POSTGRES_HOST: test-db
POSTGRES_USER: test_analyzer
POSTGRES_PASSWORD: test_password_123
POSTGRES_DB: analyzer_test
POSTGRES_PORT: 5432
LOG_LEVEL: DEBUG
PYTHONPATH: /app
PYTHONDONTWRITEBYTECODE: 1
```

**Differences**:

- ❌ GitHub uses `DATABASE_URL`, local uses `TEST_DATABASE_URL`
- ❌ Local has extra `LOG_LEVEL: DEBUG`
- ❌ Local has `PYTHONDONTWRITEBYTECODE: 1`
- ✅ Both set PYTHONPATH

**Impact**: conftest looks for `TEST_DATABASE_URL` first, then `DATABASE_URL`. Local uses TEST_DATABASE_URL, GitHub uses DATABASE_URL. Could cause confusion.

**Recommendation**: Standardize on one env var name (TEST_DATABASE_URL preferred for test-specific)

---

### 4. **Database Network Configuration** 🟡 MEDIUM PRIORITY

| Aspect  | Local                                | GitHub                          |
| ------- | ------------------------------------ | ------------------------------- |
| Host    | `test-db` (Docker internal)          | `localhost` (direct connection) |
| Network | Shared Docker network `test-network` | GitHub Actions runner localhost |
| DNS     | Via Docker DNS                       | Direct localhost                |

**Impact**: Network topology is completely different. Local uses Docker networking, GitHub uses direct localhost.

**Recommendation**: No change needed - this is by design (Docker vs bare runner)

---

### 5. **Pytest Configuration** 🟡 MEDIUM PRIORITY

#### Local Docker

```bash
-p no:cacheprovider      # Disables pytest caching
--junit-xml=/app/test-results/junit.xml  # JUnit XML output
```

#### GitHub Actions

```bash
--durations=10          # Show 10 slowest tests
# No cache disabling
# No explicit junit output (uses default)
```

**Differences**:

- ❌ Local explicitly disables cache provider
- ❌ GitHub shows test durations (helps identify slow tests)
- ❌ Different output formats

**Recommendation**: Add `--durations=10` to local config for consistency

---

### 6. **Test File Selection** 🔴 HIGH PRIORITY

| Environment    | Test Discovery                                                                            |
| -------------- | ----------------------------------------------------------------------------------------- |
| GitHub Actions | `tests/contract/integration/` - discovers ALL test files                                  |
| Local Docker   | Explicitly lists: `test_github_extraction_e2e.py` + `test_azure_devops_extraction_e2e.py` |

**Missing from Local**:

- `test_dependency_enrichment_e2e.py`
- `test_team_management_e2e.py`
- Any new test files added

**Impact**: 🔴 CRITICAL - Local Docker is only running a subset of integration tests! New tests won't run locally.

**Recommendation**: Change docker-compose.test.yml to use `tests/contract/integration/` discovery

---

### 7. **Coverage Generation** 🟡 MEDIUM PRIORITY

| Environment    | Coverage                                                          |
| -------------- | ----------------------------------------------------------------- |
| GitHub Actions | Generated: `--cov=src --cov-report=xml --cov-report=term-missing` |
| Local Docker   | Not generated                                                     |

**Impact**: Coverage reports not available locally

**Recommendation**: Add coverage generation to docker-compose.test.yml

---

### 8. **Timeout and Resource Settings** 🟢 LOW PRIORITY

| Setting               | Local           | GitHub | Note                          |
| --------------------- | --------------- | ------ | ----------------------------- |
| Pytest timeout        | None            | None   | Default infinite              |
| Health check interval | 5s              | 10s    | DB startup check              |
| tmpfs                 | Yes (in-memory) | N/A    | Local uses RAM disk for speed |

**Impact**: Minimal - tmpfs is just optimization

---

## Summary of All Changes Needed

| Priority  | File                                                      | Change                                                                                                                           | Reason                                                                       |
| --------- | --------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| 🔴 HIGH   | `docker-compose.test.yml`                                 | Run ALL integration tests (`tests/contract/integration/`), not just 2 files                                                      | Local missing test_dependency_enrichment_e2e.py, test_team_management_e2e.py |
| 🔴 HIGH   | `.github/workflows/tests.yml`                             | Change creds from `postgres:postgres` to `test_analyzer:test_password_123` OR docker-compose.test.yml to use `postgres:postgres` | Credentials must match                                                       |
| 🟡 MEDIUM | `docker-compose.test.yml`                                 | Add `--durations=10` to pytest command                                                                                           | GitHub shows slow tests, local doesn't                                       |
| 🟡 MEDIUM | `docker-compose.test.yml`                                 | Add coverage generation flags                                                                                                    | GitHub generates coverage, local doesn't                                     |
| 🟡 MEDIUM | `.github/workflows/tests.yml` + `docker-compose.test.yml` | Standardize on `TEST_DATABASE_URL` env var name                                                                                  | Currently using `DATABASE_URL` in GitHub, `TEST_DATABASE_URL` in local       |
| 🟡 MEDIUM | `docker-compose.test.yml`                                 | Add unit tests to test runner                                                                                                    | GitHub runs `tests/unit/`, local doesn't                                     |

---

## Recommended Implementation Order

1. **Fix test discovery** - Change docker-compose.test.yml to discover all tests
2. **Standardize database credentials** - Use same creds in both environments
3. **Standardize env var name** - Use TEST_DATABASE_URL everywhere
4. **Add coverage** - Generate coverage reports locally
5. **Add unit tests** - Run unit tests in docker environment
6. **Add test durations** - Show slow tests in local runs
