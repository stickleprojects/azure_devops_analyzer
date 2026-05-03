# Wave 1B — Plan 022 Track A: Tech Radar schema and categorization engine

## Goal

Land the foundation for Plan 022 (Tech Radar Publication): three database tables, a Python categorization engine, its config file, and the contract + unit tests that prove the categorization rules work. **Do not** implement the workflow (Track B) or the API endpoints (Track C) — those are separate PRs.

## Source plan

`.ai/plans/022-tech-radar-publication-plan.md`. Read **Part A** (Schema), **Part B** (Categorization Engine), and **Part D** (Tests). Skip Part C (API) and the workflow file in Part B — out of scope here.

## Files to create

### Schema (Part A)

- `database/migrations/018_tech_radar_schema.sql` — three new tables: `radar_publications`, `radar_blips`, `radar_blip_history`. Exact DDL is in Plan 022 Part A. Migration must be **idempotent** (use `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS`) to match this project's migration conventions — see existing migrations like `database/migrations/017_*.sql` for the pattern.

### Categorization engine (Part B)

- `src/analyzers/radar_categorization.py` — defines:
  - `Ring` enum: ADOPT, TRIAL, ASSESS, HOLD
  - `Quadrant` enum: INFRASTRUCTURE, PLATFORMS, TOOLS, LANGUAGES (= "Languages & Frameworks")
  - `RadarBlip` dataclass with the fields shown in Plan 022 Part B
  - `RadarCategorizer` class with `categorize(package_name, ecosystem, metrics) -> RadarBlip` and the helper `_ring_from_adoption(repo_count, time_in_use_days) -> Ring`
  - Loads rules from `radar_categorization_config.json` (see below)
  - Categorization priority on conflicting signals: **EOL > CVE Exposure > Adoption Metrics** (Plan 022 Implementation Note 2)

- `src/analyzers/radar_categorization_config.json` — exact JSON in Plan 022 Part B "File: src/analyzers/radar_categorization_config.json"

### Tests (Part D)

- `tests/contract/database/test_radar_schema.py` — five tests S1–S5 from Plan 022 Part D
- `tests/contract/database/test_radar_categorization.py` — six tests C1–C6 from Plan 022 Part D
- `tests/unit/test_radar_categorizer.py` — property-based + deterministic tests as shown in Plan 022 Part D. Uses `hypothesis`. **Check whether `hypothesis` is already in `requirements-test.txt`** — if not, add it; if it is, do nothing.

## Architecture rules (non-negotiable)

This codebase has strict component boundaries — see `.ai/principles.md` Principle 2.

- `src/analyzers/radar_categorization.py` is in **analyzers**. It must:
  - Be platform-agnostic (no GitHub or Azure DevOps SDK imports)
  - **Not** import from `src/extractors/`, `src/database/storage.py`, or `src/workflows/`
  - **Not** write to the database — return data structures only
  - Take metrics as a `dict` parameter, don't query for them
- The schema migration is the only DB-touching artifact. The workflow that populates `radar_blips` from real data is **Track B (a separate PR)**.

If you find yourself wanting to import from `src/database/` or `src/workflows/`, stop — that's the workflow's job (Track B), not the analyzer's.

## Test approach

- Database contract tests use the standard pytest fixtures in `tests/contract/database/conftest.py` (look at neighbouring tests like `test_dependency_dashboard_views.py` for the pattern).
- Categorization contract tests construct `RadarCategorizer` directly and assert ring/quadrant outputs for handcrafted metrics dicts.
- Unit tests use `@hypothesis.given(...)` for property tests like "more repos/time → same or higher ring" (monotonic), plus deterministic asserts for "EOL never Adopt" and "high CVE exposure never Adopt".

Tests run via `bash scripts/run-tests-docker.sh` — the canonical way. Python is **never** run on the host on this project; always Docker.

## Acceptance criteria

- [ ] Migration `database/migrations/018_tech_radar_schema.sql` exists, is idempotent, and creates the three tables and their indices as specified in Plan 022 Part A
- [ ] Migration runs cleanly on a fresh DB (verify by running `bash scripts/run-tests-docker.sh` — migrations apply at test setup)
- [ ] `RadarCategorizer.categorize()` correctly produces a `RadarBlip` for any valid metrics input
- [ ] Config file is loaded at construction time; passing a custom `min_adopt_repos` in config changes categorization (test C6 verifies)
- [ ] All 5 schema tests, 6 categorization contract tests, and the unit tests pass
- [ ] `bash scripts/run-tests-docker.sh` exits 0 — full suite green
- [ ] No imports from `src/extractors/`, `src/database/storage.py`, or `src/workflows/` in `radar_categorization.py`
- [ ] No new endpoints in `src/api/` (that's Track C)
- [ ] No new file in `src/workflows/` (that's Track B)

## Branch and PR conventions

- Branch from `main`: `git checkout -b plan-022/track-a-radar-schema-and-categorizer`
- PR title: `feat(plan-022): radar schema migration and categorization engine`
- PR body: link to `.ai/plans/022-tech-radar-publication-plan.md`, list the three tables, list the test counts (5 + 6 + N unit tests), state explicitly that Track B (workflow) and Track C (API) are out of scope.

## ACCEPTANCE — DO NOT STOP UNTIL CI IS GREEN

This is non-negotiable. Previous Copilot agents on this project have declared work done while CI was red, costing the user 2+ feedback rounds per task.

1. **Before pushing**, run the full test suite locally: `bash scripts/run-tests-docker.sh`. Catch failures here, not in CI.
2. After pushing your branch and opening the PR, run: `gh pr checks <PR#> --watch`
3. If any required check fails:
   1. `gh run view <run-id> --log-failed` to read the failure logs
   2. Identify root cause; do **NOT** skip with `--no-verify`, disable tests, or weaken assertions to make CI pass
   3. Fix the actual problem, commit, push
   4. Repeat from step 2
4. Required check: the `tests` workflow (`.github/workflows/tests.yml`).
5. Only declare done when:
   - All required checks are green
   - PR has no merge conflicts
   - Final PR comment links to the green check run

If you cannot get CI green after 3 attempts, **stop** and post a comment explaining what you tried and what's blocking.

## Out of scope (other tracks / waves)

- `src/workflows/radar_publication.py` — that's Track B (separate PR, depends on this one being merged)
- `/api/radar`, `/api/radar/history`, `/api/radar/export` endpoints — that's Track C
- `src/api/radar_viewer.html` — **deleted from the plan**; the radar viewer is now a React route in Plan 025 Phase 1c
- Any changes to existing extraction workflows or storage code

## Estimated size

~3 hours. Independent of all other Wave 1 prompts — disjoint files.
