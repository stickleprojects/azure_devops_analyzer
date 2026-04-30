#!/usr/bin/env bash

set -e

if [ "${BASH_VERSINFO[0]}" -lt 4 ]; then
    echo "Error: Bash 4.0+ is required (found ${BASH_VERSION}). On macOS, run: brew install bash" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="${SCRIPT_DIR}/startup-scripts/lib"

# shellcheck source=/dev/null
source "${LIB_DIR}/constants.sh"
# shellcheck source=/dev/null
source "${LIB_DIR}/output_helpers.sh"
# shellcheck source=/dev/null
source "${LIB_DIR}/environment_helpers.sh"
# shellcheck source=/dev/null
source "${LIB_DIR}/docker_helpers.sh"
# shellcheck source=/dev/null
source "${LIB_DIR}/env_file_helpers.sh"

SKIP_INFRASTRUCTURE="false"
RUN_DIRECT="false"
TEAR_DOWN="false"
REGENERATE_ENV="false"

usage() {
    cat << 'EOF'
Usage: ./Start-RepoAnalysis.sh [options]

Options:
  --skip-infrastructure   Skip starting Docker containers
  --run-direct            Run extraction directly (no Celery workers)
  --tear-down             Stop and remove containers/volumes after analysis
  --regenerate-env        Recreate .env and prompt for values
  --help                  Show this help
EOF
}

parse_args() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --skip-infrastructure)
                SKIP_INFRASTRUCTURE="true"
                ;;
            --run-direct)
                RUN_DIRECT="true"
                ;;
            --tear-down)
                TEAR_DOWN="true"
                ;;
            --regenerate-env)
                REGENERATE_ENV="true"
                ;;
            --help|-h)
                usage
                exit 0
                ;;
            *)
                write_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
        shift
    done
}

initialize_environment() {
    write_step "Configuring environment..."

    if ! new_env_file "$REGENERATE_ENV" "$ENV_FILE" "$ENV_EXAMPLE_FILE"; then
        return 1
    fi

    write_info "Validating required credentials..."
    if ! test_required_env_vars "$ENV_FILE"; then
        write_error "Environment validation failed. Please configure valid credentials."
        return 1
    fi

    write_info "Resolving and exporting environment variables..."
    if ! export_resolved_env_vars "$ENV_FILE"; then
        write_error "Failed to resolve environment variable references. See warnings above."
        return 1
    fi

    return 0
}

start_infrastructure() {
    write_step "Starting Docker infrastructure..."

    (
        cd "$PROJECT_ROOT" || exit 1

        write_info "Pulling Docker images..."
        run_docker_compose pull >/dev/null 2>&1

        # db-migrations embeds the migration runner script in the image.
        # Rebuild it so script changes are always picked up.
        write_info "Building migration image (to avoid stale migration runner)..."
        run_docker_compose build "$DOCKER_MIGRATION_SERVICE" >/dev/null

        write_info "Starting all services (scheduler, celery-beat, workers, monitoring)..."
        local up_output
        if ! up_output=$(run_docker_compose up -d 2>&1); then
            write_error "Docker services failed to start"
            echo "$up_output"
            write_info "Recent db-migrations logs:"
            run_docker_compose logs --no-color --tail 80 "$DOCKER_MIGRATION_SERVICE" || true
            return 1
        fi

        write_info "Waiting for services to be healthy..."
        wait_for_healthy "analyzer-timescaledb" "$MAX_HEALTH_CHECK_RETRIES" "$HEALTH_CHECK_INTERVAL" >/dev/null
        wait_for_healthy "analyzer-rabbitmq" "$MAX_HEALTH_CHECK_RETRIES" "$HEALTH_CHECK_INTERVAL" >/dev/null
    )
}

initialize_database() {
    write_step "Initializing database schema and migrations..."

    (
        cd "$PROJECT_ROOT" || exit 1

        write_info "Starting database migration service..."
        if ! run_docker_compose run --rm "$DOCKER_MIGRATION_SERVICE"; then
            write_error "Migration service failed"
            write_info "Recent db-migrations logs:"
            run_docker_compose logs --no-color --tail 120 "$DOCKER_MIGRATION_SERVICE" || true
            return 1
        fi

        write_success "Database schema and migrations initialized successfully"
    )
}

