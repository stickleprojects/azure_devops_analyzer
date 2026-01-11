# Data Storage Layer

## Overview

The storage layer uses PostgreSQL with TimescaleDB extension for efficient time-series data handling and comprehensive querying capabilities for Grafana.

## Database Setup

The system requires PostgreSQL 15 with the TimescaleDB extension enabled. Additional extensions `pg_trgm` and `btree_gin` are used for text search and indexing.

## Database Schema

### Core Entity Tables

```sql
-- Organizations and Projects
CREATE TABLE organizations (
    organization_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE projects (
    project_id SERIAL PRIMARY KEY,
    organization_id INTEGER REFERENCES organizations(organization_id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(organization_id, name)
);

-- Repositories
CREATE TABLE repositories (
    repo_id VARCHAR(255) PRIMARY KEY,  -- Azure DevOps repo ID
    project_id INTEGER REFERENCES projects(project_id),
    name VARCHAR(255) NOT NULL,
    url TEXT NOT NULL,
    default_branch VARCHAR(255),
    created_at TIMESTAMP,
    last_analyzed_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    INDEX idx_repo_project (project_id),
    INDEX idx_repo_last_analyzed (last_analyzed_at)
);

-- Branches
CREATE TABLE branches (
    branch_id SERIAL PRIMARY KEY,
    repo_id VARCHAR(255) REFERENCES repositories(repo_id) ON DELETE CASCADE,
    branch_name VARCHAR(255) NOT NULL,
    latest_commit_sha VARCHAR(255),
    created_at TIMESTAMP,
    last_analyzed_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(repo_id, branch_name),
    INDEX idx_branch_repo (repo_id),
    INDEX idx_branch_last_analyzed (last_analyzed_at)
);
```

### Language and Dependency Tables

```sql
-- Repository Languages
CREATE TABLE repository_languages (
    id SERIAL PRIMARY KEY,
    repo_id VARCHAR(255) REFERENCES repositories(repo_id) ON DELETE CASCADE,
    branch_id INTEGER REFERENCES branches(branch_id) ON DELETE CASCADE,
    language VARCHAR(100) NOT NULL,
    percentage DECIMAL(5,2),
    line_count INTEGER,
    byte_count BIGINT,
    analyzed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_lang_repo (repo_id),
    INDEX idx_lang_branch (branch_id),
    INDEX idx_lang_analyzed (analyzed_at)
);

-- Convert to hypertable for time-series
SELECT create_hypertable('repository_languages', 'analyzed_at',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE
);

-- Dependencies
CREATE TABLE dependencies (
    id SERIAL PRIMARY KEY,
    repo_id VARCHAR(255) REFERENCES repositories(repo_id) ON DELETE CASCADE,
    branch_id INTEGER REFERENCES branches(branch_id) ON DELETE CASCADE,
    package_name VARCHAR(500) NOT NULL,
    version VARCHAR(100),
    ecosystem VARCHAR(100) NOT NULL,  -- PyPI, npm, Maven, NuGet, etc.
    latest_version VARCHAR(100),
    is_dev_dependency BOOLEAN DEFAULT FALSE,
    has_vulnerabilities BOOLEAN DEFAULT FALSE,
    is_eol BOOLEAN DEFAULT FALSE,
    eol_date DATE,
    analyzed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_dep_repo (repo_id),
    INDEX idx_dep_branch (branch_id),
    INDEX idx_dep_has_vuln (has_vulnerabilities),
    INDEX idx_dep_is_eol (is_eol),
    INDEX idx_dep_analyzed (analyzed_at)
);

SELECT create_hypertable('dependencies', 'analyzed_at',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE
);

-- Vulnerabilities
CREATE TABLE vulnerabilities (
    id SERIAL PRIMARY KEY,
    dependency_id INTEGER REFERENCES dependencies(id) ON DELETE CASCADE,
    cve_id VARCHAR(50),
    vulnerability_id VARCHAR(100),  -- OSV or other ID
    severity VARCHAR(20) NOT NULL,  -- CRITICAL, HIGH, MEDIUM, LOW
    summary TEXT,
    description TEXT,
    published_date TIMESTAMP,
    modified_date TIMESTAMP,
    fixed_in_version VARCHAR(100),
    references JSONB,  -- Array of reference URLs
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_vuln_dependency (dependency_id),
    INDEX idx_vuln_severity (severity),
    INDEX idx_vuln_cve (cve_id)
);
```

### Code Quality Tables

