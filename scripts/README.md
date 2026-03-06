# Scripts Directory

Utility scripts for the Azure DevOps Analyzer project.

## Available Scripts

### `ollama-generate.py`

Core Ollama API caller used by all orchestration scripts. Runs inside Docker (`python:3.12-slim`) — no host Python dependencies required.

**Usage:**

```bash
docker run --rm -v "$PROJECT_ROOT:/app" -w /app python:3.12-slim \
    python scripts/ollama-generate.py \
    --model qwen2.5-coder:14b \
    --prompt .ai/ollama-prompts/fixture-repo-seeds.md \
    --output scripts/generated/generate-repo-seeds.py \
    [--context src/extractors/base.py] \
    [--ollama-url http://host.docker.internal:11434] \
    [--num-ctx 8192] \
    [--raw]
```

**What it does:**

- Calls the Ollama `/api/chat` endpoint with streaming
- Injects optional context files as a system message (for extending existing classes)
- Extracts the largest fenced code block from the response (avoids capturing usage examples)
- Shows live token/s progress and final performance stats
- Writes the extracted code directly to `--output`

**Flags:**

| Flag             | Description                                                    |
| ---------------- | -------------------------------------------------------------- |
| `--model`        | Ollama model name (e.g. `qwen2.5-coder:14b`)                   |
| `--prompt`       | Markdown prompt file                                           |
| `--output`       | Destination file path                                          |
| `--context FILE` | Read-only context file shown as system message (repeatable)    |
| `--ollama-url`   | Ollama base URL (default: `http://host.docker.internal:11434`) |
| `--num-ctx`      | Context window tokens (default: 8192)                          |
| `--raw`          | Write full model response instead of extracting code block     |

**Pattern documentation:** [.ai/patterns/ollama-fixture-and-code-generation.md](../.ai/patterns/ollama-fixture-and-code-generation.md)

---

### `capture_snapshot.py`

Captures a live repository snapshot and saves it as a fixture scenario JSON file. Used to create realistic test fixtures from real repositories.

**Usage (run inside Docker):**

```bash
docker compose run --rm scheduler python scripts/capture_snapshot.py \
    owner/repo \
    --platform github \
    --output tests/fixtures/scenarios/captured/my-repo.json \
    [--branch main]
```

**Arguments:**

| Argument     | Description                                          |
| ------------ | ---------------------------------------------------- |
| `repo_id`    | Repository identifier (e.g. `owner/repo` for GitHub) |
| `--platform` | `github` or `azure_devops`                           |
| `--output`   | Path to write scenario JSON                          |
| `--branch`   | Branch to scan (default: repository default branch)  |

**Output format:** Fixture scenario JSON matching the schema in [.ai/ollama-prompts/fixture-scenarios.md](../.ai/ollama-prompts/fixture-scenarios.md). Captured snapshots should be placed in `tests/fixtures/scenarios/captured/` to distinguish them from generated scenarios.

---

### `verify_canary.py`

Verifies that a canary repository has complete data in the database after a scan. Eliminates manual SQL checks post-scan.

**Usage (run inside Docker):**

```bash
docker compose run --rm scheduler \
    python scripts/verify_canary.py --repo-id my-canary-repo
```

**Environment variables required:**

- `DATABASE_URL` — PostgreSQL connection string

**What it checks:**

| Check           | Query                                                   |
| --------------- | ------------------------------------------------------- |
| `commits`       | Commits exist for the repo                              |
| `pull_requests` | Pull requests exist for the repo                        |
| `dependencies`  | Dependencies exist for the repo                         |
| `languages`     | Languages exist for the repo                            |
| `canary_join`   | All four tables joinable for the repo (full inner join) |

Exits `0` if all checks pass, `1` if any fail.

---

### `generate-fixtures.sh`

Config-driven fixture generation (Plan 014) using templates and repo sets.

**Usage:**

```bash
# Full run: validate config, generate seeds, enrich all repos
./scripts/generate-fixtures.sh

# Run a single step
./scripts/generate-fixtures.sh --step validate
./scripts/generate-fixtures.sh --step seeds
./scripts/generate-fixtures.sh --step enrich
```

---

### `validate-fixture-config.py`

Validates the config-driven fixture generation format in `tests/fixtures/scenarios/config.json`.

**Usage:**

```bash
python scripts/validate-fixture-config.py
```

Checks:

- Required top-level keys (`patterns`, `repo_templates`, `repo_sets`)
- Range sanity (min <= median <= max)
- PR status sums to 1.0 (or all zero)
- Template references are valid
- Expanded repo names are unique

