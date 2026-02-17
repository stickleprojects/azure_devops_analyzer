# GitHub Private Repository Access - API Constraints

## Overview

GitHub's API for accessing repositories has significant complexity around private repo visibility. This document explains the constraints and how the extractor handles them.

## API Endpoints & Private Repo Behavior

### 1. **Authenticated User Endpoint** ✅ Full Private Access

```python
client.get_user()  # No argument = authenticated user
user.get_repos(visibility="all")
```

**Returns:**

- All public repos owned by the authenticated user
- All private repos owned by the authenticated user
- Private repos where the user is a collaborator (invited to access)

**Use case:** Extracting your own repos including private ones

---

### 2. **Named User Endpoint** ❌ NO Private Access

```python
client.get_user("username")  # Specific user by name
user.get_repos(type="all")
```

**Returns:**

- Only PUBLIC repos owned by that user
- **Cannot access their private repos** (even if you know them)

**Limitation:** This is a GitHub API hard constraint. You cannot access another user's private repositories through the API.

**Use case:** Getting public profiles/repos

---

### 3. **Organization Endpoint** ⚠️ Conditional Private Access

```python
client.get_organization("org_name")
org.get_repos(type="all")
```

**Returns:**

- All public organization repos
- All private organization repos **IF you are an organization member** with sufficient permissions

**Constraint:** If you're not a member, you can't access private org repos

**Use case:** Extracting organization repos you have access to

---

## Token Scope Impact

Your GitHub token's scope affects even where you WOULD have access:

```
Token Scope          | Can Access Private? | Notes
=====================|====================|==================================
public_repo (old)    | NO                 | Only public repos
repo (full control)  | YES                | Public + private repos
repo:status          | LIMITED            | Check current permissions
```

**Example:**

```python
# Even with authenticated endpoint, if token only allows public_repo:
user.get_repos(visibility="all")
# Still returns ONLY public repos! Private repos not included.
```

## Implementation in Extractor

### The `include_private` Parameter

**When True (default):**

- **Authenticated user**: Uses `visibility="all"` → gets private repos ✓
- **Organization**: Uses `type="all"` → gets private IF member ✓
- **Other user**: Uses `type="all"` (only public, API limitation) ❌

**When False:**

- **Authenticated user**: Uses `visibility="public"` → only public ✓
- **Organization**: Uses `type="public"` → only public ✓
- **Other user**: Uses `type="all"` (only public anyway) ✓

### Access Mode Logging

The extractor logs which access mode was used:

```python
# You'll see one of these in logs:
"organization (public + private if member)"
"authenticated_user (public + private)"
"user 'username' (public only - GitHub API limitation)"
```

This helps you verify you're getting the data you expect.

---

## Real-World Scenarios

### Scenario 1: Extracting Your Own Private Repos

```python
config = GitHubExtractorConfig(
    token="ghp_yourtoken",
    user="yourname"
)
extractor = GitHubExtractor(config)
repos = extractor.get_repositories("yourname", include_private=True)
# ✓ Returns: all your repos including private ones
```

**Requirements:**

- Token must have `repo` scope (full control)
- `organization` parameter must match authenticated username

---

### Scenario 2: Extracting Organization Private Repos

```python
config = GitHubExtractorConfig(
    token="ghp_token_with_org_scope",
    organization="my-company"
)
extractor = GitHubExtractor(config)
repos = extractor.get_repositories("my-company", include_private=True)
# ✓ Returns: org's repos if you're a member
```

**Requirements:**

- Token must have org membership/access
- You must be part of the organization
- Token scope must allow org repo access

---

### Scenario 3: Extracting Public Repos from Another User

```python
repos = extractor.get_repositories("octocat", include_private=True)
# ✓ Returns: only octocat's public repos
# ✗ Note: include_private=True has NO EFFECT here (API limitation)
```

**Constraint:** GitHub API doesn't allow this. This is by design for privacy.

---

### Scenario 4: What Happens With Wrong Token Scope

```python
config = GitHubExtractorConfig(
    token="ghp_token_with_only_public_repo_scope",
    user="yourname"
)
extractor = GitHubExtractor(config)
repos = extractor.get_repositories("yourname", include_private=True)
# ✗ Returns: ONLY public repos
# Why: Token doesn't have permission to see private repos
# Debug: Check logs - will show "authenticated_user" was used
```

**Solution:** Regenerate token with `repo` (full control) scope

---

## Caching Implications

The `include_private` parameter is part of the cache key:

```
Cache Key: get_repositories|stickleprojects|None|True
Cache Key: get_repositories|stickleprojects|None|False
```

These are separate cache entries. However, **GitHub API limitations affect what's actually cached:**

```
Scenario: Call order matters for org repos
1. get_repositories("my-org", include_private=False)
   → Cached: my-org public repos only

2. get_repositories("my-org", include_private=True)
   → Different cache key!
   → Fresh API call
   → May return: public + private if you're a member
```

---

## Debugging Private Repo Issues

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now run extraction
extractor = GitHubExtractor()
repos = extractor.get_repositories("myaccount")
```

**Look for:** "GitHub extractor: Fetching repositories using access mode:"

### Verify Token Scope

```bash
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user
# Check the "scopes" field in response
```

### Verify Organization Membership

```python
# If extracting org repos, verify you're a member:
auth_user = client.get_user()
# Then check if you appear in org members
```

---

## Summary: What Works

| Scenario         | include_private=True                    | include_private=False |
| ---------------- | --------------------------------------- | --------------------- |
| Your own repos   | ✅ Gets all including private           | ✅ Gets public only   |
| Your org repos   | ✅ Gets all if member                   | ✅ Gets public only   |
| Other user       | ❌ API limitation (public only)         | ✅ Gets public        |
| New private repo | ✅ If fetched again, uses new cache key | ✅ Won't appear       |

## See Also

- [GitHub API Docs: Repositories](https://docs.github.com/en/rest/repos)
- [GitHub Token Scopes](https://docs.github.com/en/developers/apps/building-oauth-apps/scopes-for-oauth-apps)
- [src/extractors/github/extractor.py](../../../src/extractors/github/extractor.py) - Implementation
