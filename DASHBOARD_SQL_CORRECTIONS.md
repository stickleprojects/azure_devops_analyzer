# Dashboard SQL Corrections Reference

## Exact Changes Required

---

## 1. contributor-analytics.json

### Change 1: Line 121

**Current (INCORRECT):**

```sql
SELECT COUNT(DISTINCT author_id) as active_contributors
FROM commits
WHERE commit_date > NOW() - INTERVAL '30 days';
```

**Correct:**

```sql
SELECT contributors as active_contributors
FROM v_active_contributors_30d_total;
```

**Reason:** View `v_active_contributors_30d_total` already computes this metric with guaranteed consistency across dashboards.

---

### Change 2: Line 182

**Current (INCORRECT):**

```sql
SELECT COUNT(*) as commits
FROM commits
WHERE commit_date > NOW() - INTERVAL '30 days';
```

**Correct:**

```sql
SELECT commits
FROM v_commits_30d_total;
```

**Reason:** View `v_commits_30d_total` provides single source of truth for this metric.

---

## 2. dashboard-home.json

### Change 1: Line 103

**Current (INCORRECT):**

```sql
SELECT COUNT(*) as total FROM repositories WHERE is_active = true;
```

**Correct:**

```sql
SELECT total FROM v_active_repositories_total;
```

**Reason:** View `v_active_repositories_total` computed specifically for this metric.

---

### Change 2: Line 164

**Current (INCORRECT):**

```sql
SELECT COUNT(DISTINCT author_id) as contributors FROM commits WHERE commit_date > NOW() - INTERVAL '30 days';
```

**Correct:**

```sql
SELECT contributors FROM v_active_contributors_30d_total;
```

**Reason:** Single source of truth for active contributor count.

---

### Change 3: Line 225

**Current (INCORRECT):**

```sql
SELECT COUNT(*) as commits FROM commits WHERE commit_date > NOW() - INTERVAL '30 days';
```

**Correct:**

```sql
SELECT commits FROM v_commits_30d_total;
```

**Reason:** Ensures consistency with other dashboards tracking commits.

---

### Change 4: Line 408

**Current (INCORRECT):**

```sql
SELECT COUNT(*) as open_prs FROM pull_requests WHERE status = 'open';
```

**Correct:**

```sql
SELECT open_prs FROM v_open_prs_total;
```

**Reason:** View `v_open_prs_total` ensures this critical metric is consistent across dashboards.

---

## 3. repository-overview.json

### Change 1: Line 121

**Current (INCORRECT):**

```sql
SELECT COUNT(*) as total FROM repositories WHERE is_active = true;
```

**Correct:**

```sql
SELECT total FROM v_active_repositories_total;
```

**Reason:** Consistency with dashboard-home.json and team-overview.json.

---

## 4. team-overview.json

### Change 1: Line 368

**Current (INCORRECT):**

```sql
SELECT COUNT(*) as merged
FROM pull_requests
WHERE merged_at > NOW() - INTERVAL '30 days';
```

**Correct:**

```sql
SELECT merged_prs as merged
FROM v_merged_prs_30d_total;
```

**Reason:** View `v_merged_prs_30d_total` ensures consistency with pull-requests.json dashboard.

---

### Change 2: Line 427

**Current (INCORRECT):**

```sql
SELECT COUNT(*) as open_prs
FROM pull_requests
WHERE status = 'open';
```

**Correct:**

```sql
SELECT open_prs
FROM v_open_prs_total;
```

**Reason:** Single source of truth for open PR count across all dashboards.

---

## Summary Table

| Dashboard                  | Lines | View Name                       | Column Mapping                     |
| -------------------------- | ----- | ------------------------------- | ---------------------------------- |
| contributor-analytics.json | 121   | v_active_contributors_30d_total | contributors → active_contributors |
| contributor-analytics.json | 182   | v_commits_30d_total             | commits → commits                  |
| dashboard-home.json        | 103   | v_active_repositories_total     | total → total                      |
| dashboard-home.json        | 164   | v_active_contributors_30d_total | contributors → contributors        |
| dashboard-home.json        | 225   | v_commits_30d_total             | commits → commits                  |
| dashboard-home.json        | 408   | v_open_prs_total                | open_prs → open_prs                |
| repository-overview.json   | 121   | v_active_repositories_total     | total → total                      |
| team-overview.json         | 368   | v_merged_prs_30d_total          | merged_prs → merged                |
| team-overview.json         | 427   | v_open_prs_total                | open_prs → open_prs                |

**Total Changes: 9 queries across 4 dashboards**

---

## Notes

1. **Column Name Mapping:** Some views use different column names than the original queries. Ensure Grafana aliases are set correctly if needed.

2. **View Column Names (from views.sql):**
   - `v_active_repositories_total` → `total`
   - `v_active_contributors_30d_total` → `contributors`
   - `v_commits_30d_total` → `commits`
   - `v_open_prs_total` → `open_prs`
   - `v_merged_prs_30d_total` → `merged_prs`

3. **No Changes Needed:**
   - pull-requests.json (already correct)
   - admin-dashboard.json (already correct)
   - repository-deep-dive.json (parameterized queries are appropriate)
   - service-overview.json (service metrics have own aggregation)
   - security-dashboard.json (security drill-down requires direct access)

4. **Future Consideration:** Missing dashboard queries could benefit from new views:
   - `v_prs_created_30d_total` — Used by dashboard-home and team-overview
   - `v_pr_reviews_30d_total` — Used by contributor-analytics
