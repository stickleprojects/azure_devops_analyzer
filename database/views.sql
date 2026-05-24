-- =============================================================================
-- Reporting Views for Grafana Dashboards
-- =============================================================================
-- These views provide a testable, single-source-of-truth reporting layer.
-- Grafana dashboards query these views instead of embedding raw SQL.
--
-- Created: 2026-03-07 (Plan 016)
-- =============================================================================

-- =============================================================================
-- Pull Request Views - Per-Repository Breakdown
-- =============================================================================

-- View 1: Count open PRs per repository
CREATE OR REPLACE VIEW v_open_prs AS
SELECT repo_id, COUNT(*) AS count
FROM pull_requests
WHERE status = 'open'
GROUP BY repo_id;

-- View 2: Count PRs merged in last 30 days per repository
CREATE OR REPLACE VIEW v_merged_prs_30d AS
SELECT repo_id, COUNT(*) AS count
FROM pull_requests
WHERE status = 'merged' AND merged_at > NOW() - INTERVAL '30 days'
GROUP BY repo_id;

-- View 3: Count PRs closed in last 30 days per repository
CREATE OR REPLACE VIEW v_closed_prs_30d AS
SELECT repo_id, COUNT(*) AS count
FROM pull_requests
WHERE status = 'closed' AND closed_at > NOW() - INTERVAL '30 days'
GROUP BY repo_id;

-- View 8: PR size distribution per repository
CREATE OR REPLACE VIEW v_pr_size_distribution AS
SELECT repo_id, size_category, COUNT(*) AS count
FROM pull_requests
WHERE size_category IS NOT NULL
GROUP BY repo_id, size_category;

-- =============================================================================
-- Pull Request Views - Global Summaries (for dashboard top-level metrics)
-- =============================================================================

-- View: Global open PRs count
CREATE OR REPLACE VIEW v_open_prs_total AS
SELECT COUNT(*) AS open_prs
FROM pull_requests
WHERE status = 'open';

-- View: Global merged PRs in last 30 days
CREATE OR REPLACE VIEW v_merged_prs_30d_total AS
SELECT COUNT(*) AS merged_prs
FROM pull_requests
WHERE status = 'merged' AND merged_at > NOW() - INTERVAL '30 days';

-- View: Global closed PRs in last 30 days
CREATE OR REPLACE VIEW v_closed_prs_30d_total AS
SELECT COUNT(*) AS closed_prs
FROM pull_requests
WHERE status = 'closed' AND closed_at > NOW() - INTERVAL '30 days';

-- View: PR status distribution (global)
CREATE OR REPLACE VIEW v_pr_status_distribution AS
SELECT status, COUNT(*) AS count
FROM pull_requests
GROUP BY status;

-- View: PR size distribution (global, 30 days)
CREATE OR REPLACE VIEW v_pr_size_distribution_30d AS
SELECT COALESCE(size_category, 'unknown') AS size_category, COUNT(*) AS count
FROM pull_requests
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY size_category;

-- View: Average PR change volume (30 days)
CREATE OR REPLACE VIEW v_pr_avg_changes_30d AS
SELECT COALESCE(AVG(lines_added + lines_removed), 0)::int AS avg_changes
FROM pull_requests
WHERE created_at > NOW() - INTERVAL '30 days';

-- =============================================================================
-- Pull Request Views - Time Series (for trend charts)
-- =============================================================================

-- View: Daily PR creation trend (30 days)
CREATE OR REPLACE VIEW v_pr_creation_daily_trend AS
SELECT 
  date_trunc('day', created_at) AS time,
  COUNT(*) AS created
FROM pull_requests
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY date_trunc('day', created_at)
ORDER BY time;

-- View: Daily PR merge trend (30 days)
CREATE OR REPLACE VIEW v_pr_merge_daily_trend AS
SELECT 
  date_trunc('day', merged_at) AS time,
  COUNT(*) AS merged
FROM pull_requests
WHERE merged_at > NOW() - INTERVAL '30 days'
GROUP BY date_trunc('day', merged_at)
ORDER BY time;

-- View: PR details (recent 50)
CREATE OR REPLACE VIEW v_pr_recent_details AS
SELECT 
  r.repo_id,
  r.name AS repository,
  pr.pr_number,
  pr.title,
  COALESCE(c.name, c.email) AS author,
  pr.status,
  pr.size_category,
  pr.files_changed,
  pr.lines_added,
  pr.lines_removed,
  pr.created_at,
  pr.merged_at
FROM pull_requests pr
JOIN repositories r ON pr.repo_id = r.repo_id
LEFT JOIN contributors c ON pr.author_id = c.id
WHERE pr.created_at > NOW() - INTERVAL '30 days'
ORDER BY pr.created_at DESC
LIMIT 50;

-- =============================================================================
-- Contributor and Commit Views - Per-Repository Breakdown
-- =============================================================================

-- View 4: Count distinct contributors with commits in last 30 days per repository
CREATE OR REPLACE VIEW v_active_contributors_30d AS
SELECT repo_id, COUNT(DISTINCT author_id) AS count
FROM commits
WHERE commit_date > NOW() - INTERVAL '30 days'
GROUP BY repo_id;

-- View 5: Count commits in last 30 days per repository
CREATE OR REPLACE VIEW v_commits_30d AS
SELECT repo_id, COUNT(*) AS count
FROM commits
WHERE commit_date > NOW() - INTERVAL '30 days'
GROUP BY repo_id;

-- View 10: Contributor-level commit counts (all time)
CREATE OR REPLACE VIEW v_contributor_commits AS
SELECT 
    c.id AS author_id,
    co.repo_id,
    COUNT(*) AS commit_count
FROM 
    commits co
JOIN 
    contributors c ON co.author_id = c.id
GROUP BY 
    c.id, co.repo_id;

-- =============================================================================
-- Contributor and Commit Views - Global Summaries
-- =============================================================================

-- View: Global active contributors (30 days)
CREATE OR REPLACE VIEW v_active_contributors_30d_total AS
SELECT COUNT(DISTINCT author_id) AS contributors
FROM commits
WHERE commit_date > NOW() - INTERVAL '30 days';

-- View: Global commits (30 days)
CREATE OR REPLACE VIEW v_commits_30d_total AS
SELECT COUNT(*) AS commits
FROM commits
WHERE commit_date > NOW() - INTERVAL '30 days';

-- View: Global pull requests created in last 30 days
CREATE OR REPLACE VIEW v_prs_created_30d_total AS
SELECT COUNT(*) AS prs
FROM pull_requests
WHERE created_at > NOW() - INTERVAL '30 days';

-- View: Global teams count
CREATE OR REPLACE VIEW v_teams_total AS
SELECT COUNT(*) AS teams
FROM teams;

-- View: Global commits count (all time)
CREATE OR REPLACE VIEW v_commits_total AS
SELECT COUNT(*) AS total
FROM commits;

-- View: Global PR reviews in last 30 days
CREATE OR REPLACE VIEW v_pr_reviews_30d_total AS
SELECT COUNT(*) AS reviews
FROM pr_reviews
WHERE review_date > NOW() - INTERVAL '30 days';

-- View: Global pull requests count (all time)
CREATE OR REPLACE VIEW v_pull_requests_total AS
SELECT COUNT(*) AS total
FROM pull_requests;

-- View: Global contributors count (all time)
CREATE OR REPLACE VIEW v_contributors_total AS
SELECT COUNT(*) AS total
FROM contributors;

-- View: Daily commit trend (last 30 days)
CREATE OR REPLACE VIEW v_commits_daily_trend_30d AS
SELECT
    date_trunc('day', commit_date) AS time,
    COUNT(*) AS commits
FROM commits
WHERE commit_date > NOW() - INTERVAL '30 days'
GROUP BY date_trunc('day', commit_date)
ORDER BY time;

