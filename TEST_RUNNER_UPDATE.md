# Test Runner Update - GitHub & Azure DevOps Integration

## Changes Made

Updated `run-tests-docker.sh` and `docker-compose.test.yml` to ensure **both GitHub and Azure DevOps tests are executed**, including live API tests when requested.

## What Changed

### 1. `scripts/run-tests-docker.sh`
**Before:** Ran `pytest tests/contract/integration/` (all tests in directory)
**After:** Explicitly runs both test files:
- `tests/contract/integration/test_github_extraction_e2e.py`
- `tests/contract/integration/test_azure_devops_extraction_e2e.py`

**With `--live-api` flag:**
- Runs both GitHub AND Azure DevOps live API tests (marked with `@pytest.mark.live_api`)
- Uses separate JUnit output: `junit-live-api.xml`

**Without `--live-api` flag:**
- Runs both GitHub AND Azure DevOps tests excluding live API tests (marked with `not live_api`)
- Uses standard JUnit output: `junit.xml`

### 2. `docker-compose.test.yml`
**Before:** 
```yaml
pytest tests/contract/integration/ -v -m 'not live_api'
```

**After:**
```yaml
pytest tests/contract/integration/test_github_extraction_e2e.py \
       tests/contract/integration/test_azure_devops_extraction_e2e.py \
       -v -m 'not live_api'
```

### 3. Updated Help Text
New help message clarifies:
- Both GitHub and Azure DevOps platforms are tested
- What each platform tests (extraction, language detection, technology detection)
- Environment variables needed (GITHUB_TOKEN, AZURE_DEVOPS_PAT, AZURE_DEVOPS_ORG_URL)

## Usage

### Run both platforms (without live API)
```bash
./scripts/run-tests-docker.sh
```

### Run both platforms (with live API)
```bash
./scripts/run-tests-docker.sh --live-api
```

### Show help
```bash
./scripts/run-tests-docker.sh --help
```

## Test Coverage

### GitHub Tests (14 methods)
✅ Repository extraction
✅ Branch & commit tracking
✅ Language detection (API-based)
✅ Technology detection (file patterns)

### Azure DevOps Tests (10 methods)
✅ Repository extraction
✅ Branch & commit tracking
✅ Language detection (file heuristics)
✅ Technology detection (file patterns)

### Total: 24 test methods across both platforms

## Output Files

- `test-results/junit.xml` - Standard test results
- `test-results/junit-live-api.xml` - Live API test results (when `--live-api` used)

## Verification

✅ Script syntax validated
✅ Both platform test files explicitly specified
✅ Live API tests properly scoped
✅ Help text updated with platform information
