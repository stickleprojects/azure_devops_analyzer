-- Migration 011: Add reporting views for Grafana dashboards
-- Replaces embedded SQL in dashboard JSON files with testable PostgreSQL views.
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
    COUNT(DISTINCT rl.language) AS language_count,
    MAX(c.commit_date) AS last_commit_date
FROM 
    repositories r
LEFT JOIN 
    commits c ON c.repo_id = r.repo_id
LEFT JOIN 
    pull_requests pr ON pr.repo_id = r.repo_id
LEFT JOIN 
    repository_languages rl ON rl.repo_id = r.repo_id
GROUP BY 
    r.repo_id, r.name, r.is_active;

-- View 7: Language distribution per repository
CREATE OR REPLACE VIEW v_language_summary AS
SELECT repo_id, language, percentage, byte_count
FROM repository_languages;

-- View: Active repositories count
CREATE OR REPLACE VIEW v_active_repositories_total AS
SELECT COUNT(*) AS total
FROM repositories
WHERE is_active = true;

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
    repo_id,
    package_name,
    ecosystem,
    version,
    latest_version,
    has_vulnerabilities,
    is_eol,
    eol_date
FROM 
    dependencies;

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

-- View: Recent extraction runs (20)
CREATE OR REPLACE VIEW v_extraction_runs_recent AS
SELECT run_id, platform, organization_name, project_name, status, processed_repositories, total_repositories, current_repository_id, updated_at
FROM extraction_runs
ORDER BY updated_at DESC
LIMIT 20;

-- View: Extraction metrics with repository details (recent 50)
CREATE OR REPLACE VIEW v_extraction_metrics_recent AS
SELECT 
    r.name AS repository,
    em.platform,
    em.status,
    em.extraction_started_at,
    em.extraction_completed_at,
    em.extraction_duration_seconds
FROM extraction_metrics em
JOIN repositories r ON em.repository_id = r.repo_id
ORDER BY em.extraction_started_at DESC
LIMIT 50;

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
