#!/usr/bin/env bats

setup() {
    load test_helper
    setup_temp_dir
}

teardown() {
    teardown_temp_dir
}

# --- read_env_file ---

@test "read_env_file reads key=value pairs" {
    create_test_env "${TEST_TEMP_DIR}/.env"
    run read_env_file "${TEST_TEMP_DIR}/.env"
    [ "$status" -eq 0 ]
    [[ "$output" == *"POSTGRES_USER=analyzer"* ]]
    [[ "$output" == *"POSTGRES_PASSWORD=testpass123"* ]]
}

@test "read_env_file skips comment lines" {
    cat > "${TEST_TEMP_DIR}/.env" << 'EOF'
# This is a comment
KEY1=value1
# Another comment
KEY2=value2
EOF
    run read_env_file "${TEST_TEMP_DIR}/.env"
    [ "$status" -eq 0 ]
    [[ "$output" != *"# This"* ]]
    [[ "$output" == *"KEY1=value1"* ]]
    [[ "$output" == *"KEY2=value2"* ]]
}

@test "read_env_file resolves variable references" {
    export TEST_READ_SECRET="my_secret_token"
    cat > "${TEST_TEMP_DIR}/.env" << 'EOF'
MY_TOKEN=$TEST_READ_SECRET
PLAIN_VALUE=hello
EOF
    run read_env_file "${TEST_TEMP_DIR}/.env"
    [ "$status" -eq 0 ]
    [[ "$output" == *"MY_TOKEN=my_secret_token"* ]]
    [[ "$output" == *"PLAIN_VALUE=hello"* ]]
    unset TEST_READ_SECRET
}

@test "read_env_file handles values containing equals signs" {
    cat > "${TEST_TEMP_DIR}/.env" << 'EOF'
BROKER_URL=amqp://user:pass@host:5672//
SIMPLE=value
EOF
    run read_env_file "${TEST_TEMP_DIR}/.env"
    [ "$status" -eq 0 ]
    [[ "$output" == *"BROKER_URL=amqp://user:pass@host:5672//"* ]]
}

@test "read_env_file returns error for missing file" {
    run read_env_file "${TEST_TEMP_DIR}/nonexistent"
    [ "$status" -eq 1 ]
}

@test "read_env_file skips blank lines" {
    cat > "${TEST_TEMP_DIR}/.env" << 'EOF'
KEY1=val1

KEY2=val2
EOF
    run read_env_file "${TEST_TEMP_DIR}/.env"
    [ "$status" -eq 0 ]
    local line_count
    line_count=$(echo "$output" | grep -c '=')
    [ "$line_count" -eq 2 ]
}

# --- test_required_env_vars ---

@test "test_required_env_vars passes with valid credentials" {
    cat > "${TEST_TEMP_DIR}/.env" << 'EOF'
POSTGRES_PASSWORD=secret123
RABBITMQ_DEFAULT_PASS=rabbit456
GITHUB_TOKEN=ghp_realtoken123
AZURE_DEVOPS_PAT=
EOF
    run test_required_env_vars "${TEST_TEMP_DIR}/.env"
    [ "$status" -eq 0 ]
}

@test "test_required_env_vars fails when POSTGRES_PASSWORD is blank" {
    cat > "${TEST_TEMP_DIR}/.env" << 'EOF'
POSTGRES_PASSWORD=
RABBITMQ_DEFAULT_PASS=rabbit456
GITHUB_TOKEN=ghp_realtoken123
EOF
    run test_required_env_vars "${TEST_TEMP_DIR}/.env"
    [ "$status" -eq 1 ]
    [[ "$output" == *"POSTGRES_PASSWORD"* ]]
}

@test "test_required_env_vars fails when no auth token configured" {
    cat > "${TEST_TEMP_DIR}/.env" << 'EOF'
POSTGRES_PASSWORD=secret123
RABBITMQ_DEFAULT_PASS=rabbit456
GITHUB_TOKEN=your_github_token
AZURE_DEVOPS_PAT=
EOF
    run test_required_env_vars "${TEST_TEMP_DIR}/.env"
    [ "$status" -eq 1 ]
    [[ "$output" == *"No authentication token"* ]]
}

@test "test_required_env_vars accepts AZURE_DEVOPS_PAT as sole auth token" {
    cat > "${TEST_TEMP_DIR}/.env" << 'EOF'
POSTGRES_PASSWORD=secret123
RABBITMQ_DEFAULT_PASS=rabbit456
GITHUB_TOKEN=
AZURE_DEVOPS_PAT=real_azure_pat_here
EOF
    run test_required_env_vars "${TEST_TEMP_DIR}/.env"
    [ "$status" -eq 0 ]
}

@test "test_required_env_vars rejects placeholder values" {
    cat > "${TEST_TEMP_DIR}/.env" << 'EOF'
POSTGRES_PASSWORD=secret123
RABBITMQ_DEFAULT_PASS=rabbit456
GITHUB_TOKEN=changeme
AZURE_DEVOPS_PAT=your_azure_pat
EOF
    run test_required_env_vars "${TEST_TEMP_DIR}/.env"
    [ "$status" -eq 1 ]
    [[ "$output" == *"No authentication token"* ]]
}

@test "test_required_env_vars fails for missing file" {
    run test_required_env_vars "${TEST_TEMP_DIR}/nonexistent"
    [ "$status" -eq 1 ]
    [[ "$output" == *"not found"* ]]
}

# --- export_resolved_env_vars ---

@test "export_resolved_env_vars exports plain values" {
    cat > "${TEST_TEMP_DIR}/.env" << 'EOF'
TEST_EXPORT_KEY=plain_value
EOF
    export_resolved_env_vars "${TEST_TEMP_DIR}/.env"
    [ "$TEST_EXPORT_KEY" = "plain_value" ]
    unset TEST_EXPORT_KEY
}

@test "export_resolved_env_vars resolves variable references" {
    export TEST_SOURCE_VAR="the_real_value"
    cat > "${TEST_TEMP_DIR}/.env" << 'EOF'
TEST_TARGET_KEY=$TEST_SOURCE_VAR
EOF
    export_resolved_env_vars "${TEST_TEMP_DIR}/.env"
    [ "$TEST_TARGET_KEY" = "the_real_value" ]
    unset TEST_SOURCE_VAR TEST_TARGET_KEY
}

@test "export_resolved_env_vars reports missing references" {
    unset TOTALLY_MISSING_VAR_XYZ 2>/dev/null || true
    cat > "${TEST_TEMP_DIR}/.env" << 'EOF'
MY_KEY=$TOTALLY_MISSING_VAR_XYZ
EOF
    run export_resolved_env_vars "${TEST_TEMP_DIR}/.env"
    [ "$status" -eq 1 ]
    [[ "$output" == *"could not be resolved"* ]]
}

# --- new_env_file (non-interactive skip path) ---

@test "new_env_file skips generation when .env exists and force is false" {
    create_test_env_example "${TEST_TEMP_DIR}/.env.example"
    touch "${TEST_TEMP_DIR}/.env"
    run new_env_file "false" "${TEST_TEMP_DIR}/.env" "${TEST_TEMP_DIR}/.env.example"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Existing .env found"* ]]
}

@test "new_env_file fails when .env.example is missing" {
    run new_env_file "false" "${TEST_TEMP_DIR}/.env" "${TEST_TEMP_DIR}/nonexistent.example"
    [ "$status" -eq 1 ]
    [[ "$output" == *".env.example not found"* ]]
}
