# Solution Summary: Private Repo Test & Caching Strategy

A point-in-time record of the private-repository inclusion + caching-strategy
work. The implementation lives in the linked source files — this page is the
narrative and the rationale, not a copy of the code.

## What Was Fixed

### 1. Private repos included by default

`GitHubExtractor.get_repositories()` gained an `include_private: bool = True`
parameter, so production extraction retrieves public **and** private repositories
unless a caller explicitly opts out. Endpoint selection and access-mode logging
live in [github/extractor.py](../../src/extractors/github/extractor.py#L142).

### 2. Caching strategy — `get_repositories()` is intentionally not cached

The method makes external API calls whose results must stay fresh (private-repo
availability can change), and a correct cache key would have to hash every
parameter (`include_private`, `organization`, …). It is simpler and safer never to
cache it; the derived per-repo methods (`get_branches()`, `get_commits()`, …) are
cached by `repo_id`. This holds for every call pattern — public-only and
public+private callers each get fresh, correct data with no cross-call staleness.
Full rationale: [caching-strategy.md](caching-strategy.md).

### 3. Config property names + backward-compatible aliases

Tests referenced `username` / `org`, which did not exist — the real fields are
`user` / `organization`. Convenience `@property` aliases (`username` → `user`,
`org` → `organization`) were added in
[config/github.py](../../src/config/github.py#L27-L35) so both spellings work.

### 4. Private-repo verification test

[test_github_extraction_e2e.py](../../tests/contract/integration/test_github_extraction_e2e.py#L136-L188)
now lists all available repos with `include_private=True`, fails with a diagnostic
listing when the target private repo is absent (a token-scope signal), and asserts
`is_private` plus the GitHub security flags with descriptive messages.

## GitHub API endpoint handling

`get_repositories()` selects the right endpoint for three cases, logging the
access mode each time:

- **Organization** — `org.get_repos(type="all")` when private is requested, else `type="public"`.
- **Authenticated user (token owner)** — `user.get_repos(visibility="all" | "public")`.
- **Other user** — `user.get_repos()` returns public repos only; the GitHub API cannot expose another user's private repos regardless of the flag.

## Prerequisites

The live private-repo test needs a `repo`-scoped token (not just `public_repo`)
owned by / with access to the repo under test:

```bash
GITHUB_TOKEN=ghp_xxxxxxxxxx               # 'repo' scope
GITHUB_USER=stickleprojects               # token owner
GITHUB_PRIVATE_REPO=azure_devops_analyzer # owner/repo_id under test
```

## Verifying

```bash
# Just this test, in Docker
./scripts/run-tests-docker.sh -k test_private_repo_flags_stored

# All live_api tests
./scripts/run-tests-docker.sh -m live_api
```

On success the test prints the target repo marked in the available list and
confirms `is_private` plus the security flags. On failure it prints the available
repositories, so a missing target points at a token scope / ownership problem.

## Files changed

| File | Change |
| ---- | ------ |
| [src/extractors/github/extractor.py](../../src/extractors/github/extractor.py#L142) | `include_private=True` default, endpoint selection, access-mode logging |
| [src/config/github.py](../../src/config/github.py#L27-L35) | `username` / `org` property aliases for backward compatibility |
| [tests/contract/integration/test_github_extraction_e2e.py](../../tests/contract/integration/test_github_extraction_e2e.py#L136-L188) | Debug listing, exception handling, descriptive assertions |
| [caching-strategy.md](caching-strategy.md) | Caching rationale (new at the time of this work) |

## Design principles applied

1. **Default to correctness** — private repos included unless opted out.
2. **No stale caches** — `get_repositories()` always hits the live API.
3. **Clear diagnostics** — failures show which repos *were* available.
4. **API compliance** — endpoint choice respects GitHub's constraints.
5. **Backward compatible** — config aliases keep old property names working.

## Architecture Guardian

This change respects the system boundaries (see
[agents/02a-architecture-guardian.md](../../agents/02a-architecture-guardian.md)):

- Endpoint selection and access-mode logging stay inside the **GitHub extractor**; no platform specifics leak outward.
- The not-cached decision is a property of the extractor layer; analyzers and the storage layer are untouched.
- Config aliases live in the **config** layer, not in callers.
