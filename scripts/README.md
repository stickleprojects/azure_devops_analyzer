# Scripts Directory

Utility scripts for the Azure DevOps Analyzer project.

## Available Scripts

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
