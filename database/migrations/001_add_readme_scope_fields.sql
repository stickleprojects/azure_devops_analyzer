-- =============================================================================
-- Migration: Add scope and context fields to readme_files table
-- =============================================================================
-- Purpose: Enhance README files with scope context for multi-README repositories
-- Version: 001
-- Date: 2026-01-18
-- =============================================================================

-- Add scope and context fields to readme_files table
ALTER TABLE readme_files
  ADD COLUMN scope_type VARCHAR(50),           -- repository, module, package, component
  ADD COLUMN scope_path TEXT,                  -- directory path this README covers
  ADD COLUMN parent_readme_id INTEGER,         -- reference to parent README
  ADD COLUMN affects_paths TEXT[];             -- array of paths this README documents

-- Add foreign key constraint for parent_readme_id (self-referencing)
ALTER TABLE readme_files
  ADD CONSTRAINT fk_readme_parent
  FOREIGN KEY (parent_readme_id)
  REFERENCES readme_files(id)
  ON DELETE SET NULL;

-- Add indexes for new fields
CREATE INDEX idx_readme_scope_type ON readme_files(scope_type);
CREATE INDEX idx_readme_scope_path ON readme_files(scope_path);
CREATE INDEX idx_readme_parent ON readme_files(parent_readme_id);
CREATE INDEX idx_readme_affects_paths ON readme_files USING gin(affects_paths);

-- Add comments for documentation
COMMENT ON COLUMN readme_files.scope_type IS 'Type of scope: repository, module, package, component';
COMMENT ON COLUMN readme_files.scope_path IS 'Directory path that this README documents';
COMMENT ON COLUMN readme_files.parent_readme_id IS 'ID of parent README in hierarchical structure';
COMMENT ON COLUMN readme_files.affects_paths IS 'Array of file/directory paths this README covers';

-- Optional: Update existing readme_files to have repository scope for root READMEs
UPDATE readme_files
SET scope_type = 'repository',
    scope_path = '/'
WHERE file_path IN ('README.md', 'README.rst', 'README.txt', 'README',
                   'readme.md', 'readme.rst', 'readme.txt', 'readme',
                   'Readme.md', 'Readme.rst', 'Readme.txt', 'Readme');

-- Optional: Set module scope for READMEs in subdirectories
UPDATE readme_files
SET scope_type = 'module',
    scope_path = regexp_replace(file_path, '/[^/]+$', '/')
WHERE scope_type IS NULL
  AND file_path LIKE '%/%';