#!/bin/bash
# =============================================================================
# Integration Test Runner - Docker Compose
# =============================================================================
# Runs integration tests in fully isolated Docker environment.
#
# Usage:
#   ./scripts/run-tests-docker.sh              # Run all integration tests
#   ./scripts/run-tests-docker.sh --live-api   # Run live API tests only
#   ./scripts/run-tests-docker.sh --keep-db    # Keep database for debugging
#   ./scripts/run-tests-docker.sh --help       # Show help
#
# Environment Variables:
#   .env file populated
#
# Exit Codes:
#   0  - All tests passed
#   1  - Tests failed
#   2  - Setup error (missing token, Docker not running, etc.)
# =============================================================================

set -e  # Exit on error

# =============================================================================
# Configuration
# =============================================================================
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.test.yml"
RESULTS_DIR="${PROJECT_ROOT}/test-results"
KEEP_DB=false
RUN_LIVE_API=false
ENV_FILE="${PROJECT_ROOT}/.env"
RESOLVED_ENV_FILE="${PROJECT_ROOT}/.env.resolved"
RESOLVE_SCRIPT="${PROJECT_ROOT}/scripts/resolve_env.sh"


# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# Helper Functions
# =============================================================================
log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

show_help() {
    cat << EOF
Integration Test Runner - Docker Compose

Runs integration tests for GitHub AND Azure DevOps extraction in fully isolated 
Docker environment with dedicated test database.

USAGE:
    $0 [OPTIONS]

OPTIONS:
    --live-api      Run live API tests (tests marked with @pytest.mark.live_api)
                    Includes both GitHub and Azure DevOps platform tests
    --keep-db       Keep test database after run (for debugging)
    --no-cleanup    Don't clean up containers after run
    --help          Show this help message

EXAMPLES:
    # Run all GitHub and Azure DevOps integration tests (excluding live API)
    $0

    # Run only live API tests for both GitHub and Azure DevOps
    $0 --live-api

    # Keep database for debugging
    $0 --keep-db

    # Run tests without cleanup (inspect containers after)
    $0 --no-cleanup

WHAT GETS TESTED:
    GitHub Platform:
    - Repository extraction and metadata storage
    - Branch and commit tracking
    - Language detection (via GitHub API)
    - Technology stack detection

    Azure DevOps Platform:
    - Repository extraction and metadata storage
    - Branch and commit tracking
    - Language detection (via file heuristics)
    - Technology stack detection

REQUIREMENTS:
    - Docker and Docker Compose installed
    - GITHUB_TOKEN environment variable set (for GitHub tests)
    - AZURE_DEVOPS_PAT and AZURE_DEVOPS_ORG_URL (for Azure DevOps tests, optional)

OUTPUT:
    Test results saved to: $RESULTS_DIR/
    - junit.xml - Test results in JUnit format
    - junit-live-api.xml - Live API test results (if --live-api used)
EOF
}

cleanup() {
    if [ "$KEEP_DB" = false ]; then
        log_info "Cleaning up test environment..."
        docker compose --env-file "$RESOLVED_ENV_FILE" -f "$COMPOSE_FILE" down -v > /dev/null 2>&1 || true
        log_success "Cleanup complete"
    else
        log_warning "Keeping test database (--keep-db flag set)"
        log_info "To clean up manually: docker compose -f $COMPOSE_FILE down -v"
    fi
}

# =============================================================================
# Parse Arguments
# =============================================================================
CLEANUP=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --live-api)
            RUN_LIVE_API=true
            shift
            ;;
        --keep-db)
            KEEP_DB=true
            shift
            ;;
        --no-cleanup)
            CLEANUP=false
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 2
            ;;
    esac
done

# =============================================================================
# Pre-flight Checks
# =============================================================================

# Resolve environment variables (always re-resolve to pick up current environment)
# Use subshell+source so the resolve script can access non-exported shell variables
log_info "Resolving environment variables..."
( source "$RESOLVE_SCRIPT" --quiet )


log_info "Starting integration test run..."
echo

# Check Docker is running
if ! docker info > /dev/null 2>&1; then
    log_error "Docker is not running"
    log_info "Please start Docker and try again"
    exit 2
fi
log_success "Docker is running"

# Check Docker Compose is available
if ! docker compose version > /dev/null 2>&1; then
    log_error "Docker Compose (V2) not found"
    log_info "Please install Docker Compose V2"
    exit 2
fi
log_success "Docker Compose V2 available"

# Create results directory
mkdir -p "$RESULTS_DIR"
log_success "Test results directory: $RESULTS_DIR/"

echo

# =============================================================================
# Run Tests
# =============================================================================
# Change to project root so docker-compose volume paths resolve correctly
cd "$PROJECT_ROOT"

if [ "$RUN_LIVE_API" = true ]; then
    log_info "Running GitHub AND Azure DevOps tests with LIVE API..."
    log_warning "This will hit real external APIs - may be slow and count against rate limits"
    echo
    
    # Run both GitHub and Azure DevOps tests with live_api marker
    TEST_EXIT_CODE=0
    docker compose --env-file "$RESOLVED_ENV_FILE" -f "$COMPOSE_FILE" run --rm test-runner \
        sh -c "pip install pytest pytest-cov pytest-asyncio pytest-mock && \
               pytest tests/contract/integration/*.py \
                      -v \
               -m 'live_api' \
               --junit-xml=/app/test-results/junit-live-api.xml \
               -o junit_family=xunit2 \
               -o junit_logging=all \
               -rs \
               --tb=short" || TEST_EXIT_CODE=$?
else
    log_info "Running GitHub AND Azure DevOps integration tests (excluding live API)..."
    log_info "Use --live-api flag to run tests against real external APIs"
    echo
    
    # Run tests with exit code capture (only watch test-runner, not migrations)
    TEST_EXIT_CODE=0
    docker compose --env-file "$RESOLVED_ENV_FILE" -f "$COMPOSE_FILE" run --rm test-runner \
        sh -c "pip install pytest pytest-cov pytest-asyncio pytest-mock && \
               pytest tests/contract/integration/*.py \
                      -v \
               -m 'not live_api' \
               --junit-xml=/app/test-results/junit.xml \
               -o junit_family=xunit2 \
               -o junit_logging=all \
               -rs \
               -p no:cacheprovider \
               --tb=short" || TEST_EXIT_CODE=$?
fi

echo

# =============================================================================
# Report Results
# =============================================================================
if [ $TEST_EXIT_CODE -eq 0 ]; then
    log_success "All tests passed! 🎉"
    echo
    log_info "Test results available at:"
    echo "  - JUnit XML: $RESULTS_DIR/junit.xml"
    echo "  - Coverage:  $RESULTS_DIR/coverage/index.html"
    echo
else
    log_error "Tests failed (exit code: $TEST_EXIT_CODE)"
    echo
    log_info "Test results available at:"
    echo "  - JUnit XML: $RESULTS_DIR/junit.xml"
    echo
    log_info "To debug:"
    echo "  1. Check test output above"
    echo "  2. Review test results in $RESULTS_DIR/"
    echo "  3. Run with --keep-db to inspect database state"
    echo
fi

# =============================================================================
# Cleanup
# =============================================================================
if [ "$CLEANUP" = true ]; then
    cleanup
else
    log_warning "Skipping cleanup (--no-cleanup flag set)"
    log_info "To clean up manually: docker compose -f $COMPOSE_FILE down -v"
fi

exit $TEST_EXIT_CODE
