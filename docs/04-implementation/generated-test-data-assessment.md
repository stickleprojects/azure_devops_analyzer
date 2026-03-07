# Generated Test Data: Assessment & Usage Guide

**Date:** 2026-03-07  
**Scope:** Evaluation of the generated test fixture system introduced in the latest PR

---

## Overview

The premise behind introducing generated test data was:

1. **Coverage** – Generate fixture data that exercises all ingestion code paths and all queries used by the current dashboards.
2. **Predictability** – Allow developers to predict the impact of future changes by adjusting the data generation, regenerating test data, and validating dashboards against the new data before deploying.
3. **Independence** – Tests should run without live API credentials.

This document assesses whether that premise is fulfilled, and provides instructions for using the system.

---

## Assessment

### Overall Verdict: Partially Fulfilled ✅⚠️

The foundational infrastructure is solid and represents significant progress. Three of the five layers are complete. Two layers have gaps that prevent the system from fully fulfilling the original premise.

---

### What Is Fulfilled ✅

#### 1. Generated Fixture Library (27 files)

**Location:** `tests/fixtures/scenarios/generated/`

27 fixture JSON files are generated and committed, covering:

| Category | Examples | Count |
|----------|----------|-------|
| Python / Docker | python-docker-billing, python-docker-payroll, python-docker-reports | 5 |
| Python / Dual CI | dual-ci-analytics, dual-ci-auth, dual-ci-billing, dual-ci-catalog, dual-ci-gateway | 11 |
| Polyglot / Monorepo | fullstack-monorepo, deep-nested-manifests, python-dual-deps | 3 |
| Other stacks | go-microservice, java-maven-jenkins, react-spa | 3 |
| .NET / Legacy | legacy-migration-billing, legacy-migration-inventory, legacy-migration-payroll | 3 |
| Edge cases | empty-stub, empty-archive, empty-handoff | 3 |

Each fixture contains realistic commits (6–15), pull requests (4–13), language declarations, and manifest file content. This range of scenarios is sufficient to expose ingestion defects across all supported tech stacks.

#### 2. FixtureExtractor — Credential-Free Test Double

**Location:** `tests/fixtures/fixture_extractor.py`

A complete test double for the live `RepositoryExtractor`. It loads any fixture file and implements the full extractor interface (`get_commits`, `get_pull_requests`, `get_languages`, `get_file_content`, `get_branches`). Tests using it require no live API credentials or network access.

#### 3. 30 SQL Reporting Views

**Location:** `database/migrations/011_add_reporting_views.sql`

All dashboard metrics are abstracted into 30 named views. This is the cornerstone of testability — views are a stable, queryable contract between the database and the dashboards.

#### 4. View Test Coverage (22 of 30 views)

**Location:** `tests/contract/database/test_reporting_views.py`

22 of the 30 views are covered by dedicated integration tests that verify correct SQL execution and expected output with controlled test data. All core dashboard views are covered.

#### 5. Fixture-to-Storage Integration Tests (6 of 27 scenarios)

**Location:** `tests/contract/integration/test_fixture_scenarios.py`

Six representative scenarios are tested through the full extraction → storage pipeline:
- `go-microservice`
- `java-maven-jenkins`
- `fullstack-monorepo`
- `dual-ci-analytics`
- `deep-nested-manifests`
- `empty-stub`

Tests verify that commits, pull requests, and languages extracted from fixture files are correctly persisted to the database.

---

### Gaps ⚠️

#### Gap 1: Dashboard Queries Not Fully Routed Through Views

**Impact: HIGH** — Undermines the core premise

Four dashboards contain embedded SQL aggregations that bypass the reporting view layer. This means those dashboard panels are not exercised by the view tests and are invisible to the test data system.

| Dashboard | Panels with Embedded SQL |
|-----------|--------------------------|
| `contributor-analytics.json` | Active contributors count (line 121), Commits count (line 182) |
| `dashboard-home.json` | Active repos (line 103), Active contributors (line 164), Commits (line 225), Open PRs (line 408) |
| `team-overview.json` | Merged PRs (line 368), Open PRs (line 427) |
| `repository-overview.json` | Active repos count (line 121) |

Views exist for all of these queries (see `DASHBOARD_VIEW_AUDIT.md` for the exact corrections). Until the dashboards are updated, changes to the underlying data model could break these panels without any test failure.

#### Gap 2: Eight Views Have No Test Coverage

**Impact: MEDIUM**

8 of 30 views are defined but have no tests in `test_reporting_views.py`:

| View | Used By |
|------|---------|
| `v_contributor_commits` | repository-deep-dive.json |
| `v_dependency_summary` | repository-deep-dive.json |
| `v_pr_size_distribution` | repository-deep-dive.json (per-repo variant) |
| `v_extraction_run_summary` | Internal/admin tooling |
| `v_extraction_runs_active` | admin-dashboard.json |
| `v_extraction_runs_recent` | admin-dashboard.json |
| `v_extraction_metrics_recent` | admin-dashboard.json |
| `v_team_metrics_summary` | team-overview.json |

