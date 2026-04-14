# Generated Test Data Assessment

How to run the automated audit of reporting-view coverage, fixture-scenario
coverage, and dashboard SQL routing — locally (Docker parity) or via GitHub
Actions.

---

## Overview

Three lightweight audit scripts live under `scripts/` and produce
machine-readable JSON artifacts under `artifacts/assessment/`. The artifacts
give exact counts and lists that can be fed directly to an LLM to produce
a precise findings table.

| Script                                     | What it measures                                                                                                           |
| ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------- |
| `scripts/audit_reporting_view_coverage.py` | Which views in `database/views.sql` have / lack direct test coverage in `tests/contract/database/test_reporting_views.py`  |
| `scripts/audit_fixture_scenarios.py`       | How many generated fixture JSONs exist vs how many are exercised by `tests/contract/integration/test_fixture_scenarios.py` |
| `scripts/audit_dashboards_routing.py`      | Whether Grafana dashboard panels use `v_*` reporting views or bypass them with raw base-table SQL                          |

---

## Running locally (preferred – Docker parity)

> **Repo policy:** Docker is the source of truth for test execution.
> Always prefer `bash scripts/run-tests-docker.sh` over running `pytest`
> directly on the host.

### Full assessment in one pass

```bash
# 1. Run both contract test suites in Docker
bash scripts/run-tests-docker.sh tests/contract/database/test_reporting_views.py
bash scripts/run-tests-docker.sh tests/contract/integration/test_fixture_scenarios.py

# 2. Run audit scripts (these only read workspace files, no DB needed)
python scripts/audit_reporting_view_coverage.py
python scripts/audit_fixture_scenarios.py
python scripts/audit_dashboards_routing.py
```

Artifacts are written to `artifacts/assessment/` in the repo root.

### Running audit scripts inside the Docker test-runner container

If you want complete parity (same Python version as CI):

```bash
docker compose -f docker-compose.test.yml run --rm test-runner \
  sh -c "python scripts/audit_reporting_view_coverage.py && \
         python scripts/audit_fixture_scenarios.py && \
         python scripts/audit_dashboards_routing.py"
```

---

## Running via GitHub Actions

The workflow `.github/workflows/generated-test-data-assessment.yml` is a
manual (`workflow_dispatch`) workflow that:

1. Checks out the repository.
2. Runs the reporting-views and fixture-scenario contract tests in Docker.
3. Runs all three audit scripts on the runner.
4. Uploads `artifacts/assessment/` as a workflow artifact.

### How to trigger

1. Go to **Actions → Generated Test Data Assessment** in the GitHub UI.
2. Click **Run workflow** → select branch → **Run workflow**.
3. Once complete, open the run and download the `assessment-<run_number>`
   artifact.

No secrets are required. The workflow runs entirely offline.

---

## Artifact reference

All artifacts are written to `artifacts/assessment/`.

| File                                    | Contents                                                         |
| --------------------------------------- | ---------------------------------------------------------------- |
| `reporting_views_all.json`              | Sorted list of all view names defined in `database/views.sql`    |
| `reporting_views_tested.json`           | Views that are referenced in the test file                       |
| `reporting_views_untested.json`         | Views with no test coverage                                      |
| `reporting_views_summary.json`          | Counts and percentage coverage                                   |
| `reporting_views_possible_renames.json` | Pairs where a tested name may be a renamed view (suffix drift)   |
| `fixture_generated_all.json`            | Sorted list of generated fixture scenario base names             |
| `fixture_exercised.json`                | Scenarios that appear in the `SCENARIOS` list in the test file   |
| `fixture_unexercised.json`              | Generated scenarios not exercised by any test                    |
| `fixture_summary.json`                  | Counts and coverage ratio                                        |
| `dashboards_routing_summary.json`       | Total SQL targets, views count, raw-SQL count, and offender list |

---

## Interpreting the results

### Reporting-view coverage

`reporting_views_summary.json` shows `coverage_pct`.  
`reporting_views_untested.json` lists every view that lacks a direct test.

A view is considered **tested** if its name appears anywhere in
`tests/contract/database/test_reporting_views.py` (inside a SQL string,
as a quoted literal, or as a bare identifier).

`reporting_views_possible_renames.json` flags cases where the test
references a name that doesn't exist in `views.sql` but differs from a
known view only by a common suffix (e.g. `_30d` vs `_30d_total`). These
are worth reviewing manually.

### Fixture coverage

`fixture_summary.json` shows `exercised` / `total_generated`.  
`fixture_unexercised.json` lists scenarios that exist as JSON files but
aren't in the `SCENARIOS` list in the integration test.

### Dashboard routing

`dashboards_routing_summary.json` shows `raw_sql_count`. If this is `0`
all panels route through reporting views. Any non-zero value lists the
offending panels under `raw_sql_offenders`.

---

## Next actions (ordered by impact)

1. **Add a fixture → storage → reporting-view E2E test** – load one generated
   scenario, store it, then assert a `v_*` view returns expected aggregates.
2. **Expand `SCENARIOS` in `test_fixture_scenarios.py`** to cover more (or
   all) of the 27 generated scenarios.
3. **Add tests for untested views** – start with dashboard-facing views listed
   in `reporting_views_untested.json`.
4. **Run this workflow on every PR** by adding a `pull_request` trigger to
   `.github/workflows/generated-test-data-assessment.yml` once the baseline
   coverage is acceptable.

## Architecture Guardian

Boundary validation for this assessment:

- Test-data generation and audit tooling remain outside runtime extraction workflows.
- Reporting-view validation does not introduce direct production schema writes.
- Workflow/CI adjustments remain operational orchestration, not domain logic migration.
- Existing extractor and database service boundaries are unchanged.
