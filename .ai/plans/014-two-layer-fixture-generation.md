# Plan 014: Two-Layer Fixture Generation

**Status**: 🔲 Not started
**Depends on**: Plan 013 (fixture factory infrastructure already in place)
**Problem**: Ollama context window overflow when scaling up commits/PRs per scenario
**Solution**: Split the single monolithic generation call into seeds + per-repo enrichment layers

---

## Problem Summary

`fixture-scenarios.md` (used in Plan 013 Step A) asks Ollama to generate a single Python file
that hardcodes ALL scenario data for all 10 repos in one response — including commits and PRs.
When the `commits` array is pushed beyond ~5 entries per repo, or `pull_requests` beyond ~3, the
combined prompt + output tokens exceed the model's context window and generation truncates.

Root cause: one call must produce ~300+ objects (10 repos × 20 commits + 10 repos × 10 PRs)
as hardcoded Python data. That is too large for a single context window.

---

## Solution: Two-Layer Generation + Python Orchestrator

### Layer 1 — Repository Seeds (one Ollama call)

Prompt: `.ai/ollama-prompts/fixture-repo-seeds.md`

Generates a Python script (`scripts/generated/generate-repo-seeds.py`) that writes one
`{name}.json` seed file per repository. Seeds contain only structural metadata:

- `name`, `description`, `file_names`, `language_data`, `manifests`, `branches`
- **No `commits` or `pull_requests`** — explicitly excluded to keep output compact

Same 10 repository identities as the current `fixture-scenarios.md` (stable names mean
downstream code — FixtureExtractor, sample_data.py — needs no changes).

### Layer 2 — Per-Repo Enrichment (one Ollama call per repo)

Prompt: `.ai/ollama-prompts/fixture-repo-enrichment.md`

Called once per seed file. The seed JSON is passed via `--context` so Ollama can see the
language mix, manifests, and branch names and generate a realistic, stack-appropriate response.

Each call generates a Python enrichment script (`scripts/generated/enrich-{name}.py`) with
this interface:

```python
# enrich-{name}.py — accepts seed file path as sys.argv[1]
import json, pathlib, sys
path = pathlib.Path(sys.argv[1])
data = json.loads(path.read_text())
data["commits"] = [...]        # 15–30 entries, language-appropriate commit messages
data["pull_requests"] = [...]  # 5–15 entries, mix of "merged" / "open" / "closed"
path.write_text(json.dumps(data, indent=2) + "\n")
print(f"[OK] Enriched {path.name}")
```

Target scale (much larger than before, now feasible because each call handles one repo):
- `commits`: 15–30 entries, ordered oldest→newest by `commit_date`
- `pull_requests`: 5–15 entries, dates aligned with commits

### Architecture

```
generate-fixtures.sh          (host — bash, thin launcher only)
  └── docker run python:3.12-slim python scripts/generate-fixtures.py [args]
        │  (everything below runs inside Docker)
        │
        ├── Step A1: ollama-generate.py --prompt fixture-repo-seeds.md
        │           python scripts/generated/generate-repo-seeds.py
        │           → writes 10 seed JSONs to tests/fixtures/scenarios/generated/
        │
        ├── Step A2: for each seed JSON:
        │     ├── ollama-generate.py --prompt fixture-repo-enrichment.md --context {seed}
        │     └── python scripts/generated/enrich-{name}.py {seed.json}
        │           → appends commits + PRs in place
        │
        ├── Step B:  ollama-generate.py --prompt fixture-extractor.md      (unchanged)
        ├── Step C:  ollama-generate.py --prompt fixture-factories.md       (unchanged)
        ├── Step D:  ollama-generate.py --prompt repo-snapshot.md           (unchanged)
        └── Step E:  ollama-generate.py --prompt canary-verification.md     (unchanged)
```

Key properties:
- **No Python on host** — bash launcher only runs `docker run`
- **No Docker-in-Docker** — orchestrator and all subprocesses share the same container
- **`ollama-generate.py` unchanged** — orchestrator calls it via `subprocess`
- **Final JSON schema unchanged** — downstream consumers need no modifications

---

## Deliverables

### 1. `.ai/ollama-prompts/fixture-repo-seeds.md`

Prompt for Layer 1. Specifies:
- Exactly 10 repositories (same names/language distributions as current `fixture-scenarios.md`)
- Schema: only the fields listed above (no commits/PRs)
- Output: complete Python source for `scripts/generated/generate-repo-seeds.py`
- Manifest content should be realistic but minimal (same guidelines as current prompt)