-- View: Top contributors by commits in last 30 days
CREATE OR REPLACE VIEW v_top_contributors_30d AS
SELECT
    COALESCE(c.name, c.email) AS contributor,
    COUNT(cm.commit_sha) AS commits
FROM contributors c
JOIN commits cm ON c.id = cm.author_id
WHERE cm.commit_date > NOW() - INTERVAL '30 days'
GROUP BY c.id, c.name, c.email
ORDER BY commits DESC
LIMIT 10;

-- View: Top reviewers by review count in last 30 days
CREATE OR REPLACE VIEW v_top_reviewers_30d AS
SELECT
    COALESCE(c.name, c.email) AS reviewer,
    COUNT(r.id) AS reviews
FROM contributors c
JOIN pr_reviews r ON c.id = r.reviewer_id
WHERE r.review_date > NOW() - INTERVAL '30 days'
GROUP BY c.id, c.name, c.email
ORDER BY reviews DESC
LIMIT 10;

-- View: Contributor activity rollup for last 30 days
CREATE OR REPLACE VIEW v_contributor_activity_30d AS
SELECT
    COALESCE(c.name, c.email) AS contributor,
    c.email,
    COUNT(DISTINCT cm.commit_sha) AS commits,
    COALESCE(SUM(cm.lines_added), 0) AS lines_added,
    COALESCE(SUM(cm.lines_removed), 0) AS lines_removed,
    COUNT(DISTINCT pr.id) AS prs_authored,
    COUNT(DISTINCT r.id) AS reviews_given
FROM contributors c
LEFT JOIN commits cm ON c.id = cm.author_id AND cm.commit_date > NOW() - INTERVAL '30 days'
LEFT JOIN pull_requests pr ON c.id = pr.author_id AND pr.created_at > NOW() - INTERVAL '30 days'
LEFT JOIN pr_reviews r ON c.id = r.reviewer_id AND r.review_date > NOW() - INTERVAL '30 days'
GROUP BY c.id, c.name, c.email
HAVING COUNT(DISTINCT cm.commit_sha) > 0 OR COUNT(DISTINCT pr.id) > 0 OR COUNT(DISTINCT r.id) > 0
ORDER BY commits DESC, prs_authored DESC, reviews_given DESC;

-- =============================================================================
-- Repository Summary Views
-- =============================================================================

-- View 6: Repository aggregate summary
CREATE OR REPLACE VIEW v_repository_summary AS
SELECT 
    r.repo_id,
    r.name,
    r.is_active,
    COUNT(DISTINCT c.commit_sha) AS total_commits,
    COUNT(DISTINCT pr.id) AS total_prs,
    COUNT(DISTINCT rs.name) AS language_count,
    MAX(c.commit_date) AS last_commit_date
FROM 
    repositories r
LEFT JOIN 
    commits c ON c.repo_id = r.repo_id
LEFT JOIN 
    pull_requests pr ON pr.repo_id = r.repo_id
LEFT JOIN 
    repository_stack rs ON rs.repo_id = r.repo_id AND rs.category = 'language'
GROUP BY 
    r.repo_id, r.name, r.is_active;

-- View 7: Language distribution per repository
CREATE OR REPLACE VIEW v_language_summary AS
SELECT repo_id, name AS language, percentage, byte_count
FROM repository_stack
WHERE category = 'language';

-- View: Active repositories count
CREATE OR REPLACE VIEW v_active_repositories_total AS
SELECT COUNT(*) AS total
FROM repositories
WHERE is_active = true;

-- View: Top 10 repositories by commits in last 30 days
CREATE OR REPLACE VIEW v_top_repositories_by_commits_30d AS
SELECT
    r.repo_id,
    r.name AS repository,
    COUNT(c.commit_sha) AS commits,
    r.url
FROM repositories r
LEFT JOIN commits c ON r.repo_id = c.repo_id
    AND c.commit_date > NOW() - INTERVAL '30 days'
WHERE r.is_active = true
GROUP BY r.repo_id, r.name, r.url
ORDER BY commits DESC
LIMIT 10;

-- View: Repository table for repository-overview dashboard
CREATE OR REPLACE VIEW v_repository_overview_table AS
SELECT
    r.repo_id,
    r.name AS repository,
    o.name AS organization,
    r.default_branch,
    r.url,
    r.last_analyzed_at,
    (SELECT COUNT(*) FROM commits c WHERE c.repo_id = r.repo_id) AS total_commits,
    (SELECT COUNT(*) FROM pull_requests p WHERE p.repo_id = r.repo_id) AS total_prs
FROM repositories r
JOIN projects p ON r.project_id = p.project_id
JOIN organizations o ON p.organization_id = o.organization_id
WHERE r.is_active = true
ORDER BY r.last_analyzed_at DESC NULLS LAST;

-- View: Repository selector values
CREATE OR REPLACE VIEW v_repository_names AS
SELECT repo_id, name AS repository
FROM repositories
WHERE is_active = true
ORDER BY name;

-- View: Total contributors per repository (all time)
CREATE OR REPLACE VIEW v_repo_total_contributors AS
SELECT repo_id, COUNT(DISTINCT author_id) AS contributors
FROM commits
GROUP BY repo_id;

-- View: Daily commit trend per repository (last 30 days)
CREATE OR REPLACE VIEW v_repo_commits_daily_trend_30d AS
SELECT
    repo_id,
    date_trunc('day', commit_date) AS time,
    COUNT(*) AS commits
FROM commits
WHERE commit_date > NOW() - INTERVAL '30 days'
GROUP BY repo_id, date_trunc('day', commit_date)
ORDER BY time;

-- View: Daily code churn per repository (last 30 days)
CREATE OR REPLACE VIEW v_repo_lines_changed_daily_trend_30d AS
SELECT
    repo_id,
    date_trunc('day', commit_date) AS time,
    COALESCE(SUM(lines_added), 0) AS added,
    COALESCE(SUM(lines_removed), 0) AS removed
FROM commits
WHERE commit_date > NOW() - INTERVAL '30 days'
GROUP BY repo_id, date_trunc('day', commit_date)
ORDER BY time;

-- View: Top contributors per repository (last 30 days)
CREATE OR REPLACE VIEW v_repo_top_contributors_30d AS
SELECT
    cm.repo_id,
    COALESCE(c.name, c.email) AS contributor,
    COUNT(cm.commit_sha) AS commits
FROM commits cm
JOIN contributors c ON c.id = cm.author_id
WHERE cm.commit_date > NOW() - INTERVAL '30 days'
GROUP BY cm.repo_id, c.id, c.name, c.email;

-- View: Top reviewers per repository (last 30 days)
CREATE OR REPLACE VIEW v_repo_top_reviewers_30d AS
SELECT
    pr.repo_id,
    COALESCE(c.name, c.email) AS reviewer,
    COUNT(r.id) AS reviews
FROM pr_reviews r
JOIN pull_requests pr ON pr.id = r.pr_id
JOIN contributors c ON c.id = r.reviewer_id
WHERE r.review_date > NOW() - INTERVAL '30 days'
GROUP BY pr.repo_id, c.id, c.name, c.email;

-- View: PR status distribution per repository
CREATE OR REPLACE VIEW v_repo_pr_status_distribution AS
SELECT repo_id, status, COUNT(*) AS count
FROM pull_requests
GROUP BY repo_id, status;

-- View: PR size distribution per repository (last 30 days)
CREATE OR REPLACE VIEW v_repo_pr_size_distribution_30d AS
SELECT
    repo_id,
    COALESCE(size_category, 'unknown') AS size_category,
    COUNT(*) AS count
FROM pull_requests
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY repo_id, size_category;

-- View: Daily PR creation trend per repository (last 30 days)
CREATE OR REPLACE VIEW v_repo_pr_creation_daily_trend_30d AS
SELECT
    repo_id,
    date_trunc('day', created_at) AS time,
    COUNT(*) AS created
