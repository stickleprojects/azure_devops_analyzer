# Plan 024: Auth Error Taxonomy and Cross-View Consistency

_Last reviewed: 2026-05-25_

## Status: COMPLETE ✅ (Implemented — PR #100, merged 2026-05-25)

**Motivation**: Admin dashboard auth panels can show blank results while recent-run panels show obvious auth failures, due to message-pattern drift and inconsistent classification rules across views.

---

## Problem Statement

Current reporting uses inline text matching in multiple places, with different rules per view. This causes semantic drift.

Observed example:

- Recent runs shows Azure DevOps failures like: Access Denied: The Personal Access Token used has expired.
- Auth summary panels are blank because auth filters only match a narrow phrase list (401/403/bad credentials/unauthorized/etc.).

Result: same underlying failures are classified as OTHER_ERROR in one view and excluded in another.

---

## Goals

1. Define one canonical error-classification taxonomy for extraction failures.
2. Map common platform error-message variants (GitHub + Azure DevOps) into stable categories.
3. Ensure all dashboard-facing views use the same classification logic.
4. Add contract tests that prevent classification drift.
5. Keep SQL and dashboard routing simple: dashboards query reporting views, not ad-hoc raw SQL.

---

## Non-Goals

1. Rewriting extraction error handling internals in this plan.
2. Building a full anomaly-detection system.
3. Historical backfill beyond what is needed for dashboard correctness.

---

## Proposed Taxonomy

Use two-level classification:

1. `error_category` — high-level bucket (used for dashboard stats and panel filtering)
2. `error_subcategory` — actionable diagnosis (used for drill-down and alerting)

### High-level categories (`error_category`)

| Category           | Meaning                                          |
| ------------------ | ------------------------------------------------ |
| AUTH               | *Who are you?* Credential / identity failures    |
| PERMISSION         | *You are known, but cannot do this.* Authorization failures |
| RATE_LIMIT         | Quota or throttle imposed by the API             |
| NETWORK            | Connectivity or DNS failure                      |
| TIMEOUT            | Request exceeded time budget                     |
| SERVICE_UNAVAILABLE| Upstream API temporarily down (5xx)              |
| NOT_FOUND          | Resource does not exist (404)                    |
| VALIDATION         | Malformed request or schema mismatch (422)       |
| CONFLICT           | Concurrent modification or duplicate (409)       |
| DATA_INTEGRITY     | Inconsistent or corrupted data returned          |
| PLATFORM_API       | Unclassified upstream API error                  |
| UNKNOWN            | Catch-all — no pattern matched                   |

### Auth subcategories (`error_subcategory` where `error_category = 'AUTH'`)

These cover credential / identity failures only (*authn*):

| Subcategory       | Trigger                                       |
| ----------------- | --------------------------------------------- |
| AUTH_TOKEN_MISSING | No token present in request                  |
| AUTH_TOKEN_INVALID | Token present but rejected (bad credentials) |
| AUTH_TOKEN_EXPIRED | Token was valid but has since expired        |
| AUTH_UNAUTHORIZED  | Raw 401 with no clearer signal               |

### Permission subcategories (`error_subcategory` where `error_category = 'PERMISSION'`)

These cover authorization failures (*authz* — identity confirmed, action denied):

| Subcategory                 | Trigger                                               |
| --------------------------- | ----------------------------------------------------- |
| PERMISSION_SCOPE_INSUFFICIENT | Token lacks required OAuth/PAT scope               |
| PERMISSION_FORBIDDEN         | Raw 403 with no clearer signal                     |
| PERMISSION_RESOURCE_DENIED   | Azure DevOps `access denied`, `not authorized to access this resource`, `vs30063` |
| PERMISSION_ACCOUNT_DISABLED  | Account suspended or deleted                       |

Dashboard panels can show combined auth+permission coverage by filtering
`error_category IN ('AUTH', 'PERMISSION')`. Panels that need finer slices use
the two boolean helper columns (`is_credential_failure`, `is_authorization_failure`)
rather than re-implementing the rule in panel SQL.

---

## Variant Mapping Plan

A table-driven mapping translates raw error-message patterns into
`(error_category, error_subcategory)` pairs. Every row in the table has
a corresponding test.

### Pattern table (initial set)

