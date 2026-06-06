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
- **Accessible** — readable by the existing CI credentials (`github.token` /
  `AZURE_DEVOPS_PAT`) with read-only scope.
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
| Credential required | `github.token` (exported as `GITHUB_TOKEN` by the workflow) |

The `azure_devops_analyzer` repo is used as its own canary: it has a growing
but modest number of pull requests and a small set of known contributors.
Lower-bound assertions prevent flaky failures as the repository naturally grows.

---

## Azure DevOps Canary

| Property | Value |
|---|---|
| Organisation URL | `AZURE_DEVOPS_ORG_URL` secret |
| Baseline repo count (lower bound) | 1 |
| Secret required | `AZURE_DEVOPS_PAT` (Code(read) scope) |

---

## Refreshing Baselines

Baseline counts are **lower bounds**, not exact values, so the canary survives
normal repository growth.  Refresh the baseline if the count in
`test_canary_live_api.py` drifts significantly below the real count — typically
when you add a new batch of PRs or contributors deliberately.

To update, edit the `EXPECTED_*` constants in each `Test*Canary` class, commit,
and open a PR.  No secrets or production changes are required.

---

## Credentials and Secrets

The nightly workflow reuses CI credentials/secrets from GitHub Actions and the
repository settings; **no separate
provisioning step is required**:

| Credential/Secret | Used as | Purpose |
|---|---|---|
| `github.token` | `GITHUB_TOKEN` env var | GitHub API access |
| `AZURE_DEVOPS_PAT` | `AZURE_DEVOPS_PAT` env var | Azure DevOps API access |
| `AZURE_DEVOPS_ORG_URL` | `AZURE_DEVOPS_ORG_URL` env var | Azure DevOps organisation URL |

The nightly workflow (`live-api-nightly.yml`) is **not** a required PR check.
Failures from missing secrets or API outages open a GitHub Issue rather than
blocking merges.
