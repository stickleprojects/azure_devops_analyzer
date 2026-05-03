# Wave 1A — Plan 025 Phase 2: Uniform Grafana top-link bar

## Goal

Replace the inconsistent top-link bar across 11 Grafana dashboard JSON files with a single canonical 6-entry bar. Today there are 7 distinct shapes (1–6 entries each), and `technology-landscape.json` has no bar at all. After this PR, every dashboard except `dashboard-home.json` should render the same bar in the same order.

## Source plan

`.ai/plans/025-bespoke-admin-and-navigation-ui.md`, "Phase 2 — Uniform Grafana top-link bar". Read the **Scope → In scope → Phase 2** section before starting.

## Files to modify

All of `dashboards/*.json` **except** `dashboard-home.json`. Eleven files:

```
dashboards/admin-dashboard.json
dashboards/contributor-analytics.json
dashboards/dependency-vulnerability-portfolio.json
dashboards/library-detail-deep-dive.json
dashboards/pull-requests.json
dashboards/repository-deep-dive.json
dashboards/repository-overview.json
dashboards/security-dashboard.json
dashboards/service-overview.json
dashboards/team-overview.json
dashboards/technology-landscape.json
```

`dashboards/dashboard-home.json` keeps no top-link bar — it IS Home.

## What to do

For each of the 11 files: **fully replace** the `links` array at the top level of the JSON with the following 6-entry array. Do **not** append — replace.

```json
"links": [
  {
    "asDropdown": false,
    "icon": "home",
    "includeVars": false,
    "keepTime": true,
    "tags": [],
    "targetBlank": false,
    "title": "Home",
    "type": "link",
    "url": "/d/dashboard-home"
  },
  {
    "asDropdown": false,
    "icon": "dashboard",
    "includeVars": false,
    "keepTime": true,
    "tags": [],
    "targetBlank": false,
    "title": "Repos",
    "type": "link",
    "url": "/d/repo-overview"
  },
  {
    "asDropdown": false,
    "icon": "dashboard",
    "includeVars": false,
    "keepTime": true,
    "tags": [],
    "targetBlank": false,
    "title": "Security",
    "type": "link",
    "url": "/d/security-dashboard"
  },
  {
    "asDropdown": false,
    "icon": "dashboard",
    "includeVars": false,
    "keepTime": true,
    "tags": [],
    "targetBlank": false,
    "title": "Technology",
    "type": "link",
    "url": "/d/technology-landscape"
  },
  {
    "asDropdown": false,
    "icon": "cog",
    "includeVars": false,
    "keepTime": true,
    "tags": [],
    "targetBlank": false,
    "title": "Admin",
    "type": "link",
    "url": "/d/admin-dashboard"
  },
  {
    "asDropdown": false,
    "icon": "external link",
    "includeVars": false,
    "keepTime": false,
    "tags": [],
    "targetBlank": true,
    "title": "Admin UI",
    "type": "link",
    "url": "http://localhost:8080/"
  }
]
```

Notes:
- The `Admin UI` entry is the **only one** with `targetBlank: true`. It points to a React app that does not exist yet (Plan 025 Phase 1) — opening in a new tab keeps the dead-link impact minimal until Phase 1 ships.
- Use 2-space indentation to match the existing dashboard JSON files. Run a JSON formatter / linter if unsure — the files in `dashboards/` are pretty-printed.

## What NOT to do

- Do **not** touch `dashboards/dashboard-home.json`. It deliberately has no top-link bar.
- Do **not** modify any other top-level dashboard property (`title`, `uid`, `panels`, `templating`, `tags`, `time`, etc.).
- Do **not** modify panels, queries, or data links inside panels — that's Wave 2 / Plan 025 Phase 3.
- Do **not** rename files, change `uid` values, or restructure the JSON.
- Do **not** change Grafana schema version, datasource references, or anything not in the `links` array.

## Acceptance criteria

- [ ] 11 files modified, all with identical `links[]` arrays in the same order.
- [ ] `dashboards/dashboard-home.json` is unchanged.
- [ ] No other top-level fields modified in any file.
- [ ] Each modified file passes JSON sanity:
      ```bash
      for f in dashboards/*.json; do
        python -c "import json; json.load(open('$f'))" || echo "FAIL: $f"
      done
      ```
- [ ] `git diff` shows ONLY `links[]` array changes (no formatting churn elsewhere). Use a JSON-aware diff if possible.

## Test plan

This change is config-only (no Python). The existing test suite should pass unchanged:

```bash
bash scripts/run-tests-docker.sh
```

If it doesn't, you've changed something you shouldn't have — `git diff` and revert.

## Branch and PR conventions

- Branch from `main`: `git checkout -b plan-025/phase-2-uniform-top-link-bar`
- PR title: `feat(plan-025): uniform 6-entry top-link bar across Grafana dashboards`
- PR body must include: link to `.ai/plans/025-bespoke-admin-and-navigation-ui.md`, brief summary of which files changed, note that `Admin UI` link is intentionally dead until Plan 025 Phase 1 ships.

## ACCEPTANCE — DO NOT STOP UNTIL CI IS GREEN

This is non-negotiable. Previous Copilot agents on this project have declared work done while CI was red, costing the user 2+ feedback rounds per task.

1. After pushing your branch and opening the PR, run: `gh pr checks <PR#> --watch`
2. If any required check fails:
   1. `gh run view <run-id> --log-failed` to read the failure logs
   2. Identify root cause; do **NOT** skip with `--no-verify` or disable tests to make CI pass
   3. Fix the actual problem, commit, push
   4. Repeat from step 1
3. Required check for this repo: the `tests` workflow (`.github/workflows/tests.yml`). Informational checks (lint warnings, codecov) do not block.
4. Only declare the task complete when:
   - All required checks are green
   - The PR has no merge conflicts
   - You have posted a final comment on the PR linking to the green check run

If you cannot get CI green after 3 attempts, **stop** and post a comment explaining what you tried and what's blocking. Do not declare the task complete with red CI.

## Out of scope (defer to other waves / plans)

- Adding data links to panels (Plan 025 Phase 3 — Wave 2)
- React UI implementation (Plan 025 Phase 1 — Wave 3)
- Any backend, schema, or workflow changes
- Touching `dashboard-home.json`

## Estimated size

~1 day. Mechanical JSON edits; no logic.
