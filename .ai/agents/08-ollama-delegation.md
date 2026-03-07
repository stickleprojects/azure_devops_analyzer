# Agent 08: Ollama Delegation Policy

Delegate to Ollama MCP tools to reduce Claude token usage. Ollama runs locally via the `mcp__ollama__*` tools and is well-suited for mechanical, code-focused tasks. Keep Claude for judgment-heavy work.

## Tell the user if this tool is not running or if there are any problems with it that prevent you from using it

## When to delegate to Ollama

| Task                                          | Tool                                             |
| --------------------------------------------- | ------------------------------------------------ |
| Generate new code from a description          | `mcp__ollama__ollama_generate_code`              |
| Generate code using existing files as context | `mcp__ollama__ollama_generate_code_with_context` |
| Write tests for existing code                 | `mcp__ollama__ollama_write_tests`                |
| Explain what a file does                      | `mcp__ollama__ollama_explain_file`               |
| Refactor code to a spec                       | `mcp__ollama__ollama_refactor_code`              |
| Fix a specific bug in a code snippet          | `mcp__ollama__ollama_fix_code`                   |
| Analyse multiple files together               | `mcp__ollama__ollama_analyze_files`              |
| Any other mechanical coding task              | `mcp__ollama__ollama_general_task`               |
| Render a Mermaid diagram for review           | `mcp__mermaid__mermaid_preview`                  |
| Save a Mermaid diagram to a file              | `mcp__mermaid__mermaid_save`                     |

---

## Do NOT delegate to Ollama

- **Code review** (`ollama_review_file`, `ollama_review_code`) — Ollama catches style issues but misses logic bugs and runtime behaviour. Use Claude for all code review. The token savings do not justify weaker analysis. See `agents/05-code-review.md` for how to conduct reviews.

---

## When to keep Claude in the loop

- Architecture decisions and trade-off analysis
- Interpreting ambiguous or incomplete requirements
- Planning work (plans, investigations, task breakdowns)
- **All code review** — logic errors, control flow issues, cross-file reasoning
- Final review of Ollama output before committing
- Anything that requires knowledge of the full project context

---

## Workflow

1. Delegate the task to the appropriate Ollama tool
2. Review the output — Ollama output is a first draft, not ground truth
3. Apply edits using `Edit` or `Write` tools as normal
4. Run tests to validate: `bash scripts/run-tests-docker.sh`

---

## Repo-Specific Defaults (Use These Often)

When working in this repository, default to Ollama for these mechanical checks:

1. CI vs local test flow drift check
- Use `mcp__ollama__ollama_analyze_files` on:
	- `.github/workflows/tests.yml`
	- `scripts/run-tests-docker.sh`
	- `docker-compose.test.yml`
- Task prompt example: "Find ordering/env differences that could cause CI-only failures"

2. Database schema/migration/view consistency check
- Use `mcp__ollama__ollama_analyze_files` on:
	- `database/schema.sql`
	- `database/views.sql`
	- `database/migrations/*.sql`
	- `docker/scripts/run_migrations.sh`
- Task prompt example: "Find references to missing columns/tables/views and non-idempotent migration patterns"

3. Test scaffolding for regressions
- Use `mcp__ollama__ollama_write_tests` or `mcp__ollama__ollama_generate_code_with_context` to draft regression tests for CI-only failures.

Do not skip the human validation step: Ollama output is draft-quality and must be verified with Docker tests before commit.

---

## Model

Default model: `qwen2.5-coder:14b`. This can be overridden per call if a task needs a different capability.
