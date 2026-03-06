# Plan 016: SQL Reporting Views as the Testable Reporting Layer

## Status: READY TO IMPLEMENT

## Problem

Grafana dashboards currently embed 136+ raw SQL queries directly in 9 JSON files
(`dashboards/*.json`). This creates two problems:

1. **Drift risk** — any test that extracts SQL from JSON will silently fall out of sync when
   dashboards are edited in the Grafana UI or by hand.
2. **Duplication** — business logic ("what is an active contributor?", "what is an open PR?")
   is defined in 9 places simultaneously, making it impossible to test or reason about
   consistently.

## Decision

Move business logic SQL into **PostgreSQL views**. Grafana dashboards then use trivial queries
like `SELECT * FROM v_open_prs WHERE repo_id = '${repository}'`. The views are the single
source of truth and are directly testable with plain SQL.

The test DB is already PostgreSQL/TimescaleDB (confirmed via `tests/contract/integration/conftest.py`
and `tests/contract/database/conftest.py`), so views work immediately with the existing test
infrastructure.

We do **not** extract or test SQL from Grafana JSON — that path is abandoned entirely.

## Implementation Steps

### 1. Create `database/views.sql`

New file containing all reporting views. Cover the ~12 distinct business concepts that appear
across the 9 dashboards. Use `CREATE OR REPLACE VIEW` for idempotency.

Key views to create (based on query audit of all 9 dashboards):

```sql
-- Pull request status
CREATE OR REPLACE VIEW v_open_prs AS
    SELECT repo_id, COUNT(*) AS count
    FROM pull_requests WHERE status = 'open'
    GROUP BY repo_id;

CREATE OR REPLACE VIEW v_merged_prs_30d AS
    SELECT repo_id, COUNT(*) AS count
    FROM pull_requests
    WHERE status = 'merged' AND merged_at > NOW() - INTERVAL '30 days'
    GROUP BY repo_id;

CREATE OR REPLACE VIEW v_closed_prs_30d AS
    SELECT repo_id, COUNT(*) AS count
    FROM pull_requests
    WHERE status = 'closed' AND closed_at > NOW() - INTERVAL '30 days'
    GROUP BY repo_id;

-- Contributor activity
CREATE OR REPLACE VIEW v_active_contributors_30d AS
    SELECT repo_id, COUNT(DISTINCT author_id) AS count
    FROM commits
    WHERE commit_date > NOW() - INTERVAL '30 days'
    GROUP BY repo_id;

-- Repository summary (used by repository-overview, repository-deep-dive)
CREATE OR REPLACE VIEW v_repository_summary AS
    SELECT
        r.repo_id, r.name, r.is_active,
        COUNT(DISTINCT c.commit_sha)   AS total_commits,
        COUNT(DISTINCT pr.id)          AS total_prs,
        COUNT(DISTINCT rl.language)    AS language_count,
        MAX(c.commit_date)             AS last_commit_date
    FROM repositories r
    LEFT JOIN commits c              ON c.repo_id  = r.repo_id
    LEFT JOIN pull_requests pr       ON pr.repo_id = r.repo_id
    LEFT JOIN repository_languages rl ON rl.repo_id = r.repo_id
    GROUP BY r.repo_id, r.name, r.is_active;

-- Commits (30d)
CREATE OR REPLACE VIEW v_commits_30d AS
    SELECT repo_id, COUNT(*) AS count
    FROM commits
    WHERE commit_date > NOW() - INTERVAL '30 days'
    GROUP BY repo_id;

-- Language distribution per repo
CREATE OR REPLACE VIEW v_language_summary AS
    SELECT repo_id, language, percentage, byte_count
    FROM repository_languages;

-- PR size distribution (used by pull-requests.json)
CREATE OR REPLACE VIEW v_pr_size_distribution AS
    SELECT repo_id, size_category, COUNT(*) AS count
    FROM pull_requests
    WHERE size_category IS NOT NULL
    GROUP BY repo_id, size_category;
```

Additional views to cover `admin-dashboard.json` (extraction_runs) and
`contributor-analytics.json` (contributor-level aggregates) — audit those files during
implementation to catch anything missing.

### 2. Create `database/migrations/011_add_reporting_views.sql`

Thin wrapper that applies `views.sql` to existing databases:

```sql
-- Migration 011: Add reporting views for Grafana dashboards
-- Replaces embedded SQL in dashboard JSON files with testable PostgreSQL views.
\i database/views.sql
```

### 3. Update Grafana dashboards (incremental — start with most complex)

Priority order (by query count):
1. `repository-deep-dive.json` — 43 queries
2. `service-overview.json` — 24 queries
3. `team-overview.json` — 23 queries
4. `pull-requests.json` — 9 queries
5. Remaining 5 dashboards

For each panel, replace embedded SQL with a view reference. Example:

**Before:**
```sql
SELECT COUNT(DISTINCT author_id) as active_contributors
FROM commits WHERE commit_date > NOW() - INTERVAL '30 days'
```

**After:**
```sql
SELECT SUM(count) as active_contributors FROM v_active_contributors_30d
```

Panels needing repo-level filtering add `WHERE repo_id = '${repository}'` — trivial, not
business logic, so no further testing needed.

### 4. Create `tests/contract/database/test_reporting_views.py`

Uses the existing PostgreSQL test DB + `FixtureExtractor` pattern already established in
`tests/contract/integration/test_fixture_scenarios.py`.

```python
@pytest.mark.integration
class TestReportingViews:

    def test_v_open_prs_counts_correctly(self, test_session, organization):
        repo = _load_fixture(test_session, organization, "go-microservice")
        result = test_session.execute(
            text("SELECT count FROM v_open_prs WHERE repo_id = :rid"),
            {"rid": repo.repo_id}
        ).scalar_one()
        # Count open PRs from the fixture JSON directly
        expected = _count_fixture_prs("go-microservice", status="open")
        assert result == expected

    def test_v_merged_prs_30d_counts_correctly(self, ...): ...
    def test_v_repository_summary_includes_repo(self, ...): ...
    def test_v_active_contributors_30d_handles_future_dates(self, ...): ...
    # Note: fixture commit dates are 2025-2026, NOW() is 2026-03-06 — most within 30d window
    def test_v_open_prs_returns_zero_for_empty_stub(self, ...): ...
```

## Files to Create/Modify

| File | Action |
|---|---|
| `database/views.sql` | Create — all reporting views |
| `database/migrations/011_add_reporting_views.sql` | Create — migration |
| `dashboards/repository-deep-dive.json` | Update — replace embedded SQL |
| `dashboards/service-overview.json` | Update — replace embedded SQL |
| `dashboards/team-overview.json` | Update — replace embedded SQL |
| `dashboards/pull-requests.json` | Update — replace embedded SQL |
| `dashboards/*.json` (remaining 5) | Update — replace embedded SQL |
| `tests/contract/database/test_reporting_views.py` | Create — view tests |

## Verification

```bash
bash scripts/run-tests-docker.sh
```

Manual: start Grafana (`docker compose up grafana`), open each dashboard, confirm panels render.

## What We Are NOT Doing

- No extraction of SQL from Grafana JSON for testing
- No separate "Grafana test" file — once the views exist, dashboard SQL is too trivial to test
- No changes to the Python extraction layer or storage layer
