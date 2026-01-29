-- Migration 007: Fix contributor_metrics primary key for SQLAlchemy 2.0+ compatibility
-- 
-- Changes composite primary key (id, period_start) to single primary key (id)
-- with unique constraint on (repo_id, contributor_id, period_start) for time-series uniqueness.
-- This resolves SQLAlchemy autoincrement issues and NULL insertion errors.

-- Drop the hypertable (must be done before altering table structure)
SELECT drop_hypertable('contributor_metrics', if_exists => TRUE);

-- Recreate the table with corrected schema
DROP TABLE IF EXISTS contributor_metrics CASCADE;

CREATE TABLE contributor_metrics (
    id BIGSERIAL PRIMARY KEY,
    repo_id VARCHAR(255),
    contributor_id INTEGER,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    commit_count INTEGER DEFAULT 0,
    lines_added INTEGER DEFAULT 0,
    lines_removed INTEGER DEFAULT 0,
    files_modified INTEGER DEFAULT 0,
    pr_created INTEGER DEFAULT 0,
    pr_reviews INTEGER DEFAULT 0,
    pr_approvals INTEGER DEFAULT 0,
    active_days INTEGER DEFAULT 0,
    avg_commit_message_quality DECIMAL(5,2),
    UNIQUE (repo_id, contributor_id, period_start),
    CONSTRAINT fk_contribmetrics_repository FOREIGN KEY (repo_id) REFERENCES repositories(repo_id) ON DELETE CASCADE,
    CONSTRAINT fk_contribmetrics_contributor FOREIGN KEY (contributor_id) REFERENCES contributors(id) ON DELETE CASCADE
);

CREATE INDEX idx_contrib_metrics_repo ON contributor_metrics(repo_id);
CREATE INDEX idx_contrib_metrics_contributor ON contributor_metrics(contributor_id);

-- Re-create the hypertable with period_start as time column
SELECT create_hypertable('contributor_metrics', 'period_start',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE
);
