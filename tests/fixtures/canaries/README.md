# Canary Repositories

*Plan 020 Component 2 — Live-API Nightly Monitoring*

These are the designated **canary repositories** used by the nightly live-API
monitoring workflow (`.github/workflows/live-api-nightly.yml`).  They provide
known-stable baselines for the `TestGitHubCanary` and `TestAzureDevOpsCanary`
test classes in `tests/contract/integration/test_canary_live_api.py`.

---

## Selection Criteria

A canary repository must be:

- **Small** — handful of PRs and contributors, not hundreds.
- **Stable** — rarely changes; predictable counts.
- **Accessible** — readable by the `CANARY_GITHUB_TOKEN` / `CANARY_AZURE_DEVOPS_PAT`
  secrets with read-only scope.
- **Representative** — contains at least one mixed-case contributor email and
  one reviewer scenario so the key contributor-identity invariants are exercised.

---

## GitHub Canary

| Property | Value |
|---|---|
| Repository | `stickleprojects/azure_devops_analyzer` |
| URL | <https://github.com/stickleprojects/azure_devops_analyzer> |
| Baseline PR count (lower bound) | 10 |
| Baseline contributor count (lower bound) | 1 |
| Secret required | `CANARY_GITHUB_TOKEN` (read-only, `repo:read` or fine-grained `contents:read`) |

The `azure_devops_analyzer` repo is used as its own canary: it has a growing
but modest number of pull requests and a small set of known contributors.
Lower-bound assertions prevent flaky failures as the repository naturally grows.

---

## Azure DevOps Canary

| Property | Value |
|---|---|
| Organisation URL | `https://dev.azure.com/kieronwray` |
| Project | `azure_devops_analyzer` |
| Baseline repo count (lower bound) | 1 |
| Secret required | `CANARY_AZURE_DEVOPS_PAT` (read-only, `Code (read)` scope) |

---

## Refreshing Baselines

Baseline counts are **lower bounds**, not exact values, so the canary survives
normal repository growth.  Refresh the baseline if the count in
`test_canary_live_api.py` drifts significantly below the real count — typically
when you add a new batch of PRs or contributors deliberately.

To update, edit the `EXPECTED_*` constants in each `Test*Canary` class, commit,
and open a PR.  No secrets or production changes are required.

---

## Secrets Setup (one-time, admin only)

Both secrets are stored in the GitHub repository secrets vault.  They must be
provisioned by someone with `admin` access to the `stickleprojects` organisation:

1. **`CANARY_GITHUB_TOKEN`** — A fine-grained personal access token (or classic
   PAT with `repo:read`) scoped only to `stickleprojects/azure_devops_analyzer`.
2. **`CANARY_AZURE_DEVOPS_PAT`** — A PAT with `Code (read)` scope on the
   `azure_devops_analyzer` project in the `kieronwray` Azure DevOps organisation.

The nightly workflow (`live-api-nightly.yml`) uses these secrets exclusively and
is **not** a required PR check.  Failures from missing secrets or API outages
open a GitHub Issue rather than blocking merges.