| Pattern (case-insensitive)                            | error_category | error_subcategory              |
| ----------------------------------------------------- | -------------- | ------------------------------ |
| `bad credentials`                                     | AUTH           | AUTH_TOKEN_INVALID             |
| `requires authentication`                             | AUTH           | AUTH_UNAUTHORIZED              |
| `token has expired`                                   | AUTH           | AUTH_TOKEN_EXPIRED             |
| `personal access token used has expired`              | AUTH           | AUTH_TOKEN_EXPIRED             |
| `no token` / `missing token` / `token not provided`  | AUTH           | AUTH_TOKEN_MISSING             |
| `401` (raw, no clearer signal)                        | AUTH           | AUTH_UNAUTHORIZED              |
| `resource not accessible by integration`              | PERMISSION     | PERMISSION_SCOPE_INSUFFICIENT  |
| `insufficient scopes`                                 | PERMISSION     | PERMISSION_SCOPE_INSUFFICIENT  |
| `access denied`                                       | PERMISSION     | PERMISSION_RESOURCE_DENIED     |
| `not authorized to access this resource`              | PERMISSION     | PERMISSION_RESOURCE_DENIED     |
| `vs30063`                                             | PERMISSION     | PERMISSION_RESOURCE_DENIED     |
| `tf400813`                                            | PERMISSION     | PERMISSION_RESOURCE_DENIED     |
| `permission denied`                                   | PERMISSION     | PERMISSION_FORBIDDEN           |
| `forbidden`                                           | PERMISSION     | PERMISSION_FORBIDDEN           |
| `403` (raw, no clearer signal)                        | PERMISSION     | PERMISSION_FORBIDDEN           |
| `not authorized` (generic)                            | PERMISSION     | PERMISSION_FORBIDDEN           |
| `account disabled` / `account suspended`              | PERMISSION     | PERMISSION_ACCOUNT_DISABLED    |
| `rate limit` / `secondary rate limit` / `x-ratelimit` | RATE_LIMIT    | *(none)*                       |
| `abuse detection`                                     | RATE_LIMIT     | *(none)*                       |
| `connection reset` / `connection refused`             | NETWORK        | *(none)*                       |
| `temporary failure in name resolution`                | NETWORK        | *(none)*                       |
| `timed out` / `timeout`                               | TIMEOUT        | *(none)*                       |
| `502` / `503` / `504` / `service unavailable`         | SERVICE_UNAVAILABLE | *(none)*                  |
| `404` / `not found`                                   | NOT_FOUND      | *(none)*                       |
| `422` / `unprocessable`                               | VALIDATION     | *(none)*                       |
| *(no pattern matched)*                                | UNKNOWN        | *(none)*                       |

---

## Architecture: Option B — SQL classifier function

A `STABLE` SQL function is the canonical single source of classification logic.
This supersedes the earlier Option A (base view).

**Why Option B:**

- **Composability** — every existing view calls it inline; no view dependency chain.
- **Schema evolution safety** — adding a column does not require ordering `CREATE OR REPLACE` across all dependent views.
- **Testability** — the classifier can be unit-tested directly (`SELECT classify_extraction_error('Access Denied: ...')`), independent of the runs table.
- **Single-row semantics** — classification is intrinsically a per-row pure function; a function expresses that accurately.

### Function signature

```sql
-- classify_extraction_error(error_message)
--   Maps a raw error message string to its canonical taxonomy fields.
--   Returns one row; callers spread it with (classify_extraction_error(col)).*.
--   STABLE (not IMMUTABLE): pattern rules may evolve without cache invalidation.
CREATE OR REPLACE FUNCTION classify_extraction_error(error_message text)
RETURNS TABLE (
  error_category           text,
  error_subcategory        text,
  is_credential_failure    boolean,   -- true when error_category = 'AUTH'
  is_authorization_failure boolean    -- true when error_category = 'PERMISSION'
)
LANGUAGE sql
STABLE     -- allows pattern evolution without invalidating planner caches
PARALLEL SAFE
AS $$
  SELECT
    category,
    subcategory,
    category = 'AUTH',
    category = 'PERMISSION'
  FROM classify_extraction_error_internal(error_message);
$$;
```

### Consumer pattern

All reporting views call the function inline:

```sql
SELECT
  r.*,
  (classify_extraction_error(r.error_message)).*
FROM extraction_runs r;
```

---

## Precedence Rules

The classifier applies patterns in the following **strict order**. The first
matching rule wins; lower rules are not evaluated.

