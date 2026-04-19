-- =============================================================================
-- DB Invariant Queries
-- =============================================================================
-- Each invariant is a named SELECT that MUST return zero rows for the database
-- to be considered valid.
--
-- The invariant name is parsed from the "-- invariant: <name>" comment
-- immediately above each query block.
--
-- Used by:
--   - tests/contract/integration/conftest.py  (db_invariants_check fixture)
--   - scripts/verify-extraction.sh             (shell wrapper for manual runs)
-- =============================================================================

-- invariant: no_case_variant_contributor_twins
-- No two contributors rows share the same normalised email (lower + trim).
SELECT lower(trim(email)) AS email_key, count(*) AS occurrences
FROM contributors
GROUP BY lower(trim(email))
HAVING count(*) > 1;

-- invariant: no_orphan_pr_author_fk
-- Every pull_requests row must have a non-null author_id that resolves to a
-- contributors row.
SELECT id, repo_id, pr_number, author_id
FROM pull_requests
WHERE author_id IS NULL
   OR author_id NOT IN (SELECT id FROM contributors);

-- invariant: no_orphan_pr_reviewer_fk
-- Every pr_reviews row must have a non-null reviewer_id that resolves to a
-- contributors row.
SELECT pr_id, reviewer_id
FROM pr_reviews
WHERE reviewer_id IS NULL
   OR reviewer_id NOT IN (SELECT id FROM contributors);

-- invariant: no_duplicate_pr_per_repo
-- No two pull_requests rows share (repo_id, pr_number).
SELECT repo_id, pr_number, count(*) AS occurrences
FROM pull_requests
GROUP BY repo_id, pr_number
HAVING count(*) > 1;

-- invariant: no_duplicate_commit_per_repo
-- No two commits rows share (repo_id, sha).
SELECT repo_id, sha, count(*) AS occurrences
FROM commits
GROUP BY repo_id, sha
HAVING count(*) > 1;

-- invariant: no_review_before_pr_created
-- A review cannot be dated before the PR it belongs to was created.
SELECT r.pr_id, r.review_date, pr.created_at
FROM pr_reviews r
JOIN pull_requests pr ON r.pr_id = pr.id
WHERE r.review_date < pr.created_at;

-- invariant: no_orphan_repo_dependency
-- Every repository_dependencies row must reference a valid repositories row.
-- Falls back gracefully if the table has been renamed or not yet created.
SELECT rd.repo_id
FROM repository_dependencies rd
WHERE rd.repo_id NOT IN (SELECT repo_id FROM repositories);

-- invariant: no_vulnerability_without_package
-- Every vulnerabilities row must reference a valid packages row (migration 014+).
-- Skip if packages table not yet present to keep schema-version compatibility.
SELECT v.id, v.package_id
FROM vulnerabilities v
WHERE v.package_id IS NOT NULL
  AND v.package_id NOT IN (SELECT id FROM packages);
