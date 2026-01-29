-- =============================================================================
-- Repository Analysis System - Database Schema
-- =============================================================================
-- Supports multiple platforms: Azure DevOps, GitHub
-- This schema uses PostgreSQL 15+ with TimescaleDB extension
-- Run: psql -U postgres -d repo_analyzer -f schema.sql
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- =============================================================================
-- CORE ENTITY TABLES
-- =============================================================================

-- Organizations and Projects
CREATE TABLE organizations (
    organization_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    url TEXT NOT NULL,
    platform VARCHAR(20) NOT NULL DEFAULT 'azure_devops',  -- azure_devops, github
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(platform, name)
);

CREATE INDEX idx_org_platform ON organizations(platform);

CREATE TABLE projects (
    project_id SERIAL PRIMARY KEY,
    organization_id INTEGER,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(organization_id, name),
    CONSTRAINT fk_project_organization FOREIGN KEY (organization_id) REFERENCES organizations(organization_id)
);

-- teams
CREATE TABLE teams (
    team_id SERIAL PRIMARY KEY,
    organization_id INTEGER,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(team_id, name),
    CONSTRAINT fk_team_organization FOREIGN KEY (organization_id) REFERENCES organizations(organization_id)
);

-- Repositories
CREATE TABLE repositories (
    repo_id VARCHAR(255) PRIMARY KEY,  -- Platform-specific ID (Azure GUID or GitHub owner/repo)
    project_id INTEGER,
    team_id INTEGER,
    
    name VARCHAR(255) NOT NULL,
    url TEXT NOT NULL,
    default_branch VARCHAR(255),
    platform_repo_id BIGINT,  -- GitHub numeric repo ID (optional)
    created_at TIMESTAMPTZ,
    last_analyzed_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    CONSTRAINT fk_repository_project FOREIGN KEY (project_id) REFERENCES projects(project_id),
    CONSTRAINT fk_repository_team FOREIGN KEY (team_id) REFERENCES teams(team_id)
);

CREATE INDEX idx_repo_project ON repositories(project_id);
CREATE INDEX idx_repo_last_analyzed ON repositories(last_analyzed_at);

-- Branches
CREATE TABLE branches (
    branch_id SERIAL PRIMARY KEY,
    repo_id VARCHAR(255),
    branch_name VARCHAR(255) NOT NULL,
    latest_commit_sha VARCHAR(255),
    created_at TIMESTAMPTZ,
    last_analyzed_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(repo_id, branch_name),
    CONSTRAINT fk_branch_repository FOREIGN KEY (repo_id) REFERENCES repositories(repo_id) ON DELETE CASCADE
);

CREATE INDEX idx_branch_repo ON branches(repo_id);
CREATE INDEX idx_branch_last_analyzed ON branches(last_analyzed_at);

-- =============================================================================
-- LANGUAGE AND DEPENDENCY TABLES
-- =============================================================================

-- Repository Languages (Time-series)
CREATE TABLE repository_languages (
    id SERIAL PRIMARY KEY,
    repo_id VARCHAR(255),
    branch_id INTEGER,
    language VARCHAR(100) NOT NULL,
    percentage DECIMAL(5,2),
    line_count INTEGER,
    byte_count BIGINT,
    analyzed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_repolang_repository FOREIGN KEY (repo_id) REFERENCES repositories(repo_id) ON DELETE CASCADE,
    CONSTRAINT fk_repolang_branch FOREIGN KEY (branch_id) REFERENCES branches(branch_id) ON DELETE CASCADE
);

CREATE INDEX idx_lang_repo ON repository_languages(repo_id);
CREATE INDEX idx_lang_branch ON repository_languages(branch_id);
CREATE INDEX idx_lang_analyzed ON repository_languages(analyzed_at);

SELECT create_hypertable('repository_languages', 'analyzed_at',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE
);

-- Dependencies (Time-series)
CREATE TABLE dependencies (
    id SERIAL PRIMARY KEY,
    repo_id VARCHAR(255),
    branch_id INTEGER,
    package_name VARCHAR(500) NOT NULL,
    version VARCHAR(100),
    ecosystem VARCHAR(100) NOT NULL,  -- PyPI, npm, Maven, NuGet, etc.
    latest_version VARCHAR(100),
    is_dev_dependency BOOLEAN DEFAULT FALSE,
    has_vulnerabilities BOOLEAN DEFAULT FALSE,
    is_eol BOOLEAN DEFAULT FALSE,
    eol_date DATE,
    analyzed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_dependency_repository FOREIGN KEY (repo_id) REFERENCES repositories(repo_id) ON DELETE CASCADE,
    CONSTRAINT fk_dependency_branch FOREIGN KEY (branch_id) REFERENCES branches(branch_id) ON DELETE CASCADE
);

