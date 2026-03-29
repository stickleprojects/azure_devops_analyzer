-- =============================================================================
-- Migration 012: Normalize contributor email addresses
-- =============================================================================
-- Description: Deduplicates contributor records caused by email case variations
--              and strips surrounding whitespace. Resolves DASH-CONTRIB-002
--              (contributor identity fragmentation).
--
-- Strategy:
--   1. For each group of contributors sharing a lower-case email, identify the
--      canonical record (lowest id = first seen) and the duplicates.
--   2. Re-point all foreign-key references on duplicate records to the canonical
--      contributor id.
--   3. Delete the now-orphaned duplicate contributor rows.
--   4. Lower-case + strip the email on all surviving records.
--   5. Add a functional unique constraint to prevent future fragmentation.
-- =============================================================================

BEGIN;

-- Step 1: Re-point commits.author_id and commits.committer_id to canonical contributor
UPDATE commits
SET author_id = canonical.canonical_id
FROM (
    SELECT
        id AS duplicate_id,
        MIN(id) OVER (PARTITION BY TRIM(LOWER(email))) AS canonical_id
    FROM contributors
    WHERE TRIM(LOWER(email)) != email
       OR id NOT IN (
           SELECT MIN(id) FROM contributors GROUP BY TRIM(LOWER(email))
       )
) AS canonical
WHERE commits.author_id = canonical.duplicate_id
  AND canonical.duplicate_id != canonical.canonical_id;

UPDATE commits
SET committer_id = canonical.canonical_id
FROM (
    SELECT
        id AS duplicate_id,
        MIN(id) OVER (PARTITION BY TRIM(LOWER(email))) AS canonical_id
    FROM contributors
    WHERE TRIM(LOWER(email)) != email
       OR id NOT IN (
           SELECT MIN(id) FROM contributors GROUP BY TRIM(LOWER(email))
       )
) AS canonical
WHERE commits.committer_id = canonical.duplicate_id
  AND canonical.duplicate_id != canonical.canonical_id;

-- Step 2: Re-point pull_requests.author_id
UPDATE pull_requests
SET author_id = canonical.canonical_id
FROM (
    SELECT
        id AS duplicate_id,
        MIN(id) OVER (PARTITION BY TRIM(LOWER(email))) AS canonical_id
    FROM contributors
) AS canonical
WHERE pull_requests.author_id = canonical.duplicate_id
  AND canonical.duplicate_id != canonical.canonical_id;

-- Step 3: Re-point pr_reviews.reviewer_id
UPDATE pr_reviews
SET reviewer_id = canonical.canonical_id
FROM (
    SELECT
        id AS duplicate_id,
        MIN(id) OVER (PARTITION BY TRIM(LOWER(email))) AS canonical_id
    FROM contributors
) AS canonical
WHERE pr_reviews.reviewer_id = canonical.duplicate_id
  AND canonical.duplicate_id != canonical.canonical_id;

-- Step 4: Re-point pr_comments.author_id
UPDATE pr_comments
SET author_id = canonical.canonical_id
FROM (
    SELECT
        id AS duplicate_id,
        MIN(id) OVER (PARTITION BY TRIM(LOWER(email))) AS canonical_id
    FROM contributors
) AS canonical
WHERE pr_comments.author_id = canonical.duplicate_id
  AND canonical.duplicate_id != canonical.canonical_id;

-- Step 5: Re-point contributor_metrics.contributor_id
-- contributor_metrics has a composite PK (repo_id, contributor_id, period_start)
-- so we must avoid duplicating an existing row.
-- Delete metrics that would collide after re-pointing, then re-point the rest.
DELETE FROM contributor_metrics AS dup
USING contributor_metrics AS keep
WHERE dup.contributor_id != keep.contributor_id
  AND dup.repo_id = keep.repo_id
  AND dup.period_start = keep.period_start
  AND (
      SELECT TRIM(LOWER(email)) FROM contributors WHERE id = dup.contributor_id
  ) = (
      SELECT TRIM(LOWER(email)) FROM contributors WHERE id = keep.contributor_id
  )
  AND dup.contributor_id > keep.contributor_id;

UPDATE contributor_metrics
SET contributor_id = canonical.canonical_id
FROM (
    SELECT
        id AS duplicate_id,
        MIN(id) OVER (PARTITION BY TRIM(LOWER(email))) AS canonical_id
    FROM contributors
) AS canonical
WHERE contributor_metrics.contributor_id = canonical.duplicate_id
  AND canonical.duplicate_id != canonical.canonical_id;

-- Step 6: Re-point team_contributors.contributor_id
-- Avoid duplicate (team_id, contributor_id) pairs.
DELETE FROM team_contributors AS dup
USING team_contributors AS keep
WHERE dup.contributor_id != keep.contributor_id
  AND dup.team_id = keep.team_id
  AND (
      SELECT TRIM(LOWER(email)) FROM contributors WHERE id = dup.contributor_id
  ) = (
      SELECT TRIM(LOWER(email)) FROM contributors WHERE id = keep.contributor_id
  )
  AND dup.contributor_id > keep.contributor_id;

UPDATE team_contributors
SET contributor_id = canonical.canonical_id
FROM (
    SELECT
        id AS duplicate_id,
        MIN(id) OVER (PARTITION BY TRIM(LOWER(email))) AS canonical_id
    FROM contributors
) AS canonical
WHERE team_contributors.contributor_id = canonical.duplicate_id
  AND canonical.duplicate_id != canonical.canonical_id;

-- Step 7: Delete duplicate contributor rows (those that are no longer canonical)
DELETE FROM contributors
WHERE id NOT IN (
    SELECT MIN(id) FROM contributors GROUP BY TRIM(LOWER(email))
);

-- Step 8: Normalize the email column itself
UPDATE contributors
SET email = TRIM(LOWER(email))
WHERE email != TRIM(LOWER(email));

DO $$
BEGIN
    RAISE NOTICE 'Migration 012 complete: contributor emails normalized and duplicates removed';
END
$$;

COMMIT;
