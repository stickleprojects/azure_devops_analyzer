-- Migration 017: Dependency Vulnerability & EOL Dashboard Views (Plan 021 / FR-5)
--
-- View definitions live exclusively in database/views.sql to prevent drift.
-- This migration simply re-applies the views so they are available after a
-- fresh migration run.
--
-- Prerequisites: Plan 012 (packages, repository_dependencies, vulnerabilities tables)
-- and Plan 012 R-B (has_known_vulnerabilities flag on repository_dependencies).

\ir ../views.sql