CREATE INDEX idx_dep_repo ON dependencies(repo_id);
CREATE INDEX idx_dep_branch ON dependencies(branch_id);
CREATE INDEX idx_dep_has_vuln ON dependencies(has_vulnerabilities);
CREATE INDEX idx_dep_is_eol ON dependencies(is_eol);
CREATE INDEX idx_dep_analyzed ON dependencies(analyzed_at);

SELECT create_hypertable('dependencies', 'analyzed_at',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE
);

-- Vulnerabilities
CREATE TABLE vulnerabilities (
    id SERIAL PRIMARY KEY,
    dependency_id INTEGER,
    cve_id VARCHAR(50),
    vulnerability_id VARCHAR(100),  -- OSV or other ID
    severity VARCHAR(20) NOT NULL,  -- CRITICAL, HIGH, MEDIUM, LOW
    summary TEXT,
    description TEXT,
    published_date TIMESTAMPTZ,
    modified_date TIMESTAMPTZ,
    fixed_in_version VARCHAR(100),
    references JSONB,  -- Array of reference URLs
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_vulnerability_dependency FOREIGN KEY (dependency_id) REFERENCES dependencies(id) ON DELETE CASCADE
);

CREATE INDEX idx_vuln_dependency ON vulnerabilities(dependency_id);
CREATE INDEX idx_vuln_severity ON vulnerabilities(severity);
CREATE INDEX idx_vuln_cve ON vulnerabilities(cve_id);

-- =============================================================================
-- CODE QUALITY TABLES
-- =============================================================================

-- Code Quality Metrics (Time-series)
CREATE TABLE code_quality_metrics (
    id SERIAL,
    repo_id VARCHAR(255),
    branch_id INTEGER,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
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
    CONSTRAINT fk_quality_repository FOREIGN KEY (repo_id) REFERENCES repositories(repo_id) ON DELETE CASCADE,
    CONSTRAINT fk_quality_branch FOREIGN KEY (branch_id) REFERENCES branches(branch_id) ON DELETE CASCADE
);

CREATE INDEX idx_quality_repo ON code_quality_metrics(repo_id);
CREATE INDEX idx_quality_branch ON code_quality_metrics(branch_id);

SELECT create_hypertable('code_quality_metrics', 'timestamp',
    chunk_time_interval => INTERVAL '1 week',
    if_not_exists => TRUE
);

-- Individual Code Issues
CREATE TABLE code_issues (
    id SERIAL PRIMARY KEY,
    quality_metric_id INTEGER NOT NULL,
    repo_id VARCHAR(255),
    branch_id INTEGER,
    file_path TEXT NOT NULL,
    line_number INTEGER,
    severity VARCHAR(20) NOT NULL,
    category VARCHAR(100),  -- bug, vulnerability, code_smell, etc.
    rule_id VARCHAR(100),
    message TEXT,
    detected_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMPTZ,
    CONSTRAINT fk_issue_repository FOREIGN KEY (repo_id) REFERENCES repositories(repo_id) ON DELETE CASCADE,
    CONSTRAINT fk_issue_branch FOREIGN KEY (branch_id) REFERENCES branches(branch_id) ON DELETE CASCADE
);

CREATE INDEX idx_issue_repo ON code_issues(repo_id);
CREATE INDEX idx_issue_severity ON code_issues(severity);
CREATE INDEX idx_issue_category ON code_issues(category);
CREATE INDEX idx_issue_detected ON code_issues(detected_at);

-- =============================================================================
-- REPOSITORY SUMMARY TABLES
-- =============================================================================

-- Repository Summaries (AI-generated)
CREATE TABLE repository_summaries (
    id SERIAL PRIMARY KEY,
    repo_id VARCHAR(255),
    branch_id INTEGER,
    summary_text TEXT NOT NULL,
    purpose TEXT,
    key_technologies TEXT[],  -- Array of technologies
    target_audience TEXT,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    generated_by VARCHAR(100),  -- e.g., "claude-3-opus", "gpt-4"
    CONSTRAINT fk_summary_repository FOREIGN KEY (repo_id) REFERENCES repositories(repo_id) ON DELETE CASCADE,
    CONSTRAINT fk_summary_branch FOREIGN KEY (branch_id) REFERENCES branches(branch_id) ON DELETE CASCADE
);

