-- =============================================================================
-- Migration 010: Add Service Metrics Table
-- =============================================================================
-- Description: Creates service_metrics time-series table for aggregating
--              repository metrics at the service level
-- Date: 2026-02-20
-- Requirement: FR-10.4 - Service-level metric aggregation
-- =============================================================================

-- Ensure TimescaleDB extension is available
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create service_metrics table (idempotent)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'service_metrics'
    ) THEN
        CREATE TABLE service_metrics (
            id SERIAL,
            service_id INTEGER NOT NULL,
            period_start TIMESTAMPTZ NOT NULL,
            period_end TIMESTAMPTZ NOT NULL,
            
            -- Repository counts
            total_repositories INTEGER DEFAULT 0,
            active_repositories INTEGER DEFAULT 0,  -- repos with commits in period
            
            -- Commit metrics (aggregated from contributor_metrics)
            total_commits INTEGER DEFAULT 0,
            total_lines_added INTEGER DEFAULT 0,
            total_lines_removed INTEGER DEFAULT 0,
            total_files_modified INTEGER DEFAULT 0,
            
            -- Pull request metrics
            total_prs_created INTEGER DEFAULT 0,
            total_prs_merged INTEGER DEFAULT 0,
            avg_pr_review_time_hours NUMERIC(10,2),
            
            -- Quality metrics (averaged across repos)
            avg_test_coverage NUMERIC(5,2),
            avg_maintainability_index NUMERIC(5,2),
            total_quality_issues INTEGER DEFAULT 0,
            
            -- Security metrics
            total_vulnerabilities INTEGER DEFAULT 0,
            critical_vulnerabilities INTEGER DEFAULT 0,
            high_vulnerabilities INTEGER DEFAULT 0,
            
            -- Dependency health
            total_dependencies INTEGER DEFAULT 0,
            eol_dependencies INTEGER DEFAULT 0,
            
            -- Activity metrics
            unique_contributors INTEGER DEFAULT 0,
            
            -- Audit
            computed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            
            PRIMARY KEY (id, period_start),
            CONSTRAINT fk_servicemetrics_service 
                FOREIGN KEY (service_id) 
                REFERENCES services(service_id) 
                ON DELETE CASCADE
        );
        
        RAISE NOTICE 'Created table: service_metrics';
    ELSE
        RAISE NOTICE 'Table service_metrics already exists, skipping creation';
    END IF;
END
$$;

-- Convert to hypertable (idempotent)
DO $$
BEGIN
    -- Check if already a hypertable
    IF NOT EXISTS (
        SELECT 1 FROM timescaledb_information.hypertables 
        WHERE hypertable_name = 'service_metrics'
    ) THEN
        PERFORM create_hypertable(
            'service_metrics', 
            'period_start',
            chunk_time_interval => INTERVAL '1 month',
            if_not_exists => TRUE
        );
        RAISE NOTICE 'Converted service_metrics to hypertable';
    ELSE
        RAISE NOTICE 'service_metrics is already a hypertable, skipping conversion';
    END IF;
END
$$;

-- Create indexes (idempotent)
CREATE INDEX IF NOT EXISTS idx_service_metrics_service_period 
    ON service_metrics(service_id, period_start DESC);

CREATE INDEX IF NOT EXISTS idx_service_metrics_period 
    ON service_metrics(period_start DESC, period_end DESC);

-- Add table comment
COMMENT ON TABLE service_metrics IS 
    'Aggregated metrics across all repositories belonging to a service. Time-series data stored in TimescaleDB hypertable with 1-month chunks.';

-- Migration complete
DO $$
BEGIN
    RAISE NOTICE 'Migration 010 completed: service_metrics table ready';
END
$$;
