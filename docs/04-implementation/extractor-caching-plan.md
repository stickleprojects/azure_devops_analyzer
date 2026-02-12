# Plan: Extractor API Caching via Decorator Pattern

## Context

NFR-1 targets performance optimization. Profiling the extraction workflow reveals that several expensive API calls are made redundantly within a single extraction run. Most notably, `get_file_tree()` is called **3 times per repository** (once for technology detection, once for README extraction, once for manifest extraction). Other methods like `get_file_content()` may also be called for the same file from different callers.

A decorator-based caching layer on the extractor interface will eliminate redundant API calls without changing workflow logic. By building it on `BaseExtractor`, both GitHub and Azure DevOps extractors get caching for free.

## Design

### Decorator: `@cached`

A simple instance-method decorator that:
- Generates a cache key from method name + normalized arguments
- Stores results in `self._cache` (a dict on the extractor instance)
- Returns cached results on subsequent calls with the same arguments
- Normalizes `datetime` args to ISO strings and `None` to a sentinel for consistent keys
- Logs cache hits at DEBUG level for observability

**Scope**: Session-scoped (no TTL). The cache lives as long as the extractor instance, which is created per extraction run. Cache naturally clears when the run completes.

**Thread safety**: Not required — each Celery task creates its own extractor instance.

### Cache management on `BaseExtractor`

- `_cache: dict` initialized in `__init__`
- `clear_cache()` method to manually reset
- `cache_stats` property returning hit/miss counts

## Files to Create

### 1. `src/extractors/cache.py` (NEW) ✅ Created

The caching decorator module:
- `_normalize_arg(arg)` — converts datetime→ISO string, None→sentinel, else→str
- `_make_cache_key(method_name, args, kwargs)` — builds deterministic string key
- `@cached` — the decorator itself, looks up `self._cache` and `self._cache_hits`/`self._cache_misses`

## Files to Modify

### 2. `src/extractors/base.py` ✅ Done

- Added `RepositoryExtractor.__init__` with `self._cache = {}`, `self._cache_hits = 0`, `self._cache_misses = 0`
- Added `clear_cache()` method
- Added `cache_stats` property → `{"hits": N, "misses": N, "size": N}`
- Both `GitHubExtractor` and `AzureDevOpsExtractor` now call `super().__init__()`

### 3. `src/extractors/github/extractor.py` ✅ Done

Applied `@cached` decorator to:
- `get_file_tree()` — **biggest win**, called 3x per repo
- `get_file_content()` — called N times for READMEs + manifests, same files may overlap
- `get_languages()` — called once per repo, cheap for GitHub but consistency with Azure
- `get_branches()` — called once per repo
- `_get_repo()` — **new finding**, called 6+ times per repo by other methods

Also added `_user_email_cache` dict for `get_pull_requests()` — avoids redundant `client.get_user()` calls when the same author appears on multiple PRs.

NOT cached (called once with unique params, or results change between calls):
- `get_organizations()`, `get_projects()` — called once at workflow start, cheap
- `get_repositories()` — called once per org, already paginated
- `get_commits()` — called once per repo with unique date params
- `get_pull_requests()` — called once per repo (very expensive but not repeated)

### 4. `src/extractors/azure_devops/extractor.py` ✅ Done

Applied `@cached` decorator to:
- `get_file_tree()`
- `get_file_content()`
- `get_languages()` — **especially valuable here** since Azure walks the entire file tree locally
- `get_branches()`

### 5. `src/workflows/github_analysis.py` ✅ Done

- Logs `cache_stats` at end of each repository extraction for visibility
- Calls `clear_cache()` after each repo (prevents unbounded memory growth)
- Also clears cache on error path

### 6. `src/workflows/azure_devops_analysis.py` ✅ Done

- Same: logs `cache_stats` + `clear_cache()` at end of each repository extraction

## Implementation Steps

1. ~~Create `src/extractors/cache.py` with the `@cached` decorator~~ ✅ Done
2. ~~Update `RepositoryExtractor.__init__` in `src/extractors/base.py` with cache state + management methods~~ ✅ Done
3. ~~Apply `@cached` to GitHub extractor methods~~ ✅ Done (5 methods + `_user_email_cache`)
4. ~~Apply `@cached` to Azure DevOps extractor methods~~ ✅ Done (4 methods)
5. ~~Add cache stats logging to both workflows~~ ✅ Done (log + clear_cache per repo)
6. ~~Write unit tests for the decorator (key generation, hit/miss, datetime normalization)~~ ✅ Done (23 tests)
7. ~~Run existing test suite to verify no regressions~~ ✅ Done (100 passed, 0 failures)

## Expected Impact

| Scenario | Before | After |
|----------|--------|-------|
| `_get_repo()` (GitHub) per repo | 6+ (one per method) | 1 (+ 5+ cache hits) |
| `get_file_tree()` calls per repo | 3 | 1 (+ 2 cache hits) |
| `get_file_content()` for shared files | N calls | 1 per unique file |
| `get_user()` for PR authors | 1 per PR | 1 per unique author |
| Azure `get_languages()` file walk | Full walk every call | 1 walk per repo |
| Total API calls per 100 repos | ~800+ | ~400 (est. 50% reduction) |

## Verification

1. **Unit tests**: ✅ `tests/unit/test_extractor_cache.py` — 23 tests passing
   - `TestNormalizeArg` (6 tests): None→sentinel, datetime→ISO, string, int, bool
   - `TestMakeCacheKey` (7 tests): positional, kwargs sorted, mixed, datetime, collisions
   - `TestCachedDecorator` (6 tests): miss, hit, same-object identity, different args/kwargs, explicit-None vs omitted
   - `TestCacheManagement` (4 tests): initial state, stats, clear_cache, fresh calls after clear
2. **Existing tests**: ✅ 100 passed, 3 skipped (live API), 0 failures — no regressions
3. **Manual verification**: Run extraction against a repo and check DEBUG logs for cache hit messages
