#!/usr/bin/env bats

setup() {
    load test_helper
}

@test "PROJECT_ROOT is set and is a directory" {
    [ -n "$PROJECT_ROOT" ]
    [ -d "$PROJECT_ROOT" ]
}

@test "ENV_FILE points to .env in project root" {
    [[ "$ENV_FILE" == *"/.env" ]]
}

@test "ENV_EXAMPLE_FILE points to .env.example in project root" {
    [[ "$ENV_EXAMPLE_FILE" == *"/.env.example" ]]
}

@test "DOCKER_CORE_SERVICES contains expected services" {
    local found_timescaledb=false
    local found_rabbitmq=false
    for svc in "${DOCKER_CORE_SERVICES[@]}"; do
        [ "$svc" = "timescaledb" ] && found_timescaledb=true
        [ "$svc" = "rabbitmq" ] && found_rabbitmq=true
    done
    [ "$found_timescaledb" = "true" ]
    [ "$found_rabbitmq" = "true" ]
}

@test "DOCKER_WORKER_SERVICE is set" {
    [ -n "$DOCKER_WORKER_SERVICE" ]
    [ "$DOCKER_WORKER_SERVICE" = "celery-worker" ]
}

@test "DOCKER_MIGRATION_SERVICE is set" {
    [ -n "$DOCKER_MIGRATION_SERVICE" ]
    [ "$DOCKER_MIGRATION_SERVICE" = "db-migrations" ]
}

@test "DOCKER_SCHEDULER_SERVICE is set" {
    [ -n "$DOCKER_SCHEDULER_SERVICE" ]
    [ "$DOCKER_SCHEDULER_SERVICE" = "scheduler" ]
}

@test "health check defaults are reasonable" {
    [ "$MAX_HEALTH_CHECK_RETRIES" -gt 0 ]
    [ "$HEALTH_CHECK_INTERVAL" -gt 0 ]
}

@test "PASSWORD_LENGTH is set" {
    [ "$PASSWORD_LENGTH" -gt 0 ]
}

@test "service URLs are well-formed" {
    [[ "$GRAFANA_URL" == http://localhost:* ]]
    [[ "$FLOWER_URL" == http://localhost:* ]]
    [[ "$RABBITMQ_MANAGEMENT_URL" == http://localhost:* ]]
}
