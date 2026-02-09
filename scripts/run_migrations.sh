#!/bin/bash
# Host-friendly migration runner (wraps docker compose)

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"
RESOLVED_ENV_FILE="${PROJECT_ROOT}/.env.resolved"
RESOLVE_SCRIPT="${PROJECT_ROOT}/scripts/resolve_env.sh"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

if [ ! -f "$ENV_FILE" ]; then
    log_error ".env not found at $ENV_FILE"
fi

if ! docker info >/dev/null 2>&1; then
    log_error "Docker is not running"
fi

if ! docker compose version >/dev/null 2>&1; then
    log_error "Docker Compose V2 not found"
fi

log_info "Resolving environment variables..."
( source "$RESOLVE_SCRIPT" --quiet )

if [ ! -f "$RESOLVED_ENV_FILE" ]; then
    log_error "Resolved env file not created: $RESOLVED_ENV_FILE"
fi

log_info "Running migrations via docker compose..."
cd "$PROJECT_ROOT"

docker compose --env-file "$RESOLVED_ENV_FILE" run --rm db-migrations

log_success "Migrations complete"
