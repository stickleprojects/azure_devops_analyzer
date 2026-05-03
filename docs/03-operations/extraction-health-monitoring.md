# Extraction Health Monitoring

*Plan 020 Component 3 — Production Observability*

## Overview

After every successful extraction batch (GitHub or Azure DevOps), the system
runs a set of named **database invariants** against the live database and logs
any violations.  Results are also persisted to the `extraction_health_log`
table so that the **Extraction Health** Grafana dashboard can show current
status and a 7-day trend.

The invariant definitions live in **`tests/db_invariants.sql`** — a single
source of truth consumed by both the CI test suite (Plan 019) and this
production health check.  Adding an invariant to that file automatically adds
it to both CI and the production check without any code changes.

---

## What Each Invariant Means

| Invariant name | What it detects | Typical root cause |
|---|---|---|
| `no_case_variant_contributor_twins` | Two `contributors` rows share the same normalised email (lower+trim) | Email normalisation bug or race condition during concurrent upserts |
| `no_orphan_pr_author_fk` | A `pull_requests` row has a non-null `author_id` that doesn't resolve to a `contributors` row | Contributor deleted after PR was stored; storage ordering issue |
| `no_orphan_pr_reviewer_fk` | A `pr_reviews` row has a null or unresolvable `reviewer_id` | Reviewer data missing from API response; storage ordering issue |
| `no_duplicate_pr_per_repo` | Two `pull_requests` rows share `(repo_id, pr_number)` | Idempotency failure; unique constraint missing |
| `no_duplicate_commit_per_repo` | Two `commits` rows share `(repo_id, commit_sha)` | Idempotency failure; unique constraint missing |
| `no_review_before_pr_created` | A `pr_reviews.review_date` is earlier than the parent PR's `created_at` | Timezone handling bug; API returning inconsistent dates |
| `no_orphan_repo_dependency` | A `repository_dependencies` row references a non-existent `repositories` row | Storage ordering issue; migration not applied |
| `no_vulnerability_without_package` | A `vulnerabilities` row has a `package_id` that doesn't resolve to a `packages` row | Migration 014 not applied; enrichment ordering issue |

---

## What to Do When a Violation Fires

### 1. Identify the invariant

Check the `extraction_health_log` table or the Grafana **Extraction Health**
dashboard (`/d/extraction-health`).  The `sample_rows` column contains up to 5
example rows from the violation query, which pinpoints the affected data.

```sql
SELECT platform, repo_id, invariant_name, violations, sample_rows, checked_at
FROM   extraction_health_log
WHERE  violations > 0
ORDER  BY checked_at DESC
LIMIT  20;
```

### 2. Assess severity

| Violations | Action |
|---|---|
| 1–5 | Investigate but not urgent — likely a one-off edge case |
| > 5 | Treat as production incident; extraction may be creating bad data continuously |

### 3. Remediation paths by invariant

**`no_case_variant_contributor_twins`**

```sql
-- Find the twins
SELECT lower(trim(email)) AS email_key, count(*), array_agg(id)
FROM contributors
GROUP BY lower(trim(email))
HAVING count(*) > 1;

-- Merge: update FK references to the canonical id, then delete the duplicate
BEGIN;
UPDATE pull_requests SET author_id = <canonical_id> WHERE author_id = <dupe_id>;
UPDATE pr_reviews    SET reviewer_id = <canonical_id> WHERE reviewer_id = <dupe_id>;
DELETE FROM contributors WHERE id = <dupe_id>;
COMMIT;
```

**`no_orphan_pr_author_fk` / `no_orphan_pr_reviewer_fk`**

Examine the sample rows.  If the contributor truly no longer exists on the
platform, set `author_id = NULL` (allowed by schema).  If it is a storage
ordering bug, re-run the extraction for the affected repository.

**`no_duplicate_pr_per_repo` / `no_duplicate_commit_per_repo`**

```sql
-- Find the duplicates
SELECT repo_id, pr_number, count(*), array_agg(id)
FROM pull_requests
GROUP BY repo_id, pr_number
HAVING count(*) > 1;

-- Keep the row with the higher id (most recently upserted), delete the older one
BEGIN;
DELETE FROM pull_requests
WHERE id IN (
  SELECT id FROM (
    SELECT id, ROW_NUMBER() OVER (PARTITION BY repo_id, pr_number ORDER BY id DESC) AS rn
    FROM pull_requests
  ) t WHERE rn > 1
);
COMMIT;
```

**`no_review_before_pr_created`**

Likely a timezone bug.  Check the raw API response for the affected PR and
review.  If the dates are actually correct (rare), set `review_date =
created_at` as a floor.  If it is a bug in the extractor, fix the extractor
and re-run the affected repository.

**`no_orphan_repo_dependency` / `no_vulnerability_without_package`**

Verify the relevant migration has been applied:

```sql
SELECT version FROM schema_migrations ORDER BY version;
```

If `019` (or the relevant migration) is missing, run:

```bash
bash docker/scripts/run_migrations.sh
```

---

## How to Add a New Invariant

1. Open `tests/db_invariants.sql`.
2. Add a comment block at the end of the file:

   ```sql
   -- invariant: your_invariant_name
   -- Optional description of what this invariant detects.
   SELECT <columns that identify violating rows>
   FROM   <table>
   WHERE  <violation condition>;
   ```

3. If the invariant depends on a table that may not exist in all deployments,
   add a `requires-table` annotation:

   ```sql
   -- invariant: your_invariant_name
   -- requires-table: the_optional_table
   SELECT ...
   ```

   The health check will skip this invariant gracefully when the table does
   not exist (e.g. older migration sets).

4. Run the test suite to verify CI picks up the new invariant:

   ```bash
   bash scripts/run-tests-docker.sh tests/contract/database/test_extraction_health_integration.py
   ```

5. The production health check automatically picks up the new invariant on
   the next extraction — no code changes needed.

---

## Architecture Notes

* **`src/utils/extraction_health.py`** — Parses `tests/db_invariants.sql`,
  runs each query, returns a `HealthReport` dataclass.  Read-only; never
  writes to the database.
* **`src/utils/metrics.py`** — Emits structured log lines and persists results
  to `extraction_health_log` for Grafana.  Failures are logged as warnings and
  swallowed — a bug here cannot crash an extraction.
* **`extraction_health_log` table** — Created by migration 019.  One row per
  invariant per extraction run.
* **`dashboards/extraction-health.json`** — Grafana dashboard (`/d/extraction-health`).
  Queries `extraction_health_log` directly via the TimescaleDB datasource.

The health call in the workflow is wrapped in a broad `try/except` that logs
and swallows any exception.  This is intentional — observability must never
crash production.  If the health check raises unexpectedly, a `WARNING` log
line is emitted with the error details.
