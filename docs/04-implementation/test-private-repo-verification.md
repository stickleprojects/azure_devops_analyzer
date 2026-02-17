# Test: test_private_repo_flags_stored - Verification Guide

## Overview

This test verifies that the GitHub extractor can retrieve **private repositories** from the authenticated user's account and correctly store their metadata, including privacy flags.

## Configuration Required

The test requires these environment variables (in `.env` or `.env.resolved`):

```
GITHUB_TOKEN=<valid-token-with-repo-scope>
GITHUB_USER=<username-owning-private-repo>
GITHUB_ORG=<leave-empty-if-using-user>
GITHUB_PRIVATE_REPO=<owner/private-repo-name>
```

Example from `azure-devops-analyzer` repo:

```
GITHUB_TOKEN=github_pat_11A...  # Must have "repo" scope (full access)
GITHUB_USER=stickleprojects      # Must own the private repo
GITHUB_ORG=                      # Leave empty (using user, not org)
GITHUB_PRIVATE_REPO=stickleprojects/azure_devops_analyzer
```

---

## Test Flow

### Step 1: Load Configuration

```python
private_repo_id = github_config.private_repo
# Result: "stickleprojects/azure_devops_analyzer"

if not private_repo_id:
    pytest.skip("GITHUB_PRIVATE_REPO not configured for private repo test")
```

**If fails**: Test is skipped (no private repo env var)

---

### Step 2: Create Extractor

```python
extractor = GitHubExtractor(config=github_config)
```

Creates extractor with:

- Token from GITHUB_TOKEN
- Username from GITHUB_USER ("stickleprojects")
- Private repo config from GITHUB_PRIVATE_REPO

---

### Step 3: Debug - List All Available Repos

```python
target_account = github_config.user or github_config.organization or ""
# Result: "stickleprojects"

all_repos = extractor.get_repositories(target_account, include_private=True)
#                                                     ↑ CRITICAL: Explicit True
#                                                     Ensures visibility="all"
```

**Code Path**:

```
1. Try as organization → likely fails (it's a user)
2. Fall back to user endpoint
3. Check if "stickleprojects" == authenticated user login → YES
4. Use authenticated endpoint: user.get_repos(visibility="all")
5. Returns: ALL repos (public + private)
```

**Debug Output**:

```
Available repositories (N total):
  - stickleprojects/public-repo
  - stickleprojects/another-public-repo
  - stickleprojects/azure_devops_analyzer  <-- TARGET
```

**If private repo NOT in list**:

- Token might not have "repo" scope (only "public_repo")
- User might not actually own the private repo
- Repo might be archived/deleted

---

### Step 4: Fetch Private Repo Metadata

```python
repo = get_or_create_repository(extractor, private_repo_id, test_session)
```

Calls: `extractor.get_repository("stickleprojects/azure_devops_analyzer")`

**Expected**: Returns `RepositoryData` with:

- `repo_id = "stickleprojects/azure_devops_analyzer"`
- `is_private = True`
- `has_secret_scanning = <bool>`
- `has_dependabot_alerts = <bool>`
- `has_vulnerability_alerts = <bool>`

---

### Step 5: Assert Private Flags

```python
assert repo.is_private is True
assert repo.has_secret_scanning is not None
assert repo.has_dependabot_alerts is not None
assert repo.has_vulnerability_alerts is not None
```

Verifies that:

1. Repository is marked as private
2. Security flags were fetched from API
3. Data was properly persisted to database

---

## Pass Criteria

Test passes when:

✅ `include_private=True` is used → `visibility="all"` applies  
✅ Private repo appears in repo list  
✅ Private repo metadata is fetched successfully  
✅ Privacy and security flags are recorded  
✅ Database stores all fields correctly

---

## Failure Scenarios & Diagnosis

### ❌ Scenario 1: GITHUB_PRIVATE_REPO Not Configured

**Error**: Test is skipped

**Cause**: `GITHUB_PRIVATE_REPO` env var not set

**Fix**: Add to `.env`:

```
GITHUB_PRIVATE_REPO=stickleprojects/azure_devops_analyzer
```

---

### ❌ Scenario 2: Private Repo Not in List

**Error**: List shows available repos, but private repo missing