FROM pull_requests
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY repo_id, date_trunc('day', created_at)
ORDER BY time;

-- View: Daily PR merge trend per repository (last 30 days)
CREATE OR REPLACE VIEW v_repo_pr_merge_daily_trend_30d AS
SELECT
    repo_id,
    date_trunc('day', merged_at) AS time,
    COUNT(*) AS merged
FROM pull_requests
WHERE merged_at > NOW() - INTERVAL '30 days'
GROUP BY repo_id, date_trunc('day', merged_at)
ORDER BY time;

-- View: PR health rollup per repository
CREATE OR REPLACE VIEW v_repo_pr_health_summary AS
SELECT
    repo_id,
    COALESCE(
        AVG(
            CASE
                WHEN merged_at IS NOT NULL AND created_at > NOW() - INTERVAL '90 days'
                THEN EXTRACT(EPOCH FROM (merged_at - created_at)) / 86400
            END
        ),
        0
    )::numeric(10,1) AS days_to_merge,
    COUNT(*) FILTER (
        WHERE has_issues = true AND created_at > NOW() - INTERVAL '30 days'
    ) AS prs_with_issues,
    COALESCE(
        AVG(CASE WHEN created_at > NOW() - INTERVAL '30 days' THEN comment_count END),
        0
    )::numeric(10,1) AS avg_comments,
    COALESCE(
        AVG(CASE WHEN created_at > NOW() - INTERVAL '30 days' THEN approval_count END),
        0
    )::numeric(10,1) AS avg_approvals
FROM pull_requests
GROUP BY repo_id;

-- View: Latest language distribution per repository
CREATE OR REPLACE VIEW v_repo_language_distribution_latest AS
SELECT rs.repo_id, rs.name AS language, rs.percentage
FROM repository_stack rs
WHERE rs.category = 'language'
  AND rs.last_seen_at = (
    SELECT MAX(rs2.last_seen_at)
    FROM repository_stack rs2
    WHERE rs2.repo_id = rs.repo_id
      AND rs2.category = 'language'
)
ORDER BY rs.percentage DESC;

-- View: Recent commit details per repository
CREATE OR REPLACE VIEW v_repo_recent_commits AS
SELECT
    cm.repo_id,
    LEFT(cm.commit_sha, 7) AS sha,
    COALESCE(c.name, c.email) AS author,
    LEFT(cm.message, 80) AS message,
    cm.files_changed AS files,
    cm.lines_added AS lines_added,
    cm.lines_removed AS lines_removed,
    cm.commit_date AS commit_date
FROM commits cm
LEFT JOIN contributors c ON c.id = cm.author_id;

-- View: Recent pull request details per repository
CREATE OR REPLACE VIEW v_repo_recent_prs AS
SELECT
    pr.repo_id,
    pr.pr_number,
    pr.title,
    COALESCE(c.name, c.email) AS author,
    pr.status,
    pr.source_branch,
    pr.target_branch,
    pr.size_category,
    pr.files_changed,
    pr.lines_added,
    pr.lines_removed,
    pr.comment_count,
    pr.approval_count,
    pr.has_issues,
    pr.created_at
FROM pull_requests pr
LEFT JOIN contributors c ON c.id = pr.author_id;

-- View: Latest repository summary text per repository
CREATE OR REPLACE VIEW v_repo_summary_latest AS
SELECT DISTINCT ON (repo_id)
    repo_id,
    summary_text,
    purpose,
    key_technologies,
    generated_at
FROM repository_summaries
ORDER BY repo_id, generated_at DESC;

-- View: Latest service metrics snapshot per service
CREATE OR REPLACE VIEW v_service_metrics_latest AS
SELECT
    s.service_id,
    s.name AS service,
    sm.period_start,
    sm.total_repositories,
    sm.active_repositories,
    sm.unique_contributors,
    sm.total_commits,
    sm.total_prs_created,
    sm.total_prs_merged,
    sm.avg_pr_review_time_hours,
    sm.avg_test_coverage,
    sm.avg_maintainability_index,
    sm.total_quality_issues,
    sm.total_vulnerabilities,
    sm.critical_vulnerabilities,
    sm.high_vulnerabilities,
    sm.eol_dependencies,
    sm.total_dependencies
FROM services s
JOIN LATERAL (
    SELECT sm.*
    FROM service_metrics sm
    WHERE sm.service_id = s.service_id
    ORDER BY sm.period_start DESC
    LIMIT 1
) sm ON true;

-- View: Service trend metrics by period
CREATE OR REPLACE VIEW v_service_metrics_trend AS
SELECT
    s.name AS service,
    sm.period_start AS time,
    sm.total_commits AS commits,
    sm.total_prs_created AS prs_created,
    sm.total_prs_merged AS prs_merged,
    sm.avg_test_coverage AS coverage,
    sm.avg_maintainability_index AS maintainability,
    sm.total_vulnerabilities AS vulnerabilities,
    sm.critical_vulnerabilities AS critical
FROM service_metrics sm
JOIN services s ON s.service_id = sm.service_id;

-- View: Repository breakdown per service
CREATE OR REPLACE VIEW v_service_repository_breakdown AS
SELECT
    r.repo_id,
    r.name AS repository,
    s.name AS service,
    (SELECT COUNT(*) FROM commits c WHERE c.repo_id = r.repo_id AND c.commit_date > NOW() - INTERVAL '30 days') AS commits_30d,
    (SELECT COUNT(DISTINCT c.author_id) FROM commits c WHERE c.repo_id = r.repo_id AND c.commit_date > NOW() - INTERVAL '30 days') AS contributors_30d,
    (SELECT COUNT(*) FROM pull_requests p WHERE p.repo_id = r.repo_id AND p.status = 'open') AS open_prs,
    (SELECT COUNT(*) FROM pull_requests p WHERE p.repo_id = r.repo_id AND p.merged_at > NOW() - INTERVAL '30 days') AS merged_prs_30d,
    COALESCE(
        (
            SELECT COUNT(DISTINCT v.id)
            FROM repository_dependencies d
            JOIN packages p ON p.package_name = d.package_name AND p.ecosystem = d.ecosystem
            JOIN vulnerabilities v ON v.package_id = p.id
            WHERE d.repo_id = r.repo_id
              AND d.last_seen_at = (
                  SELECT MAX(d2.last_seen_at)
                  FROM repository_dependencies d2
                  WHERE d2.repo_id = r.repo_id
              )
        ),
        0
    ) AS vulnerabilities,
    r.last_analyzed_at
FROM repositories r
JOIN repository_services rs ON rs.repo_id = r.repo_id
JOIN services s ON s.service_id = rs.service_id
WHERE r.is_active = true;

-- View: Vulnerability severity distribution per service (latest dependency scan per repo)
-- Only repository_dependencies rows where has_known_vulnerabilities = true are
-- considered, so repos on patched versions are excluded from the counts.
CREATE OR REPLACE VIEW v_service_vulnerabilities_by_severity AS
SELECT
    s.name AS service,
    v.severity,
    COUNT(DISTINCT v.id) AS count
FROM repository_dependencies d
JOIN packages p ON p.package_name = d.package_name AND p.ecosystem = d.ecosystem
JOIN vulnerabilities v ON v.package_id = p.id
JOIN repository_services rs ON rs.repo_id = d.repo_id
JOIN services s ON s.service_id = rs.service_id
WHERE d.last_seen_at = (
    SELECT MAX(d2.last_seen_at)
    FROM repository_dependencies d2
    WHERE d2.repo_id = d.repo_id
)
  AND d.has_known_vulnerabilities = true
GROUP BY s.name, v.severity;

-- View: Extraction throughput as repositories per hour in 5-minute buckets
CREATE OR REPLACE VIEW v_extraction_repos_per_hour_5m AS
SELECT
    time_bucket(INTERVAL '5 minutes', extraction_completed_at) AS time,
    COUNT(*) * 12 AS repos_per_hour
