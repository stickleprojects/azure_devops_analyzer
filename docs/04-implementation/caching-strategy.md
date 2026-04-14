# Repository Extraction Caching Strategy

## Overview

The GitHub extractor uses **selective caching** to balance performance with correctness:

- **NOT cached**: `get_repositories()` - Always hits API for fresh data
- **Cached**: `get_branches()`, `get_commits()`, `get_languages()`, etc. - Cached per repository

This design prevents caching from interfering with test isolation and repository discovery.

---

## Why `get_repositories()` is NOT Cached

### Reasons

1. **Parameter variation**: Method accepts variable parameters:
   - `organization` - which account to list repos for
   - `project` - optional project scope
   - `include_private` - whether to include private repos

2. **Test isolation**: Tests need fresh API data
   - Private repo test assumes fresh call returns all repos
   - Caching would cause stale data from previous runs

3. **Dynamic data**: Repository lists change
   - New private repos get created
   - Old repos get deleted/archived
   - Permissions change

4. **API design**: GitHub's API requires fresh calls for different scopes
   - `include_private=True` uses `visibility="all"` (all repos)
   - `include_private=False` uses `visibility="public"` (public only)
   - These should never return the same cached data

### Caching Rules

```python
get_repositories("org", include_private=True)   # ← Always fresh API call
get_repositories("org", include_private=False)  # ← Always fresh API call (different endpoint)
get_repositories("org")                         # ← Always fresh API call (uses default)
```

---

## Why Derived Methods ARE Cached

Methods like `get_branches()`, `get_commits()`, `get_languages()` are cached because:

1. **Single parameter**: Typically just `repo_id` or `repo_id + branch`
2. **Static data**: Branch names, commit history don't change during extraction
3. **Deduplication**: Multiple methods might request the same data
4. **Performance**: Significantly speeds up extraction runs

### Cache Keys for Cached Methods

```python
Cache Key: get_branches|owner/repo
Cache Key: get_commits|owner/repo|main
Cache Key: get_languages|owner/repo
```

These keys are deterministic and include all relevant parameters.

---

## Testing Private Repos

The `test_private_repo_flags_stored` test ensures private repos work correctly:

### Test Flow

```python
# Step 1: Get list of ALL repos (fresh API call)
target_account = github_config.user or github_config.organization
all_repos = extractor.get_repositories(target_account, include_private=True)
#                                                       ↑
#                                                 Explicit parameter=TRUE
#                                                 Ensures visibility="all"

# Step 2: Verify private repo is in the list
assert private_repo_id in repo_ids

# Step 3: Fetch and verify the specific repo
repo = get_or_create_repository(extractor, private_repo_id, test_session)
assert repo.is_private is True
```

### Why This Works

1. **No caching**: `get_repositories()` is not cached → always fresh API call
2. **Explicit parameter**: We explicitly pass `include_private=True` → no ambiguity
3. **Auth check**: Code detects if `target_account` is the authenticated user → uses authenticated endpoint
4. **Visibility**: For authenticated user, uses `visibility="all"` → gets private repos

---

## Cache Eventualities Covered

### Scenario 1: Multiple Tests in One Run

Problem: Cache persists between tests, causing test interference

Solution:

- `get_repositories()` not cached → no interference
- File cache disabled in `pytest_configure()` → test cleanup ensures fresh state
- Between-test fixture clears any leftover cache files

Result: ✅ Each test gets fresh API data

---

### Scenario 2: Different Users/Orgs in One Run

Problem: Cache might confuse repos from different accounts

Solution:

- `get_repositories()` cache key would include organization name
- But `get_repositories()` is NOT cached anyway
- Derived methods (get_branches, get_commits) use `repo_id` as key, which is already scoped to owner

Result: ✅ No confusion between repos from different accounts

---

### Scenario 3: include_private Flag Changes

Problem: Calling with `include_private=True` then `include_private=False` on same org

Solution (if `get_repositories` were cached):

- Cache key would include the bool: `get_repositories|org|None|True` vs `get_repositories|org|None|False`
- These are different cache entries → no mixing

Current solution:

- `get_repositories()` not cached → always fresh

Result: ✅ No stale data mismatches

---

### Scenario 4: Production Cache Stays Fresh

Problem: File cache from Day 1 used in Day 2 extraction

Solution:

- `get_repositories()` not cached → always fresh
- Cached methods (branches, commits, languages) have TTL-like behavior:
  - Each extraction run creates fresh cache entries
  - Old repo IDs won't appear in new runs if repos deleted

Result: ✅ Cache stays reasonably fresh

---

### Scenario 5: Token Permissions Change

Problem: Yesterday's token had full access, today's only has public access

Solution:

- `get_repositories()` not cached → will reflect new permissions
- Cached branch/commit data might be stale, but won't prevent repo discovery

Result: ✅ Changes in permissions detected

---

## Verification Commands

### Check Which Methods Are Cached

```bash
grep "@cached" src/extractors/github/extractor.py
```

Expected output:

```
Line 253:    @cached
Line 268:    @cached
Line 569:    @cached
Line 593:    @cached
Line 612:    @cached
```

These cache:

- `get_branches()`
- `get_commits()`
- `get_languages()`
- `get_pull_requests()`
- `get_file_tree()`

NOT cached:

- `get_organizations()`
- `get_projects()`
- `get_repositories()` ← **This is intentional**
- `get_repository()`

---

## Implementation Details

### Cache Key Format

For cached methods, the key is built as:

```python
_make_cache_key(method_name, args, kwargs)
```

Example:

```python
# Code:
extractor.get_branches("owner/repo")

# Cache Key Generated:
"get_branches|owner/repo"

# File Path:
.cache/get_branches/abc123def456...json
```

### Cache File Location

- **Default root**: `.cache/` in project root
- **Configurable via**: `EXTRACTOR_FILE_CACHE_PATH` env var
- **Structure**: `.cache/{method_name}/{hash_of_cache_key}.json`

### Cache Enabled/Disabled

```bash
EXTRACTOR_FILE_CACHE_ENABLED=true   # Production: caching on
EXTRACTOR_FILE_CACHE_ENABLED=false  # Tests: caching off (set by pytest_configure)
```

---

## Conclusion

The caching strategy is:

1. ✅ **For `get_repositories()`**: No caching (always fresh)
   - Ensures test isolation
   - Prevents private repo discovery issues
   - Respects parameter variations

2. ✅ **For derived methods**: Selective caching (by repo_id)
   - Improves performance
   - Safe because data is relatively static

3. ✅ **For tests**: File cache disabled
   - Each test gets fresh state
   - No cross-test contamination

4. ✅ **For production**: File caching enabled
   - Reduces API calls
   - Survives process restart
   - Can be manually cleared if stale

This ensures all eventualities are covered.

## Architecture Guardian

This implementation plan stays within architecture boundaries:

- Extractors remain API clients and do not own persistence logic.
- Workflow code orchestrates extraction and cache lifecycle only.
- Database writes remain in storage/database layers.
- Caching concerns are isolated to extractor support utilities.
