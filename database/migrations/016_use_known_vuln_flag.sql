-- Migration 016: Switch vulnerability counts to has_known_vulnerabilities flag
--
-- SEMANTIC CHANGE: vulnerability counts in the dashboard will drop for repos
-- that are on a patched version of a package.  This is intentional — the
-- previous JOIN-based approach counted every CVE linked to a package regardless
-- of whether the repo's pinned version was actually affected.  The flag
-- has_known_vulnerabilities is set only when the repo's version is below
-- fixed_in_version, so using it eliminates false positives.
--
-- Views changed:
--   v_repo_dependency_rollup_latest     — replaces LEFT JOIN + COUNT(DISTINCT v.id)
--                                          with COUNT(*) FILTER (WHERE flag = true)
--   v_service_vulnerabilities_by_severity — adds AND d.has_known_vulnerabilities = true
--                                            to the WHERE clause

DO $$ BEGIN

    -- Recreate v_repo_dependency_rollup_latest using the flag instead of a JOIN.
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

    -- Recreate v_service_vulnerabilities_by_severity restricted to exposed repos.
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

END $$;