FROM extraction_metrics
WHERE status = 'completed'
  AND extraction_completed_at IS NOT NULL
GROUP BY time
ORDER BY time;

-- View: Latest code quality snapshot per repository
CREATE OR REPLACE VIEW v_repo_code_quality_latest AS
SELECT DISTINCT ON (repo_id)
    repo_id,
    timestamp,
    total_issues,
    critical_issues,
    high_issues,
    medium_issues,
    low_issues,
    complexity_score,
    maintainability_index,
    test_coverage,
    code_smells,
    technical_debt_minutes
FROM code_quality_metrics
WHERE repo_id IS NOT NULL
ORDER BY repo_id, timestamp DESC;

-- View: Code quality trend per repository for last 90 days
CREATE OR REPLACE VIEW v_repo_code_quality_trend_90d AS
SELECT
    repo_id,
    timestamp AS time,
    critical_issues AS critical,
    high_issues AS high,
    medium_issues AS medium,
    low_issues AS low,
    test_coverage AS coverage,
    technical_debt_minutes AS debt
FROM code_quality_metrics
WHERE timestamp > NOW() - INTERVAL '90 days'
ORDER BY time;

-- View: Latest issue severity distribution per repository
CREATE OR REPLACE VIEW v_repo_issue_severity_latest AS
SELECT
    q.repo_id,
    severity_data.severity,
    severity_data.count
FROM v_repo_code_quality_latest q
CROSS JOIN LATERAL (
    VALUES
        ('Critical', COALESCE(q.critical_issues, 0)),
        ('High', COALESCE(q.high_issues, 0)),
        ('Medium', COALESCE(q.medium_issues, 0)),
        ('Low', COALESCE(q.low_issues, 0))
) AS severity_data(severity, count);

-- View: Latest dependency snapshot per repository
CREATE OR REPLACE VIEW v_dependency_snapshot_latest AS
SELECT
    d.id,
    d.repo_id,
    d.branch_id,
    d.package_name,
    d.version,
    d.ecosystem,
    d.is_dev_dependency,
    d.has_known_vulnerabilities,
    d.first_seen_at,
    d.last_seen_at,
    p.latest_version,
    p.is_eol,
    p.eol_date,
    p.id AS package_id
FROM repository_dependencies d
LEFT JOIN packages p ON p.package_name = d.package_name AND p.ecosystem = d.ecosystem
WHERE d.last_seen_at = (
    SELECT MAX(d2.last_seen_at)
    FROM repository_dependencies d2
    WHERE d2.repo_id = d.repo_id
);

-- View: Repository dependency/security rollup from latest dependency snapshot
-- vulnerabilities uses the pre-computed has_known_vulnerabilities flag on
-- repository_dependencies rather than a JOIN to the vulnerabilities table, so
-- only repos pinned to an affected version (flag = true) are counted.
CREATE OR REPLACE VIEW v_repo_dependency_rollup_latest AS
SELECT
    d.repo_id,
    COUNT(*) FILTER (WHERE d.has_known_vulnerabilities = true) AS vulnerabilities,
    COUNT(*) FILTER (
        WHERE d.version != d.latest_version AND d.latest_version IS NOT NULL
    ) AS outdated_dependencies,
    COUNT(*) FILTER (WHERE d.is_eol = true) AS eol_dependencies,
    COUNT(*) AS total_dependencies,
    COUNT(*) FILTER (WHERE d.is_dev_dependency = true) AS dev_dependencies
FROM v_dependency_snapshot_latest d
GROUP BY d.repo_id;

-- View: Vulnerability severity distribution per repository from latest dependency snapshot
CREATE OR REPLACE VIEW v_repo_vulnerabilities_by_severity_latest AS
SELECT
    d.repo_id,
    v.severity,
    COUNT(*) AS count
FROM v_dependency_snapshot_latest d
JOIN vulnerabilities v ON v.package_id = d.package_id
GROUP BY d.repo_id, v.severity;

-- View: Dependency ecosystem distribution per repository from latest dependency snapshot
CREATE OR REPLACE VIEW v_repo_dependency_ecosystems_latest AS
SELECT
    repo_id,
    ecosystem,
    COUNT(*) AS count
FROM v_dependency_snapshot_latest
GROUP BY repo_id, ecosystem;

-- View: Vulnerability details per repository from latest dependency snapshot
CREATE OR REPLACE VIEW v_repo_vulnerability_details_latest AS
SELECT
    d.repo_id,
    d.package_name,
    d.version,
    v.cve_id,
    v.severity,
    LEFT(v.summary, 100) AS summary,
    v.fixed_in_version,
    v.published_date
FROM v_dependency_snapshot_latest d
JOIN vulnerabilities v ON v.package_id = d.package_id;

-- View: Latest branch metrics snapshot
CREATE OR REPLACE VIEW v_branch_metrics_latest AS
SELECT
    b.repo_id,
    b.branch_id,
    b.branch_name,
    b.latest_commit_sha,
    b.is_active,
    COALESCE(m.commit_count, 0) AS commit_count,
    COALESCE(m.unique_contributors, 0) AS unique_contributors,
    COALESCE(m.age_days, 0) AS age_days,
    COALESCE(m.staleness_days, 0) AS staleness_days,
    COALESCE(m.divergence_from_main, 0) AS divergence_from_main
FROM branches b
LEFT JOIN LATERAL (
    SELECT
        bm.commit_count,
        bm.unique_contributors,
        bm.age_days,
        bm.staleness_days,
        bm.divergence_from_main
    FROM branch_metrics bm
    WHERE bm.branch_id = b.branch_id
    ORDER BY bm.timestamp DESC
    LIMIT 1
) m ON true;

-- View: Repository branch health rollup
CREATE OR REPLACE VIEW v_repo_branch_rollup AS
SELECT
    repo_id,
    COUNT(*) FILTER (WHERE is_active = true) AS active_branches,
    COUNT(*) FILTER (WHERE is_active = true AND COALESCE(staleness_days, 999) > 30) AS stale_branches
FROM v_branch_metrics_latest
GROUP BY repo_id;

-- View: Security dashboard latest overview
CREATE OR REPLACE VIEW v_security_overview_latest AS
SELECT
    COUNT(DISTINCT v.id) AS total_vulnerabilities,
    COUNT(*) FILTER (WHERE d.is_eol = true) AS total_eol_deps,
    COUNT(DISTINCT CASE WHEN d.has_known_vulnerabilities = true THEN d.repo_id END) AS repos_with_vulns,
    COUNT(DISTINCT CASE WHEN d.is_eol = true THEN d.repo_id END) AS repos_with_eol
FROM v_dependency_snapshot_latest d
LEFT JOIN vulnerabilities v ON v.package_id = d.package_id;

-- View: Security dashboard vulnerability severity distribution
CREATE OR REPLACE VIEW v_security_vulnerabilities_by_severity_latest AS
SELECT
    v.severity,
    COUNT(*) AS count
FROM v_dependency_snapshot_latest d
JOIN vulnerabilities v ON v.package_id = d.package_id
GROUP BY v.severity;

-- View: Security dashboard top repositories by critical vulnerabilities
CREATE OR REPLACE VIEW v_security_top_repositories_critical_vulns AS
SELECT
    r.name AS repository,
    COUNT(*) AS critical_vulns
FROM v_dependency_snapshot_latest d
JOIN vulnerabilities v ON v.package_id = d.package_id
JOIN repositories r ON r.repo_id = d.repo_id
WHERE v.severity = 'CRITICAL'
GROUP BY r.name
ORDER BY critical_vulns DESC
LIMIT 10;

-- View: Security dashboard EOL status distribution
CREATE OR REPLACE VIEW v_security_eol_status_latest AS
SELECT
    CASE
        WHEN eol_date < CURRENT_DATE THEN 'Expired'
        WHEN eol_date < CURRENT_DATE + INTERVAL '90 days' THEN 'Expiring Soon'
        ELSE 'Future EOL'
    END AS category,
    COUNT(*) AS count
