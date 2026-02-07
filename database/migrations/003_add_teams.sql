-- =====
-- migration - add the teams db to existing schema
-- add the teams column to repositories and contributors
-- =====

-- Create teams table
CREATE TABLE IF NOT EXISTS teams (
    team_id SERIAL PRIMARY KEY,
    organization_id INTEGER REFERENCES organizations(organization_id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(organization_id, name)
);
-- Add team_id column to repositories table
ALTER TABLE repositories
  ADD COLUMN IF NOT EXISTS team_id INTEGER REFERENCES teams(team_id); 

-- Add team_id column to contributors table
ALTER TABLE contributors
  ADD COLUMN IF NOT EXISTS team_id INTEGER REFERENCES teams(team_id);

-- Add comments for documentation
COMMENT ON TABLE teams IS 'Table to store teams within organizations';
COMMENT ON COLUMN repositories.team_id IS 'Reference to the team associated with the repository';
COMMENT ON COLUMN contributors.team_id IS 'Reference to the team associated with the contributor';  

-- Create indexes for new foreign key columns
CREATE INDEX IF NOT EXISTS idx_repositories_team_id ON repositories(team_id);
CREATE INDEX IF NOT EXISTS idx_contributors_team_id ON contributors(team_id);