```sql
-- Code Quality Metrics (Time-series)
CREATE TABLE code_quality_metrics (
    id SERIAL,
    repo_id VARCHAR(255) REFERENCES repositories(repo_id) ON DELETE CASCADE,
    branch_id INTEGER REFERENCES branches(branch_id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    total_issues INTEGER DEFAULT 0,
    critical_issues INTEGER DEFAULT 0,
    high_issues INTEGER DEFAULT 0,
    medium_issues INTEGER DEFAULT 0,
    low_issues INTEGER DEFAULT 0,
    complexity_score DECIMAL(10,2),
    maintainability_index DECIMAL(5,2),
    test_coverage DECIMAL(5,2),
    code_smells INTEGER DEFAULT 0,
    technical_debt_minutes INTEGER DEFAULT 0,
    PRIMARY KEY (id, timestamp),
    INDEX idx_quality_repo (repo_id),
    INDEX idx_quality_branch (branch_id)
);

SELECT create_hypertable('code_quality_metrics', 'timestamp',
    chunk_time_interval => INTERVAL '1 week',
    if_not_exists => TRUE
);

-- Individual Code Issues
CREATE TABLE code_issues (
    id SERIAL PRIMARY KEY,
    quality_metric_id INTEGER NOT NULL,
    repo_id VARCHAR(255) REFERENCES repositories(repo_id) ON DELETE CASCADE,
    branch_id INTEGER REFERENCES branches(branch_id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    line_number INTEGER,
    severity VARCHAR(20) NOT NULL,
    category VARCHAR(100),  -- bug, vulnerability, code_smell, etc.
    rule_id VARCHAR(100),
    message TEXT,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    INDEX idx_issue_repo (repo_id),
    INDEX idx_issue_severity (severity),
    INDEX idx_issue_category (category),
    INDEX idx_issue_detected (detected_at)
);
```

### Repository Summary Tables

```sql
-- Repository Summaries
CREATE TABLE repository_summaries (
    id SERIAL PRIMARY KEY,
    repo_id VARCHAR(255) REFERENCES repositories(repo_id) ON DELETE CASCADE,
    branch_id INTEGER REFERENCES branches(branch_id) ON DELETE CASCADE,
    summary_text TEXT NOT NULL,
    purpose TEXT,
    key_technologies TEXT[],  -- Array of technologies
    target_audience TEXT,
    generated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    generated_by VARCHAR(100),  -- e.g., "claude-3-opus", "gpt-4"
    INDEX idx_summary_repo (repo_id),
    INDEX idx_summary_generated (generated_at)
);

-- README Files
CREATE TABLE readme_files (
    id SERIAL PRIMARY KEY,
    repo_id VARCHAR(255) REFERENCES repositories(repo_id) ON DELETE CASCADE,
    branch_id INTEGER REFERENCES branches(branch_id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    content TEXT,
    summary TEXT,
    word_count INTEGER,
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(repo_id, branch_id, file_path),
    INDEX idx_readme_repo (repo_id)
);

-- Enable full-text search on README content
CREATE INDEX idx_readme_content_fts ON readme_files
USING gin(to_tsvector('english', content));
```

### Contributor and Activity Tables

```sql
-- Contributors
CREATE TABLE contributors (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255),
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP,
    INDEX idx_contributor_email (email)
);

-- Contributor Metrics (Time-series)
CREATE TABLE contributor_metrics (
    id SERIAL,
    repo_id VARCHAR(255) REFERENCES repositories(repo_id) ON DELETE CASCADE,
    contributor_id INTEGER REFERENCES contributors(id) ON DELETE CASCADE,
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    commit_count INTEGER DEFAULT 0,
    lines_added INTEGER DEFAULT 0,
    lines_removed INTEGER DEFAULT 0,
    files_modified INTEGER DEFAULT 0,
    pr_created INTEGER DEFAULT 0,
    pr_reviews INTEGER DEFAULT 0,
    pr_approvals INTEGER DEFAULT 0,
    active_days INTEGER DEFAULT 0,
    avg_commit_message_quality DECIMAL(5,2),
    PRIMARY KEY (id, period_start),
    INDEX idx_contrib_metrics_repo (repo_id),
    INDEX idx_contrib_metrics_contributor (contributor_id)
);

SELECT create_hypertable('contributor_metrics', 'period_start',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE
);

-- Commits (for detailed tracking)
CREATE TABLE commits (
    commit_sha VARCHAR(255) PRIMARY KEY,
    repo_id VARCHAR(255) REFERENCES repositories(repo_id) ON DELETE CASCADE,
    branch_name VARCHAR(255),
    author_id INTEGER REFERENCES contributors(id),
    committer_id INTEGER REFERENCES contributors(id),
    message TEXT,
    message_quality_score DECIMAL(5,2),
    commit_date TIMESTAMP NOT NULL,
    parent_shas TEXT[],
    files_changed INTEGER,
    lines_added INTEGER,
    lines_removed INTEGER,
    INDEX idx_commit_repo (repo_id),
    INDEX idx_commit_author (author_id),
    INDEX idx_commit_date (commit_date)
);
```

### Pull Request Tables

