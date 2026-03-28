#!/bin/bash
# NOTE: Keep this script in sync with .github/workflows/tests.yml.
# Default test flow here mirrors CI step order and database env assumptions.
# =============================================================================
# Integration Test Runner - Docker Compose
# =============================================================================
# Runs tests in Docker in the same order as GitHub Actions CI.
#
# Usage:
#   ./scripts/run-tests-docker.sh              # Run CI-equivalent test sequence
#   ./scripts/run-tests-docker.sh --live-api   # Run only live API tests
#   ./scripts/run-tests-docker.sh <test_path>  # Run specific test file or pattern
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
TEST_PATH=""
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
Integration Test Runner - Docker Compose (CI-Equivalent)

Runs tests in Docker environment to closely match GitHub Actions CI workflow.
Tests run in the same sequence used by CI (unit, integration, live-api gate, coverage).

USAGE:
    $0 [OPTIONS] [TEST_PATH]

OPTIONS:
    TEST_PATH       Run specific test file or pattern (e.g., tests/unit/test_*.py)
    --live-api      Run live API tests (tests marked with @pytest.mark.live_api)
                    Includes both GitHub and Azure DevOps platform tests
    --keep-db       Keep test database after run (for debugging)
    --no-cleanup    Don't clean up containers after run
    --help          Show this help message

EXAMPLES:
    # Run all tests (CI-equivalent: unit → integration → live-api gate → coverage)
    $0

    # Run specific test file
    $0 tests/unit/extractors/test_cache.py

    # Run only live API tests for both GitHub and Azure DevOps
    $0 --live-api

    # Keep database for debugging
    $0 --keep-db

TEST SEQUENCE (matches .github/workflows/tests.yml):
    When no TEST_PATH specified, runs in 4 steps (like CI):
    
    1. Unit tests (tests/unit/) - no coverage
    2. Integration tests (tests/contract/integration/) - no coverage
    3. Live API tests (credentials gated; skipped when creds absent)
    4. Coverage report - runs ALL tests again with coverage analysis
    
    This matches GitHub Actions CI exactly, helping catch CI failures before pushing.

WHAT GETS TESTED (excluding live API):
    Unit Tests:
    - Extractor caching and utilities
    - Analyzer logic and helpers

    Contract & Integration Tests:
    - Database schema and views
    - Repository extraction and metadata storage
    - Branch and commit tracking

REQUIREMENTS:
    - Docker and Docker Compose installed
    - GITHUB_TOKEN environment variable set (for GitHub tests)
    - AZURE_DEVOPS_PAT and AZURE_DEVOPS_ORG_URL (for Azure DevOps tests, optional)

OUTPUT:
    Test results saved to: $RESULTS_DIR/
    - junit.xml - Test results in JUnit format
    - coverage.xml - Coverage report
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

start_test_db_and_migrations() {
    log_info "Starting test database..."
    docker compose --env-file "$RESOLVED_ENV_FILE" -f "$COMPOSE_FILE" up -d test-db >/dev/null 2>&1
    log_success "Test database started"

    log_info "Applying database schema/migrations..."
    docker compose --env-file "$RESOLVED_ENV_FILE" -f "$COMPOSE_FILE" run --rm test-migrations
    log_success "Database schema/migrations applied"
}

run_pytest_in_runner() {
    local pytest_cmd="$1"
    local exit_code=0
    docker compose --env-file "$RESOLVED_ENV_FILE" -f "$COMPOSE_FILE" run --rm test-runner \
        sh -c "pip install pytest pytest-cov pytest-asyncio pytest-mock && ${pytest_cmd}" || exit_code=$?
    return $exit_code
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
        -*)
            log_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 2
            ;;
        *)
            # Treat as test path
            TEST_PATH="$1"
            shift
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

start_test_db_and_migrations