FROM v_dependency_snapshot_latest
WHERE is_eol = true
GROUP BY 1;

-- View: Security dashboard repository overview
CREATE OR REPLACE VIEW v_security_repository_overview AS
SELECT
    r.repo_id,
    r.name AS repository,
    COALESCE(vs.critical, 0) AS critical_vulns,
    COALESCE(vs.high, 0) AS high_vulns,
    COALESCE(vs.medium, 0) AS medium_vulns,
    COALESCE(vs.low, 0) AS low_vulns,
    COALESCE(es.eol_deps, 0) AS eol_deps
FROM repositories r
LEFT JOIN (
    SELECT
        d.repo_id,
        SUM(CASE WHEN v.severity = 'CRITICAL' THEN 1 ELSE 0 END) AS critical,
        SUM(CASE WHEN v.severity = 'HIGH' THEN 1 ELSE 0 END) AS high,
        SUM(CASE WHEN v.severity = 'MEDIUM' THEN 1 ELSE 0 END) AS medium,
        SUM(CASE WHEN v.severity = 'LOW' THEN 1 ELSE 0 END) AS low
    FROM v_dependency_snapshot_latest d
    LEFT JOIN vulnerabilities v ON v.package_id = d.package_id
    GROUP BY d.repo_id
) vs ON vs.repo_id = r.repo_id
LEFT JOIN (
    SELECT repo_id, COUNT(*) AS eol_deps
    FROM v_dependency_snapshot_latest
    WHERE is_eol = true
    GROUP BY repo_id
) es ON es.repo_id = r.repo_id
WHERE r.is_active = true;

-- View: Security dashboard vulnerability trend
CREATE OR REPLACE VIEW v_security_vulnerability_trend AS
SELECT
    time_bucket(INTERVAL '1 day', d.last_seen_at) AS time,
    COUNT(DISTINCT v.id) AS vulnerabilities
FROM repository_dependencies d
JOIN packages p ON p.package_name = d.package_name AND p.ecosystem = d.ecosystem
JOIN vulnerabilities v ON v.package_id = p.id
GROUP BY time_bucket('1 day', d.last_seen_at)
ORDER BY time;

-- View: Security dashboard top vulnerable dependencies
CREATE OR REPLACE VIEW v_security_top_vulnerable_dependencies AS
SELECT
    d.package_name,
    d.version,
    d.ecosystem,
    v.severity,
    COUNT(DISTINCT d.repo_id) AS affected_repositories,
    STRING_AGG(DISTINCT r.name, ', ') AS repositories
FROM v_dependency_snapshot_latest d
JOIN vulnerabilities v ON v.package_id = d.package_id
JOIN repositories r ON r.repo_id = d.repo_id
GROUP BY d.package_name, d.version, d.ecosystem, v.severity
ORDER BY
    CASE v.severity
        WHEN 'CRITICAL' THEN 1
        WHEN 'HIGH' THEN 2
        WHEN 'MEDIUM' THEN 3
        WHEN 'LOW' THEN 4
        ELSE 5
    END,
    COUNT(DISTINCT d.repo_id) DESC;

-- View: Repository to team label mapping
CREATE OR REPLACE VIEW v_repository_team_labels AS
SELECT
    r.repo_id,
    r.name AS repository,
    COALESCE(t.name, 'No Team') AS team,
    r.default_branch,
    r.last_analyzed_at,
    r.is_active
FROM repositories r
LEFT JOIN teams t ON t.team_id = r.team_id;

-- View: Team commit activity trend
CREATE OR REPLACE VIEW v_team_commits_daily_trend_30d AS
SELECT
    date_trunc('day', c.commit_date) AS time,
    rtl.team,
    COUNT(*) AS commits
FROM commits c
JOIN v_repository_team_labels rtl ON rtl.repo_id = c.repo_id
WHERE c.commit_date > NOW() - INTERVAL '30 days'
GROUP BY date_trunc('day', c.commit_date), rtl.team
ORDER BY time, rtl.team;

-- View: Team PR creation activity trend
CREATE OR REPLACE VIEW v_team_pr_creation_daily_trend_30d AS
SELECT
    date_trunc('day', p.created_at) AS time,
    rtl.team,
    COUNT(*) AS created
FROM pull_requests p
JOIN v_repository_team_labels rtl ON rtl.repo_id = p.repo_id
WHERE p.created_at > NOW() - INTERVAL '30 days'
GROUP BY date_trunc('day', p.created_at), rtl.team
ORDER BY time, rtl.team;

-- View: Team PR merge activity trend
CREATE OR REPLACE VIEW v_team_pr_merge_daily_trend_30d AS
SELECT
    date_trunc('day', p.merged_at) AS time,
    rtl.team,
    COUNT(*) AS merged
FROM pull_requests p
JOIN v_repository_team_labels rtl ON rtl.repo_id = p.repo_id
WHERE p.merged_at > NOW() - INTERVAL '30 days'
GROUP BY date_trunc('day', p.merged_at), rtl.team
ORDER BY time, rtl.team;

-- View: Team active contributors trend
CREATE OR REPLACE VIEW v_team_active_contributors_daily_30d AS
SELECT
    date_trunc('day', c.commit_date) AS time,
    rtl.team,
    COUNT(DISTINCT c.author_id) AS contributors
FROM commits c
JOIN v_repository_team_labels rtl ON rtl.repo_id = c.repo_id
WHERE c.commit_date > NOW() - INTERVAL '30 days'
GROUP BY date_trunc('day', c.commit_date), rtl.team
ORDER BY time, rtl.team;

-- View: Team lines changed trend
CREATE OR REPLACE VIEW v_team_lines_changed_daily_trend_30d AS
SELECT
    date_trunc('day', c.commit_date) AS time,
    rtl.team,
    COALESCE(SUM(c.lines_added), 0) AS added,
    COALESCE(SUM(c.lines_removed), 0) AS removed
FROM commits c
JOIN v_repository_team_labels rtl ON rtl.repo_id = c.repo_id
WHERE c.commit_date > NOW() - INTERVAL '30 days'
GROUP BY date_trunc('day', c.commit_date), rtl.team
ORDER BY time, rtl.team;

-- View: Team repository health matrix
CREATE OR REPLACE VIEW v_team_repository_health_matrix AS
SELECT
    rtl.repo_id,
    rtl.repository,
    rtl.team,
    COALESCE(c30.count, 0) AS commits_30d,
    COALESCE(ac30.count, 0) AS contributors_30d,
    COALESCE(op.count, 0) AS open_prs,
    COALESCE(mp.count, 0) AS merged_prs_30d,
    COALESCE(dr.vulnerabilities, 0) AS vulnerabilities,
    COALESCE(br.stale_branches, 0) AS stale_branches,
    rtl.last_analyzed_at
FROM v_repository_team_labels rtl
LEFT JOIN v_commits_30d c30 ON c30.repo_id = rtl.repo_id
LEFT JOIN v_active_contributors_30d ac30 ON ac30.repo_id = rtl.repo_id
LEFT JOIN v_open_prs op ON op.repo_id = rtl.repo_id
LEFT JOIN v_merged_prs_30d mp ON mp.repo_id = rtl.repo_id
LEFT JOIN v_repo_dependency_rollup_latest dr ON dr.repo_id = rtl.repo_id
LEFT JOIN v_repo_branch_rollup br ON br.repo_id = rtl.repo_id
WHERE rtl.is_active = true;