### 2. `.ai/ollama-prompts/fixture-repo-enrichment.md`

Prompt for Layer 2. Specifies:
- Context: a single repository seed JSON will be present in the system context
- Task: generate commits and PRs appropriate for that repo's language/stack
- Commit message style: realistic for the stack (e.g. Go → gin routes, Java → Spring beans)
- Interface: the `sys.argv[1]` pattern shown above
- Output instruction: "Write the complete Python source for the enrichment script."

### 3. `scripts/generate-fixtures.py`

Python orchestrator. Runs inside Docker (`python:3.12-slim`). Stdlib only.

```python
#!/usr/bin/env python3
"""Fixture generation orchestrator. Runs inside Docker (python:3.12-slim).
Calls Ollama via HTTP and coordinates all generation steps via subprocess.
"""
import argparse, json, os, pathlib, subprocess, sys, urllib.request

PROJECT_ROOT = pathlib.Path("/app")
PROMPTS   = PROJECT_ROOT / ".ai" / "ollama-prompts"
GENERATED = PROJECT_ROOT / "scripts" / "generated"
SCENARIOS = PROJECT_ROOT / "tests" / "fixtures" / "scenarios" / "generated"

def run(cmd): subprocess.run(cmd, check=True)

def run_ollama_generate(prompt, output, min_lines, context_files=()):
    cmd = ["python", "scripts/ollama-generate.py",
           "--model", MODEL, "--ollama-url", OLLAMA_URL,
           "--prompt", str(prompt), "--output", str(output)]
    for f in context_files:
        cmd += ["--context", str(f)]
    run(cmd)
    validate(output, min_lines)

def validate(path, min_lines): ...   # py_compile + line count check
def require_ollama(): ...            # urllib GET /api/tags, verify model present

def step_a():
    # A1: seeds
    run_ollama_generate(PROMPTS / "fixture-repo-seeds.md",
                        GENERATED / "generate-repo-seeds.py", 80)
    run(["python", str(GENERATED / "generate-repo-seeds.py")])
    # A2: enrich each seed
    for seed in sorted(SCENARIOS.glob("*.json")):
        script = GENERATED / f"enrich-{seed.stem}.py"
        run_ollama_generate(PROMPTS / "fixture-repo-enrichment.md", script, 30,
                            context_files=[seed])
        run(["python", str(script), str(seed)])

def step_b(): ...
def step_c(): ...
def step_d(): ...
def step_e(): ...
```

### 4. `scripts/generate-fixtures.sh`

Thin bash launcher. Host-side code only handles Docker invocation:

```bash
#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL="${OLLAMA_MODEL:-qwen2.5-coder:14b}"

if ! docker info &>/dev/null; then echo "ERROR: Docker not running"; exit 1; fi

MSYS_NO_PATHCONV=1 docker run --rm \
    -e PYTHONUNBUFFERED=1 \
    -v "$PROJECT_ROOT:/app" \
    -w /app \
    python:3.12-slim \
    python scripts/generate-fixtures.py --model "$MODEL" "$@"
```

Usage: `bash scripts/generate-fixtures.sh [--model <name>] [--step A|B|C|D|E]`

---

## Files Summary

| Action | File |
|--------|------|
| Create | `.ai/ollama-prompts/fixture-repo-seeds.md` |
| Create | `.ai/ollama-prompts/fixture-repo-enrichment.md` |
| Create | `scripts/generate-fixtures.py` |
| Create | `scripts/generate-fixtures.sh` |
| Keep (legacy) | `scripts/generate-test-fixtures.sh` |
| Keep (legacy) | `.ai/ollama-prompts/fixture-scenarios.md` |
| Unchanged | `scripts/ollama-generate.py` |
| Unchanged | Steps B–E prompts, FixtureExtractor, sample_data.py |

---

## Verification

1. `bash scripts/generate-fixtures.sh --step A`
2. `tests/fixtures/scenarios/generated/` contains 10 JSON files
3. Spot-check one file: `commits` ≥ 15 entries, `pull_requests` ≥ 5 entries
4. Commit messages are language-appropriate (Go file has gin/module messages, not Java imports)
5. `bash scripts/generate-fixtures.sh` (all steps) — B through E complete without error
6. `bash scripts/run-tests-docker.sh` — existing tests still pass
