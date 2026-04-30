-- Migration 014: Normalise package metadata into a dedicated packages table
--
-- Splits the dependencies table into:
--   packages              — version-agnostic global facts (EOL, latest version)
--   repository_dependencies — per-repo usage + version-specific has_known_vulnerabilities
--
-- Vulnerabilities are re-linked from dependencies.id → packages.id so the same
-- CVE is stored once per package rather than once per repo.

-- ── Phase 1: Create packages table ───────────────────────────────────────────
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'packages'
    ) THEN
        CREATE TABLE packages (
            id SERIAL PRIMARY KEY,
            package_name VARCHAR(500) NOT NULL,
            ecosystem VARCHAR(100) NOT NULL,
            latest_version VARCHAR(100),
            is_eol BOOLEAN NOT NULL DEFAULT FALSE,
            eol_date DATE,
            enriched_at TIMESTAMPTZ,
            CONSTRAINT uq_package UNIQUE (package_name, ecosystem)
        );
        CREATE INDEX idx_pkg_eol ON packages(is_eol, eol_date);
        CREATE INDEX idx_pkg_eco ON packages(ecosystem);
    END IF;
END $$;

-- ── Phase 2: Populate packages from existing dependencies ─────────────────────
-- Pick the most recently-seen row per (package_name, ecosystem) for metadata.
-- has_vulnerabilities is intentionally NOT migrated — it is version-specific
-- and will be recomputed per-repo as has_known_vulnerabilities on the next scan.
DO $$ BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = 'dependencies'
    ) THEN
        INSERT INTO packages (package_name, ecosystem, latest_version, is_eol, eol_date, enriched_at)
        SELECT DISTINCT ON (package_name, ecosystem)
            package_name,
            ecosystem,
            latest_version,
            is_eol,
            eol_date,
            NOW()
        FROM dependencies
        ORDER BY package_name, ecosystem, last_seen_at DESC
        ON CONFLICT (package_name, ecosystem) DO NOTHING;
    END IF;
END $$;

-- ── Phase 3: Add package_id to vulnerabilities and populate it ────────────────
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'vulnerabilities' AND column_name = 'package_id'
    ) THEN
        ALTER TABLE vulnerabilities ADD COLUMN package_id INTEGER;
    END IF;
END $$;

DO $$ BEGIN
        IF EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                    AND table_name = 'dependencies'
        )
        AND EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                    AND table_name = 'vulnerabilities'
                    AND column_name = 'dependency_id'
        ) THEN
                UPDATE vulnerabilities v
                SET package_id = p.id
                FROM dependencies d
                JOIN packages p ON p.package_name = d.package_name AND p.ecosystem = d.ecosystem
                WHERE v.dependency_id = d.id
                    AND v.package_id IS NULL;
        END IF;
END $$;

-- Make package_id NOT NULL and add FK only when all rows are populated
DO $$ BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'vulnerabilities'
          AND column_name = 'package_id'
          AND is_nullable = 'YES'
    ) THEN
        IF NOT EXISTS (SELECT 1 FROM vulnerabilities WHERE package_id IS NULL) THEN
            ALTER TABLE vulnerabilities ALTER COLUMN package_id SET NOT NULL;
            ALTER TABLE vulnerabilities
                ADD CONSTRAINT fk_vuln_package
                FOREIGN KEY (package_id) REFERENCES packages(id) ON DELETE CASCADE;
        END IF;
    END IF;
END $$;