-- View: Team PR health summary
CREATE OR REPLACE VIEW v_team_pr_health_summary_30d AS
SELECT
    rtl.team,
    COALESCE(
        AVG(
            CASE WHEN p.merged_at > NOW() - INTERVAL '30 days'
                THEN EXTRACT(EPOCH FROM (p.merged_at - p.created_at)) / 86400
            END
        ),
        0
    )::numeric(10,1) AS avg_merge_time_days,
    COALESCE(
        AVG(CASE WHEN p.merged_at > NOW() - INTERVAL '30 days' THEN p.approval_count END),
        0
    )::numeric(10,1) AS avg_approvals,
    COUNT(*) FILTER (WHERE p.has_issues = true AND p.created_at > NOW() - INTERVAL '30 days') AS prs_with_issues
FROM pull_requests p
JOIN v_repository_team_labels rtl ON rtl.repo_id = p.repo_id
GROUP BY rtl.team;

-- View: Team vulnerability totals
CREATE OR REPLACE VIEW v_team_vulnerabilities_total_latest AS
SELECT
    rtl.team,
    COUNT(DISTINCT v.id) AS total_vulnerabilities
FROM v_dependency_snapshot_latest d
JOIN v_repository_team_labels rtl ON rtl.repo_id = d.repo_id
LEFT JOIN vulnerabilities v ON v.package_id = d.package_id
GROUP BY rtl.team;

-- View: Team PR size distribution
CREATE OR REPLACE VIEW v_team_pr_size_distribution_30d AS
SELECT
    rtl.team,
    COALESCE(p.size_category, 'unknown') AS size,
    COUNT(*) AS count
FROM pull_requests p
JOIN v_repository_team_labels rtl ON rtl.repo_id = p.repo_id
WHERE p.created_at > NOW() - INTERVAL '30 days'
GROUP BY rtl.team, COALESCE(p.size_category, 'unknown');

-- View: Team vulnerability severity distribution
CREATE OR REPLACE VIEW v_team_vulnerabilities_by_severity_latest AS
SELECT
    rtl.team,
    v.severity,
    COUNT(*) AS count
FROM v_dependency_snapshot_latest d
JOIN v_repository_team_labels rtl ON rtl.repo_id = d.repo_id
JOIN vulnerabilities v ON v.package_id = d.package_id
GROUP BY rtl.team, v.severity;

-- View: Team language distribution
CREATE OR REPLACE VIEW v_team_language_distribution_latest AS
SELECT
    rtl.team,
    rs.name AS language,
    SUM(COALESCE(rs.line_count, 0)) AS lines
FROM repository_stack rs
JOIN v_repository_team_labels rtl ON rtl.repo_id = rs.repo_id
WHERE rs.category = 'language'
  AND rs.last_seen_at = (
    SELECT MAX(rs2.last_seen_at)
    FROM repository_stack rs2
    WHERE rs2.repo_id = rs.repo_id
      AND rs2.category = 'language'
)
GROUP BY rtl.team, rs.name;

-- View: Team top contributors
CREATE OR REPLACE VIEW v_team_top_contributors_30d AS
SELECT
    rtl.team,
    COALESCE(c.name, c.email) AS contributor,
    COUNT(cm.commit_sha) AS commits
FROM commits cm
JOIN v_repository_team_labels rtl ON rtl.repo_id = cm.repo_id
JOIN contributors c ON c.id = cm.author_id
WHERE cm.commit_date > NOW() - INTERVAL '30 days'
GROUP BY rtl.team, c.id, c.name, c.email;

-- View: Team top reviewers
CREATE OR REPLACE VIEW v_team_top_reviewers_30d AS
SELECT
    rtl.team,
    COALESCE(c.name, c.email) AS reviewer,
    COUNT(r.id) AS reviews
FROM pr_reviews r
JOIN pull_requests p ON p.id = r.pr_id
JOIN v_repository_team_labels rtl ON rtl.repo_id = p.repo_id
JOIN contributors c ON c.id = r.reviewer_id
WHERE r.review_date > NOW() - INTERVAL '30 days'
GROUP BY rtl.team, c.id, c.name, c.email;

-- View: Team performance summary
CREATE OR REPLACE VIEW v_team_performance_summary AS
SELECT
    rtl.team,
    COUNT(DISTINCT rtl.repo_id) AS repositories,
    COUNT(DISTINCT cm.author_id) AS contributors,
    COUNT(cm.commit_sha) AS commits_30d,
    COUNT(DISTINCT CASE WHEN p.status = 'open' THEN p.id END) AS open_prs,
    COUNT(DISTINCT CASE WHEN p.merged_at > NOW() - INTERVAL '30 days' THEN p.id END) AS merged_prs_30d,
    ROUND(AVG(EXTRACT(EPOCH FROM (p.merged_at - p.created_at)) / 86400), 1) AS avg_merge_time_days
FROM v_repository_team_labels rtl
LEFT JOIN commits cm ON cm.repo_id = rtl.repo_id AND cm.commit_date > NOW() - INTERVAL '30 days'
LEFT JOIN pull_requests p ON p.repo_id = rtl.repo_id
GROUP BY rtl.team;

-- View: Recent pull requests by team
CREATE OR REPLACE VIEW v_team_recent_prs_7d AS
SELECT
    rtl.repo_id,
    rtl.repository,
    rtl.team,
    pr.pr_number,
    pr.title,
    COALESCE(c.name, c.email) AS author,
    pr.status,
    pr.size_category AS size,
    pr.files_changed AS files,
    pr.approval_count AS approvals,
    pr.created_at
FROM pull_requests pr
JOIN v_repository_team_labels rtl ON rtl.repo_id = pr.repo_id
LEFT JOIN contributors c ON c.id = pr.author_id
WHERE pr.created_at > NOW() - INTERVAL '7 days';

-- View: Stale repositories (>7 days without analysis)
CREATE OR REPLACE VIEW v_stale_repositories AS
SELECT r.repo_id, r.name, r.last_analyzed_at, NOW() - r.last_analyzed_at AS age
FROM repositories r
WHERE r.last_analyzed_at < NOW() - INTERVAL '7 days' AND r.is_active = true
ORDER BY r.last_analyzed_at ASC
LIMIT 50;

-- View: Never-analyzed repositories
CREATE OR REPLACE VIEW v_unanalyzed_repositories AS
SELECT r.repo_id, r.name, r.created_at
FROM repositories r
WHERE r.last_analyzed_at IS NULL AND r.is_active = true
ORDER BY r.created_at DESC
LIMIT 50;

-- View 12: Dependencies with vulnerability/EOL flags per repository
CREATE OR REPLACE VIEW v_dependency_summary AS
SELECT
    d.repo_id,
    d.package_name,
    d.ecosystem,
    d.version,
    p.latest_version,
    d.has_known_vulnerabilities,
    p.is_eol,
    p.eol_date
FROM repository_dependencies d
LEFT JOIN packages p ON p.package_name = d.package_name AND p.ecosystem = d.ecosystem;

-- =============================================================================
-- System and Operational Views
-- =============================================================================

-- View 9: Extraction run summary for admin dashboard
CREATE OR REPLACE VIEW v_extraction_run_summary AS
SELECT 
    run_id,
    platform,
    organization_name,
    project_name,
    status,
    total_repositories,
    processed_repositories,
    started_at,
    updated_at,
    completed_at,
    error_message
FROM 
    extraction_runs;

-- View: Active extraction runs
CREATE OR REPLACE VIEW v_extraction_runs_active AS
SELECT COUNT(*) AS active_runs
FROM extraction_runs
WHERE status = 'running';

-- View: Latest extraction run progress
CREATE OR REPLACE VIEW v_extraction_run_latest_progress AS
SELECT ROUND(processed_repositories * 100.0 / NULLIF(total_repositories, 0), 1) AS progress_pct
FROM extraction_runs
ORDER BY started_at DESC
LIMIT 1;

