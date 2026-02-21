-- =============================================================================
-- Populate Services from Repository Data
-- =============================================================================
-- This script creates services based on repository owners/teams and links
-- repositories to those services.
--
-- Usage:
--   docker compose exec -T timescaledb psql -U analyzer -d repo_analyzer -f /tmp/populate_services.sql
-- =============================================================================

BEGIN;

-- Create services based on repository teams
INSERT INTO services (name, purpose)
SELECT 
    COALESCE(t.name, 'Unassigned') as name,
    'Auto-created from team: ' || COALESCE(t.name, 'Unassigned') as purpose
FROM (
    SELECT DISTINCT team_id 
    FROM repositories 
    WHERE team_id IS NOT NULL
) r
INNER JOIN teams t ON r.team_id = t.team_id
ON CONFLICT (name) DO NOTHING;

-- Create an "Unassigned" service for repos without a team
INSERT INTO services (name, purpose)
VALUES ('Unassigned', 'Repositories not assigned to any team')
ON CONFLICT (name) DO NOTHING;

-- Create services based on repository owner prefixes (for GitHub repos)
-- This extracts the owner from repo_id (e.g., "stickleprojects/repo-name" -> "stickleprojects")
INSERT INTO services (name, purpose)
SELECT DISTINCT
    split_part(repo_id, '/', 1) as name,
    'Auto-created from owner: ' || split_part(repo_id, '/', 1) as purpose
FROM repositories
WHERE repo_id LIKE '%/%'  -- GitHub-style repo IDs
  AND split_part(repo_id, '/', 1) != ''
  AND split_part(repo_id, '/', 1) NOT IN (SELECT name FROM services)
ON CONFLICT (name) DO NOTHING;

-- Link repositories to services based on teams
INSERT INTO repository_services (repo_id, service_id)
SELECT 
    r.repo_id,
    s.service_id
FROM repositories r
INNER JOIN teams t ON r.team_id = t.team_id
INNER JOIN services s ON s.name = t.name
WHERE r.team_id IS NOT NULL
ON CONFLICT (repo_id, service_id) DO NOTHING;

-- Link repositories to services based on owner (for GitHub repos without teams)
INSERT INTO repository_services (repo_id, service_id)
SELECT 
    r.repo_id,
    s.service_id
FROM repositories r
INNER JOIN services s ON s.name = split_part(r.repo_id, '/', 1)
WHERE r.repo_id LIKE '%/%'  -- GitHub-style repo IDs
  AND r.team_id IS NULL
  AND split_part(r.repo_id, '/', 1) != ''
ON CONFLICT (repo_id, service_id) DO NOTHING;

-- Link unassigned repositories (no team, not GitHub-style)
INSERT INTO repository_services (repo_id, service_id)
SELECT 
    r.repo_id,
    s.service_id
FROM repositories r
CROSS JOIN services s
WHERE s.name = 'Unassigned'
  AND r.repo_id NOT LIKE '%/%'  -- Not GitHub-style
  AND r.team_id IS NULL
  AND NOT EXISTS (
    SELECT 1 FROM repository_services rs 
    WHERE rs.repo_id = r.repo_id
  )
ON CONFLICT (repo_id, service_id) DO NOTHING;

-- Display results
SELECT 
    s.service_id,
    s.name,
    COUNT(rs.repo_id) as repository_count
FROM services s
LEFT JOIN repository_services rs ON s.service_id = rs.service_id
GROUP BY s.service_id, s.name
ORDER BY repository_count DESC, s.name;

COMMIT;
