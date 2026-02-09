#!/bin/bash

set -e

# Configuration from environment variables
POSTGRES_HOST="${POSTGRES_HOST:-timescaledb}"
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
    if PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1" >/dev/null 2>&1; then
        log_success "PostgreSQL is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        log_error "PostgreSQL did not become ready in time"
    fi
    sleep 1
done

# Check if schema already exists
log_info "Checking if database schema exists..."
SCHEMA_EXISTS=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'organizations';" 2>/dev/null || echo "0")

if [ "$SCHEMA_EXISTS" -gt 0 ]; then
    log_info "Database schema already exists, skipping initial schema creation"
else
    log_info "Creating initial database schema..."
    if PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f schema.sql >/dev/null 2>&1; then
        log_success "Database schema initialized"
    else
        log_warning "Schema creation had some warnings (this is often OK for IF NOT EXISTS clauses)"
    fi
fi

# Apply migrations in order
log_info "Applying database migrations..."

MIGRATION_COUNT=0
MIGRATION_APPLIED=0
MIGRATION_SKIPPED=0

# Process migration files in order
for migration_file in migrations/*.sql; do
    if [ ! -f "$migration_file" ]; then
        continue
    fi

    migration_name=$(basename "$migration_file")
    MIGRATION_COUNT=$((MIGRATION_COUNT + 1))

    log_info "Processing migration: $migration_name..."

    # Execute migration and capture output
    if PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$migration_file" >/dev/null 2>&1; then
        log_success "Applied migration: $migration_name"
        MIGRATION_APPLIED=$((MIGRATION_APPLIED + 1))
    else
        # Check if the error is about already existing columns/tables (idempotent)
        OUTPUT=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$migration_file" 2>&1)

        if echo "$OUTPUT" | grep -q "already exists\|duplicate"; then
            log_info "Migration already applied: $migration_name"
            MIGRATION_SKIPPED=$((MIGRATION_SKIPPED + 1))
        else
            log_warning "Migration had warnings: $migration_name"
            log_info "Output: $OUTPUT"
            MIGRATION_APPLIED=$((MIGRATION_APPLIED + 1))
        fi
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

# Exit with success
exit 0