**Example Output**:

```
Available repositories (5 total):
  - stickleprojects/public-repo-1
  - stickleprojects/public-repo-2
  ... more public repos ...

⚠ Warning: Target private repo 'stickleprojects/azure_devops_analyzer' NOT in available repos
```

**Possible Causes**:

1. **Token lacks "repo" scope**
   - Token only has "public_repo" scope
   - Fix: Regenerate token with `repo` (full control) scope
   - Check: `curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user`
   - Look for: "scopes" field in response

2. **Private repo is archived or deleted**
   - Fix: Configure `GITHUB_PRIVATE_REPO` to point to an actual private repo you own

3. **Auth user doesn't own the repo**
   - Example: `GITHUB_USER=alice` but private repo is `bob/private-repo`
   - Fix: Use username that matches the private repo owner

---

### ❌ Scenario 3: Private Repo Not Retrievable

**Error**: Repo in list, but fetch fails

**Example Output**:

```
Failed to retrieve private repo 'stickleprojects/azure_devops_analyzer':
Repository not found: stickleprojects/azure_devops_analyzer

See debug output above for available repositories.
```

**Possible Causes**:

1. **Repo access permissions changed**
   - Repo might have been made private after you lost access
   - Fix: Verify you still have access to the repo

2. **Token revoked or expired**
   - Fix: Regenerate token and update `.env`

3. **Rate limit exceeded**
   - Fix: Wait a bit and retry; check GitHub API status

---

### ❌ Scenario 4: Private Flags Not Populated

**Error**: Assertion fails on privacy flags

**Example**:

```
AssertionError: Expected is_private=True for ..., got False
```

**Possible Causes**:

1. **Repository was recently made public**
   - Fix: Use a different private repo

2. **Wrong repo being tested**
   - Verify `GITHUB_PRIVATE_REPO` points to an actual private repo

---

## Success Output

When test passes, you'll see:

```
======================================================================
Private Repo Test - Debug Info
======================================================================
Looking for private repo: stickleprojects/azure_devops_analyzer

Fetching all available repositories...

Available repositories (N total):
  - stickleprojects/azure_devops_analyzer <-- TARGET
  ... more repos ...

======================================================================

======================================================================
✓ SUCCESS: Private repo test passed for stickleprojects/azure_devops_analyzer
  - repo.is_private = True
  - repo.has_secret_scanning = <bool>
  - repo.has_dependabot_alerts = <bool>
  - repo.has_vulnerability_alerts = <bool>
======================================================================
```

---

## Key Points

1. **Default `include_private=True`** works correctly
   - Always fetches private repos for authenticated user
   - No caching interference (get_repositories not cached)
2. **Explicit parameter in test** ensures clarity
   - Makes the intention clear: we want private repos
   - Avoids ambiguity about defaults

3. **Debug output is comprehensive**
   - Shows which repos ARE available
   - Shows if target private repo found or not
   - Helps diagnose token/permission issues

4. **Caching is bulletproof**
   - `get_repositories()` not cached → always fresh
   - Different parameters get fresh API calls
   - Test isolation preserved

---

## Running the Test

```bash
# Run just this test
pytest tests/contract/integration/test_github_extraction_e2e.py::TestGitHubExtractionBasic::test_private_repo_flags_stored -v

# Run with live API (required for this test)
pytest tests/contract/integration/test_github_extraction_e2e.py::TestGitHubExtractionBasic::test_private_repo_flags_stored -v -m live_api

# With debug logging
LOG_LEVEL=DEBUG pytest tests/contract/integration/test_github_extraction_e2e.py::TestGitHubExtractionBasic::test_private_repo_flags_stored -v -s
```

---

## Verification Checklist

Before running the test, verify:

- [ ] `GITHUB_TOKEN` is set and valid (repo scope)
- [ ] `GITHUB_USER` matches token owner
- [ ] `GITHUB_PRIVATE_REPO` is a real private repo you own
- [ ] `.env.resolved` is up-to-date (`./scripts/resolve_env.sh`)
- [ ] Docker is running (test uses Docker)
- [ ] Internet access available (hits real GitHub API)

Then run the test and look for the "SUCCESS" message.
