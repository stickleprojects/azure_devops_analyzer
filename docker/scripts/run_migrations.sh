#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Resolve schema/migrations paths for both container and host invocation contexts.
if [ -f "schema.sql" ] && [ -d "migrations" ]; then
    SCHEMA_FILE="schema.sql"
    MIGRATIONS_DIR="migrations"
    VIEWS_FILE="views.sql"
elif [ -f "database/schema.sql" ] && [ -d "database/migrations" ]; then
    SCHEMA_FILE="database/schema.sql"
    MIGRATIONS_DIR="database/migrations"
    VIEWS_FILE="database/views.sql"
elif [ -f "$SCRIPT_DIR/../../database/schema.sql" ] && [ -d "$SCRIPT_DIR/../../database/migrations" ]; then
    SCHEMA_FILE="$SCRIPT_DIR/../../database/schema.sql"
    MIGRATIONS_DIR="$SCRIPT_DIR/../../database/migrations"
    VIEWS_FILE="$SCRIPT_DIR/../../database/views.sql"
else
    echo "[ERROR] Could not locate schema.sql and migrations directory from current context"
    exit 1
fi

# Configuration from environment variables
# Resolve host from explicit setting first, then DATABASE_URL/TEST_DATABASE_URL.
if [ -n "${POSTGRES_HOST:-}" ]; then
    RESOLVED_POSTGRES_HOST="$POSTGRES_HOST"
else
    DB_URL="${DATABASE_URL:-${TEST_DATABASE_URL:-}}"
    if [ -n "$DB_URL" ]; then
        RESOLVED_POSTGRES_HOST="$(echo "$DB_URL" | sed -E 's#^[a-zA-Z0-9+]+://([^@/]+@)?([^:/?#]+).*#\2#')"
    else
        RESOLVED_POSTGRES_HOST="timescaledb"
    fi
fi

POSTGRES_HOST="$RESOLVED_POSTGRES_HOST"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-repo_analyzer}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Wait for PostgreSQL to be ready
log_info "Waiting for PostgreSQL to be ready at $POSTGRES_HOST:$POSTGRES_PORT..."
for i in {1..30}; do
    if PGPASSWORD="$POSTGRES_PASSWORD" psql --no-password -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1" >/dev/null 2>&1; then
        log_success "PostgreSQL is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        log_error "PostgreSQL did not become ready in time"
    fi
    sleep 1
done

# Ensure TimescaleDB extension exists before any migration/view references time_bucket.
# TimescaleDB is required for hypertable features in production; warn if unavailable
# (e.g. plain postgres:16 in local development or minimal CI environments).
log_info "Ensuring TimescaleDB extension is enabled..."
if PGPASSWORD="$POSTGRES_PASSWORD" psql -v ON_ERROR_STOP=1 -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE EXTENSION IF NOT EXISTS timescaledb;" >/dev/null 2>&1; then
    log_success "TimescaleDB extension is enabled"
else
    log_warning "TimescaleDB extension is not available on this PostgreSQL server."
    log_warning "Hypertable features (time_bucket, create_hypertable) will not be active."
    log_warning "Migrations that reference TimescaleDB functions may be skipped or produce warnings."
    log_warning "For production use, ensure the timescaledb/timescaledb Docker image is used."
fi

# Check if schema already exists
log_info "Checking if database schema exists..."
SCHEMA_EXISTS=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'organizations';" 2>/dev/null || echo "0")

if [ "$SCHEMA_EXISTS" -gt 0 ]; then
    log_info "Database schema already exists, skipping initial schema creation"
else
    log_info "Creating initial database schema..."
    if PGPASSWORD="$POSTGRES_PASSWORD" psql -v ON_ERROR_STOP=1 -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$SCHEMA_FILE" >/dev/null 2>&1; then
        log_success "Database schema initialized"
    else
        log_error "Schema creation failed"
    fi
fi

# Create the migration tracking table and detect whether it was freshly created.
# A freshly-created table combined with an already-populated schema means this is
# an existing deployment being upgraded; backfill all known migrations so they are
# not re-executed against a schema that already reflects them.
log_info "Ensuring schema_migrations tracking table exists..."
TRACKING_TABLE_EXISTED=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'schema_migrations';" 2>/dev/null || echo "0")

