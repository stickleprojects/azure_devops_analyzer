-- =============================================================================
-- Migration: Convert TIMESTAMP columns to TIMESTAMPTZ
-- =============================================================================
-- Purpose: Fix timezone-naive datetime comparisons by using timezone-aware columns
-- Version: 002
-- Date: 2026-01-18
-- =============================================================================
-- This migration converts all TIMESTAMP columns to TIMESTAMPTZ (timestamp with
-- time zone). Existing data is assumed to be UTC and will be preserved correctly.
-- PostgreSQL automatically treats naive timestamps as UTC when converting.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Core Entity Tables
-- -----------------------------------------------------------------------------

-- organizations
ALTER TABLE organizations
  ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC';

-- projects
ALTER TABLE projects
  ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC';

-- repositories
ALTER TABLE repositories
  ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
  ALTER COLUMN last_analyzed_at TYPE TIMESTAMPTZ USING last_analyzed_at AT TIME ZONE 'UTC';

-- branches
ALTER TABLE branches
  ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
  ALTER COLUMN last_analyzed_at TYPE TIMESTAMPTZ USING last_analyzed_at AT TIME ZONE 'UTC';

-- -----------------------------------------------------------------------------
-- Language and Dependency Tables
-- -----------------------------------------------------------------------------

-- repository_languages (hypertable)
ALTER TABLE repository_languages
  ALTER COLUMN analyzed_at TYPE TIMESTAMPTZ USING analyzed_at AT TIME ZONE 'UTC';

-- dependencies (hypertable)
ALTER TABLE dependencies
  ALTER COLUMN analyzed_at TYPE TIMESTAMPTZ USING analyzed_at AT TIME ZONE 'UTC';

-- vulnerabilities
ALTER TABLE vulnerabilities
  ALTER COLUMN published_date TYPE TIMESTAMPTZ USING published_date AT TIME ZONE 'UTC',
  ALTER COLUMN modified_date TYPE TIMESTAMPTZ USING modified_date AT TIME ZONE 'UTC',
  ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC';

-- -----------------------------------------------------------------------------
-- Code Quality Tables
-- -----------------------------------------------------------------------------

-- code_quality_metrics (hypertable)
ALTER TABLE code_quality_metrics
  ALTER COLUMN timestamp TYPE TIMESTAMPTZ USING timestamp AT TIME ZONE 'UTC';

-- code_issues
ALTER TABLE code_issues
  ALTER COLUMN detected_at TYPE TIMESTAMPTZ USING detected_at AT TIME ZONE 'UTC',
  ALTER COLUMN resolved_at TYPE TIMESTAMPTZ USING resolved_at AT TIME ZONE 'UTC';

-- -----------------------------------------------------------------------------
-- Repository Summary Tables
-- -----------------------------------------------------------------------------

-- repository_summaries
ALTER TABLE repository_summaries
  ALTER COLUMN generated_at TYPE TIMESTAMPTZ USING generated_at AT TIME ZONE 'UTC';

-- readme_files
ALTER TABLE readme_files
  ALTER COLUMN analyzed_at TYPE TIMESTAMPTZ USING analyzed_at AT TIME ZONE 'UTC';

-- -----------------------------------------------------------------------------
-- Contributor and Activity Tables
-- -----------------------------------------------------------------------------

-- contributors
ALTER TABLE contributors
  ALTER COLUMN first_seen_at TYPE TIMESTAMPTZ USING first_seen_at AT TIME ZONE 'UTC',
  ALTER COLUMN last_seen_at TYPE TIMESTAMPTZ USING last_seen_at AT TIME ZONE 'UTC';

-- contributor_metrics (hypertable)
ALTER TABLE contributor_metrics
  ALTER COLUMN period_start TYPE TIMESTAMPTZ USING period_start AT TIME ZONE 'UTC',
  ALTER COLUMN period_end TYPE TIMESTAMPTZ USING period_end AT TIME ZONE 'UTC';

-- commits
ALTER TABLE commits
  ALTER COLUMN commit_date TYPE TIMESTAMPTZ USING commit_date AT TIME ZONE 'UTC';

-- -----------------------------------------------------------------------------
-- Pull Request Tables
-- -----------------------------------------------------------------------------

-- pull_requests
ALTER TABLE pull_requests
  ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
  ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC',
  ALTER COLUMN merged_at TYPE TIMESTAMPTZ USING merged_at AT TIME ZONE 'UTC',
  ALTER COLUMN closed_at TYPE TIMESTAMPTZ USING closed_at AT TIME ZONE 'UTC';

-- pr_reviews
ALTER TABLE pr_reviews
  ALTER COLUMN review_date TYPE TIMESTAMPTZ USING review_date AT TIME ZONE 'UTC';

-- pr_comments
ALTER TABLE pr_comments
  ALTER COLUMN published_date TYPE TIMESTAMPTZ USING published_date AT TIME ZONE 'UTC';

-- -----------------------------------------------------------------------------
-- Branch Metrics Tables
-- -----------------------------------------------------------------------------

-- branch_metrics (hypertable)
ALTER TABLE branch_metrics
  ALTER COLUMN timestamp TYPE TIMESTAMPTZ USING timestamp AT TIME ZONE 'UTC';

-- -----------------------------------------------------------------------------
-- Service Tables
-- -----------------------------------------------------------------------------

-- services
ALTER TABLE services
  ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
  ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC';

-- repository_services
ALTER TABLE repository_services
  ALTER COLUMN linked_at TYPE TIMESTAMPTZ USING linked_at AT TIME ZONE 'UTC';

-- -----------------------------------------------------------------------------
-- Add comments for documentation
-- -----------------------------------------------------------------------------
COMMENT ON COLUMN repositories.last_analyzed_at IS 'Last time this repository was analyzed (timezone-aware UTC)';
COMMENT ON COLUMN branches.last_analyzed_at IS 'Last time this branch was analyzed (timezone-aware UTC)';
