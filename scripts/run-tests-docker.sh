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
#   GITHUB_TOKEN - GitHub API token (required, loaded from .env.resolved)
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
COMPOSE_FILE="docker-compose.test.yml"
RESULTS_DIR="test-results"
KEEP_DB=false
RUN_LIVE_API=false

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

Runs integration tests in fully isolated Docker environment with dedicated test database.

USAGE:
    $0 [OPTIONS]

OPTIONS:
    --live-api      Run live API tests (tests marked with @pytest.mark.live_api)
    --keep-db       Keep test database after run (for debugging)
    --no-cleanup    Don't clean up containers after run
    --help          Show this help message

EXAMPLES:
    # Run all integration tests (excluding live API tests)
    $0

    # Run only live API tests
    $0 --live-api

    # Keep database for debugging
    $0 --keep-db

    # Run tests without cleanup (inspect containers after)
    $0 --no-cleanup

ENVIRONMENT:
    GITHUB_TOKEN - Required for GitHub API tests
                   Auto-loaded from .env.resolved if available

REQUIREMENTS:
    - Docker and Docker Compose installed
    - .env.resolved file with GITHUB_TOKEN (or set in environment)

OUTPUT:
    Test results saved to: $RESULTS_DIR/
    - junit.xml - Test results in JUnit format
    - coverage/ - HTML coverage report
EOF
}

cleanup() {
    if [ "$KEEP_DB" = false ]; then
        log_info "Cleaning up test environment..."
        docker compose -f "$COMPOSE_FILE" down -v > /dev/null 2>&1 || true
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

# Load GitHub token from .env.resolved if not set
if [ -z "$GITHUB_TOKEN" ]; then
    if [ -f ".env.resolved" ]; then
        log_info "Loading GITHUB_TOKEN from .env.resolved..."
        export GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" .env.resolved | cut -d'=' -f2 | tr -d '"' | tr -d "'")
    fi
fi

# Verify GitHub token is available
if [ -z "$GITHUB_TOKEN" ]; then
    log_error "GITHUB_TOKEN not found"
    log_info "Set GITHUB_TOKEN environment variable or add to .env.resolved"
    exit 2
fi
log_success "GitHub token loaded"

# Create results directory
mkdir -p "$RESULTS_DIR"
log_success "Test results directory: $RESULTS_DIR/"

echo

# =============================================================================
# Run Tests
# =============================================================================
if [ "$RUN_LIVE_API" = true ]; then
    log_info "Running LIVE API tests (will hit real external APIs)..."
    log_warning "This may be slow and count against API rate limits"
    echo
    
    # Modify command to run live_api tests
    TEST_EXIT_CODE=0
    docker compose -f "$COMPOSE_FILE" run --rm test-runner \
        sh -c "pip install pytest pytest-cov pytest-asyncio pytest-mock && \
               pytest tests/contract/integration/ -v \
               -m 'live_api' \
               --junit-xml=/app/test-results/junit-live-api.xml \
               --tb=short" || TEST_EXIT_CODE=$?
else
    log_info "Running integration tests (excluding live API tests)..."
    log_info "Use --live-api flag to run tests against real external APIs"
    echo
    
    # Run tests with exit code capture (only watch test-runner, not migrations)
    TEST_EXIT_CODE=0
    docker compose -f "$COMPOSE_FILE" run --rm test-runner || TEST_EXIT_CODE=$?
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
