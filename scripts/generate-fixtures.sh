#!/usr/bin/env bash
# generate-fixtures.sh
#
# Config-driven fixture generation (Plan 014):
# - validates config.json
# - generates seed generator script via Ollama
# - runs seed generator to create JSON seeds
# - generates enrichment scripts per seed and enriches them
#
# Usage:
#   bash scripts/generate-fixtures.sh [--model <model>] [--ollama-url <url>] [--step validate|seeds|enrich|all]
#
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

MODEL="${OLLAMA_MODEL:-qwen2.5-coder:14b}"
OLLAMA_URL="${OLLAMA_URL:-http://host.docker.internal:11434}"
STEP="all"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --model) MODEL="$2"; shift 2 ;;
        --ollama-url) OLLAMA_URL="$2"; shift 2 ;;
        --step) STEP="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

info()  { echo ""; echo "==> $*"; }
check() { echo "  [check] $*"; }

run_docker_python() {
    MSYS_NO_PATHCONV=1 docker run --rm \
        -e PYTHONUNBUFFERED=1 \
        -v "$PROJECT_ROOT:/app" \
        -w /app \
        python:3.12-slim \
        "$@"
}

_OLLAMA_CHECKED=false
require_ollama() {
    [[ "$_OLLAMA_CHECKED" == true ]] && return
    local check_url="$OLLAMA_URL"
    if [[ "$check_url" == *"host.docker.internal"* ]]; then
        check_url="${check_url/host.docker.internal/localhost}"
    fi

    if ! curl -sf "$check_url/api/tags" &>/dev/null; then
        echo "ERROR: Ollama not responding at $check_url"
        echo "       Start Ollama with: ollama serve"
        exit 1
    fi
    if ! curl -sf "$check_url/api/tags" | grep -q "\"$MODEL\""; then
        echo "ERROR: Model '$MODEL' not found in Ollama."
        echo "       Pull it with: ollama pull $MODEL"
        exit 1
    fi
    check "Ollama running, model available: $MODEL"
    _OLLAMA_CHECKED=true
}

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

validate_config() {
    info "Validating fixture config"
    run_docker_python python scripts/validate-fixture-config.py
}

run_seeds() {
    info "Generating seed generator script"
    run_ollama_generate \
        .ai/ollama-prompts/fixture-repo-seeds.md \
        scripts/generated/generate-repo-seeds.py \
        --context tests/fixtures/scenarios/config.json

    info "Creating seed JSON files"
    run_docker_python python scripts/generated/generate-repo-seeds.py
}

run_enrich() {
    info "Enriching seed JSON files"
    local seeds=(tests/fixtures/scenarios/generated/*.json)
    if [[ ${#seeds[@]} -eq 1 && "${seeds[0]}" == "tests/fixtures/scenarios/generated/*.json" ]]; then
        echo "ERROR: No seed JSON files found. Run --step seeds first."
        exit 1
    fi

    for seed in "${seeds[@]}"; do
        local name
        name="$(basename "$seed" .json)"
        local output="scripts/generated/enrich-${name}.py"

        info "Generating enrichment script for ${name}"
        run_ollama_generate \
            .ai/ollama-prompts/fixture-repo-enrichment.md \
            "$output" \
            --context tests/fixtures/scenarios/config.json \
            --context "$seed"

        info "Running enrichment for ${name}"
        run_docker_python python "$output" "$seed"
    done
}

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
echo "Step       : $STEP"
echo ""

case "$STEP" in
    validate) validate_config ;;
    seeds) validate_config; run_seeds ;;
    enrich) validate_config; run_enrich ;;
    all)
        validate_config
        run_seeds
        run_enrich
        ;;
    *)
        echo "Unknown step: $STEP (valid: validate|seeds|enrich|all)"
        exit 1
        ;;
esac

info "Done"