-- Function: Canonical extraction error classifier
CREATE OR REPLACE FUNCTION classify_extraction_error(error_message text)
RETURNS TABLE (
    error_category text,
    error_subcategory text,
    is_credential_failure boolean,
    is_authorization_failure boolean
)
LANGUAGE sql
STABLE
PARALLEL SAFE
AS $$
    WITH normalized AS (
        SELECT lower(coalesce(error_message, '')) AS msg
    ),
    classified AS (
        SELECT
            CASE
                WHEN msg LIKE '%rate limit%'
                  OR msg LIKE '%secondary rate limit%'
                  OR msg LIKE '%abuse detection%'
                  OR msg LIKE '%x-ratelimit-remaining: 0%' THEN 'RATE_LIMIT'
                WHEN msg LIKE '%connection reset%'
                  OR msg LIKE '%connection refused%'
                  OR msg LIKE '%temporary failure in name resolution%' THEN 'NETWORK'
                WHEN msg LIKE '%timed out%'
                  OR msg LIKE '%timeout%'
                  OR msg LIKE '%read timeout%'
                  OR msg LIKE '%connect timeout%' THEN 'TIMEOUT'
                WHEN msg LIKE '%service unavailable%'
                  OR msg LIKE '%bad gateway%'
                  OR msg LIKE '% 502 %'
                  OR msg LIKE '% 503 %'
                  OR msg LIKE '% 504 %'
                  OR msg LIKE '502%'
                  OR msg LIKE '503%'
                  OR msg LIKE '504%' THEN 'SERVICE_UNAVAILABLE'
                WHEN msg LIKE '%bad credentials%'
                  OR msg LIKE '%requires authentication%'
                  OR msg LIKE '%requires user authentication%'
                  OR msg LIKE '%token has expired%'
                  OR msg LIKE '%personal access token used has expired%'
                  OR msg LIKE '%no token%'
                  OR msg LIKE '%missing token%'
                  OR msg LIKE '%token not provided%'
                  OR msg LIKE '%401%'
                  OR msg LIKE '%unauthorized%' THEN 'AUTH'
                WHEN msg LIKE '%resource not accessible by integration%'
                  OR msg LIKE '%insufficient scopes%'
                  OR msg LIKE '%access denied%'
                  OR msg LIKE '%not authorized to access this resource%'
                  OR msg LIKE '%vs30063%'
                  OR msg LIKE '%tf400813%'
                  OR msg LIKE '%permission denied%'
                  OR msg LIKE '%forbidden%'
                  OR msg LIKE '%403%'
                  OR msg LIKE '%not authorized%'
                  OR msg LIKE '%account disabled%'
                  OR msg LIKE '%account suspended%' THEN 'PERMISSION'
                WHEN msg LIKE '%404%'
                  OR msg LIKE '%not found%' THEN 'NOT_FOUND'
                WHEN msg LIKE '%422%'
                  OR msg LIKE '%unprocessable%' THEN 'VALIDATION'
                WHEN msg LIKE '%409%'
                  OR msg LIKE '%conflict%' THEN 'CONFLICT'
                WHEN msg LIKE '%data integrity%'
                  OR msg LIKE '%corrupt data%'
                  OR msg LIKE '%inconsistent data%' THEN 'DATA_INTEGRITY'
                WHEN msg LIKE '%api error%'
                  OR msg LIKE '%upstream api%' THEN 'PLATFORM_API'
                ELSE 'UNKNOWN'
            END AS category,
            CASE
                WHEN msg LIKE '%bad credentials%' THEN 'AUTH_TOKEN_INVALID'
                WHEN msg LIKE '%token has expired%'
                  OR msg LIKE '%personal access token used has expired%' THEN 'AUTH_TOKEN_EXPIRED'
                WHEN msg LIKE '%no token%'
                  OR msg LIKE '%missing token%'
                  OR msg LIKE '%token not provided%' THEN 'AUTH_TOKEN_MISSING'
                WHEN msg LIKE '%requires authentication%'
                  OR msg LIKE '%requires user authentication%'
                  OR msg LIKE '%401%'
                  OR msg LIKE '%unauthorized%' THEN 'AUTH_UNAUTHORIZED'
                WHEN msg LIKE '%resource not accessible by integration%'
                  OR msg LIKE '%insufficient scopes%' THEN 'PERMISSION_SCOPE_INSUFFICIENT'
                WHEN msg LIKE '%access denied%'
                  OR msg LIKE '%not authorized to access this resource%'
                  OR msg LIKE '%vs30063%'
                  OR msg LIKE '%tf400813%' THEN 'PERMISSION_RESOURCE_DENIED'
                WHEN msg LIKE '%account disabled%'
                  OR msg LIKE '%account suspended%' THEN 'PERMISSION_ACCOUNT_DISABLED'
                WHEN msg LIKE '%permission denied%'
                  OR msg LIKE '%forbidden%'
                  OR msg LIKE '%403%'
                  OR msg LIKE '%not authorized%' THEN 'PERMISSION_FORBIDDEN'
                ELSE NULL
            END AS subcategory
        FROM normalized
    )
    SELECT
        category AS error_category,
        subcategory AS error_subcategory,
        category = 'AUTH' AS is_credential_failure,
        category = 'PERMISSION' AS is_authorization_failure
    FROM classified
$$;

-- View: Recent extraction runs (20)
CREATE OR REPLACE VIEW v_extraction_runs_recent AS
SELECT
    r.run_id,
    r.platform,
    r.organization_name,
    r.project_name,
    r.status,
    r.processed_repositories,
    r.total_repositories,
    r.current_repository_id,
    r.updated_at,
    r.error_message,
    c.error_category,
    c.error_subcategory,
    c.is_credential_failure,
    c.is_authorization_failure
FROM extraction_runs r
CROSS JOIN LATERAL classify_extraction_error(r.error_message) c
ORDER BY r.updated_at DESC
LIMIT 20;

-- View: Extraction metrics with repository details (recent 50)
CREATE OR REPLACE VIEW v_extraction_metrics_recent AS
SELECT 
    COALESCE(r.name, em.repository_id) AS repository,
    em.platform,
    em.status,
    em.extraction_started_at,
    em.extraction_completed_at,
    em.extraction_duration_seconds,
    em.error_message,
    c.error_category,
    c.error_subcategory,
    c.is_credential_failure,
    c.is_authorization_failure
FROM extraction_metrics em
LEFT JOIN repositories r ON em.repository_id = r.repo_id
CROSS JOIN LATERAL classify_extraction_error(em.error_message) c
ORDER BY em.extraction_started_at DESC
LIMIT 50;

-- View: Platform-level auth failures in last 24 hours
CREATE OR REPLACE VIEW v_auth_errors_by_platform AS
SELECT
    r.platform,
    c.error_category,
    COUNT(*) AS error_count,
    COUNT(DISTINCT r.run_id) AS affected_runs,
    MAX(r.updated_at) AS last_error_time
FROM extraction_runs r
CROSS JOIN LATERAL classify_extraction_error(r.error_message) c
WHERE r.status = 'failed'
  AND r.updated_at > NOW() - INTERVAL '24 hours'
  AND c.error_category IN ('AUTH', 'PERMISSION')
GROUP BY r.platform, c.error_category
ORDER BY error_count DESC;

-- View: Total auth failures in last 24 hours
CREATE OR REPLACE VIEW v_auth_errors_24h_total AS
SELECT COALESCE(SUM(error_count), 0) AS auth_errors
FROM v_auth_errors_by_platform;

-- View: Recent extraction metrics with normalized error categories
CREATE OR REPLACE VIEW v_extraction_metrics_with_errors AS
SELECT
    em.id,
    em.run_id,
    em.repository_id,
    COALESCE(r.name, em.repository_id) AS repository_name,
    em.platform,
    em.status,
    em.extraction_started_at,
    em.extraction_completed_at,
    em.extraction_duration_seconds,
    em.error_message,
    c.error_category,
    c.error_subcategory,
    c.is_credential_failure,
    c.is_authorization_failure
