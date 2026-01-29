-- Migration 006: Add team contributors and team metrics tables
-- Purpose: Implement many-to-many contributor-team relationships
-- Implements: FR-11.2, FR-11.3, FR-11.5

-- Step 1: Create team_contributors junction table
CREATE TABLE IF NOT EXISTS team_contributors (
    id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams(team_id) ON DELETE CASCADE,
    contributor_id INTEGER NOT NULL REFERENCES contributors(id) ON DELETE CASCADE,
    effective_start_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    effective_end_date TIMESTAMPTZ,
    CONSTRAINT uq_team_contributor UNIQUE (team_id, contributor_id)
);

CREATE INDEX IF NOT EXISTS idx_team_contributors_team_id ON team_contributors(team_id);
CREATE INDEX IF NOT EXISTS idx_team_contributors_contributor_id ON team_contributors(contributor_id);
CREATE INDEX IF NOT EXISTS idx_team_contributors_effective_dates ON team_contributors(effective_start_date, effective_end_date);

-- Step 2: Migrate existing data from contributors.team_id (if column exists)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='contributors' AND column_name='team_id'
    ) THEN
        -- Migrate existing team assignments to junction table
        INSERT INTO team_contributors (team_id, contributor_id, effective_start_date)
        SELECT team_id, id, NOW()
        FROM contributors
        WHERE team_id IS NOT NULL
        ON CONFLICT (team_id, contributor_id) DO NOTHING;
        
        -- Drop the old foreign key constraint
        ALTER TABLE contributors
        DROP CONSTRAINT IF EXISTS fk_contributor_team;
        
        -- Drop the old team_id column
        ALTER TABLE contributors
        DROP COLUMN IF EXISTS team_id;
    END IF;
END $$;

-- Step 3: Create team_metrics table (TimescaleDB hypertable for time-series)
CREATE TABLE IF NOT EXISTS team_metrics (
    id SERIAL,
    team_id INTEGER NOT NULL REFERENCES teams(team_id) ON DELETE CASCADE,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    total_commits INTEGER DEFAULT 0,
    total_lines_added INTEGER DEFAULT 0,
    total_lines_removed INTEGER DEFAULT 0,
    total_files_modified INTEGER DEFAULT 0,
    total_prs_created INTEGER DEFAULT 0,
    total_pr_reviews INTEGER DEFAULT 0,
    total_pr_approvals INTEGER DEFAULT 0,
    avg_pr_size_lines NUMERIC(10, 2),
    active_contributors INTEGER DEFAULT 0,
    avg_commit_message_quality NUMERIC(5, 2),
    PRIMARY KEY (id, period_start)
);

-- Convert to TimescaleDB hypertable if extension is available
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = 'team_metrics' 
            AND table_schema NOT LIKE 'pg_%'
        ) THEN
            -- Table already exists, skip hypertable creation
            NULL;
        ELSE
            SELECT create_hypertable('team_metrics', 'period_start',
                if_not_exists => TRUE,
                chunk_time_interval => INTERVAL '1 month');
        END IF;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_team_metrics_team_id ON team_metrics(team_id, period_start DESC);
CREATE INDEX IF NOT EXISTS idx_team_metrics_period ON team_metrics(period_start DESC, period_end DESC);