CREATE INDEX idx_summary_repo ON repository_summaries(repo_id);
CREATE INDEX idx_summary_generated ON repository_summaries(generated_at);

-- README Files
CREATE TABLE readme_files (
    id SERIAL PRIMARY KEY,
    repo_id VARCHAR(255),
    branch_id INTEGER,
    file_path TEXT NOT NULL,
    content TEXT,
    summary TEXT,
    word_count INTEGER,
    analyzed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(repo_id, branch_id, file_path),
    CONSTRAINT fk_readme_repository FOREIGN KEY (repo_id) REFERENCES repositories(repo_id) ON DELETE CASCADE,
    CONSTRAINT fk_readme_branch FOREIGN KEY (branch_id) REFERENCES branches(branch_id) ON DELETE CASCADE
);

CREATE INDEX idx_readme_repo ON readme_files(repo_id);
CREATE INDEX idx_readme_content_fts ON readme_files USING gin(to_tsvector('english', content));

-- =============================================================================
-- CONTRIBUTOR AND ACTIVITY TABLES
-- =============================================================================

-- Contributors
CREATE TABLE contributors (
    id SERIAL PRIMARY KEY,
    team_id INTEGER,
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255),
    first_seen_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMPTZ,
    CONSTRAINT fk_contributor_team FOREIGN KEY (team_id) REFERENCES teams(team_id)
);

CREATE INDEX idx_contributor_email ON contributors(email);