start_analysis() {
    write_step "Running repository analysis..."

    (
        cd "$PROJECT_ROOT" || exit 1

        write_info "Building application image..."
        run_docker_compose build "$DOCKER_SCHEDULER_SERVICE" >/dev/null 2>&1

        if [ "$RUN_DIRECT" = "true" ]; then
            write_info "Starting repository extraction in DIRECT mode (synchronous)..."
            if ! run_docker_compose run --rm "$DOCKER_SCHEDULER_SERVICE" python /app/scripts/run_extraction.py; then
                write_warning "Extraction completed with some warnings"
            else
                write_success "Extraction completed successfully"
            fi
        else
            write_info "Submitting extraction task to Celery workers..."
            if ! run_docker_compose run --rm "$DOCKER_SCHEDULER_SERVICE" python /app/scripts/submit_extraction_task.py; then
                write_error "Failed to submit extraction task"
            else
                write_success "Extraction task submitted successfully"
                write_info "Task is now being processed by Celery workers"
            fi
        fi
    )
}

show_access_info() {
    write_step "Analysis complete! Access your data:"

    local mode_info
    if [ "$RUN_DIRECT" = "true" ]; then
        mode_info="DIRECT mode - extraction ran synchronously"
    else
        mode_info="CELERY mode - extraction submitted to background workers"
    fi

    cat << EOF

 EXECUTION MODE:
 ---------------
 ${mode_info}

 SERVICES AVAILABLE:
 -------------------
 TimescaleDB:     localhost:5432
 RabbitMQ:        localhost:5672
 RabbitMQ UI:     ${RABBITMQ_MANAGEMENT_URL}
 Flower UI:       ${FLOWER_URL} (task monitoring)
 Grafana UI:      ${GRAFANA_URL} (no auth required)
 Scheduler:       Running (APScheduler for periodic extractions)
 Celery Beat:     Running (Celery periodic task scheduler)
 Celery Worker:   Running (background task processing)

 DATABASE CONNECTION:
 --------------------
 Host:     localhost
 Port:     5432
 Database: repo_analyzer
 User:     analyzer
 Password: (see .env file)

 USEFUL QUERIES:
 ---------------
 -- List all repositories
 SELECT r.name, r.url, r.default_branch, o.name as org
 FROM repositories r
 JOIN projects p ON r.project_id = p.project_id
 JOIN organizations o ON p.organization_id = o.organization_id;

 -- Count commits by contributor
 SELECT c.name, c.email, COUNT(cm.commit_sha) as commit_count
 FROM contributors c
 JOIN commits cm ON c.id = cm.author_id
 GROUP BY c.id, c.name, c.email
 ORDER BY commit_count DESC;

 -- PR statistics
 SELECT status, COUNT(*) as count, AVG(lines_added + lines_removed) as avg_changes
 FROM pull_requests
 GROUP BY status;

 NEXT STEPS:
 -----------
 1. Open Grafana at ${GRAFANA_URL} to view dashboards
 2. Connect a SQL client to explore raw data if needed
 3. Run scheduled analysis with: docker compose up -d
EOF

    if [ "$RUN_DIRECT" != "true" ]; then
        echo " 4. Monitor task progress in Flower at ${FLOWER_URL}"
    fi

    echo ""
}

stop_infrastructure() {
    write_step "Tearing down infrastructure..."

    (
        cd "$PROJECT_ROOT" || exit 1
        run_docker_compose down -v >/dev/null 2>&1
        write_success "Infrastructure stopped and volumes removed"
    )
}

main() {
    show_banner

    if ! test_docker_prerequisites; then
        write_error "Docker prerequisites not met"
        exit 1
    fi

    if ! initialize_environment; then
        write_error "Failed to initialize environment"
        exit 1
    fi

    if [ "$SKIP_INFRASTRUCTURE" != "true" ]; then
        start_infrastructure
        initialize_database
    fi

    start_analysis
    show_access_info

    if [ "$TEAR_DOWN" = "true" ]; then
        stop_infrastructure
    fi
}

parse_args "$@"
main