| Priority | Category            | Matching signals                                                            |
| -------- | ------------------- | --------------------------------------------------------------------------- |
| 1        | RATE_LIMIT          | `rate limit`, `secondary rate limit`, `abuse detection`, `x-ratelimit-remaining: 0` |
| 2        | NETWORK             | `connection reset`, `connection refused`, `temporary failure in name resolution` |
| 3        | TIMEOUT             | `timed out`, `timeout`, `read timeout`, `connect timeout`                  |
| 4        | SERVICE_UNAVAILABLE | `502`, `503`, `504`, `service unavailable`, `bad gateway`                  |
| 5        | AUTH                | token-implicating phrases (`bad credentials`, `token has expired`, `requires authentication`, `401`, …) |
| 6        | PERMISSION          | resource-implicating phrases (`access denied`, `insufficient scopes`, `forbidden`, `403`, …) |
| 7        | NOT_FOUND           | `404`, `not found`                                                         |
| 8        | VALIDATION          | `422`, `unprocessable`                                                      |
| 9        | UNKNOWN             | Catch-all fallback — no earlier rule matched                               |

Key precedence decisions made explicit:

- `403` + rate-limit phrase → **RATE_LIMIT** (rule 1 wins over rule 6)
- `403` + `access denied` phrase → **PERMISSION/PERMISSION_RESOURCE_DENIED** (rule 6)
- `403` with no further signal → **PERMISSION/PERMISSION_FORBIDDEN**
- `connection reset` during token fetch → **NETWORK** (rule 2 wins over rule 5)

---

## View Inventory

The following views are in-scope for refactoring. Each must call `classify_extraction_error` after the migration.

| View name                        | Introduced by migration | Migration strategy  | Current status |
| -------------------------------- | ----------------------- | ------------------- | -------------- |
| `v_auth_errors_by_platform`      | To be verified          | `CREATE OR REPLACE` | Exists — uses ad-hoc text matching |
| `v_auth_errors_24h_total`        | To be verified          | `CREATE OR REPLACE` | Exists — aggregates `v_auth_errors_by_platform` |
| `v_extraction_runs_recent`       | To be verified          | `CREATE OR REPLACE` | Exists — no error_category column yet |
| `v_extraction_metrics_with_errors` | To be verified        | `CREATE OR REPLACE` | Exists — aligned naming needed |

> **Pre-implementation gate**: Run `\dv *auth*; \dv *extraction*` in psql to confirm
> exact names before writing migration SQL. Update this table if actual names differ.

The new migration will also create:

| View / object                       | Purpose                                            |
| ----------------------------------- | -------------------------------------------------- |
| `classify_extraction_error` (func)  | Canonical classifier — single source of truth      |
| `v_extraction_errors_unknown_recent`| UNKNOWN-bucket monitoring — rows from last 7 days grouped by message prefix |

---

## Unknown-Bucket Monitoring

To close the loop on new uncategorized error strings:

1. Add view `v_extraction_errors_unknown_recent`:

   ```sql
   CREATE OR REPLACE VIEW v_extraction_errors_unknown_recent AS
   SELECT
     date_trunc('day', updated_at) AS day,
     left(error_message, 80)       AS message_prefix,
     count(*)                      AS occurrences
   FROM extraction_runs,
        LATERAL classify_extraction_error(error_message) c
   WHERE c.error_category = 'UNKNOWN'
     AND updated_at >= now() - interval '7 days'
   GROUP BY 1, 2
   ORDER BY occurrences DESC;
   ```

2. Add a Grafana panel **"Unrecognized Error Patterns (last 7 days)"** sourcing this view.

---

## Consistency Rules

1. All run-level dashboard views must expose `error_category` and `error_subcategory` columns sourced from `classify_extraction_error`.
2. Auth summary stats must use `is_credential_failure` or `is_authorization_failure` flags, not custom text fragments.
3. Dashboard panel label strings must reference taxonomy terms used in SQL output.
4. Any new category/subcategory requires a pattern added to the classifier **and** a test row added to the parametrised test.

---

## Test Plan (Docker parity)

### Contract tests to add/update

1. **`tests/contract/database/test_reporting_views.py`**
   - Add Azure DevOps expired PAT message case
   - Add permission denied variant case
   - Verify `v_auth_errors_by_platform` counts both GitHub and Azure variants
   - Verify `v_extraction_runs_recent` and auth views agree on classification

2. **`tests/contract/database/test_error_classification_taxonomy.py`** (new)
   - Parametrised test reading every row from the canonical pattern table
   - Each row asserts `(input_message → expected_category, expected_subcategory)`
   - Test **fails** if a pattern is added to the classifier without a corresponding test row
   - Precedence tests: e.g. `403 + "rate limit"` → `RATE_LIMIT`, not `PERMISSION`
   - Unknown fallback tests: unrecognised message → `UNKNOWN`

3. **`tests/contract/database/test_full_pipeline_e2e.py`** (update)
   - Include one scenario per major category (AUTH, PERMISSION, RATE_LIMIT, NETWORK, UNKNOWN)
   - Assert that `v_extraction_errors_unknown_recent` is non-empty when seeded with an unrecognised message

