# Scripts Directory

_Last reviewed: 2026-04-30_

Utility scripts for the Azure DevOps Analyzer project.

## Available Scripts

### Testing Scripts

#### `run-tests-docker.sh` ⭐ (Primary test runner)

Runs tests in Docker with a clean database. **Now matches CI exactly** - runs tests in the same 3-step sequence as GitHub Actions.

**Usage:**

```bash
./scripts/run-tests-docker.sh                          # Run all tests (CI-equivalent sequence)
./scripts/run-tests-docker.sh tests/unit/              # Run specific test path
./scripts/run-tests-docker.sh --live-api               # Run live API tests
./scripts/run-tests-docker.sh --keep-db                # Keep database for debugging
```

**What it does (matches CI exactly):**

1. Starts PostgreSQL with TimescaleDB in Docker
2. Applies schema and migrations
3. **Runs unit tests** (no coverage)
4. **Runs integration tests** (no coverage)
5. **Generates coverage report** (runs all tests again)
6. Cleans up automatically (unless `--keep-db` specified)

**Why 3 steps instead of 1?**

The CI workflow runs tests in separate steps, which can surface different failures than running everything together. By matching this sequence, you catch CI failures locally BEFORE pushing.

**When to use:**

- ✅ **Always** - This is your primary test runner
- ✅ Before pushing to GitHub
- ✅ To reproduce CI failures locally
- ✅ For iterative development (it runs all tests)

---

#### `run_coverage.sh`

Runs tests with coverage on the host machine (requires Python venv).

**Usage:**

```bash
./scripts/run_coverage.sh
```

Generates:

- Terminal report (shown immediately)
- `htmlcov/index.html` - Interactive HTML report
- `coverage.xml` - XML report for CI

**Note:** This runs on your host machine, not in Docker. Docker-based scripts are recommended for consistency.

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

**Output format:** Fixture scenario JSON. Captured snapshots should be placed in `tests/fixtures/scenarios/captured/` to distinguish them from generated scenarios.

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

### `enrich-repo.py`

Enriches a fixture repository seed (JSON) with commits and pull requests
based on templates in `tests/fixtures/scenarios/config.json`.

**Usage:**

```bash
python scripts/enrich-repo.py tests/fixtures/scenarios/generated/python-docker.json
```

Writes atomically in-place. No external services required.

---

### `run-enrich.py`

Orchestrates `enrich-repo.py` across every seed listed in
`tests/fixtures/scenarios/config.json`.

**Usage:**

```bash
python scripts/run-enrich.py
```

---

### `generated/generate-repo-seeds.py` and `generated/generate-fixture-scenarios.py`

Deterministic (seeded-PRNG) fixture generators. They produce the JSON files
in `tests/fixtures/scenarios/generated/` from templates in
`tests/fixtures/scenarios/config.json`, including synthetic vulnerability
data. No external services — re-runs are idempotent.

**Usage:**

```bash
python scripts/generated/generate-repo-seeds.py
python scripts/generated/generate-fixture-scenarios.py
```

---

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
