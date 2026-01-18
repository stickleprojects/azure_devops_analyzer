-- =====
-- migration - add security and code quality fields to repositories and commits
-- =====

-- Add security and code quality fields to repositories table
ALTER TABLE repositories
  ADD COLUMN is_private BOOLEAN,
  ADD COLUMN is_archived BOOLEAN,
  ADD COLUMN repository_size INTEGER,  -- Size in KB
  ADD COLUMN open_issues_count INTEGER,
  ADD COLUMN license_name VARCHAR(255),
  ADD COLUMN license_key VARCHAR(100),
  ADD COLUMN has_vulnerability_alerts BOOLEAN,
  ADD COLUMN has_secret_scanning BOOLEAN,
  ADD COLUMN has_dependabot_alerts BOOLEAN,
  ADD COLUMN pushed_at TIMESTAMPTZ,
  ADD COLUMN updated_at TIMESTAMPTZ;

-- Add GPG verification fields to commits table
ALTER TABLE commits
  ADD COLUMN is_verified BOOLEAN,  -- GPG signature verification
  ADD COLUMN verification_reason VARCHAR(255);  -- Reason if verification failed

-- Add comments for documentation
COMMENT ON COLUMN repositories.is_private IS 'Whether the repository is private';
COMMENT ON COLUMN repositories.is_archived IS 'Whether the repository is archived';
COMMENT ON COLUMN repositories.repository_size IS 'Repository size in KB';
COMMENT ON COLUMN repositories.open_issues_count IS 'Number of open issues in the repository';
COMMENT ON COLUMN repositories.license_name IS 'Name of the repository license';
COMMENT ON COLUMN repositories.license_key IS 'Key identifier of the repository license';
COMMENT ON COLUMN repositories.has_vulnerability_alerts IS 'Whether vulnerability alerts are enabled';
COMMENT ON COLUMN repositories.has_secret_scanning IS 'Whether secret scanning is enabled';
COMMENT ON COLUMN repositories.has_dependabot_alerts IS 'Whether Dependabot alerts are enabled';
COMMENT ON COLUMN repositories.pushed_at IS 'Last push timestamp';
COMMENT ON COLUMN repositories.updated_at IS 'Last update timestamp';
COMMENT ON COLUMN commits.is_verified IS 'Whether the commit has a valid GPG signature';
COMMENT ON COLUMN commits.verification_reason IS 'Reason for GPG verification failure if applicable';

-- Create indexes for commonly queried fields
CREATE INDEX idx_repositories_is_private ON repositories(is_private);
CREATE INDEX idx_repositories_is_archived ON repositories(is_archived);
CREATE INDEX idx_repositories_has_vulnerability_alerts ON repositories(has_vulnerability_alerts);
CREATE INDEX idx_repositories_has_secret_scanning ON repositories(has_secret_scanning);
CREATE INDEX idx_repositories_has_dependabot_alerts ON repositories(has_dependabot_alerts);
CREATE INDEX idx_repositories_license_key ON repositories(license_key);
CREATE INDEX idx_commits_is_verified ON commits(is_verified);