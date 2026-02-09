#!/usr/bin/env bash

# Common test helper for bats tests.
# Sources the library modules and provides shared fixtures.

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="${TEST_DIR}/../lib"

# Source all library modules in dependency order
source "${LIB_DIR}/constants.sh"
source "${LIB_DIR}/output_helpers.sh"
source "${LIB_DIR}/environment_helpers.sh"
source "${LIB_DIR}/env_file_helpers.sh"

# Create a temporary directory for test fixtures
setup_temp_dir() {
    TEST_TEMP_DIR="$(mktemp -d)"
}

# Clean up temporary directory
teardown_temp_dir() {
    if [ -n "$TEST_TEMP_DIR" ] && [ -d "$TEST_TEMP_DIR" ]; then
        rm -rf "$TEST_TEMP_DIR"
    fi
}

# Create a minimal .env.example file for testing
create_test_env_example() {
    local file="${1:-${TEST_TEMP_DIR}/.env.example}"
    cat > "$file" << 'EOF'
# Database
POSTGRES_USER=analyzer
POSTGRES_PASSWORD=changeme
POSTGRES_DB=repo_analyzer
POSTGRES_HOST=timescaledb
POSTGRES_PORT=5432

# RabbitMQ
RABBITMQ_DEFAULT_USER=analyzer
RABBITMQ_DEFAULT_PASS=changeme
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672

# Auth tokens
GITHUB_TOKEN=your_github_token
AZURE_DEVOPS_PAT=

# Celery
CELERY_BROKER_URL=amqp://analyzer:changeme@rabbitmq:5672//
EOF
}

# Create a .env file with resolved values for testing
create_test_env() {
    local file="${1:-${TEST_TEMP_DIR}/.env}"
    cat > "$file" << 'EOF'
POSTGRES_USER=analyzer
POSTGRES_PASSWORD=testpass123
POSTGRES_DB=repo_analyzer
POSTGRES_HOST=timescaledb
POSTGRES_PORT=5432
RABBITMQ_DEFAULT_USER=analyzer
RABBITMQ_DEFAULT_PASS=rabbitpass456
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
GITHUB_TOKEN=ghp_test1234567890
AZURE_DEVOPS_PAT=
CELERY_BROKER_URL=amqp://analyzer:rabbitpass456@rabbitmq:5672//
EOF
}
