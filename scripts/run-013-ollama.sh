#!/usr/bin/env bash
# run-013-ollama.sh
#
# Executes plan 013 deliverables using a local Ollama model.
# Everything runs inside Docker — no host Python or Aider required.
#
# Usage:
#   bash scripts/run-013-ollama.sh [--model <model>] [--step A|B|C|D|E]
#
# Options:
#   --model   Ollama model name (default: qwen3-coder:30b)
#   --step    Run a single step only (default: run all steps)
#
# Prerequisites:
#   Docker running
#   Ollama running at http://localhost:11434 (reachable as host.docker.internal from Docker)

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ── Config ────────────────────────────────────────────────────────────────────
MODEL="${OLLAMA_MODEL:-qwen3-coder:30b}"
OLLAMA_URL="${OLLAMA_URL:-http://host.docker.internal:11434}"
PROMPTS=".ai/ollama-prompts"
STEP=""

# ── Arg parsing ───────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --model) MODEL="$2"; shift 2 ;;
        --step)  STEP="$2";  shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ── Helpers ───────────────────────────────────────────────────────────────────
info()  { echo ""; echo "==> $*"; }
check() { echo "  [check] $*"; }

# Run any Python script inside Docker with the project mounted at /app.
# MSYS_NO_PATHCONV=1 prevents Git Bash on Windows from mangling /app into
# C:/Program Files/Git/app.
run_docker_python() {
    MSYS_NO_PATHCONV=1 docker run --rm \
        -v "$PROJECT_ROOT:/app" \
        -w /app \
        python:3.12-slim \
        "$@"
}

# Validate a generated Python file
validate_python_file() {
    local file="$1"
    local min_lines="${2:-20}"
    
    if [ ! -f "$file" ]; then
        echo "  [FAIL] File not created: $file"
        return 1
    fi
    
    local lines=$(wc -l < "$file" 2>/dev/null || echo "0")
    if [ "$lines" -lt "$min_lines" ]; then
        echo "  [WARN] File suspiciously small: $lines lines (expected >$min_lines)"
        echo "         Please review: $file"
    fi
    
    if ! python -m py_compile "$file" 2>/dev/null; then
        echo "  [FAIL] Syntax errors in: $file"
        return 1
    fi
    
    echo "  [OK] $file validated ($lines lines)"
    return 0
}

# Lazy Ollama check — runs once, skipped on subsequent calls.
_OLLAMA_CHECKED=false
require_ollama() {
    [ "$_OLLAMA_CHECKED" = true ] && return
    if ! curl -sf http://localhost:11434/api/tags &>/dev/null; then
        echo "ERROR: Ollama not responding at http://localhost:11434"
        echo "       Start Ollama with: ollama serve"
        exit 1
    fi
    if ! curl -sf http://localhost:11434/api/tags | grep -q "\"$MODEL\""; then
        echo "ERROR: Model '$MODEL' not found in Ollama."
        echo "       Pull it with: ollama pull $MODEL"
        exit 1
    fi
    check "Ollama running, model available: $MODEL"
    _OLLAMA_CHECKED=true
}

# Call ollama-generate.py inside Docker for a given prompt + output file.
# Usage: run_ollama_generate <prompt-file> <output-file> [--context <file>] ...
run_ollama_generate() {
    require_ollama
    local prompt="$1"
    local output="$2"
    shift 2
    run_docker_python \
        python scripts/ollama-generate.py \
            --model "$MODEL" \
            --ollama-url "$OLLAMA_URL" \
            --prompt "$prompt" \
            --output "$output" \
            "$@"
}

# Enhanced generation with automatic validation
# Usage: run_ollama_generate_safe <prompt-file> <output-file> <min-lines> [--context <file>] ...
run_ollama_generate_safe() {
    local prompt="$1"
    local output="$2"
    local min_lines="${3:-20}"
    shift 3
    
    run_ollama_generate "$prompt" "$output" "$@"
    validate_python_file "$output" "$min_lines"
}

# ── Preflight ─────────────────────────────────────────────────────────────────
info "Preflight checks"

if ! docker info &>/dev/null; then
    echo "ERROR: Docker is not running."
    echo "       Please start Docker and try again."
    exit 1
fi
check "Docker running"

echo ""
echo "Model      : $MODEL"
echo "Ollama URL : $OLLAMA_URL"
echo "Steps      : ${STEP:-A B C D E}"
echo ""

# ── Step A: Generate fixture generator script + run it ───────────────────────
run_step_a() {
    info "Step A1: Generating scripts/generate-013-fixtures.py"
    run_ollama_generate_safe \
        "$PROMPTS/013-A-generate-fixtures.md" \
        "scripts/generate-013-fixtures.py" \
        100
    echo "  Done — scripts/generate-013-fixtures.py"
    
    info "Step A2: Running generated script to create JSON fixture files"
    run_docker_python python scripts/generate-013-fixtures.py
    echo "  Done — 10 files written to tests/fixtures/scenarios/generated/"
}

# ── Step B: FixtureExtractor ──────────────────────────────────────────────────
run_step_b() {
    info "Step B: Generating tests/fixtures/fixture_extractor.py"
    run_ollama_generate_safe \
        "$PROMPTS/013-B-fixture-extractor.md" \
        "tests/fixtures/fixture_extractor.py" \
        30 \
        --context "src/extractors/base.py"
    echo "  Done — tests/fixtures/fixture_extractor.py"
}

# ── Step C: Factory functions ─────────────────────────────────────────────────
run_step_c() {
    info "Step C: Extending tests/fixtures/sample_data.py"
    # Pass the existing file as context so the model can produce the full updated file.
    run_ollama_generate_safe \
        "$PROMPTS/013-C-factory-functions.md" \
        "tests/fixtures/sample_data.py" \
        200 \
        --context "tests/fixtures/sample_data.py" \
        --context "src/analyzers/technology_detector.py"
    echo "  Done — tests/fixtures/sample_data.py"
}

# ── Step D: capture_snapshot.py ───────────────────────────────────────────────
run_step_d() {
    info "Step D: Generating scripts/capture_snapshot.py"
    run_ollama_generate_safe \
        "$PROMPTS/013-D-capture-snapshot.md" \
        "scripts/capture_snapshot.py" \
        40 \
        --context "src/extractors/base.py" \
        --context "src/extractors/factory.py"
    echo "  Done — scripts/capture_snapshot.py"
}

# ── Step E: verify_canary.py ──────────────────────────────────────────────────
run_step_e() {
    info "Step E: Generating scripts/verify_canary.py"
    run_ollama_generate_safe \
        "$PROMPTS/013-E-verify-canary.md" \
        "scripts/verify_canary.py" \
        50
    echo "  Done — scripts/verify_canary.py"
}

# ── Dispatch ──────────────────────────────────────────────────────────────────
case "${STEP:-all}" in
    A|a) run_step_a ;;
    B|b) run_step_b ;;
    C|c) run_step_c ;;
    D|d) run_step_d ;;
    E|e) run_step_e ;;
    all)
        run_step_a
        run_step_b
        run_step_c
        run_step_d
        run_step_e
        ;;
    *) echo "Unknown step: $STEP (valid: A B C D E)"; exit 1 ;;
esac

# ── Post-run hint ─────────────────────────────────────────────────────────────
echo ""
echo "=================================================="
echo "  Review generated files before committing."
echo "  Run tests: bash scripts/run-tests-docker.sh"
echo "  Pre-commit: pre-commit run --all-files"
echo "=================================================="