if [ "$RUN_LIVE_API" = true ]; then
    log_info "Running GitHub AND Azure DevOps tests with LIVE API..."
    log_warning "This will hit real external APIs - may be slow and count against rate limits"
    echo
    
    # Run both GitHub and Azure DevOps tests with live_api marker
    TEST_EXIT_CODE=0
    run_pytest_in_runner "pytest tests/contract/integration/ -v --tb=short --durations=10 -m 'live_api' --junit-xml=/app/test-results/junit-live-api.xml -o junit_family=xunit2 -o junit_logging=all -p no:cacheprovider" || TEST_EXIT_CODE=$?
elif [ -n "$TEST_PATH" ]; then
    log_info "Running specific test: $TEST_PATH"
    echo
    
    # Run specific test path
    TEST_EXIT_CODE=0
    run_pytest_in_runner "pytest '$TEST_PATH' -v --tb=short --junit-xml=/app/test-results/junit.xml -o junit_family=xunit2 -o junit_logging=all -p no:cacheprovider" || TEST_EXIT_CODE=$?
else
    log_info "Running tests in CI-equivalent sequence..."
    log_info "This matches the exact steps from .github/workflows/tests.yml"
    echo
    
    # =========================================================================
    # Step 1: Unit Tests (no coverage)
    # =========================================================================
    log_info "Step 1/4: Running unit tests..."
    TEST_EXIT_CODE=0
    run_pytest_in_runner "pytest tests/unit/ -v --tb=short" || TEST_EXIT_CODE=$?
    
    if [ $TEST_EXIT_CODE -ne 0 ]; then
        log_error "Unit tests failed (exit code: $TEST_EXIT_CODE)"
        # Continue to cleanup
    else
        log_success "Unit tests passed"
        echo
        
        # =====================================================================
        # Step 2: Integration Tests (no coverage)
        # =====================================================================
        log_info "Step 2/4: Running integration tests..."
        run_pytest_in_runner "pytest tests/contract/integration/ -v --tb=short --durations=10 -m 'not live_api'" || TEST_EXIT_CODE=$?
        
        if [ $TEST_EXIT_CODE -ne 0 ]; then
            log_error "Integration tests failed (exit code: $TEST_EXIT_CODE)"
            # Continue to cleanup
        else
            log_success "Integration tests passed"
            echo
            
            # =================================================================
            # Step 3: Live API Tests (credential-gated, like CI)
            # =================================================================
            if [ -n "${GITHUB_TOKEN:-}" ] && [ -n "${AZURE_DEVOPS_PAT:-}" ] && [ -n "${AZURE_DEVOPS_ORG_URL:-}" ]; then
                log_info "Step 3/4: Running live API tests (credentials detected)..."
                run_pytest_in_runner "pytest tests/contract/integration/ -v --tb=short --durations=10 -m 'live_api'" || TEST_EXIT_CODE=$?
                if [ $TEST_EXIT_CODE -ne 0 ]; then
                    log_error "Live API tests failed (exit code: $TEST_EXIT_CODE)"
                else
                    log_success "Live API tests passed"
                fi
            else
                log_info "Step 3/4: Skipping live API tests (missing credentials)"
            fi

            if [ $TEST_EXIT_CODE -eq 0 ]; then
                # =============================================================
                # Step 4: Coverage Report (runs ALL tests again)
                # =============================================================
                log_info "Step 4/4: Generating coverage report (runs all tests)..."
                run_pytest_in_runner "mkdir -p /app/test-results && pytest tests/ --cov=src --cov-report=xml:/app/test-results/coverage.xml --cov-report=term-missing -m 'not live_api' -p no:cacheprovider --junit-xml=/app/test-results/junit.xml" || TEST_EXIT_CODE=$?
            
                if [ $TEST_EXIT_CODE -ne 0 ]; then
                    log_error "Coverage generation failed (exit code: $TEST_EXIT_CODE)"
                else
                    log_success "Coverage report generated"
                fi
            fi
        fi
    fi
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
    echo "  - Coverage:  $RESULTS_DIR/coverage.xml"
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
