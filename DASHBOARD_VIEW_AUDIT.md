# Dashboard SQL Audit Report

## Checking Dashboard Queries Against Views

**Generated:** 2026-03-07

---

## Executive Summary

Analysis of all dashboard.json files reveals **mixed compliance** with the view layer:

- **Good:** pull-requests.json, admin-dashboard.json, most of team-overview.json
- **Issues:** contributor-analytics.json, dashboard-home.json, repository-overview.json need updates
- **Repo-specific:** repository-deep-dive.json correctly uses direct SQL for parameterized queries
- **Specialized:** service-overview.json, security-dashboard.json appropriately use direct table access

---

## Detailed Findings by Dashboard

### 1. ✅ pull-requests.json — COMPLIANT

All queries use the correct views:

- `v_open_prs_total` ✓
- `v_merged_prs_30d_total` ✓
- `v_closed_prs_30d_total` ✓
- `v_pr_avg_changes_30d` ✓
- `v_pr_status_distribution` ✓
- `v_pr_size_distribution_30d` ✓
- `v_pr_creation_daily_trend` ✓
- `v_pr_merge_daily_trend` ✓
- `v_pr_recent_details` ✓

**Status:** No changes needed.

---

### 2. ✅ admin-dashboard.json — MOSTLY COMPLIANT

Uses views appropriately:

- `v_extraction_runs_active` ✓
- `v_extraction_run_latest_progress` ✓
- `v_extraction_runs_recent` ✓
- `v_stale_repositories` ✓
- `v_unanalyzed_repositories` ✓
- `v_extraction_metrics_recent` ✓

Non-view queries are appropriate (TimescaleDB time_bucket function):

- `SELECT time_bucket('5 minutes', extraction_completed_at)...` (legitimate time-series query) ✓

**Status:** No changes needed.

---

### 3. ⚠️ contributor-analytics.json — NEEDS UPDATES

**Issues found:**

| Line | Current Query                                                                                                          | View Available                    | Recommended Change         |
| ---- | ---------------------------------------------------------------------------------------------------------------------- | --------------------------------- | -------------------------- |
| 121  | `SELECT COUNT(DISTINCT author_id) as active_contributors FROM commits WHERE commit_date > NOW() - INTERVAL '30 days';` | `v_active_contributors_30d_total` | Use view                   |
| 182  | `SELECT COUNT(*) as commits FROM commits WHERE commit_date > NOW() - INTERVAL '30 days';`                              | `v_commits_30d_total`             | Use view                   |
| 243  | `SELECT COUNT(*) as reviews FROM pr_reviews WHERE review_date > NOW() - INTERVAL '30 days';`                           | ❌ No view                        | Leave as-is or create view |

**Corrected queries:**

**Line 121:** Replace with:

```sql
SELECT contributors as active_contributors FROM v_active_contributors_30d_total;
```

**Line 182:** Replace with:

```sql
SELECT commits FROM v_commits_30d_total;
```

**Status:** 2 changes needed.

---

### 4. ⚠️ dashboard-home.json — NEEDS UPDATES

**Issues found:**

| Line | Current Query                                                                                                   | View Available                    | Recommended Change         |
| ---- | --------------------------------------------------------------------------------------------------------------- | --------------------------------- | -------------------------- |
| 103  | `SELECT COUNT(*) as total FROM repositories WHERE is_active = true;`                                            | `v_active_repositories_total`     | Use view                   |
| 164  | `SELECT COUNT(DISTINCT author_id) as contributors FROM commits WHERE commit_date > NOW() - INTERVAL '30 days';` | `v_active_contributors_30d_total` | Use view                   |
| 225  | `SELECT COUNT(*) as commits FROM commits WHERE commit_date > NOW() - INTERVAL '30 days';`                       | `v_commits_30d_total`             | Use view                   |
| 286  | `SELECT COUNT(*) as prs FROM pull_requests WHERE created_at > NOW() - INTERVAL '30 days';`                      | ❌ No view                        | Leave as-is or create view |
| 347  | `SELECT COUNT(*) as teams FROM teams;`                                                                          | ❌ No view                        | Leave as-is                |
| 408  | `SELECT COUNT(*) as open_prs FROM pull_requests WHERE status = 'open';`                                         | `v_open_prs_total`                | Use view                   |

**Corrected queries:**

**Line 103:** Replace with:

```sql
SELECT total FROM v_active_repositories_total;
```

**Line 164:** Replace with:

```sql
SELECT contributors FROM v_active_contributors_30d_total;
```

**Line 225:** Replace with:

```sql
SELECT commits FROM v_commits_30d_total;
```

**Line 408:** Replace with:

```sql
SELECT open_prs FROM v_open_prs_total;
```

**Status:** 4 changes needed.

---

### 5. ⚠️ repository-overview.json — NEEDS UPDATES

**Issues found:**