```sql
-- Pull Requests
CREATE TABLE pull_requests (
    id SERIAL PRIMARY KEY,
    repo_id VARCHAR(255) REFERENCES repositories(repo_id) ON DELETE CASCADE,
    pr_number INTEGER NOT NULL,
    azure_pr_id VARCHAR(255) UNIQUE,
    title TEXT NOT NULL,
    description TEXT,
    source_branch VARCHAR(255),
    target_branch VARCHAR(255),
    author_id INTEGER REFERENCES contributors(id),
    status VARCHAR(50),  -- active, completed, abandoned
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP,
    merged_at TIMESTAMP,
    closed_at TIMESTAMP,
    files_changed INTEGER DEFAULT 0,
    lines_added INTEGER DEFAULT 0,
    lines_removed INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    approval_count INTEGER DEFAULT 0,
    size_category VARCHAR(20),  -- small, medium, large, extra_large
    has_issues BOOLEAN DEFAULT FALSE,
    issue_flags TEXT[],  -- Array of issue descriptions
    UNIQUE(repo_id, pr_number),
    INDEX idx_pr_repo (repo_id),
    INDEX idx_pr_status (status),
    INDEX idx_pr_created (created_at),
    INDEX idx_pr_merged (merged_at)
);

-- PR Reviews
CREATE TABLE pr_reviews (
    id SERIAL PRIMARY KEY,
    pr_id INTEGER REFERENCES pull_requests(id) ON DELETE CASCADE,
    reviewer_id INTEGER REFERENCES contributors(id),
    review_date TIMESTAMP NOT NULL,
    vote INTEGER,  -- -10=rejected, 0=no vote, 5=approved with suggestions, 10=approved
    is_required BOOLEAN DEFAULT FALSE,
    comment_count INTEGER DEFAULT 0,
    INDEX idx_review_pr (pr_id),
    INDEX idx_review_reviewer (reviewer_id),
    INDEX idx_review_date (review_date)
);

-- PR Comments/Threads
CREATE TABLE pr_comments (
    id SERIAL PRIMARY KEY,
    pr_id INTEGER REFERENCES pull_requests(id) ON DELETE CASCADE,
    thread_id VARCHAR(255),
    author_id INTEGER REFERENCES contributors(id),
    content TEXT,
    comment_type VARCHAR(50),  -- text, system
    published_date TIMESTAMP NOT NULL,
    file_path TEXT,
    line_number INTEGER,
    INDEX idx_comment_pr (pr_id),
    INDEX idx_comment_author (author_id),
    INDEX idx_comment_date (published_date)
);
```

### Branch-Specific Metrics

```sql
-- Branch Metrics (Time-series)
CREATE TABLE branch_metrics (
    id SERIAL,
    branch_id INTEGER REFERENCES branches(branch_id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    commit_count INTEGER DEFAULT 0,
    unique_contributors INTEGER DEFAULT 0,
    age_days INTEGER DEFAULT 0,
    staleness_days INTEGER DEFAULT 0,
    total_lines INTEGER DEFAULT 0,
    divergence_from_main INTEGER DEFAULT 0,  -- Commit count difference
    PRIMARY KEY (id, timestamp),
    INDEX idx_branch_metrics_branch (branch_id)
);

SELECT create_hypertable('branch_metrics', 'timestamp',
    chunk_time_interval => INTERVAL '1 week',
    if_not_exists => TRUE
);
```

## Indexes for Performance

```sql
-- Additional composite indexes for common queries

-- Repository + timestamp queries
CREATE INDEX idx_quality_repo_timestamp ON code_quality_metrics(repo_id, timestamp DESC);
CREATE INDEX idx_dep_repo_timestamp ON dependencies(repo_id, analyzed_at DESC);

-- Contributor + repo queries
CREATE INDEX idx_contrib_metrics_repo_period ON contributor_metrics(repo_id, period_start DESC);

-- PR filtering
CREATE INDEX idx_pr_repo_status_created ON pull_requests(repo_id, status, created_at DESC);

-- Security-focused queries
CREATE INDEX idx_dep_security ON dependencies(repo_id, has_vulnerabilities, is_eol)
WHERE has_vulnerabilities = true OR is_eol = true;
```

## Data Access Layer (Python)

The application uses SQLAlchemy for ORM mapping and `psycopg2` for efficient database connections. It implements a `Database` class to handle connection pooling and transaction management.

## Backup and Restore

### Backup Strategy

Backups are performed daily using `pg_dump` in custom format, compressed with gzip, and uploaded to Azure Blob Storage. Local backups are retained for 7 days, and cloud backups for 30 days.

### Restore from Backup

Restoration involves downloading the backup from Azure Blob Storage, decompressing it, and using `pg_restore` to populate a clean database instance.

### Incremental Backup with WAL Archiving

PostgreSQL is configured with WAL archiving enabled (`wal_level = replica`, `archive_mode = on`) to support point-in-time recovery.

## Data Retention and Archival

Data older than 2 years is moved to archive tables. TimescaleDB chunks older than 6 months are compressed to save storage space.

## Next Steps

- See [05-orchestration.md](05-orchestration.md) for data insertion workflows
- Review [06-visualization.md](06-visualization.md) for querying this data in Grafana
