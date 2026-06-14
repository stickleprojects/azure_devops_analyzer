-- Migration 022: per-run scan_summary digest table + historical backfill
--
-- One row per completed extraction_runs.run_id with headline scan totals.
-- Re-runnable safely: table/index creation are guarded and backfill is an upsert.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'scan_summary'
    ) THEN
        CREATE TABLE scan_summary (
            run_id UUID PRIMARY KEY REFERENCES extraction_runs(run_id) ON DELETE CASCADE,
            scan_completed_at TIMESTAMPTZ NOT NULL,
            repos_scanned INTEGER NOT NULL DEFAULT 0,
            new_repos INTEGER NOT NULL DEFAULT 0,
            retired_repos INTEGER NOT NULL DEFAULT 0,
            total_new_commits INTEGER NOT NULL DEFAULT 0,
            contributors INTEGER NOT NULL DEFAULT 0,
            new_libraries INTEGER NOT NULL DEFAULT 0,
            new_vulnerabilities INTEGER NOT NULL DEFAULT 0
        );
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_indexes
        WHERE schemaname = 'public' AND indexname = 'idx_scan_summary_completed_at'
    ) THEN
        CREATE INDEX idx_scan_summary_completed_at
            ON scan_summary(scan_completed_at DESC);
    END IF;
END $$;

WITH ordered_runs AS (
    SELECT
        er.run_id,
        er.platform,
        er.completed_at AS scan_completed_at,
        LAG(er.completed_at) OVER (
            PARTITION BY er.platform
            ORDER BY er.completed_at, er.started_at, er.updated_at
        ) AS previous_completed_at
    FROM extraction_runs er
    WHERE er.completed_at IS NOT NULL
),
current_membership AS (
    SELECT
        em.run_id,
        COUNT(DISTINCT em.repository_id) AS repos_scanned,
        SUM(COALESCE(em.commits_extracted, 0)) AS total_new_commits,
        SUM(COALESCE(em.contributors_extracted, 0)) AS contributors
    FROM extraction_metrics em
    GROUP BY em.run_id
),
new_repo_counts AS (
    SELECT
        orun.run_id,
        COUNT(*) AS new_repos
    FROM ordered_runs orun
    JOIN extraction_metrics curr
      ON curr.run_id = orun.run_id
    LEFT JOIN extraction_runs prev_run
      ON prev_run.platform = orun.platform
     AND prev_run.completed_at = orun.previous_completed_at
    LEFT JOIN extraction_metrics prev
      ON prev.run_id = prev_run.run_id
     AND prev.repository_id = curr.repository_id
    WHERE prev.repository_id IS NULL
    GROUP BY orun.run_id
),
retired_repo_counts AS (
    SELECT
        orun.run_id,
        COUNT(*) AS retired_repos
    FROM ordered_runs orun
    JOIN extraction_runs prev_run
      ON prev_run.platform = orun.platform
     AND prev_run.completed_at = orun.previous_completed_at
    JOIN extraction_metrics prev
      ON prev.run_id = prev_run.run_id
    LEFT JOIN extraction_metrics curr
      ON curr.run_id = orun.run_id
     AND curr.repository_id = prev.repository_id
    WHERE curr.repository_id IS NULL
    GROUP BY orun.run_id
),
new_dependency_counts AS (
    SELECT
        orun.run_id,
        COUNT(*) AS new_libraries,
        -- FILTER is supported on PostgreSQL 9.4+ (project baseline is 15+).
        COUNT(*) FILTER (WHERE rd.has_known_vulnerabilities) AS new_vulnerabilities
    FROM ordered_runs orun
    JOIN repository_dependencies rd
      ON EXISTS (
          SELECT 1
          FROM extraction_metrics em
          WHERE em.run_id = orun.run_id
            AND em.repository_id = rd.repo_id
      )
    WHERE rd.first_seen_at <= orun.scan_completed_at
      AND (
          orun.previous_completed_at IS NULL
          OR rd.first_seen_at > orun.previous_completed_at
      )
    GROUP BY orun.run_id
)
INSERT INTO scan_summary (
    run_id,
    scan_completed_at,
    repos_scanned,
    new_repos,
    retired_repos,
    total_new_commits,
    contributors,
    new_libraries,
    new_vulnerabilities
)
SELECT
    orun.run_id,
    orun.scan_completed_at,
    COALESCE(cm.repos_scanned, 0) AS repos_scanned,
    COALESCE(nr.new_repos, 0) AS new_repos,
    COALESCE(rr.retired_repos, 0) AS retired_repos,
    COALESCE(cm.total_new_commits, 0) AS total_new_commits,
    COALESCE(cm.contributors, 0) AS contributors,
    COALESCE(nd.new_libraries, 0) AS new_libraries,
    COALESCE(nd.new_vulnerabilities, 0) AS new_vulnerabilities
FROM ordered_runs orun
LEFT JOIN current_membership cm ON cm.run_id = orun.run_id
LEFT JOIN new_repo_counts nr ON nr.run_id = orun.run_id
LEFT JOIN retired_repo_counts rr ON rr.run_id = orun.run_id
LEFT JOIN new_dependency_counts nd ON nd.run_id = orun.run_id
ON CONFLICT (run_id) DO UPDATE
SET
    scan_completed_at = EXCLUDED.scan_completed_at,
    repos_scanned = EXCLUDED.repos_scanned,
    new_repos = EXCLUDED.new_repos,
    retired_repos = EXCLUDED.retired_repos,
    total_new_commits = EXCLUDED.total_new_commits,
    contributors = EXCLUDED.contributors,
    new_libraries = EXCLUDED.new_libraries,
    new_vulnerabilities = EXCLUDED.new_vulnerabilities;