| Line          | Current Query                                                        | View Available                | Recommended Change         |
| ------------- | -------------------------------------------------------------------- | ----------------------------- | -------------------------- |
| 121           | `SELECT COUNT(*) as total FROM repositories WHERE is_active = true;` | `v_active_repositories_total` | Use view                   |
| 182           | `SELECT COUNT(*) as total FROM commits;`                             | ❌ No view                    | Leave as-is or create view |
| 243           | `SELECT COUNT(*) as total FROM pull_requests;`                       | ❌ No view                    | Leave as-is or create view |
| 304           | `SELECT COUNT(*) as total FROM contributors;`                        | ❌ No view                    | Leave as-is or create view |
| 394, 490, 586 | Various repo iteration queries                                       | N/A                           | Appropriate custom SQL     |

**Corrected queries:**

**Line 121:** Replace with:

```sql
SELECT total FROM v_active_repositories_total;
```

**Status:** 1 change needed (others are domain-specific queries).

---

### 6. ⚠️ team-overview.json — PARTIAL ISSUES

**Issues found:**

| Line          | Current Query                                                                                 | View Available           | Recommended Change         |
| ------------- | --------------------------------------------------------------------------------------------- | ------------------------ | -------------------------- |
| 132, 191, 250 | Using `v_active_repositories_total`, `v_active_contributors_30d_total`, `v_commits_30d_total` | ✓                        | **CORRECT**                |
| 309           | `SELECT COUNT(*) as prs FROM pull_requests WHERE created_at > NOW() - INTERVAL '30 days';`    | ❌ No view               | Leave as-is or create view |
| 368           | `SELECT COUNT(*) as merged FROM pull_requests WHERE merged_at > NOW() - INTERVAL '30 days';`  | `v_merged_prs_30d_total` | Use view                   |
| 427           | `SELECT COUNT(*) as open_prs FROM pull_requests WHERE status = 'open';`                       | `v_open_prs_total`       | Use view                   |

**Corrected queries:**

**Line 368:** Replace with:

```sql
SELECT merged_prs as merged FROM v_merged_prs_30d_total;
```

**Line 427:** Replace with:

```sql
SELECT open_prs FROM v_open_prs_total;
```

**Status:** 2 changes needed (team-filtered queries at lines 530, 651, 663 are correctly contextual).

---

### 7. ✅ repository-deep-dive.json — APPROPRIATE FOR PARAMETERIZED QUERIES

All queries are **correctly parameterized** with `${repository}` variable filters. These queries:

- Select data for a specific repository
- Use time-series aggregations
- Fetch code quality and dependency metrics

**Verdict:** No changes needed — direct table queries are appropriate here since views are global aggregates.

---

### 8. ✅ service-overview.json — APPROPRIATE FOR SERVICE METRICS

Queries target `service_metrics`, `service_languages`, and `vulnerabilities` tables. These:

- Aggregate across services
- Use service_metrics pre-aggregated data
- Handle time-filtered metrics

**Verdict:** No changes needed — service metrics have their own aggregation strategy.

---

### 9. ✅ security-dashboard.json — APPROPRIATE FOR SECURITY ANALYSIS

Queries directly join `vulnerabilities`, `dependencies`, and `repositories` to:

- Identify CVE severity distribution
- Track EOL module timelines
- Report per-repository security metrics

**Verdict:** No changes needed — security drill-down requires direct access to detailed data.

---

## Summary of Required Changes

### High Priority (Metric Accuracy)

| Dashboard                  | Line(s)            | Change Type                                                                                             | Impact                                    |
| -------------------------- | ------------------ | ------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| contributor-analytics.json | 121, 182           | Use v_active_contributors_30d_total, v_commits_30d_total                                                | Consistency with reporting layer          |
| dashboard-home.json        | 103, 164, 225, 408 | Use v_active_repositories_total, v_active_contributors_30d_total, v_commits_30d_total, v_open_prs_total | Single source of truth for home dashboard |
| repository-overview.json   | 121                | Use v_active_repositories_total                                                                         | Consistency                               |
| team-overview.json         | 368, 427           | Use v_merged_prs_30d_total, v_open_prs_total                                                            | Consistency across dashboards             |

### Missing Views (Consider Creating)

1. **v_prs_created_30d_total** — Count of PRs created (not merged) in last 30 days
   - Used by: dashboard-home.json (line 286), team-overview.json (line 309)
   - Current: Raw table query

2. **v_pr_reviews_30d_total** — Count of PR reviews in last 30 days
   - Used by: contributor-analytics.json (line 243)
   - Current: Raw table query

3. **v_total_commits_all_time** — Total commit count (all time)
   - Used by: repository-overview.json (line 182)
   - Current: Raw table query

4. **v_total_pull_requests_all_time** — Total PR count (all time)
   - Used by: repository-overview.json (line 243)
   - Current: Raw table query

5. **v_total_contributors_all_time** — Total contributor count (all time)
   - Used by: repository-overview.json (line 304)
   - Current: Raw table query

---

## Recommendations

1. **Immediate Actions** (Current Sprint)
   - Update 6 dashboard queries to use existing views (see table above)
   - Ensure column name consistency (e.g., `active_contributors` vs raw column names)

2. **Short-term Actions** (Next Sprint)
   - Create the 5 missing views listed above
   - Update remaining dashboard queries to use new views
   - Add index on `created_at`, `merged_at`, `commit_date` in source tables for view performance

3. **Ongoing Maintenance**
   - All new dashboard metrics should use views first
   - Views become the contract between application and reporting layer
   - Single source of truth prevents divergent calculations