-- Contributor Metrics (Time-series)
CREATE TABLE contributor_metrics (
    id BIGSERIAL PRIMARY KEY,
    repo_id VARCHAR(255) NOT NULL,
    contributor_id INTEGER NOT NULL,
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

SELECT create_hypertable('contributor_metrics', 'period_start',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE
);

-- Commits
CREATE TABLE commits (
    commit_sha VARCHAR(255) PRIMARY KEY,
    repo_id VARCHAR(255),
    branch_name VARCHAR(255),
    author_id INTEGER,
    committer_id INTEGER,
    message TEXT,
    message_quality_score DECIMAL(5,2),
    commit_date TIMESTAMPTZ NOT NULL,
    parent_shas TEXT[],
    files_changed INTEGER,
    lines_added INTEGER,
    lines_removed INTEGER,
    CONSTRAINT fk_commit_repository FOREIGN KEY (repo_id) REFERENCES repositories(repo_id) ON DELETE CASCADE,
    CONSTRAINT fk_commit_author FOREIGN KEY (author_id) REFERENCES contributors(id),
    CONSTRAINT fk_commit_committer FOREIGN KEY (committer_id) REFERENCES contributors(id)
);

CREATE INDEX idx_commit_repo ON commits(repo_id);
CREATE INDEX idx_commit_author ON commits(author_id);
CREATE INDEX idx_commit_date ON commits(commit_date);

-- =============================================================================
-- PULL REQUEST TABLES
-- =============================================================================

-- Pull Requests
CREATE TABLE pull_requests (
    id SERIAL PRIMARY KEY,
    repo_id VARCHAR(255),
    pr_number INTEGER NOT NULL,
    platform_pr_id VARCHAR(255) UNIQUE,  -- Azure PR ID or GitHub PR node_id
    title TEXT NOT NULL,
    description TEXT,
    source_branch VARCHAR(255),
    target_branch VARCHAR(255),
    author_id INTEGER,
    status VARCHAR(50),  -- active, completed, abandoned
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ,
    merged_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    files_changed INTEGER DEFAULT 0,
    lines_added INTEGER DEFAULT 0,
    lines_removed INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    approval_count INTEGER DEFAULT 0,
    size_category VARCHAR(20),  -- small, medium, large, extra_large
    has_issues BOOLEAN DEFAULT FALSE,
    issue_flags TEXT[],  -- Array of issue descriptions
    UNIQUE(repo_id, pr_number),
    CONSTRAINT fk_pr_repository FOREIGN KEY (repo_id) REFERENCES repositories(repo_id) ON DELETE CASCADE,
    CONSTRAINT fk_pr_author FOREIGN KEY (author_id) REFERENCES contributors(id)
);

CREATE INDEX idx_pr_repo ON pull_requests(repo_id);
CREATE INDEX idx_pr_status ON pull_requests(status);
CREATE INDEX idx_pr_created ON pull_requests(created_at);
CREATE INDEX idx_pr_merged ON pull_requests(merged_at);

-- PR Reviews
CREATE TABLE pr_reviews (
    id SERIAL PRIMARY KEY,
    pr_id INTEGER,
    reviewer_id INTEGER,
    review_date TIMESTAMPTZ NOT NULL,
    vote INTEGER,  -- -10=rejected, 0=no vote, 5=approved with suggestions, 10=approved
    is_required BOOLEAN DEFAULT FALSE,
    comment_count INTEGER DEFAULT 0,
    CONSTRAINT fk_review_pr FOREIGN KEY (pr_id) REFERENCES pull_requests(id) ON DELETE CASCADE,
    CONSTRAINT fk_review_reviewer FOREIGN KEY (reviewer_id) REFERENCES contributors(id)
);

CREATE INDEX idx_review_pr ON pr_reviews(pr_id);
CREATE INDEX idx_review_reviewer ON pr_reviews(reviewer_id);
CREATE INDEX idx_review_date ON pr_reviews(review_date);

-- PR Comments/Threads
CREATE TABLE pr_comments (
    id SERIAL PRIMARY KEY,
    pr_id INTEGER,
    thread_id VARCHAR(255),
    author_id INTEGER,
    content TEXT,
    comment_type VARCHAR(50),  -- text, system
    published_date TIMESTAMPTZ NOT NULL,
    file_path TEXT,
    line_number INTEGER,
    CONSTRAINT fk_comment_pr FOREIGN KEY (pr_id) REFERENCES pull_requests(id) ON DELETE CASCADE,
    CONSTRAINT fk_comment_author FOREIGN KEY (author_id) REFERENCES contributors(id)
);

CREATE INDEX idx_comment_pr ON pr_comments(pr_id);
CREATE INDEX idx_comment_author ON pr_comments(author_id);
CREATE INDEX idx_comment_date ON pr_comments(published_date);

-- =============================================================================
-- BRANCH METRICS TABLES
-- =============================================================================

-- Branch Metrics (Time-series)
CREATE TABLE branch_metrics (
    id SERIAL,
    branch_id INTEGER,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    commit_count INTEGER DEFAULT 0,
    unique_contributors INTEGER DEFAULT 0,
    age_days INTEGER DEFAULT 0,
    staleness_days INTEGER DEFAULT 0,
    total_lines INTEGER DEFAULT 0,
    divergence_from_main INTEGER DEFAULT 0,  -- Commit count difference
    PRIMARY KEY (id, timestamp),
    CONSTRAINT fk_branchmetrics_branch FOREIGN KEY (branch_id) REFERENCES branches(branch_id) ON DELETE CASCADE
);

CREATE INDEX idx_branch_metrics_branch ON branch_metrics(branch_id);

SELECT create_hypertable('branch_metrics', 'timestamp',
    chunk_time_interval => INTERVAL '1 week',
    if_not_exists => TRUE
);

-- =============================================================================
-- SERVICE TABLES
-- =============================================================================

-- Services (logical groupings of repositories)
CREATE TABLE services (
    service_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    purpose TEXT,
    cmdb_id VARCHAR(100) UNIQUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_service_name ON services(name);
CREATE INDEX idx_service_cmdb ON services(cmdb_id);

-- Repository-Service mapping (many-to-many)
CREATE TABLE repository_services (
    id SERIAL PRIMARY KEY,
    repo_id VARCHAR(255),
    service_id INTEGER,
    linked_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(repo_id, service_id),
    CONSTRAINT fk_reposervice_repository FOREIGN KEY (repo_id) REFERENCES repositories(repo_id) ON DELETE CASCADE,
    CONSTRAINT fk_reposervice_service FOREIGN KEY (service_id) REFERENCES services(service_id) ON DELETE CASCADE
);

CREATE INDEX idx_repo_service_repo ON repository_services(repo_id);
CREATE INDEX idx_repo_service_service ON repository_services(service_id);

-- =============================================================================
-- PERFORMANCE INDEXES
-- =============================================================================

-- Composite indexes for common queries
CREATE INDEX idx_quality_repo_timestamp ON code_quality_metrics(repo_id, timestamp DESC);
CREATE INDEX idx_dep_repo_timestamp ON dependencies(repo_id, analyzed_at DESC);
CREATE INDEX idx_contrib_metrics_repo_period ON contributor_metrics(repo_id, period_start DESC);
CREATE INDEX idx_pr_repo_status_created ON pull_requests(repo_id, status, created_at DESC);

-- Security-focused partial index
CREATE INDEX idx_dep_security ON dependencies(repo_id, has_vulnerabilities, is_eol)
WHERE has_vulnerabilities = true OR is_eol = true;
