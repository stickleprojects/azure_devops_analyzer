# Wave 1D — Plan 020 Component 3: Production extraction-health observability

## Goal

Add a runtime health check that runs the same invariants as the CI fixture (Plan 019 Layer B / `tests/db_invariants.sql`) at the tail of each production extraction. Emit a Prometheus gauge per invariant and ship a Grafana dashboard with an alert rule. The single-source-of-truth principle is the point — invariants are defined once in `tests/db_invariants.sql` and consumed by CI, live-API nightly (Component 2, separate PR), and production (this PR).

This prompt covers **Component 3 only** of Plan 020. Components 1 (property tests) and 2 (live-API nightly) are separate PRs.

## Source plan

`.ai/plans/020-property-based-live-api-observability.md`. Read **Component 3** sections 3.1 through 3.5. Skip Components 1 and 2 — out of scope.

## Files to create

- `src/utils/extraction_health.py` — defines `InvariantResult`, `HealthReport` dataclasses and the `compute_extraction_health(session, platform, repo_id=None) -> HealthReport` function. Parses `tests/db_invariants.sql` and runs each named invariant. See Plan 020 Section 3.1 for the dataclass shapes.
- `src/utils/metrics.py` — **only if it does not already exist**. Check first: `grep -r "prometheus_client" src/`. If a metrics module already exists, **extend it** rather than creating a new one. The function to add is `emit_health_report(report: HealthReport)` which emits one `extraction_invariant_violations{platform, repo_id, invariant_name}` gauge per invariant.
- `dashboards/extraction-health.json` — Grafana dashboard with the panels from Plan 020 Section 3.4: gauge per invariant + 7-day time-series. **Do not** add a top-link bar (`links[]` array) — Plan 025 Phase 2 has not yet shipped, and Plan 020 Section 3.4 explicitly says to omit it. Phase 2 will add the canonical bar later.
- `docs/03-operations/extraction-health-monitoring.md` — operations doc per Plan 020 Section 3.5 (what each invariant means, what to do when it fires, how to add a new invariant).

## Files to modify

- `src/workflows/github_analysis.py` — at the tail (after the final commit), call `compute_extraction_health(session, platform="github", repo_id=repo_id)` and `emit_health_report(report)`. Wrap in `try/except Exception` that logs and swallows — **a bug in health-checking must never crash an extraction** (Plan 020 Compatibility Note).
- `src/workflows/azure_devops_analysis.py` — same pattern for `platform="azure-devops"`.

## Files to handle carefully

- `tests/db_invariants.sql` — **read-only** in this PR. The file already exists from Plan 019. Do not modify it. This PR proves it can be consumed at runtime, not just by pytest.
- If `tests/db_invariants.sql` is not packaged into the runtime Docker image, copy it during the image build (e.g. update `Dockerfile` to `COPY tests/db_invariants.sql /app/tests/db_invariants.sql`). The `compute_extraction_health` function should resolve the path from a known location — prefer `Path(__file__).parents[N] / "tests/db_invariants.sql"` over hardcoded `/app/...`.

## Architecture rules (non-negotiable)

This codebase has strict component boundaries — see `.ai/principles.md` Principle 2.

- `src/utils/extraction_health.py` lives in **utils** because cross-cutting concerns (logging, metrics, health) belong there. It is allowed to:
  - Use a SQLAlchemy session passed in
  - Read `tests/db_invariants.sql`
  - Return data structures
  - Emit metrics (delegate to `src/utils/metrics.py`)
- It must **not**:
  - Import from `src/extractors/`, `src/analyzers/`, or `src/workflows/`
  - Write to the database
  - Call extraction code
- The workflow files (`github_analysis.py`, `azure_devops_analysis.py`) already orchestrate; adding a tail-call to `compute_extraction_health` does not violate boundaries — workflows are allowed to call utils.
- The `try/except` wrapper around the health call is critical. If health-checking blows up, log a warning and continue. **Never let observability crash production.**

## Test approach

- Unit-test `compute_extraction_health` with a mocked session and a stub invariants file — verify it parses the SQL, runs each query, and packs results correctly.
- Add an integration test in `tests/contract/database/` that:
  1. Inserts a known-orphan row (e.g. `pull_requests.author_id = 999999`)
  2. Runs `compute_extraction_health`
  3. Asserts the corresponding invariant has `violations > 0` and `sample_rows` populated
