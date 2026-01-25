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

Runs database migrations to update schema.

**Usage:**

```bash
./scripts/run_migrations.sh
```

### `submit_extraction_task.py`

Submits an extraction task to the Celery queue.

**Usage:**

```bash
python scripts/submit_extraction_task.py
```

## Adding New Scripts

When creating new scripts:

1. **Make executable**: `chmod +x scripts/your_script.sh`
2. **Add shebang**: Start with `#!/bin/bash` or `#!/usr/bin/env python3`
3. **Add to this README**: Document usage and purpose
4. **Use project Python**: Use `$PROJECT_DIR/venv/bin/python` for Python scripts
5. **Handle errors**: Use `set -e` in bash scripts to exit on error
6. **Provide feedback**: Use colored output and clear messages
