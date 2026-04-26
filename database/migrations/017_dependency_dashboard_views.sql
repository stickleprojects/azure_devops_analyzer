-- Migration 017: Dependency Vulnerability & EOL Dashboard Views (Plan 021 / FR-5)
--
-- Creates five portfolio-level views for the dependency vulnerability dashboard:
--   v_package_portfolio_latest        — aggregate repo/service/CVE counts per package
--   v_package_health_latest           — risk classification per package
--   v_package_adoption_timeline       — historical adoption trend (last 90 days)
--   v_package_by_team_latest          — package usage grouped by team
--   v_package_vulnerabilities_detail  — per-package CVE detail
--
-- Prerequisites: Plan 012 (packages, repository_dependencies, vulnerabilities tables)
-- and Plan 012 R-B (has_known_vulnerabilities flag on repository_dependencies).

DO $$ BEGIN

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
        MAX(v.severity) FILTER (
            WHERE rd.has_known_vulnerabilities = true
        ) AS max_severity_exposed
    FROM packages p
    LEFT JOIN repository_dependencies rd
        ON p.package_name = rd.package_name AND p.ecosystem = rd.ecosystem
    LEFT JOIN repositories r ON rd.repo_id = r.repo_id
    LEFT JOIN repository_services rs ON r.repo_id = rs.repo_id
    LEFT JOIN services s ON rs.service_id = s.service_id
    LEFT JOIN vulnerabilities v ON p.id = v.package_id
    GROUP BY p.id, p.package_name, p.ecosystem, p.latest_version, p.is_eol, p.eol_date
    HAVING COUNT(DISTINCT rd.repo_id) > 0;

    CREATE OR REPLACE VIEW v_package_health_latest AS
    SELECT
        p.id,
        p.package_name,
        p.ecosystem,
        CASE
            WHEN p.is_eol THEN 'EOL'
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

    CREATE OR REPLACE VIEW v_package_by_team_latest AS
    SELECT
        p.package_name,
        p.ecosystem,
        COALESCE(t.name, 'Unknown') AS team_name,
        COUNT(DISTINCT rd.repo_id) AS repo_count,
        COUNT(DISTINCT rd.repo_id) FILTER (WHERE rd.has_known_vulnerabilities = true) AS exposed_repos,
        STRING_AGG(DISTINCT rd.version, ', ') AS versions_in_use
    FROM packages p
    LEFT JOIN repository_dependencies rd
        ON p.package_name = rd.package_name AND p.ecosystem = rd.ecosystem
    LEFT JOIN repositories r ON rd.repo_id = r.repo_id
    LEFT JOIN teams t ON t.team_id = r.team_id
    GROUP BY p.id, p.package_name, p.ecosystem, t.name;

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

END $$;
