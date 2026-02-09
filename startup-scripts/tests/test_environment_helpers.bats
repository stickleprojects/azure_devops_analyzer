#!/usr/bin/env bats

setup() {
    load test_helper
}

# --- random_password ---

@test "random_password generates default length of 24" {
    run random_password
    [ "$status" -eq 0 ]
    [ "${#output}" -eq 24 ]
}

@test "random_password respects custom length" {
    run random_password 10
    [ "$status" -eq 0 ]
    [ "${#output}" -eq 10 ]
}

@test "random_password contains only alphanumeric characters" {
    run random_password 100
    [ "$status" -eq 0 ]
    [[ "$output" =~ ^[A-Za-z0-9]+$ ]]
}

@test "random_password generates unique values" {
    local pass1 pass2
    pass1=$(random_password 24)
    pass2=$(random_password 24)
    [ "$pass1" != "$pass2" ]
}

# --- resolve_env_value ---

@test "resolve_env_value returns plain text unchanged" {
    run resolve_env_value "hello"
    [ "$status" -eq 0 ]
    [ "$output" = "hello" ]
}

@test "resolve_env_value resolves \$VAR syntax" {
    export TEST_RESOLVE_VAR="resolved_value"
    run resolve_env_value '$TEST_RESOLVE_VAR'
    [ "$status" -eq 0 ]
    [ "$output" = "resolved_value" ]
    unset TEST_RESOLVE_VAR
}

@test "resolve_env_value resolves \${VAR} syntax" {
    export TEST_RESOLVE_VAR2="braced_value"
    run resolve_env_value '${TEST_RESOLVE_VAR2}'
    [ "$status" -eq 0 ]
    [ "$output" = "braced_value" ]
    unset TEST_RESOLVE_VAR2
}

@test "resolve_env_value resolves \$env:VAR syntax" {
    export TEST_ENV_VAR="env_value"
    run resolve_env_value '$env:TEST_ENV_VAR'
    [ "$status" -eq 0 ]
    [ "$output" = "env_value" ]
    unset TEST_ENV_VAR
}

@test "resolve_env_value returns original if variable not set" {
    unset NONEXISTENT_VAR_XYZ 2>/dev/null || true
    run resolve_env_value '$NONEXISTENT_VAR_XYZ'
    [ "$status" -eq 0 ]
    [ "$output" = '$NONEXISTENT_VAR_XYZ' ]
}

@test "resolve_env_value returns non-reference strings unchanged" {
    run resolve_env_value "amqp://user:pass@host:5672//"
    [ "$status" -eq 0 ]
    [ "$output" = "amqp://user:pass@host:5672//" ]
}
