# Test Caching Isolation

## Problem

File-based extractor caching could interfere with tests and production scenarios, causing false negatives when:

1. **First API call** returns incomplete data (e.g., only public repos)
   - This result is cached to file
2. **Second test or test phase** expects different data (e.g., include private repos)
   - Instead of calling the API, it gets the stale cached result
   - Test fails because expected data isn't in the cached result

### Real-World Scenario: Private Repos in Production

```python
# Day 1 - Extraction Run (include_private=False by mistake):
1. extractor.get_repositories("stickleprojects", include_private=False)
   - Makes API call → gets public repos only
   - Result cached to file: key_get_repositories_stickleprojects_private=false

# Day 2 - Extraction Run (corrected to include_private=True):
2. extractor.get_repositories("stickleprojects")  # include_private=True by default
   - File cache MISSES because key includes private=true
   - Makes fresh API call → gets ALL repos ✓
```

The cache key now includes `include_private`, preventing mismatches.

## Solution

### Primary: Disable File Caching in Tests

**File:** `tests/conftest.py` - `pytest_configure()`

```python
# Disable file caching for tests to ensure clean state
os.environ["EXTRACTOR_FILE_CACHE_ENABLED"] = "false"
```

**Why:**

- Tests should never depend on cached state from previous runs
- Each test should get fresh data from the API (or mocked)
- Instance cache (per extractor) is fine since each test creates new instances

### Secondary: Separation of Public vs Private Cache Entries

**File:** `src/extractors/github/extractor.py` - `get_repositories()` method

Added `include_private` parameter that controls:

- Whether to fetch private repos in addition to public
- **Most importantly**: Creates separate cache keys for public-only vs all-repos calls

```python
def get_repositories(
    self,
    organization: str,
    project: Optional[str] = None,
    include_private: bool = True,  # NEW: Cache key includes this
) -> list[RepositoryData]:
```

**Why this matters:**

- If you ever call with `include_private=False` → gets public only, caches it
- If you later call with `include_private=True` → different cache key → fresh API call
- Without this, both would share the same cache, causing false negatives

**Default:** `include_private=True`

- Ensures production extraction gets ALL repos by default
- Users can explicitly set to `False` for privacy-conscious scenarios

### Tertiary: Aggressive Cache Cleanup

**File:** `tests/conftest.py` - `_clear_extractor_caches_between_tests()`

- Clears file cache BEFORE each test (before `yield`)
- Clears file cache AFTER each test (after `yield`)
- Doesn't depend on `_file_cache_enabled()` being true
- Always removes cache directory if it exists

This ensures that even if file caching gets accidentally re-enabled, tests remain isolated.

## Configuration

### For Normal Development

File caching is ENABLED in production/dev:

- `.env`: `EXTRACTOR_FILE_CACHE_ENABLED=true`
- `.docker-compose.yml`: Inherits from `.env`

### For Tests

File caching is DISABLED automatically:

- `tests/conftest.py`: Calls `os.environ["EXTRACTOR_FILE_CACHE_ENABLED"] = "false"`
- This happens during `pytest_configure` before any tests run
- Overrides any `.env` settings

### To Run Tests WITH Caching (for testing caching itself)

```bash
# Set before running tests to enable file caching
export EXTRACTOR_FILE_CACHE_ENABLED=true
pytest tests/unit/test_extractor_cache.py
```

## How Cache Keys Work

The cache key is built from the method name + all arguments in order:

```python
# Cache key generation (from src/extractors/cache.py)
def _make_cache_key(method_name, args, kwargs):
    parts = [method_name]
    parts.extend(_normalize_arg(a) for a in args)  # positional args
    for k in sorted(kwargs):
        parts.append(f"{k}={_normalize_arg(kwargs[k])}")  # keyword args
    return "|".join(parts)
```

**Example cache keys for `get_repositories`:**

```
# Public repos only:
Cache Key: get_repositories|stickleprojects|None|False
Cached Data: [repo1(public), repo2(public)]

# Public + Private repos:
Cache Key: get_repositories|stickleprojects|None|True
Cached Data: [repo1(public), repo2(public), repo3(private), repo4(private)]

File Cache Paths:
- .cache/get_repositories/abc123def456...json  (include_private=False)
- .cache/get_repositories/xyz789uvw012...json  (include_private=True)
```

These are **completely separate cache files**, so:

- If you accidentally call with `include_private=False` first, no problem
- Calling with `include_private=True` (the default) gets a fresh API call
- Each maintains its own cache independently

## Testing the Fix

The private repo tests now include verbose debug output:

```
======================================================================
PRIVATE REPO TEST - Debug Info
======================================================================
Looking for private repo: stickleprojects/azure_devops_analyzer

Fetching all available repositories...

Available repositories (N total):
  - owner/repo1
  - owner/repo2
  - stickleprojects/azure_devops_analyzer <-- TARGET
```

This output makes it immediately obvious if:

- ✅ Private repo IS in the available list (test will pass)
- ❌ Private repo NOT in the available list (credentials issue, not caching)
- ❌ Different error (shown in exception message)

## See Also

- [File Cache Plan](./file-cache-plan.md) - Implementation details of file caching
- [test_github_extraction_e2e.py](../../tests/contract/integration/test_github_extraction_e2e.py) - Integration tests
- [test_extractor_cache.py](../../tests/unit/test_extractor_cache.py) - Cache unit tests
