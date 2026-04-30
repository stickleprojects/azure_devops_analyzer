# Plan 024: Auth Error Taxonomy and Cross-View Consistency

_Last reviewed: 2026-04-30_

## Status: DESIGN (Ready for Implementation)

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

1. error_category (high-level, dashboard/stats)
2. error_subcategory (actionable diagnosis)

### High-level categories (error_category)

1. AUTH
2. RATE_LIMIT
3. PERMISSION
4. NETWORK
5. TIMEOUT
6. SERVICE_UNAVAILABLE
7. VALIDATION
8. NOT_FOUND
9. CONFLICT
10. DATA_INTEGRITY
11. PLATFORM_API
12. UNKNOWN

### Suggested auth-focused subcategories (error_subcategory)

1. AUTH_TOKEN_EXPIRED
2. AUTH_TOKEN_INVALID
3. AUTH_TOKEN_MISSING
4. AUTH_SCOPE_INSUFFICIENT
5. AUTH_ACCOUNT_DISABLED
6. AUTH_FORBIDDEN
7. AUTH_UNAUTHORIZED
8. AUTH_PERMISSION_DENIED

---

## Variant Mapping Plan

Create a normalized mapping table of error-message patterns to categories/subcategories, including case-insensitive variants and provider-specific wording.

### Initial auth pattern set

GitHub-like variants:

1. bad credentials
2. requires authentication
3. resource not accessible by integration
4. insufficient scopes
5. token has expired

Azure DevOps-like variants:

1. access denied
2. personal access token used has expired
3. vs30063
4. tf400813
5. not authorized to access this resource
6. permission denied

Generic HTTP/status variants:

1. 401
2. 403
3. unauthorized
4. forbidden
5. not authorized

---

## Architecture Proposal

Implement one canonical SQL classification component, then reuse everywhere.

Option A (preferred): normalized classifier view

1. Add view: v_extraction_runs_classified
2. Columns:
   - run_id, platform, status, updated_at, error_message
   - error_category
   - error_subcategory
   - is_auth_failure (boolean)
3. Implement classification via ordered CASE expressions in one place.

Then refactor consumers:

1. v_auth_errors_by_platform queries v_extraction_runs_classified where is_auth_failure = true
2. v_auth_errors_24h_total sums from v_auth_errors_by_platform
3. v_extraction_runs_recent exposes error_category/error_subcategory from classifier
4. v_extraction_metrics_with_errors aligns naming and categories with the same taxonomy

Option B: SQL function (alternative)

1. Add immutable/stable SQL function returning category/subcategory for a message
2. Use function from all reporting views

Tradeoff: function centralizes logic but can be harder to debug in dashboards.

---

## Consistency Rules

1. All run-level dashboard views must use the same error_category/error_subcategory semantics.
2. Auth summary stats must be based on classifier boolean (is_auth_failure), not custom text fragments.
3. Dashboard panel labels must reference taxonomy terms used in SQL output.
4. Any new category requires test updates in one canonical test module.

---

## Test Plan (Docker parity)

### Contract tests to add/update

1. tests/contract/database/test_reporting_views.py
   - add Azure DevOps expired PAT message case
   - add permission denied variant case
   - verify v_auth_errors_by_platform counts both GitHub and Azure variants
   - verify v_extraction_runs_recent and auth views agree on auth classification

2. New file: tests/contract/database/test_error_classification_taxonomy.py
   - table-driven tests for pattern variants -> expected category/subcategory
   - precedence tests (e.g., 403 + rate limit phrase maps to RATE_LIMIT, not AUTH)
   - unknown fallback tests

3. Optional integration: tests/contract/database/test_full_pipeline_e2e.py
   - include one scenario per major category to assert non-trivial dashboard outputs

### Required commands

1. bash scripts/run-tests-docker.sh tests/contract/database/test_reporting_views.py
2. bash scripts/run-tests-docker.sh tests/contract/database/test_error_classification_taxonomy.py
3. bash scripts/run-tests-docker.sh tests/contract/database/test_full_pipeline_e2e.py

---

## Dashboard/UX Recommendations

1. Keep Auth Failures panel scoped to AUTH categories only.
2. Add companion panel: Failures by Category (24h) to expose non-auth operational failures.
3. Add Recent Runs columns:
   - error_category
   - error_subcategory
4. Add quick help text in admin dashboard for category semantics.

---

## Migration Strategy

1. Add new migration:
   - create classifier view/function
   - update dependent views (CREATE OR REPLACE)
2. Preserve backward compatibility:
   - keep existing v_auth_errors_by_platform and v_auth_errors_24h_total names
   - only update internals to source canonical classifier
3. Ensure idempotency:
   - DO blocks, IF EXISTS/IF NOT EXISTS, CREATE OR REPLACE VIEW

---

## Risks and Mitigations

1. Risk: Over-broad pattern matching causes false positives.
   - Mitigation: ordered precedence rules + table-driven tests.
2. Risk: New provider error strings still uncategorized.
   - Mitigation: UNKNOWN bucket monitoring panel + periodic pattern updates.
3. Risk: Divergence between extraction_runs and extraction_metrics classification.
   - Mitigation: shared taxonomy tests and explicit cross-view consistency assertions.

---

## Acceptance Criteria

1. Azure DevOps expired PAT and permission-denied messages are counted in auth summary views.
2. v_auth_errors_by_platform non-empty when recent runs show auth-like failures.
3. Recent runs and auth summary use consistent category semantics.
4. Contract tests cover at least 10 auth message variants across providers.
5. All new/updated tests pass via Docker commands.

---

## Implementation Checklist

1. Add taxonomy classifier (view or function).
2. Refactor auth summary views to use classifier.
3. Align recent-run classification columns with taxonomy.
4. Add contract tests for variant mapping and cross-view consistency.
5. Add/refresh admin dashboard panel docs for category meaning.
6. Validate in Docker and include sample query outputs in PR.
