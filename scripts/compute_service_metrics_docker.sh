#!/bin/bash

# =============================================================================
# Compute Service Metrics in Docker
# =============================================================================
# Runs the service metrics computation script inside the analyzer container.
#
# This script ensures the database is ready before computing metrics and
# provides a convenient way to run the computation without manual docker-compose exec.
#
# Usage:
#   bash ./scripts/compute_service_metrics_docker.sh
#   bash ./scripts/compute_service_metrics_docker.sh --all
#   bash ./scripts/compute_service_metrics_docker.sh --service 1 --period 2025-01-01
#   bash ./scripts/compute_service_metrics_docker.sh --all --verbose
# =============================================================================

set -e

# Configuration
CONTAINER="${ANALYZER_CONTAINER:-analyzer-scheduler}"
SCRIPT_NAME="compute_service_metrics.py"

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
}

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    log_error "docker-compose not found. Please install Docker Compose."
    exit 1
fi

# Check if container is running
if ! docker-compose ps "$CONTAINER" --services 2>/dev/null | grep -q "$CONTAINER"; then
    log_warning "Container '$CONTAINER' not found or not running."
    log_info "Starting Docker services..."
    docker-compose up -d
    log_info "Waiting for services to be ready..."
    sleep 5
fi

# If no arguments provided, default to computing all services for current month
if [[ $# -eq 0 ]]; then
    log_info "No arguments provided. Computing metrics for all services..."
    ARGS="--all"
else
    ARGS="$@"
fi

log_info "Running: python scripts/$SCRIPT_NAME $ARGS"
echo ""

# Execute the script inside the container
docker-compose exec "$CONTAINER" python scripts/$SCRIPT_NAME $ARGS
EXIT_CODE=$?

echo ""
if [[ $EXIT_CODE -eq 0 ]]; then
    log_success "Service metrics computation completed successfully."
else
    log_error "Service metrics computation failed with exit code $EXIT_CODE."
fi

exit $EXIT_CODE