---

### Config-Driven Fixture Generation (Plan 014)

Two-layer generation using config templates and repo sets:

```bash
# Use different model
./scripts/generate-fixtures.sh --model qwen3-coder-next:latest
```

**What it generates:**

- N test scenario JSON files (count derived from `repo_sets`)
- Seed generator script (`scripts/generated/generate-repo-seeds.py`)
- Per-repo enrichment scripts (`scripts/generated/enrich-<name>.py`)
- Utility scripts for snapshot capture and verification (unchanged)

**Output locations:**

- Scenarios: `tests/fixtures/scenarios/generated/`
- Code: `tests/fixtures/fixture_extractor.py`, `scripts/generate-fixture-scenarios.py`

**Prerequisites:**

- Ollama running at `localhost:11434`
- Model available: `ollama pull qwen2.5-coder:14b`
- Docker running (scripts execute inside containers)

**Pattern documentation:** [.ai/patterns/ollama-fixture-and-code-generation.md](../.ai/patterns/ollama-fixture-and-code-generation.md)

### `run_coverage.sh`

Runs pytest with comprehensive coverage analysis for Python source code.

**Usage:**

```bash
./scripts/run_coverage.sh
```

**What it does:**

- Runs all tests in the `tests/` directory
- Generates coverage report for `src/` Python modules
- Creates three types of coverage reports:
  - **Terminal**: Displays coverage summary in console
  - **HTML**: Interactive report in `htmlcov/index.html`
  - **XML**: Machine-readable report in `coverage.xml` (for CI/CD)

**Output:**

- Shows which lines of code are covered by tests
- Highlights missing coverage
- Displays overall coverage percentage
- Identifies branches (if/else) that aren't tested

**View HTML Report:**

```bash
xdg-open htmlcov/index.html
```

See [docs/03-operations/test-coverage.md](../docs/03-operations/test-coverage.md) for detailed coverage documentation.

### `resolve_env.sh`

Resolves indirect variable references in `.env` file and creates `.env.resolved`.

**Usage:**

```bash
./scripts/resolve_env.sh
```

Required before starting Docker services to ensure environment variables are properly resolved.

### `run_extraction.py`

Manually runs extraction workflow for testing purposes.

**Usage:**

```bash
python scripts/run_extraction.py
```

### `run_migrations.sh`

Host-friendly wrapper that runs migrations via Docker Compose.

**Usage:**

```bash
./scripts/run_migrations.sh
```

### `docker/scripts/run_migrations.sh`

Runs database migrations to update schema (container-only).

**Usage:**

```bash
./docker/scripts/run_migrations.sh
```

### `submit_extraction_task.py`

Submits an extraction task to the Celery queue.

**Usage:**

```bash
python scripts/submit_extraction_task.py
```

### `create_fine_grained_token.sh`

Creates a new fine-grained GitHub PAT using the gh CLI and includes all private repositories
for the configured user or org.

**Usage:**

```bash
./scripts/create_fine_grained_token.sh
```

**Environment:**

- `REPO_ANALYZER_GITHUB_TOKEN` (required)
- `GITHUB_USER` or `GITHUB_ORG` (required)
- `TOKEN_EXPIRES_AT` (optional, `YYYY-MM-DD`)
- `TOKEN_NAME_PREFIX` (optional)
- `TOKEN_PERMISSIONS_JSON` (optional)

## Startup Script Tests

The `startup-scripts/` directory contains the modular SH version of the bootstrap script (`Start-RepoAnalysis.sh`). These modules have a bats-core test suite in `startup-scripts/tests/`.

**Run tests:**

```bash
npx bats startup-scripts/tests/*.bats
```

**What's covered (47 tests):**

- `test_constants.bats` - Global constants, service arrays, URLs
- `test_output_helpers.bats` - All output formatting functions
- `test_environment_helpers.bats` - Password generation, env variable resolution
- `test_env_file_helpers.bats` - .env file reading, validation, export, generation
- `test_main_args.bats` - CLI argument parsing and help output

Tests run without Docker and validate all library modules used by `Start-RepoAnalysis.sh`.

## Adding New Scripts

When creating new scripts:

1. **Make executable**: `chmod +x scripts/your_script.sh`
2. **Add shebang**: Start with `#!/bin/bash` or `#!/usr/bin/env python3`
3. **Add to this README**: Document usage and purpose
4. **Use project Python**: Use `$PROJECT_DIR/venv/bin/python` for Python scripts
5. **Handle errors**: Use `set -e` in bash scripts to exit on error
6. **Provide feedback**: Use colored output and clear messages
