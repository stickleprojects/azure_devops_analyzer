# Plan 017: Security & Dependency Enrichment Tests Without Live APIs

## Status: READY TO IMPLEMENT

## Problem

The security dashboard (`dashboards/security-dashboard.json`) relies on several views:

- `v_security_overview_latest`
- `v_security_repository_overview`
- `v_security_top_vulnerable_dependencies`
- `v_security_top_repositories_critical_vulns`
- `v_security_eol_status_latest`
- `v_security_vulnerabilities_by_severity_latest`
- `v_repo_dependency_rollup_latest`
- `v_repo_vulnerabilities_by_severity_latest`
- `v_repo_vulnerability_details_latest`

All of these return empty results or zeros in CI because no enrichment is ever run —
the only existing enrichment tests (`test_dependency_enrichment_e2e.py`) call real
external APIs (OSV.dev, endoflife.date) and are marked `@pytest.mark.live_api`, so they
are excluded from CI with `-m "not live_api"`.

The current security coverage in `TestDashboardViewContracts` explicitly asserts zeros:

```
# No enrichment was performed, so all should be 0
assert row.total_vulnerabilities == 0
assert row.total_eol_deps == 0
```

This means the security views have never been verified to return correct non-zero results
in any automated test.

## Decision

Add a new test class `TestSecurityEnrichmentContractsE2E` to
`tests/contract/database/test_full_pipeline_e2e.py`.

**Key principle**: `store_package_metadata` and `store_repo_dependencies` are pure storage
functions that accept in-memory dataclasses — no HTTP calls, no fixture generation. All
enrichment data can be constructed inline using synthetic dicts, making these tests
fully CI-safe without any mocking.

The existing `@pytest.mark.live_api` tests in `test_dependency_enrichment_e2e.py` are
preserved as-is; they serve as smoke tests for real API connectivity and are run
manually or on release.

## Architecture

### Data flow (no external APIs)

```
Synthetic vuln dicts
       │
       ▼
store_package_metadata(session, "requests", "pypi", latest="2.31.0",
                        is_eol=False, vulns=[...])
       │
       ├─► packages table           (1 row per package)
       └─► vulnerabilities table    (N rows per CVE)

EnrichedDependency(package_name="requests", version="2.18.0",
                   has_known_vulnerabilities=True)
       │
       ▼
store_repo_dependencies(session, repo_id, [enriched_dep])
       │
       └─► repository_dependencies  (has_known_vulnerabilities=True)

All security views join these three tables → non-zero results
```

### Fixture strategy

Reuse repos from `DEPENDENCY_SCENARIOS` (they already have pypi deps stored).
Pick `"python-docker-billing"` as the enrichment target — simple, single-ecosystem,
deterministic.

Synthetic packages:

| Package  | Version (pinned) | Latest | CVEs                      | EOL?      |
| -------- | ---------------- | ------ | ------------------------- | --------- |
| requests | 2.18.0           | 2.31.0 | CVE-2018-18074 (HIGH)     | No        |
| urllib3  | 1.22             | 2.2.1  | CVE-2021-33503 (CRITICAL) | No        |
| certifi  | 2017.4.17        | 2024.2 | (none)                    | Yes (EOL) |

These are real CVEs/packages but the data is hard-coded — no API call.

## Implementation Steps

### Step 1 — Add imports at top of `test_full_pipeline_e2e.py`

```python
from src.database.storage import store_package_metadata, store_repo_dependencies
from src.analyzers.dependency_enricher import EnrichedDependency
```

Both are already importable; check existing imports to avoid duplicates
(`store_dependencies` is already imported, `store_package_metadata` and
`store_repo_dependencies` may not be).

### Step 2 — Add shared fixture data (module-level constants)

Add immediately after `DEPENDENCY_SCENARIOS`:

```python
# Synthetic enrichment data — deterministic, no external API calls
SYNTHETIC_PACKAGES = [
    {
        "package_name": "requests",
        "ecosystem": "pypi",
        "latest_version": "2.31.0",
        "is_eol": False,
        "eol_date": None,
        "vulnerabilities": [
            {
                "cve_id": "CVE-2018-18074",
                "osv_id": "GHSA-x84v-xcm2-53pg",
                "severity": "HIGH",
                "summary": "Redirect to non-HTTP schemes allows SSRF",
                "details": "Requests sends auth header to redirect targets",
                "fixed_in_versions": ["2.20.0"],
                "references": [],
            }
        ],
        "pinned_version": "2.18.0",
    },
    {
        "package_name": "urllib3",
        "ecosystem": "pypi",
        "latest_version": "2.2.1",
        "is_eol": False,
        "eol_date": None,
        "vulnerabilities": [
            {
                "cve_id": "CVE-2021-33503",
                "osv_id": "GHSA-q2q7-5pp4-w6pg",
                "severity": "CRITICAL",
                "summary": "ReDoS in URL parsing",
                "details": "Catastrophic backtracking in URL regular expression",
                "fixed_in_versions": ["1.26.5", "2.0.2"],
                "references": [],
            }
        ],
        "pinned_version": "1.22",
    },
    {
        "package_name": "certifi",
        "ecosystem": "pypi",
        "latest_version": "2024.2.2",
        "is_eol": True,
        "eol_date": date(2022, 5, 1),
        "vulnerabilities": [],
        "pinned_version": "2017.4.17",
    },
]
```

### Step 3 — Add `_enrich_scenario` helper

Add a module-level helper (not a fixture) for reuse within the new class:

```python
def _enrich_scenario(session, repo_id: str) -> None:
    """
    Store synthetic package metadata + per-repo enriched deps for `repo_id`.
    Covers 2 vulnerable packages (HIGH + CRITICAL) and 1 EOL package.
    """
    enriched_deps = []
    for pkg_data in SYNTHETIC_PACKAGES:
        store_package_metadata(
            session,
            package_name=pkg_data["package_name"],
            ecosystem=pkg_data["ecosystem"],
            latest_version=pkg_data["latest_version"],
            is_eol=pkg_data["is_eol"],
            eol_date=pkg_data.get("eol_date"),
            vulnerabilities=pkg_data["vulnerabilities"],
        )
        enriched_deps.append(
            EnrichedDependency(
                package_name=pkg_data["package_name"],
                version=pkg_data["pinned_version"],
                ecosystem=pkg_data["ecosystem"],
                is_dev_dependency=False,
                has_known_vulnerabilities=len(pkg_data["vulnerabilities"]) > 0,
            )
        )
    store_repo_dependencies(session, repo_id, enriched_deps)
    session.commit()
```

### Step 4 — Add `TestSecurityEnrichmentContractsE2E` class

Add after `TestDependencyEnrichmentPipelineE2E` (before `TestDashboardViewContracts`).

Tests to include:

#### 4a. `test_v_security_overview_latest_non_zero_after_enrichment`

```
CONTRACT: v_security_overview_latest reflects stored vulnerability and EOL data.
```

Calls `_load_scenario` + `_enrich_scenario`, then:

- `total_vulnerabilities >= 2` (CVE-2018-18074 + CVE-2021-33503)
- `total_eol_deps >= 1` (certifi)
- `repos_with_vulns >= 1`
- `repos_with_eol >= 1`

#### 4b. `test_v_security_repository_overview_per_repo_vuln_counts`

```
CONTRACT: v_security_repository_overview has correct severity breakdown for enriched repo.
```

Calls `_load_scenario("python-docker-billing")` + `_enrich_scenario`.

Checks the specific repo row:

- `critical_vulns >= 1` (urllib3 CVE-2021-33503 is CRITICAL)
- `high_vulns >= 1` (requests CVE-2018-18074 is HIGH)
- `eol_deps >= 1` (certifi)

#### 4c. `test_v_repo_dependency_rollup_latest_vulnerabilities_counted`

```
CONTRACT: v_repo_dependency_rollup_latest.vulnerabilities > 0 for the enriched repo.
```

Also verifies `outdated_dependencies >= 2` (requests 2.18.0 < 2.31.0, urllib3 1.22 < 2.2.1)
and `eol_dependencies >= 1`.

#### 4d. `test_v_security_top_vulnerable_dependencies_contains_urllib3`

```
CONTRACT: v_security_top_vulnerable_dependencies lists the most severe package first.
```

Asserts urllib3 appears in the result set with `severity = 'CRITICAL'`.

#### 4e. `test_v_repo_vulnerability_details_latest_has_cve_ids`

```
CONTRACT: v_repo_vulnerability_details_latest returns CVE IDs for the enriched repo.
```

Fetches rows for `repo_id`, checks `CVE-2018-18074` and `CVE-2021-33503` are present.

#### 4f. `test_v_security_eol_status_latest_shows_expired`

```
CONTRACT: v_security_eol_status_latest shows certifi as 'Expired'.
```

Fetches from `v_security_eol_status_latest`, checks that a row with `category = 'Expired'`
and `count >= 1` exists.

#### 4g. `test_v_repo_vulnerabilities_by_severity_latest_correct_severities`

```
CONTRACT: v_repo_vulnerabilities_by_severity_latest lists CRITICAL and HIGH for enriched repo.
```

Checks rows for the enriched repo include both 'CRITICAL' and 'HIGH'.

### Step 5 — Update `test_v_security_overview_latest_queryable_and_structured`

The existing test asserts zeros (correct for no-enrichment). Add an inline comment
clarifying its relationship to the new class:

```python
# This test verifies the view is queryable when no enrichment has been run.
# For non-zero enrichment coverage see TestSecurityEnrichmentContractsE2E.
```

No other changes to the existing test.

## Compatibility Notes

- `store_package_metadata` and `store_repo_dependencies` already exist and are stable
  (implemented in Plan 012).
- `EnrichedDependency` is already importable from `src.analyzers.dependency_enricher`.
- `date` (from `datetime`) is not currently imported in `test_full_pipeline_e2e.py`;
  add to the import block.
- Tests run within the `db_session` transaction-rollback scope — all synthetic data is
  rolled back after each test. No cross-test contamination.
- All new tests should be marked `@pytest.mark.integration` to match the class
  convention.

## Scope Boundary

This plan covers only CI-safe fixture-based enrichment tests.

Out of scope:

- Modifying or removing `test_dependency_enrichment_e2e.py` (live_api tests).
- Adding a new fixture scenario JSON file — SYNTHETIC_PACKAGES data is inline.
- Any changes to `store_package_metadata`, `store_repo_dependencies`, or the security
  views themselves.
- `v_security_vulnerability_trend` — this is a time-series view; because synthetic deps
  are inserted with `last_seen_at = NOW()`, it will produce rows, but asserting exact
  counts is date-sensitive. Query-without-error is sufficient here and is already
  covered by the broader view infrastructure.
- `v_security_top_repositories_critical_vulns` — covered transitively by
  `test_v_security_repository_overview_per_repo_vuln_counts` (same underlying join).

## Success Criteria

- All new tests run under `pytest -m "not live_api"` (CI gate).
- `v_security_overview_latest.total_vulnerabilities >= 2` asserted in CI.
- `v_security_overview_latest.total_eol_deps >= 1` asserted in CI.
- `v_repo_vulnerability_details_latest` returns named CVE IDs for an enriched repo.
- No external network calls in any new test.
- Existing tests continue to pass with no modifications to schema or fixtures.