- The "single source of truth" property (Plan 020 Verification step 6) is testable: add an invariant to `tests/db_invariants.sql` (in a test, monkey-patching the path) and assert `compute_extraction_health` picks it up without code changes.

Tests run via `bash scripts/run-tests-docker.sh`. Python is **never** run on the host on this project.

## Acceptance criteria

- [ ] `src/utils/extraction_health.py` exists, parses `tests/db_invariants.sql`, returns `HealthReport`
- [ ] `src/utils/metrics.py` exposes `emit_health_report` (new file, or extension of an existing metrics module — check first)
- [ ] Both production workflow files call `compute_extraction_health` + `emit_health_report` at the tail, wrapped in `try/except` that logs and swallows
- [ ] `dashboards/extraction-health.json` renders the gauge-per-invariant + 7-day time-series panels. No `links[]` array (Plan 025 Phase 2 will add it later).
- [ ] Grafana dashboard auto-provisions via the existing `grafana/provisioning/dashboards/dashboards.yml` config
- [ ] Alert rule fires when any invariant gauge is non-zero for >1 hour (configure within the dashboard JSON or as a separate alert rule file — match existing alert conventions in the repo)
- [ ] `docs/03-operations/extraction-health-monitoring.md` explains the signal, the remediation path, and how to add a new invariant
- [ ] Tests added: unit test for `compute_extraction_health`, integration test injecting a synthetic violation
- [ ] `bash scripts/run-tests-docker.sh` exits 0 — full suite green
- [ ] `tests/db_invariants.sql` is unchanged
- [ ] No imports from `src/extractors/`, `src/analyzers/`, or `src/workflows/` in `extraction_health.py`
- [ ] Health-call wrapping verified: a deliberate `raise Exception` injected at the top of `compute_extraction_health` does **not** fail the extraction workflow tests (revert the injection before pushing, but record this verification in the PR body)

## Branch and PR conventions

- Branch from `main`: `git checkout -b plan-020/component-3-extraction-health`
- PR title: `feat(plan-020): production extraction-health observability`
- PR body: link to `.ai/plans/020-property-based-live-api-observability.md`, list the new files, the modified workflows, the dashboard, and the operations doc. Explicitly note: "Components 1 and 2 are separate PRs", "tests/db_invariants.sql is unchanged (Plan 019 artifact)", "Plan 025 Phase 2 will add the top-link bar to the new dashboard later".

## ACCEPTANCE — DO NOT STOP UNTIL CI IS GREEN

This is non-negotiable. Previous Copilot agents on this project have declared work done while CI was red, costing the user 2+ feedback rounds per task.

1. **Before pushing**, run the full test suite locally: `bash scripts/run-tests-docker.sh`. Catch failures here, not in CI.
2. After pushing and opening the PR, run: `gh pr checks <PR#> --watch`
3. If any required check fails:
   1. `gh run view <run-id> --log-failed` to read the failure logs
   2. Identify root cause; do **NOT** skip with `--no-verify`, disable tests, weaken assertions, swallow exceptions in production code that should propagate, or use `@pytest.mark.skip` to make CI pass
   3. Fix the actual problem, commit, push
   4. Repeat from step 2
4. Required check: the `tests` workflow (`.github/workflows/tests.yml`).
5. Only declare done when:
   - All required checks are green
   - PR has no merge conflicts
   - Final PR comment links to the green check run **and** confirms the swallow-exception verification (deliberate `raise` in `compute_extraction_health` did not break extraction workflow tests)

If `prometheus_client` is not yet a project dependency, **stop and ask** before adding it — Plan 020 Section 3.3 says to fall back to structured logs only if Prometheus infrastructure isn't already wired. Do not introduce a new infrastructure dependency unilaterally.

If you cannot get CI green after 3 attempts, stop and post a comment explaining what you tried and what's blocking.

## Out of scope

- Plan 020 Component 1 (property tests) — separate PR
- Plan 020 Component 2 (live-API nightly + canary secrets) — separate PR
- Adding new invariants to `tests/db_invariants.sql` — that file is Plan 019's artifact
- Cross-platform identity resolution — explicitly out of scope per Plan 020
- Adding a top-link bar to `extraction-health.json` — Plan 025 Phase 2 owns that

## Estimated size

~4–6 hours. Touches workflows in production code paths, so the swallow-exception wrapper is the highest-risk part — get the test for that right first.