PGPASSWORD="$POSTGRES_PASSWORD" psql -v ON_ERROR_STOP=1 -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
    "CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW());" >/dev/null 2>&1

CORE_TABLES_EXIST=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'repositories';" 2>/dev/null || echo "0")

if [ "$TRACKING_TABLE_EXISTED" -eq 0 ] && [ "$CORE_TABLES_EXIST" -gt 0 ]; then
    # The tracking table is brand-new but the public schema already contains core
    # tables, so this is a pre-existing deployment.  Record every migration file
    # as already applied so none of them will be re-executed.
    log_warning "Detected existing schema without migration tracking — backfilling all known migrations as already applied."
    for migration_file in "$MIGRATIONS_DIR"/*.sql; do
        if [ ! -f "$migration_file" ]; then
            continue
        fi
        migration_name=$(basename "$migration_file")
        PGPASSWORD="$POSTGRES_PASSWORD" psql -v ON_ERROR_STOP=1 -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
            --set="migration_name=$migration_name" \
            -c "INSERT INTO schema_migrations (version) VALUES (:'migration_name') ON CONFLICT DO NOTHING;" >/dev/null 2>&1
        log_info "  Backfilled: $migration_name"
    done
    log_success "Backfill complete — existing migrations will be skipped on this and future runs."
fi

# Apply migrations in order
log_info "Applying database migrations..."

MIGRATION_COUNT=0
MIGRATION_APPLIED=0
MIGRATION_SKIPPED=0

# Process migration files in order
for migration_file in "$MIGRATIONS_DIR"/*.sql; do
    if [ ! -f "$migration_file" ]; then
        continue
    fi

    migration_name=$(basename "$migration_file")
    MIGRATION_COUNT=$((MIGRATION_COUNT + 1))

    ALREADY_APPLIED=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t \
        --set="migration_name=$migration_name" \
        -c "SELECT 1 FROM schema_migrations WHERE version = :'migration_name';" 2>/dev/null || echo "")

    if [ -n "$(echo "$ALREADY_APPLIED" | tr -d '[:space:]')" ]; then
        log_info "Already applied (skipping): $migration_name"
        MIGRATION_SKIPPED=$((MIGRATION_SKIPPED + 1))
        continue
    fi

    log_info "Processing migration: $migration_name..."

    set +e
    OUTPUT=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -v ON_ERROR_STOP=1 -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$migration_file" 2>&1)
    MIGRATION_EXIT_CODE=$?
    set -e

    if [ $MIGRATION_EXIT_CODE -eq 0 ]; then
        PGPASSWORD="$POSTGRES_PASSWORD" psql -v ON_ERROR_STOP=1 -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
            --set="migration_name=$migration_name" \
            -c "INSERT INTO schema_migrations (version) VALUES (:'migration_name') ON CONFLICT DO NOTHING;" >/dev/null 2>&1
        log_success "Applied migration: $migration_name"
        MIGRATION_APPLIED=$((MIGRATION_APPLIED + 1))
    else
        log_error "Migration failed: $migration_name\n$OUTPUT"
    fi
done

# Summary
log_info "Migration summary:"
log_info "  Total migrations: $MIGRATION_COUNT"
log_success "  Applied: $MIGRATION_APPLIED"
log_info "  Already applied: $MIGRATION_SKIPPED"

if [ $MIGRATION_COUNT -gt 0 ]; then
    log_success "All migrations completed successfully"
else
    log_info "No migrations to apply"
fi

# Always reapply views to keep definitions current (all statements are CREATE OR REPLACE).
if [ -f "$VIEWS_FILE" ]; then
    log_info "Reapplying views.sql..."
    if PGPASSWORD="$POSTGRES_PASSWORD" psql -v ON_ERROR_STOP=1 -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$VIEWS_FILE" >/dev/null 2>&1; then
        log_success "Views reapplied"
    else
        log_warning "views.sql reapplication had errors (non-fatal)"
    fi
else
    log_warning "views.sql not found at $VIEWS_FILE — skipping view reapplication"
fi

# Exit with success
exit 0