The three admin dashboard views (`v_extraction_runs_active`, `v_extraction_runs_recent`, `v_extraction_metrics_recent`) rely on extraction run metadata, which requires a separate test setup (extraction run records). The remaining views can be covered with standard test data.

#### Gap 3: Only 6 of 27 Fixtures Are Tested

**Impact: MEDIUM**

`test_fixture_scenarios.py` covers 6 representative scenarios. The remaining 21 fixtures are not exercised by any integration test. Schema mismatches or data quality issues in those fixtures would not be detected until someone attempts to use them.

The 6 tested scenarios adequately represent distinct tech stacks, but the following categories are not validated end-to-end:
- All 11 `dual-ci-*` variants (only `dual-ci-analytics` tested)
- All `legacy-migration-*` scenarios (.NET/C# stack)
- All `python-docker-*` variants
- `react-spa`

#### Gap 4: No End-to-End Fixture → View Pipeline Test

**Impact: MEDIUM**

The fixture integration tests and view tests are separate:

- **Fixture tests** verify data is stored correctly, using hand-crafted assertions.
- **View tests** verify view SQL works, using hand-crafted test data.

There is no test that loads a fixture end-to-end, then queries the reporting views to confirm the aggregate outputs match expected values from the fixture data. This matters for the "predict impact" premise: without such a test, you cannot automatically detect when a fixture change alters view output.

---

## Summary Table

| Capability | Status | Notes |
|-----------|--------|-------|
| Generated fixture library (27 scenarios) | ✅ Complete | Covers all major tech stacks and edge cases |
| Credential-free test double (FixtureExtractor) | ✅ Complete | Full extractor interface |
| SQL reporting views (30 views) | ✅ Complete | Stable contract for all dashboard queries |
| View test coverage | ✅ Mostly complete | 22/30 views tested (73%) |
| Fixture-to-storage pipeline tests | ✅ Partial | 6/27 scenarios tested |
| Dashboard alignment with views | ⚠️ Incomplete | 4 dashboards still use embedded SQL |
| Full fixture → view pipeline test | ⚠️ Missing | No end-to-end combined test |
| Automated impact prediction | ⚠️ Missing | No mechanism to diff view output before/after changes |

---

## How to Use the Generated Test Data System

### Prerequisites

- Docker Desktop running
- PostgreSQL container running: `docker compose up -d postgres`
- Python 3.11+ with dependencies: `pip install -r requirements.txt`

---

### Running the Test Suite

```bash
# Run all integration tests (requires DB)
POSTGRES_HOST=localhost pytest tests/contract/ -v

# Run only fixture pipeline tests
POSTGRES_HOST=localhost pytest tests/contract/integration/test_fixture_scenarios.py -v

# Run only view tests
POSTGRES_HOST=localhost pytest tests/contract/database/test_reporting_views.py -v
```

---

### Using a Fixture in a New Test

Load any of the 27 scenario files via `FixtureExtractor`:

```python
from tests.fixtures.fixture_extractor import FixtureExtractor

# Load by name (searches tests/fixtures/scenarios/generated/<name>.json)
extractor = FixtureExtractor("go-microservice")

# Extract data (no live API required)
commits   = extractor.get_commits("my-repo-id")
prs       = extractor.get_pull_requests("my-repo-id")
languages = extractor.get_languages("my-repo-id")
files     = extractor.get_file_tree("my-repo-id")
content   = extractor.get_file_content("my-repo-id", "go.mod")

# Or pass an inline dict for unit tests that don't need a file
extractor = FixtureExtractor({
    "file_names": ["go.mod"],
    "manifests": {"go.mod": "module example.com/myservice\n\ngo 1.18"},
    "commits": [],
    "pull_requests": [],
    "languages": ["Go"],
})
```

---

### Regenerating Test Data (After Fixture Config Changes)

Use the two-layer generation pipeline when you need to add new scenarios, change existing ones, or update the data to reflect new field requirements.

**Step 1: Validate the fixture configuration**

```bash
python scripts/validate-fixture-config.py
```

**Step 2: Run the full generation pipeline**

```bash
# Validate → Seeds → Enrich (all steps)
bash scripts/generate-fixtures.sh --step validate
bash scripts/generate-fixtures.sh --step seeds
bash scripts/generate-fixtures.sh --step enrich
```

*Prerequisites for generation: Ollama running at `localhost:11434` with model `qwen2.5-coder:14b` pulled (`ollama pull qwen2.5-coder:14b`).*

**Step 3: Verify the output**

```bash
# Quick schema check
python3 -c "
import json, os, pathlib
d = pathlib.Path('tests/fixtures/scenarios/generated')
for f in sorted(d.glob('*.json')):
    with open(f) as fp:
        data = json.load(fp)
    print(f'{f.stem:40} commits={len(data.get(\"commits\",[]))} prs={len(data.get(\"pull_requests\",[]))} langs={data.get(\"languages\",[])}')
"

# Run the fixture integration tests
POSTGRES_HOST=localhost pytest tests/contract/integration/test_fixture_scenarios.py -v
```

**Step 4: Commit the regenerated fixtures**

The generated JSON files in `tests/fixtures/scenarios/generated/` are version-controlled. Commit them so the CI pipeline uses the updated data.

---

### Predicting the Impact of a Change

The current infrastructure supports impact prediction through these steps:

1. **Identify the view** that backs the dashboard panel you are changing.
2. **Look up the view test** in `tests/contract/database/test_reporting_views.py`.
3. **Adjust the fixture** data to reflect the new scenario (edit the JSON file or regenerate).
4. **Run the view tests** to verify the view still returns correct results.
5. **Run the fixture tests** to verify the fixture loads cleanly.

Example: Adding a new field to commit data:
```bash
# 1. Edit the relevant fixture JSON or regenerate
# 2. Run tests to catch schema mismatches
POSTGRES_HOST=localhost pytest tests/contract/integration/test_fixture_scenarios.py -v
POSTGRES_HOST=localhost pytest tests/contract/database/test_reporting_views.py -v
```

---

## Recommended Next Steps

To fully close the gaps and complete the original premise, the following work is suggested in priority order:

### Priority 1: Fix Dashboard Alignment (High Impact)

Update the four non-compliant dashboards to query via views instead of embedding raw SQL. The exact corrections are documented in `DASHBOARD_VIEW_AUDIT.md` and `DASHBOARD_SQL_CORRECTIONS.md`.

This is the highest-priority gap because it is the direct blocker for the "exercises all queries" premise.

### Priority 2: Add Tests for the 8 Uncovered Views (Medium Impact)

Extend `tests/contract/database/test_reporting_views.py` to cover:
- `v_contributor_commits`
- `v_dependency_summary`
- `v_pr_size_distribution`
- `v_extraction_run_summary`
- `v_extraction_runs_active`, `v_extraction_runs_recent`, `v_extraction_metrics_recent`
- `v_team_metrics_summary`

### Priority 3: Extend Fixture Coverage (Medium Impact)

Add the remaining 21 fixture scenarios to `test_fixture_scenarios.py`. The parametrize list in that file can be extended with all 27 scenario names; the test logic already handles any valid fixture structure.

```python
# Extend this list in tests/contract/integration/test_fixture_scenarios.py
SCENARIOS = [
    "go-microservice",
    "java-maven-jenkins",
    "fullstack-monorepo",
    "dual-ci-analytics",
    "deep-nested-manifests",
    "empty-stub",
    # Add remaining 21 scenarios:
    "dual-ci-auth",
    "dual-ci-billing",
    "dual-ci-catalog",
    "dual-ci-gateway",
    "dual-ci-inventory",
    "dual-ci-notifications",
    "dual-ci-orders",
    "dual-ci-payments",
    "dual-ci-search",
    "empty-archive",
    "empty-handoff",
    "legacy-migration-billing",
    "legacy-migration-inventory",
    "legacy-migration-payroll",
    "python-docker-billing",
    "python-docker-inventory",
    "python-docker-invoices",
    "python-docker-payroll",
    "python-docker-reports",
    "python-dual-deps",
    "react-spa",
]
```

### Priority 4: Add End-to-End Fixture → View Tests (Medium Impact)

Create a test that loads multiple fixture scenarios into the database and then queries the reporting views to verify aggregate outputs are correct. This closes the final gap in the "predict impact" premise.

---

## File Map

| File / Directory | Purpose |
|-----------------|---------|
| `tests/fixtures/scenarios/generated/` | 27 generated fixture JSON files |
| `tests/fixtures/fixture_extractor.py` | FixtureExtractor test double |
| `tests/fixtures/sample_data.py` | Factory functions for hand-crafted test data |
| `tests/contract/integration/test_fixture_scenarios.py` | Fixture → storage pipeline tests (6 scenarios) |
| `tests/contract/database/test_reporting_views.py` | View correctness tests (22 views) |
| `database/migrations/011_add_reporting_views.sql` | 30 reporting view definitions |
| `dashboards/` | 9 Grafana dashboard JSON files |
| `scripts/generate-fixtures.sh` | Shell driver for the two-layer generation pipeline |
| `scripts/ollama-generate.py` | Ollama code generation driver |
| `scripts/validate-fixture-config.py` | Validates fixture config structure |
| `.ai/ollama-prompts/fixture-repo-seeds.md` | Prompt for Layer 1 (seed) generation |
| `.ai/ollama-prompts/fixture-repo-enrichment.md` | Prompt for Layer 2 (enrichment) generation |
| `DASHBOARD_VIEW_AUDIT.md` | Dashboard compliance audit report |
| `DASHBOARD_SQL_CORRECTIONS.md` | Exact SQL corrections for non-compliant dashboards |
