#!/usr/bin/env bats

setup() {
    load test_helper
}

@test "write_step outputs step marker with message" {
    run write_step "Testing step"
    [ "$status" -eq 0 ]
    [[ "$output" == *"==>"* ]]
    [[ "$output" == *"Testing step"* ]]
}

@test "write_success outputs OK marker" {
    run write_success "It worked"
    [ "$status" -eq 0 ]
    [[ "$output" == *"[OK]"* ]]
    [[ "$output" == *"It worked"* ]]
}

@test "write_warning outputs WARN marker" {
    run write_warning "Be careful"
    [ "$status" -eq 0 ]
    [[ "$output" == *"[WARN]"* ]]
    [[ "$output" == *"Be careful"* ]]
}

@test "write_error outputs ERROR marker" {
    run write_error "Something broke"
    [ "$status" -eq 0 ]
    [[ "$output" == *"[ERROR]"* ]]
    [[ "$output" == *"Something broke"* ]]
}

@test "write_info outputs INFO marker" {
    run write_info "Just so you know"
    [ "$status" -eq 0 ]
    [[ "$output" == *"[INFO]"* ]]
    [[ "$output" == *"Just so you know"* ]]
}

@test "show_banner outputs ASCII art" {
    run show_banner
    [ "$status" -eq 0 ]
    [[ "$output" == *"Repo"* ]]
    [[ "$output" == *"Analyzer"* ]]
}
