# Pattern: Ollama-in-Docker Code Generation

Use this when a plan deliverable is mechanical enough for a local model to follow a tight spec —
implementing a known interface, adding factory functions, writing a CLI script, generating fixture data.

Claude writes the prompt files once, then the local model does all the code generation.
Nothing runs on the host — Docker + Ollama only.

---

## Fixed infrastructure (already in repo)

| File | Role |
|------|------|
| `scripts/ollama-generate.py` | Calls Ollama `/api/chat`, extracts code block, writes output. Pure stdlib — runs inside `python:3.12-slim`. |
| `scripts/run-013-ollama.sh` | Reference orchestration script — copy and adapt for new plans. |

---

## Steps to apply to a new plan

**1. Write a prompt file per deliverable** → `.ai/ollama-prompts/<plan-id>-<step>-<name>.md`

Each prompt must include:
- Purpose (one sentence)
- Interface / schema (inline — don't rely on the model reading other files)
- Detailed behaviour rules
- Required imports
- **Output** section (see below)

**2. Copy the orchestration script**

```bash
cp scripts/run-013-ollama.sh scripts/run-<plan-id>-ollama.sh
```

Update the step functions: point each one at the right prompt, output path, and `--context` files.

**3. Run it**

```bash
bash scripts/run-<plan-id>-ollama.sh           # all steps
bash scripts/run-<plan-id>-ollama.sh --step B  # one step
bash scripts/run-<plan-id>-ollama.sh --model qwen3-coder-next:latest  # larger model
```

---

## Prompt Output section rules

| Deliverable type | Instruction |
|------------------|-------------|
| New file | "Write the complete, runnable Python source for `path/to/file.py`." |
| Extend existing file | "Write the **complete updated content** of `path/to/file.py`, including all existing code unchanged plus the additions." |
| JSON data | Don't use LLM — write a Python generator script instead (see `scripts/generate-013-fixtures.py`). |

Never say "append" or "patch" — the script overwrites the whole file.

---

## Context file strategy

Pass via `--context` flags. The script injects them as a system message before the prompt.

| Situation | Context to pass |
|-----------|-----------------|
| Implementing an ABC | The base class file |
| Extending an existing file | The existing file + any type files it imports |
| Writing a CLI script using project APIs | Relevant `base.py` and `factory.py` |
| Pure stdlib or no project dependencies | No context needed |

---

## Core bash helpers (already in the reference script)

```bash
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL="${OLLAMA_MODEL:-qwen3-coder:30b}"
OLLAMA_URL="${OLLAMA_URL:-http://host.docker.internal:11434}"

run_docker_python() {
    docker run --rm -v "$PROJECT_ROOT:/app" -w /app python:3.12-slim "$@"
}

run_ollama_generate() {
    local prompt="$1" output="$2"; shift 2
    run_docker_python python scripts/ollama-generate.py \
        --model "$MODEL" --ollama-url "$OLLAMA_URL" \
        --prompt "$prompt" --output "$output" "$@"
}
```

---

## Networking note

Ollama runs on the host at `localhost:11434`.
From inside a Docker container on Windows + Docker Desktop, reach it via `host.docker.internal:11434`.