-- Drop all views that reference dependency_id or the old dependencies table
-- before we rename columns/tables.  Migration 014 re-applies views.sql at the
-- end once the schema is in its final state.
DROP VIEW IF EXISTS v_service_repository_breakdown CASCADE;
DROP VIEW IF EXISTS v_service_vulnerabilities_by_severity CASCADE;
DROP VIEW IF EXISTS v_repo_dependency_rollup_latest CASCADE;
DROP VIEW IF EXISTS v_team_repository_health_matrix CASCADE;
DROP VIEW IF EXISTS v_repo_vulnerabilities_by_severity_latest CASCADE;
DROP VIEW IF EXISTS v_repo_vulnerability_details_latest CASCADE;
DROP VIEW IF EXISTS v_security_overview_latest CASCADE;
DROP VIEW IF EXISTS v_security_vulnerabilities_by_severity_latest CASCADE;
DROP VIEW IF EXISTS v_security_top_repositories_critical_vulns CASCADE;
DROP VIEW IF EXISTS v_security_repository_overview CASCADE;
DROP VIEW IF EXISTS v_security_vulnerability_trend CASCADE;
DROP VIEW IF EXISTS v_security_top_vulnerable_dependencies CASCADE;
DROP VIEW IF EXISTS v_team_vulnerabilities_total_latest CASCADE;
DROP VIEW IF EXISTS v_team_vulnerabilities_by_severity_latest CASCADE;
DROP VIEW IF EXISTS v_dependency_snapshot_latest CASCADE;
DROP VIEW IF EXISTS v_repo_dependency_rollup_latest CASCADE;
DROP VIEW IF EXISTS v_dependency_summary CASCADE;
DROP VIEW IF EXISTS v_security_eol_status_latest CASCADE;

-- Drop the old dependency_id FK and column
DO $$ BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'vulnerabilities' AND column_name = 'dependency_id'
    ) THEN
        ALTER TABLE vulnerabilities DROP COLUMN dependency_id;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_vuln_package ON vulnerabilities(package_id);

-- ── Phase 4: Rename dependencies → repository_dependencies ───────────────────
DO $$ BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'dependencies'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'repository_dependencies'
    ) THEN
        ALTER TABLE dependencies RENAME TO repository_dependencies;
    END IF;
END $$;

-- ── Phase 5: Clean up version-agnostic columns on repository_dependencies ─────
-- Drop: latest_version, is_eol, eol_date (now in packages)
-- Rename: has_vulnerabilities → has_known_vulnerabilities (version-specific flag)
DO $$ BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'repository_dependencies' AND column_name = 'is_eol'
    ) THEN
        ALTER TABLE repository_dependencies
            DROP COLUMN IF EXISTS is_eol,
            DROP COLUMN IF EXISTS eol_date,
            DROP COLUMN IF EXISTS latest_version;
    END IF;
END $$;

DO $$ BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'repository_dependencies' AND column_name = 'has_vulnerabilities'
    ) THEN
        ALTER TABLE repository_dependencies
            RENAME COLUMN has_vulnerabilities TO has_known_vulnerabilities;
    END IF;
END $$;

-- Partial index for fast vulnerable-repo queries
CREATE INDEX IF NOT EXISTS idx_repodep_vuln
    ON repository_dependencies(has_known_vulnerabilities)
    WHERE has_known_vulnerabilities = true;

-- Rename indexes that referenced the old table name (best-effort; ignore if they don't exist)
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_dep_repo') THEN
        ALTER INDEX idx_dep_repo RENAME TO idx_repodep_repo;
    END IF;
END $$;

DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_dep_branch') THEN
        ALTER INDEX idx_dep_branch RENAME TO idx_repodep_branch;
    END IF;
END $$;

DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_dep_has_vuln') THEN
        ALTER INDEX idx_dep_has_vuln RENAME TO idx_repodep_has_vuln_old;
    END IF;
END $$;

DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_dep_is_eol') THEN
        ALTER INDEX idx_dep_is_eol RENAME TO idx_repodep_is_eol_dropped;
    END IF;
END $$;

DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_dep_last_seen') THEN
        ALTER INDEX idx_dep_last_seen RENAME TO idx_repodep_last_seen;
    END IF;
END $$;

DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_dep_security') THEN
        ALTER INDEX idx_dep_security RENAME TO idx_repodep_security_old;
    END IF;
END $$;

-- ── Phase 6: Re-apply reporting views ────────────────────────────────────────
-- Views created by migration 011 referenced the old `dependencies` table and
-- have_vulnerabilities column.  Now that the schema has changed, recreate all
-- reporting views against the new `repository_dependencies` + `packages` tables.

\ir ../views.sql
