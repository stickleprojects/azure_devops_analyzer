-- Migration 019: Extraction Health Log (Plan 020 Component 3)
--
-- Creates the extraction_health_log table used by src/utils/metrics.py to
-- persist per-invariant health check results after each production extraction.
-- Grafana dashboards query this table to show violation counts and trends.

DO $$ BEGIN

    -- ----------------------------------------------------------------
    -- Table: extraction_health_log
    -- One row per invariant per extraction run.
    -- ----------------------------------------------------------------
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables
                   WHERE table_name = 'extraction_health_log') THEN
        CREATE TABLE extraction_health_log (
            id              BIGSERIAL PRIMARY KEY,
            platform        VARCHAR(50)  NOT NULL,
            repo_id         VARCHAR(255),               -- NULL = whole-DB check
            invariant_name  VARCHAR(255) NOT NULL,
            violations      INTEGER      NOT NULL DEFAULT 0,
            sample_rows     JSONB        NOT NULL DEFAULT '[]'::jsonb,
            checked_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        );

        CREATE INDEX idx_ehl_platform_checked_at
            ON extraction_health_log (platform, checked_at DESC);

        CREATE INDEX idx_ehl_invariant_checked_at
            ON extraction_health_log (invariant_name, checked_at DESC);

        RAISE NOTICE 'Created extraction_health_log table';
    ELSE
        RAISE NOTICE 'extraction_health_log already exists — skipping';
    END IF;

END $$;
