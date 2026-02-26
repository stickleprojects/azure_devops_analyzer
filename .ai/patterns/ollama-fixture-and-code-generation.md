# Pattern: Ollama-in-Docker Code Generation

Use this when a plan deliverable is mechanical enough for a local model to follow a tight spec —
implementing a known interface, adding factory functions, writing a CLI script, generating fixture data.

Claude writes the prompt files once, then the local model does all the code generation.
Nothing runs on the host — Docker + Ollama only.

**Convention**: AI-generated code and data files should be placed in a `generated/` subfolder to distinguish them from manually created files. For example, fixture scenarios go in `tests/fixtures/scenarios/generated/` rather than `tests/fixtures/scenarios/`.

---

## Fixed infrastructure (already in repo)

| File                                | Role                                                                                                        |
| ----------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `scripts/ollama-generate.py`        | Calls Ollama `/api/chat`, extracts code block, writes output. Pure stdlib — runs inside `python:3.12-slim`. |
| `scripts/generate-test-fixtures.sh` | Reference orchestration script — copy and adapt for new use cases.                                          |

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
cp scripts/generate-test-fixtures.sh scripts/generate-<feature>-fixtures.sh
```

Update the step functions: point each one at the right prompt, output path, and `--context` files.

**3. Run it**

```bash
bash scripts/generate-<feature>-fixtures.sh           # all steps
bash scripts/generate-<feature>-fixtures.sh --step B  # one step
bash scripts/generate-<feature>-fixtures.sh --model qwen3-coder-next:latest  # larger model
```

---

## Prompt Output section rules

| Deliverable type     | Instruction                                                                                                              |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| New file             | "Write the complete, runnable Python source for `path/to/file.py`."                                                      |
| Extend existing file | "Write the **complete updated content** of `path/to/file.py`, including all existing code unchanged plus the additions." |
| JSON data            | Use LLM to generate a Python script that produces the JSON files (see `fixture-scenarios.md` example).                   |

Never say "append" or "patch" — the script overwrites the whole file.

**Critical formatting requirements for Output section:**

````markdown
## Output

Write ONLY the complete Python implementation as a single fenced code block:

\```python
#!/usr/bin/env python3

# actual implementation here

\```

DO NOT include:

- Usage examples in code blocks
- Commentary before/after the code
- Multiple code blocks
- Explanatory text outside the code block
````

**Separate usage examples from specification:**

- Use plain text or markdown lists for CLI examples, NOT code blocks
- Keep usage examples in CLI interface sections, not in code blocks
- The model extracts the largest code block, so small example blocks can confuse it

---

## Context file strategy

Pass via `--context` flags. The script injects them as a system message before the prompt.

| Situation                               | Context to pass                               |
| --------------------------------------- | --------------------------------------------- |
| Implementing an ABC                     | The base class file                           |
| Extending an existing file              | The existing file + any type files it imports |
| Writing a CLI script using project APIs | Relevant `base.py` and `factory.py`           |
| Pure stdlib or no project dependencies  | No context needed                             |

---

## Core bash helpers (already in the reference script)

```bash
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL="${OLLAMA_MODEL:-qwen2.5-coder:14b}"
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

---

## Post-generation validation

After running the script, verify each output file:

1. **File has substantive content** — Check line count: `wc -l <file>`
   - CLI scripts should be >20 lines typically
   - Class implementations >30 lines
   - Extensions to existing files should grow the file
2. **Syntactically valid** — Run: `python -m py_compile <file>`
3. **Contains expected imports** — Verify the file imported what the prompt specified
4. **Not just usage examples** — Actually read the first few lines

**Failed generation indicators:**

- File contains only usage examples/comments
- `wc -l` shows suspiciously low line count (<10 for a CLI script)
- Syntax check fails
- File is smaller than expected

**If validation fails:**

- Regenerate with `--step <X>` to retry just that step
- Try with `--model qwen3-coder-next:latest` (better instruction following)
- Use `--raw` flag and manually extract code from response
- Check the prompt file for usage examples in code blocks

---

## Model selection guidance

| Task complexity                | Recommended model                           | Notes                                     |
| ------------------------------ | ------------------------------------------- | ----------------------------------------- |
| Implementing known interface   | `qwen2.5-coder:14b`                         | Fast, good at following specs             |
| Extending existing file        | `qwen2.5-coder:14b` or larger               | Needs to preserve existing code correctly |
| CLI script with multiple steps | `qwen2.5-coder:14b` or `qwen3-coder:latest` | More complex logic                        |
| Pure data transformation       | `qwen2.5-coder:14b`                         | Straightforward                           |
| Complex business logic         | Use Claude in main session                  | More expensive but reliable               |

**If generation fails with default model:**

1. Check prompt file for formatting issues (usage examples in code blocks?)
2. Retry with `qwen3-coder-next:latest` (newer, better instruction following)
3. Try a larger parameter model if available
4. As last resort, have Claude generate it in the main session

---

## Enhanced bash helpers for validation

Add to your orchestration script for automatic validation:

```bash
# Validate a generated Python file
validate_python_file() {
    local file="$1"
    local min_lines="${2:-20}"

    if [ ! -f "$file" ]; then
        echo "  [FAIL] File not created: $file"
        return 1
    fi

    local lines=$(wc -l < "$file")
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

# Enhanced generation with validation
run_ollama_generate_safe() {
    local prompt="$1" output="$2" min_lines="${3:-20}"
    shift 3

    run_ollama_generate "$prompt" "$output" "$@"
    validate_python_file "$output" "$min_lines"
}
```

Usage in step functions:

```bash
run_step_b() {
    info "Step B: Generating tests/fixtures/fixture_extractor.py"
    run_ollama_generate_safe \
        "$PROMPTS/fixture-extractor.md" \
        "tests/fixtures/fixture_extractor.py" \
        30 \
        --context "src/extractors/base.py"
}
```
