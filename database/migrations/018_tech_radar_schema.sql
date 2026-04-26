-- Migration 017: Tech Radar Schema (Plan 022)
--
-- Creates three tables for managing Thoughtworks Tech Radar publications:
--   radar_publications  — versioned radar snapshots
--   radar_blips         — individual technology entries per publication
--   radar_blip_history  — movement history for timeline view

DO $$ BEGIN

    -- ----------------------------------------------------------------
    -- Table: radar_publications
    -- Each row is one published radar snapshot.
    -- ----------------------------------------------------------------
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables
                   WHERE table_name = 'radar_publications') THEN
        CREATE TABLE radar_publications (
            id                  SERIAL PRIMARY KEY,
            publication_date    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            publication_version VARCHAR(50),
            description         TEXT,
            published_by        VARCHAR(255),
            is_latest           BOOLEAN DEFAULT TRUE,
            metadata            JSONB,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE INDEX idx_radar_pub_latest ON radar_publications(is_latest)
            WHERE is_latest = TRUE;
        CREATE INDEX idx_radar_pub_date   ON radar_publications(publication_date DESC);

        RAISE NOTICE 'Created table radar_publications';
    ELSE
        RAISE NOTICE 'Table radar_publications already exists — skipping';
    END IF;

    -- ----------------------------------------------------------------
    -- Table: radar_blips
    -- Individual technology blips linked to a publication.
    -- ----------------------------------------------------------------
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables
                   WHERE table_name = 'radar_blips') THEN
        CREATE TABLE radar_blips (
            id               SERIAL PRIMARY KEY,
            publication_id   INTEGER NOT NULL
                                 REFERENCES radar_publications(id) ON DELETE CASCADE,
            package_name     VARCHAR(500) NOT NULL,
            ecosystem        VARCHAR(100) NOT NULL,
            ring             VARCHAR(50)  NOT NULL,   -- Adopt | Trial | Assess | Hold
            quadrant         VARCHAR(50)  NOT NULL,   -- Infrastructure | Platforms | Tools | Languages & Frameworks
            label            TEXT,
            description      TEXT,
            is_new           BOOLEAN DEFAULT FALSE,
            is_moved         BOOLEAN DEFAULT FALSE,
            adopted_date     DATE,
            repo_count       INTEGER,
            exposed_to_cves  INTEGER DEFAULT 0,
            is_eol           BOOLEAN DEFAULT FALSE,
            eol_date         DATE,
            latest_version   VARCHAR(100),
            flags            JSONB,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE INDEX idx_blip_pub      ON radar_blips(publication_id);
        CREATE INDEX idx_blip_name_eco ON radar_blips(package_name, ecosystem);
        CREATE INDEX idx_blip_ring     ON radar_blips(ring);

        RAISE NOTICE 'Created table radar_blips';
    ELSE
        RAISE NOTICE 'Table radar_blips already exists — skipping';
    END IF;

    -- ----------------------------------------------------------------
    -- Table: radar_blip_history
    -- Ring-movement history for each (package, ecosystem) pair.
    -- ----------------------------------------------------------------
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables
                   WHERE table_name = 'radar_blip_history') THEN
        CREATE TABLE radar_blip_history (
            id                   SERIAL PRIMARY KEY,
            package_name         VARCHAR(500) NOT NULL,
            ecosystem            VARCHAR(100) NOT NULL,
            publication_date     DATE         NOT NULL,
            prior_ring           VARCHAR(50),
            current_ring         VARCHAR(50)  NOT NULL,
            repo_count_delta     INTEGER,
            vulnerability_change TEXT,          -- now_exposed | fixed | unchanged
            created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE INDEX idx_blip_hist_name ON radar_blip_history(package_name, ecosystem);
        CREATE INDEX idx_blip_hist_date ON radar_blip_history(publication_date DESC);

        RAISE NOTICE 'Created table radar_blip_history';
    ELSE
        RAISE NOTICE 'Table radar_blip_history already exists — skipping';
    END IF;

END $$;
