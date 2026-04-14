-- =============================================================================
-- Migration 015: Add repository_stack and technologies tables
-- =============================================================================
-- Description: Replaces repository_languages with unified repository_stack table
--              that stores all TechnologyDetector results. Adds technologies table
--              for global EOL metadata per technology.
-- Date: 2026-04-14
-- Requirement: Plan 011 - Technology Detection Persistence & EOL Enrichment
-- =============================================================================

-- ── technologies: global EOL metadata per technology ──────────────────────────
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = 'technologies'
    ) THEN
        CREATE TABLE technologies (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            category VARCHAR(50) NOT NULL,
                -- language | framework | database | deployment_platform
                -- build_tool | testing_framework | ci_cd | documentation
            is_eol BOOLEAN NOT NULL DEFAULT FALSE,
            eol_date DATE,
            latest_supported_version VARCHAR(100),
            eol_enriched_at TIMESTAMPTZ,
            CONSTRAINT uq_technology UNIQUE (name, category)
        );
        CREATE INDEX IF NOT EXISTS idx_tech_eol ON technologies(is_eol, eol_date);
        CREATE INDEX IF NOT EXISTS idx_tech_cat ON technologies(category);
    END IF;
END $$;

-- ── repository_stack: per-repo technology usage ───────────────────────────────
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = 'repository_stack'
    ) THEN
        CREATE TABLE repository_stack (
            id SERIAL PRIMARY KEY,
            repo_id VARCHAR(255) NOT NULL,
            branch_id INTEGER,
            category VARCHAR(50) NOT NULL,
            name VARCHAR(200) NOT NULL,
            source VARCHAR(20) NOT NULL DEFAULT 'heuristic',
                -- 'platform_api' (from GitHub/ADO API)
                -- 'heuristic'    (from TechnologyDetector)

            -- language-specific (non-null when category='language', source='platform_api')
            percentage NUMERIC(5,2),
            line_count INTEGER,
            byte_count BIGINT,

            -- heuristic-specific (non-null when source='heuristic')
            confidence NUMERIC(4,3),            -- 0.000-1.000

            first_seen_at TIMESTAMPTZ NOT NULL,
            last_seen_at TIMESTAMPTZ NOT NULL,

            CONSTRAINT fk_stack_repo
                FOREIGN KEY (repo_id) REFERENCES repositories(repo_id) ON DELETE CASCADE,
            CONSTRAINT fk_stack_branch
                FOREIGN KEY (branch_id) REFERENCES branches(branch_id) ON DELETE CASCADE,
            CONSTRAINT uq_stack
                UNIQUE (repo_id, category, name)
        );
        CREATE INDEX IF NOT EXISTS idx_stack_repo_category ON repository_stack(repo_id, category);
        CREATE INDEX IF NOT EXISTS idx_stack_name ON repository_stack(name);
        CREATE INDEX IF NOT EXISTS idx_stack_cat_name ON repository_stack(category, name);
        CREATE INDEX IF NOT EXISTS idx_stack_source ON repository_stack(source, category);
    END IF;
END $$;

-- ── Migrate existing repository_languages data ────────────────────────────────
DO $$ BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = 'repository_languages'
    ) THEN
        INSERT INTO repository_stack (
            repo_id, branch_id, category, name, source,
            percentage, line_count, byte_count,
            first_seen_at, last_seen_at
        )
        SELECT
            repo_id, branch_id, 'language', language, 'platform_api',
            percentage, line_count, byte_count,
            first_seen_at, last_seen_at
        FROM repository_languages
        ON CONFLICT (repo_id, category, name) DO NOTHING;
    END IF;
END $$;

-- ── Update views that reference repository_languages ─────────────────────────

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

CREATE OR REPLACE VIEW v_language_summary AS
SELECT repo_id, name AS language, percentage, byte_count
FROM repository_stack
WHERE category = 'language';

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

-- ── Drop old table ─────────────────────────────────────────────────────────────
DO $$ BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = 'repository_languages'
    ) THEN
        DROP TABLE repository_languages CASCADE;
    END IF;
END $$;
