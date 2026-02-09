#!/bin/bash

# Docker Compose and infrastructure utilities.

run_docker_compose() {
    # MSYS_NO_PATHCONV prevents Git Bash on Windows from converting
    # Unix-style container paths (e.g. /app/scripts/...) into Windows paths.
    MSYS_NO_PATHCONV=1 docker compose "$@"
}

test_docker_prerequisites() {
    write_step "Checking Docker prerequisites..."

    if ! command -v docker >/dev/null 2>&1; then
        write_error "Docker is not installed or not in PATH. Please install Docker Desktop."
        return 1
    fi

    if ! docker info >/dev/null 2>&1; then
        write_error "Docker daemon is not running. Please start Docker Desktop."
        return 1
    fi

    write_success "Docker is running"

    if ! docker compose version >/dev/null 2>&1; then
        write_error "Docker Compose v2 is not available. Please install Docker Desktop or Docker Compose v2."
        return 1
    fi

    write_success "Docker Compose v2 is available"
    write_success "Docker prerequisites met"
    return 0
}

wait_for_healthy() {
    local container_name="$1"
    local max_retries="${2:-30}"
    local interval="${3:-2}"

    local retry=0
    while [ $retry -lt $max_retries ]; do
        local health
        health=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "")
        if [ "$health" = "healthy" ]; then
            write_success "$container_name is healthy"
            return 0
        fi
        retry=$((retry + 1))
        printf "."
        sleep "$interval"
    done

    write_error "$container_name failed to become healthy"
    return 1
}
