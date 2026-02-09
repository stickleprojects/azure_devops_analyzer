#!/usr/bin/env bats

setup() {
    SCRIPT="d:/code/tyl/azure-devops-analyzer/Start-RepoAnalysis.sh"
}

@test "script shows usage with --help" {
    run bash "$SCRIPT" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"--skip-infrastructure"* ]]
    [[ "$output" == *"--run-direct"* ]]
    [[ "$output" == *"--tear-down"* ]]
    [[ "$output" == *"--regenerate-env"* ]]
}

@test "script shows usage with -h" {
    run bash "$SCRIPT" -h
    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
}

@test "script rejects unknown options" {
    run bash "$SCRIPT" --nonexistent-flag
    [ "$status" -eq 1 ]
    [[ "$output" == *"Unknown option"* ]]
}

@test "script requires bash 4+" {
    # Verify the version check string is present in the script
    grep -q 'BASH_VERSINFO\[0\]' "$SCRIPT"
}
