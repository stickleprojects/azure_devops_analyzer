-- Migration 013: Fix platform_pr_id unique constraint
--
-- The original schema placed a global UNIQUE constraint on
-- pull_requests.platform_pr_id.  This prevents different repositories from
-- sharing the same PR ID value (e.g. every repo's PR #1 has platform_pr_id
-- '1'), causing duplicate-key errors when more than one repository is loaded
-- in the same database.
--
-- Fix: drop the global constraint and replace it with a composite one that
-- enforces uniqueness only *within* a single repository.

-- Step 1: Drop the old global unique index/constraint (name may vary by
-- how the database was created – handle both the column-level and any
-- explicitly-named variant).
ALTER TABLE pull_requests
    DROP CONSTRAINT IF EXISTS pull_requests_platform_pr_id_key;

-- Step 2: Add the composite unique constraint.
ALTER TABLE pull_requests
    ADD CONSTRAINT uq_pr_repo_platform_pr_id UNIQUE (repo_id, platform_pr_id);