FROM extraction_metrics em
LEFT JOIN repositories r ON em.repository_id = r.repo_id
CROSS JOIN LATERAL classify_extraction_error(em.error_message) c
ORDER BY em.extraction_started_at DESC
LIMIT 500;

-- View: UNKNOWN extraction error patterns in the last 7 days
CREATE OR REPLACE VIEW v_extraction_errors_unknown_recent AS
SELECT
    date_trunc('day', r.updated_at) AS day,
    left(r.error_message, 80) AS message_prefix,
    count(*) AS occurrences
FROM extraction_runs r
CROSS JOIN LATERAL classify_extraction_error(r.error_message) c
WHERE r.status = 'failed'
  AND r.error_message IS NOT NULL
  AND c.error_category = 'UNKNOWN'
  AND r.updated_at >= now() - interval '7 days'
GROUP BY 1, 2
ORDER BY occurrences DESC;

-- =============================================================================
-- Team Metrics Views
-- =============================================================================

-- View 11: Team metrics aggregated
CREATE OR REPLACE VIEW v_team_metrics_summary AS
SELECT 
    t.team_id,
    t.name AS team_name,
    t.organization_id,
    SUM(tm.total_commits) AS total_commits,
    SUM(tm.total_prs_created) AS total_prs_created,
    AVG(tm.active_contributors) AS avg_active_contributors,
    MAX(tm.period_end) AS last_period_measured
FROM 
    teams t
LEFT JOIN 
    team_metrics tm ON t.team_id = tm.team_id
GROUP BY 
    t.team_id, t.name, t.organization_id;

-- =============================================================================
-- Plan 021: Dependency Vulnerability & EOL Dashboard Views (FR-5)
-- =============================================================================

-- v_package_portfolio_latest: latest snapshot per package with aggregate counts.
-- Only packages actually in use (HAVING repo_count > 0) are returned.
CREATE OR REPLACE VIEW v_package_portfolio_latest AS
SELECT
    p.id,
    p.package_name,
    p.ecosystem,
    p.latest_version,
    p.is_eol,
    p.eol_date,
    COUNT(DISTINCT rd.repo_id) AS repo_count,
    COUNT(DISTINCT s.service_id) AS service_count,
    COUNT(DISTINCT rd.repo_id) FILTER (WHERE rd.has_known_vulnerabilities = true) AS exposed_repos,
    COUNT(DISTINCT v.id) AS total_cves,
    MAX(CASE WHEN v.severity = 'CRITICAL' THEN 1 ELSE 0 END) AS has_critical_cve,
    CASE MAX(
        CASE WHEN rd.has_known_vulnerabilities = true THEN
            CASE v.severity WHEN 'CRITICAL' THEN 4 WHEN 'HIGH' THEN 3 WHEN 'MEDIUM' THEN 2 WHEN 'LOW' THEN 1 END
        END
    )
        WHEN 4 THEN 'CRITICAL'
        WHEN 3 THEN 'HIGH'
        WHEN 2 THEN 'MEDIUM'
        WHEN 1 THEN 'LOW'
    END AS max_severity_exposed
FROM packages p
LEFT JOIN repository_dependencies rd
    ON p.package_name = rd.package_name AND p.ecosystem = rd.ecosystem
LEFT JOIN repositories r ON rd.repo_id = r.repo_id
LEFT JOIN repository_services rs ON r.repo_id = rs.repo_id
LEFT JOIN services s ON rs.service_id = s.service_id
LEFT JOIN vulnerabilities v ON p.id = v.package_id
GROUP BY p.id, p.package_name, p.ecosystem, p.latest_version, p.is_eol, p.eol_date
HAVING COUNT(DISTINCT rd.repo_id) > 0;

-- v_package_health_latest: risk classification per package.
CREATE OR REPLACE VIEW v_package_health_latest AS
SELECT
    p.id,
    p.package_name,
    p.ecosystem,
    CASE
        WHEN p.is_eol THEN 'EOL'
        WHEN p.eol_date IS NOT NULL AND p.eol_date <= CURRENT_DATE THEN 'EOL'
        WHEN p.eol_date IS NOT NULL AND p.eol_date < CURRENT_DATE + INTERVAL '90 days' THEN 'APPROACHING_EOL'
        WHEN MAX(CASE WHEN v.severity = 'CRITICAL' THEN 1 ELSE 0 END) = 1
             AND COUNT(DISTINCT rd.repo_id) FILTER (WHERE rd.has_known_vulnerabilities = true) > 0
        THEN 'CRITICAL_EXPOSED'
        WHEN MAX(CASE WHEN v.severity IN ('CRITICAL', 'HIGH') THEN 1 ELSE 0 END) = 1
             AND COUNT(DISTINCT rd.repo_id) FILTER (WHERE rd.has_known_vulnerabilities = true) > 0
        THEN 'HIGH_EXPOSED'
        ELSE 'HEALTHY'
    END AS health_status,
    COUNT(DISTINCT rd.repo_id) AS repo_count,
    COUNT(DISTINCT v.id) FILTER (WHERE rd.has_known_vulnerabilities = true) AS exposed_cve_count,
    p.eol_date
FROM packages p
LEFT JOIN repository_dependencies rd
    ON p.package_name = rd.package_name AND p.ecosystem = rd.ecosystem
LEFT JOIN vulnerabilities v ON p.id = v.package_id
GROUP BY p.id, p.package_name, p.ecosystem, p.eol_date, p.is_eol;

-- v_package_adoption_timeline: daily repo-count per package over last 90 days.
CREATE OR REPLACE VIEW v_package_adoption_timeline AS
SELECT
    p.package_name,
    p.ecosystem,
    DATE(rd.last_seen_at) AS adoption_date,
    COUNT(DISTINCT rd.repo_id) AS repo_count
FROM packages p
JOIN repository_dependencies rd
    ON p.package_name = rd.package_name AND p.ecosystem = rd.ecosystem
WHERE rd.last_seen_at > NOW() - INTERVAL '90 days'
GROUP BY p.id, p.package_name, p.ecosystem, DATE(rd.last_seen_at)
ORDER BY adoption_date;

-- v_package_by_team_latest: package usage aggregated per team.
CREATE OR REPLACE VIEW v_package_by_team_latest AS
SELECT
    p.package_name,
    p.ecosystem,
    COALESCE(t.name, 'Unknown') AS team_name,
    COUNT(DISTINCT rd.repo_id) AS repo_count,
    COUNT(DISTINCT rd.repo_id) FILTER (WHERE rd.has_known_vulnerabilities = true) AS exposed_repos,
    STRING_AGG(DISTINCT rd.version, ', ' ORDER BY rd.version) AS versions_in_use
FROM packages p
LEFT JOIN repository_dependencies rd
    ON p.package_name = rd.package_name AND p.ecosystem = rd.ecosystem
LEFT JOIN repositories r ON rd.repo_id = r.repo_id
LEFT JOIN teams t ON t.team_id = r.team_id
GROUP BY p.id, p.package_name, p.ecosystem, t.name;

-- v_package_vulnerabilities_detail: per-package CVE detail with exposed repo count.
CREATE OR REPLACE VIEW v_package_vulnerabilities_detail AS
SELECT
    p.package_name,
    p.ecosystem,
    v.cve_id,
    v.severity,
    v.summary,
    v.fixed_in_version,
    v.published_date,
    COUNT(DISTINCT rd.repo_id) FILTER (WHERE rd.has_known_vulnerabilities = true) AS exposed_repo_count
FROM packages p
JOIN vulnerabilities v ON p.id = v.package_id
LEFT JOIN repository_dependencies rd ON (
    p.package_name = rd.package_name
    AND p.ecosystem = rd.ecosystem
    AND rd.has_known_vulnerabilities = true
)
GROUP BY p.id, p.package_name, p.ecosystem,
         v.id, v.cve_id, v.severity, v.summary, v.fixed_in_version, v.published_date;
