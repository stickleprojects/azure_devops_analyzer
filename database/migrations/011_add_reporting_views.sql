-- Migration 011: Add reporting views for Grafana dashboards
-- Keep reporting logic in one place to avoid drift between migration SQL and view definitions.

\ir ../views.sql