### Required commands

```bash
bash scripts/run-tests-docker.sh tests/contract/database/test_reporting_views.py
bash scripts/run-tests-docker.sh tests/contract/database/test_error_classification_taxonomy.py
bash scripts/run-tests-docker.sh tests/contract/database/test_full_pipeline_e2e.py
```

---

## Dashboard/UX Recommendations

1. **Auth Failures panel**: filter `error_category = 'AUTH'`.
2. **Authorization Failures panel** (new): filter `error_category = 'PERMISSION'`.
3. **Combined credential+authz panel**: filter `error_category IN ('AUTH', 'PERMISSION')`.
4. **Failures by Category (24h)** panel: expose all categories via `GROUP BY error_category`.
5. **Unrecognized Error Patterns** panel: source `v_extraction_errors_unknown_recent`.
6. **Recent Runs table**: add `error_category` and `error_subcategory` columns.
7. Add quick-help text in admin dashboard explaining category semantics.

---

## Migration Strategy

1. Add new migration:
   - Create `classify_extraction_error` function
   - `CREATE OR REPLACE` for all four existing views (add `error_category`, `error_subcategory`, `is_credential_failure`, `is_authorization_failure` columns)
   - Create `v_extraction_errors_unknown_recent`
2. Preserve backward compatibility:
   - Keep existing view names (`v_auth_errors_by_platform`, `v_auth_errors_24h_total`, etc.)
   - Only update internals to call the canonical classifier
3. Ensure idempotency:
   - `CREATE OR REPLACE FUNCTION`, `CREATE OR REPLACE VIEW`, `DO $$ IF NOT EXISTS $$`

---

## Risks and Mitigations

1. **Risk**: Over-broad pattern matching causes false positives.
   - Mitigation: ordered precedence rules + exhaustive table-driven tests for every pattern.
2. **Risk**: New provider error strings still uncategorized.
   - Mitigation: `v_extraction_errors_unknown_recent` view + Grafana panel surfaces new unknowns within 7 days. Acceptance criterion requires panel to be non-empty when seeded with an unrecognised message.
3. **Risk**: Divergence between `extraction_runs` and `extraction_metrics` classification.
   - Mitigation: shared classifier function; both views call same function; cross-view consistency assertions in contract tests.
4. **Risk**: View name drift — plan names a view that no longer exists.
   - Mitigation: pre-implementation gate requires running `\dv` to verify names; view inventory table updated before migration is written.

---

## Acceptance Criteria

1. Azure DevOps expired PAT and permission-denied messages are counted in auth/permission summary views under the correct category and subcategory.
2. `v_auth_errors_by_platform` is non-empty when recent runs contain auth-like or permission-like failures.
3. Recent runs and auth/permission summary views use consistent `error_category` / `error_subcategory` semantics sourced from `classify_extraction_error`.
4. **Every pattern enumerated in the Variant Mapping section has a corresponding parametrised test row asserting its expected `error_category` and `error_subcategory`. The test suite fails if a pattern is added to the classifier without a matching test row.**
5. All new/updated tests pass via Docker commands listed in the Test Plan.
6. `v_extraction_errors_unknown_recent` view exists and the Grafana panel **"Unrecognized Error Patterns (last 7 days)"** is present. The panel is non-empty when the contract test suite seeds an unrecognised error message.
7. `is_credential_failure` and `is_authorization_failure` boolean columns are present on all consumer views; no consumer view re-implements auth/permission classification inline.

---

## Implementation Checklist

1. Verify view names against live schema (`\dv *auth*; \dv *extraction*`); update View Inventory table.
2. Add migration: create `classify_extraction_error` function with all patterns in precedence order.
3. Refactor `v_auth_errors_by_platform` and `v_auth_errors_24h_total` to call classifier.
4. Refactor `v_extraction_runs_recent` to add `error_category`, `error_subcategory`, `is_credential_failure`, `is_authorization_failure`.
5. Align `v_extraction_metrics_with_errors` with taxonomy.
6. Create `v_extraction_errors_unknown_recent` view.
7. Add `test_error_classification_taxonomy.py` with all pattern rows (table-driven, parametrised).
8. Update `test_reporting_views.py` with cross-view consistency assertions.
9. Update `test_full_pipeline_e2e.py` with unknown-bucket seeding scenario.
10. Add/refresh Grafana admin dashboard panels (auth, permission, unknown).
11. Validate all tests pass in Docker and include sample query outputs in PR.

