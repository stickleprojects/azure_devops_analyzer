# Dashboard SQL Audit Report

## Checking Dashboard Queries Against Views

**Generated:** 2026-03-26

## Executive Summary

Plan 016 reporting-view migration is now substantially complete.

* Dashboard business logic has been moved into shared PostgreSQL views in `database/views.sql`.
* High-churn dashboards that previously embedded large SQL blocks now query view-backed projections.
* Remaining dashboard concerns are data-quality or semantics defects, not reporting-layer migration gaps.

## Current Compliance Snapshot

| Dashboard | Status | Notes |
| --- | --- | --- |
| `pull-requests.json` | Compliant | Already view-backed and unchanged in this phase. |
| `admin-dashboard.json` | Compliant | Throughput and auth/error panels now use reporting views. |
| `contributor-analytics.json` | Compliant with known defects | Wired to reporting views; open issues are contributor identity and review recency semantics. |
| `dashboard-home.json` | Compliant | Summary cards use shared global aggregate views. |
| `repository-overview.json` | Compliant | Global totals and overview table now use reporting views. |
| `repository-deep-dive.json` | Compliant | Repository-specific code quality, dependency, and branch panels now query repository-scoped views. |
| `security-dashboard.json` | Compliant | Security summaries, trends, and details now use dedicated security views. |
| `service-overview.json` | Compliant | Service snapshots, trends, and repo breakdown panels query service views. |
| `team-overview.json` | Compliant | Team-filtered trends, summaries, and recent activity now query team views. |

## Key Reporting Views Added or Expanded

### Global Summary Views

* `v_prs_created_30d_total`
* `v_pr_reviews_30d_total`
* `v_commits_total`
* `v_pull_requests_total`
* `v_contributors_total`
* `v_teams_total`

### Repository-Focused Views

* `v_repository_names`
* `v_repo_total_contributors`
* `v_repo_commits_daily_trend_30d`
* `v_repo_lines_changed_daily_trend_30d`
* `v_repo_top_contributors_30d`
* `v_repo_top_reviewers_30d`
* `v_repo_pr_status_distribution`
* `v_repo_pr_size_distribution_30d`
* `v_repo_pr_creation_daily_trend_30d`
* `v_repo_pr_merge_daily_trend_30d`
* `v_repo_pr_health_summary`
* `v_repo_code_quality_latest`
* `v_repo_code_quality_trend_90d`
* `v_repo_issue_severity_latest`
* `v_repo_language_distribution_latest`
* `v_repo_dependency_rollup_latest`
* `v_repo_vulnerabilities_by_severity_latest`
* `v_repo_dependency_ecosystems_latest`
* `v_repo_vulnerability_details_latest`
* `v_branch_metrics_latest`
* `v_repo_branch_rollup`
* `v_repo_recent_commits`
* `v_repo_recent_prs`

### Service-Focused Views

* `v_service_metrics_latest`
* `v_service_metrics_trend`
* `v_service_repository_breakdown`
* `v_service_vulnerabilities_by_severity`

### Security-Focused Views

* `v_dependency_snapshot_latest`
* `v_security_overview_latest`
* `v_security_vulnerabilities_by_severity_latest`
* `v_security_top_repositories_critical_vulns`
* `v_security_eol_status_latest`
* `v_security_repository_overview`
* `v_security_vulnerability_trend`
* `v_security_top_vulnerable_dependencies`

### Team-Focused Views

* `v_repository_team_labels`
* `v_team_commits_daily_trend_30d`
* `v_team_pr_creation_daily_trend_30d`
* `v_team_pr_merge_daily_trend_30d`
* `v_team_active_contributors_daily_30d`
* `v_team_lines_changed_daily_trend_30d`
* `v_team_repository_health_matrix`
* `v_team_pr_health_summary_30d`
* `v_team_vulnerabilities_total_latest`
* `v_team_pr_size_distribution_30d`
* `v_team_vulnerabilities_by_severity_latest`
* `v_team_language_distribution_latest`
* `v_team_top_contributors_30d`
* `v_team_top_reviewers_30d`
* `v_team_performance_summary`
* `v_team_recent_prs_7d`

### Admin and Operational Views

* `v_extraction_repos_per_hour_5m`
* `v_auth_errors_by_platform`
* `v_auth_errors_24h_total`
* `v_extraction_metrics_with_errors`
* `v_extraction_runs_recent` expanded with normalized error categories

## Validation State

Reporting-view contract validation passed in Docker after the latest migration changes.

Command used:

```sh
docker compose -f docker-compose.test.yml run --rm test-runner sh -c "pytest tests/contract/database/test_reporting_views.py"
```

Result:

* `32 passed`

## Open Dashboard Defects

These remain open, but they are not blockers for Plan 016 reporting-view migration.

| ID | Dashboard | Severity | Status | Defect | Next Action |
| --- | --- | --- | --- | --- | --- |
| `DASH-CONTRIB-002` | `contributor-analytics.json` | High | Open | Top contributor commit totals and PR authored totals are inconsistent, likely due to contributor identity fragmentation and/or extraction-scope skew rather than dashboard SQL wiring. | Normalize contributor identity in storage, audit duplicate contributor records by normalized email, and add regression coverage for contributor rollup consistency. |
| `DASH-REVIEW-003` | `contributor-analytics.json` | High | Open | Top reviewers in the last 30 days can include long-inactive contributors because Azure DevOps review timestamps may be approximated during ingestion. | Replace synthetic review timestamps with a defensible source/fallback strategy and add reporting tests that prove stale reviews do not reappear as recent. |

### Closed Migration Defects

* `DASH-TEAM-001` is closed for Plan 016 purposes.
* Team Overview panels now route through team-scoped reporting views and apply the team filter through view-backed queries.

## Notes and Guardrails

* Dependency and repository language snapshot logic must use `last_seen_at`, not `analyzed_at`.
* The contract test fixture executes `database/views.sql` as one block; one invalid view definition can prevent later views from being created.
* `database/migrations/011_add_reporting_views.sql` now sources `database/views.sql` directly to keep migration behavior aligned with the canonical reporting layer.

## Recommended Next Steps

1. Smoke-test the updated Grafana dashboards against a populated environment.
2. Treat contributor identity normalization as a separate defect-focused change.
3. Tighten reporting contract tests for the newer repository/security/team views if stronger regression protection is needed.
