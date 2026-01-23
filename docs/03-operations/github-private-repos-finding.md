# Critical Finding: GitHub API Private Repository Behavior

## The Problem

When extracting repositories from GitHub, private repositories were missing from results even when using valid authentication credentials. Specifically, the `azure_devops_analyzer` repository and 31 other private repositories were not being returned by the extraction process.

## Root Cause

**GitHub's REST API has a critical but non-obvious behavior regarding private repository visibility:**

### Named User Endpoint
```python
# ❌ Returns ONLY public repos (29 repos in our case)
user = client.get_user('stickleprojects')  # Named user
repos = user.get_repos(type="all")
# Even with valid authentication, this ONLY returns public repositories
```

### Authenticated User Endpoint
```python
# ✅ Returns ALL accessible repos including private (60 repos)
user = client.get_user()  # No arguments = authenticated user
repos = user.get_repos(visibility="all")
```

## The Critical Insight

**Even when the named user IS the authenticated user, GitHub treats these as different endpoints with different permissions:**

- The named user endpoint (`/users/{username}/repos`) is designed for **public profile viewing**
- The authenticated user endpoint (`/user/repos`) provides access to **all your repositories**

This is **BY DESIGN** in GitHub's API to separate public profile information from private account access.

## The Solution

Updated `get_repositories()` in `src/extractors/github/extractor.py` to:

1. **Detect authenticated user**: When fetching repos for a user, first check if it's the authenticated user
2. **Use correct endpoint**: 
   - If it's the authenticated user → use `client.get_user()` with `visibility="all"`
   - If it's a different user → use `client.get_user(username)` with `type="all"` (public only)
3. **Proper parameters**: `visibility` vs `type` depending on endpoint

```python
# The fix
if organization:
    auth_user = self.client.get_user()
    if auth_user.login.lower() == organization.lower():
        # Same user - use authenticated endpoint for private repos
        user = auth_user
        gh_repos = user.get_repos(visibility="all")
    else:
        # Different user - only public repos accessible
        user = self.client.get_user(organization)
        gh_repos = user.get_repos(type="all")
```

## Impact

**Before Fix:**
- 29 repositories returned (public only)
- `azure_devops_analyzer` and 31 other private repos missing
- Live tests failing

**After Fix:**
- 60 repositories returned (public + private)
- All private repos now included
- Live tests passing ✅

## Verification

Run the live integration tests to verify:
```bash
pytest tests/test_github_extractor_standalone.py::TestGetRepositoriesLive -v
```

Expected results:
- `test_extractor_returns_azure_devops_analyzer_repo` ✅ (finds 60 repos including private)
- `test_direct_api_finds_azure_devops_analyzer` ✅ (confirms API behavior)
- `test_debug_extractor_code_path` ✅ (shows code paths taken)

## Documentation References

- **API Behavior**: Documented in module docstring of `src/extractors/github/extractor.py`
- **Implementation**: Code comments at lines 147-154 in `src/extractors/github/extractor.py`
- **Tests**: `tests/test_github_extractor_standalone.py::TestGetRepositoriesLive`

## Lessons Learned

1. **Don't assume API behavior**: Even obvious things (like "my username" = "me") have distinctions in APIs
2. **Test with real data**: Mock tests passed, but live tests revealed the issue
3. **Read API docs carefully**: GitHub's distinction between user endpoints is documented but easy to miss
4. **Compare multiple approaches**: The debug test comparing different fetching methods was crucial

## Related Issues

This likely affects anyone using PyGithub to fetch repositories for their own account by name. The common pattern:
```python
# WRONG - will miss private repos
username = "myusername"
repos = client.get_user(username).get_repos(type="all")

# RIGHT - includes private repos
auth_user = client.get_user()
if auth_user.login == username:
    repos = auth_user.get_repos(visibility="all")
```

## Date Discovered
2026-01-23

## Related Commits
See branch: `feature/restructure-remove-usingclaude`
