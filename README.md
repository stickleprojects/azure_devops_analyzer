# Multi-Platform Repository Analysis System

_Last reviewed: 2026-05-25_

## Overview

This system analyzes repositories from multiple platforms (Azure DevOps and GitHub) and stores comprehensive metrics for visualization in Grafana dashboards. It provides insights into code quality, security vulnerabilities, contributor activity, pull request patterns, and repository health.

## Key Features

- **Multi-language support**: Detects and analyzes code in various programming languages
- **Dependency extraction**: Parses manifest files from 7 ecosystems (PyPI, npm, Maven, NuGet, Go, RubyGems, Cargo)
- **Security scanning**: Identifies vulnerabilities in dependencies and code
- **Dependency vulnerability & EOL dashboards**: Two Grafana dashboards — `dependency-vulnerability-portfolio` (org-wide health buckets, adoption timelines, team breakdowns) and `library-detail-deep-dive` (per-package CVE list, version usage, exposed repos). Backed by API endpoints `/api/packages/health`, `/api/packages/adoption`, `/api/packages/library/<name>/<ecosystem>`.
- **Thoughtworks Tech Radar**: Auto-generated Tech Radar publication from package adoption, CVE exposure, and EOL signals. Packages are categorised into Adopt / Trial / Assess / Hold rings across Infrastructure / Platforms / Tools / Languages & Frameworks quadrants. Ring movements (incl. `repo_count_delta` and `vulnerability_change`) are tracked publication-to-publication. Endpoints: `/api/radar` (Thoughtworks JSON format), `/api/radar/history`, `/api/radar/export` (CSV/JSON).
- **Code quality analysis**: Static analysis for best practices and structural issues
- **Contributor analytics**: Tracks developer activity and patterns
- **Pull request metrics**: Analyzes PR size, quality, and review patterns
- **Branch-level analysis**: Supports per-branch metrics and comparisons
- **Incremental updates**: Efficiently refreshes data as changes occur
- **Extraction health observability**: After every successful extraction, named database invariants are checked and results persisted to `extraction_health_log`. The **Extraction Health** Grafana dashboard (`/d/extraction-health`) shows violation counts and 7-day trends. See [docs/03-operations/extraction-health-monitoring.md](docs/03-operations/extraction-health-monitoring.md).
- **Grafana dashboards**: Rich visualizations for all metrics

## Local Repository Analysis Quickstart

Use the helper to bootstrap the Docker stack, create `.env`, initialize the schema, and start extraction:

- Bash (macOS/Linux/Git Bash on Windows): `./Start-RepoAnalysis.sh --regenerate-env`

What happens:

1. Prompts for GitHub/Azure DevOps credentials and writes `.env`
2. Starts Docker services (TimescaleDB, RabbitMQ, workers, scheduler)
3. Initializes the database schema
4. Submits an extraction task to Celery (background mode)

To start analysis manually without the helper:

1. Copy and edit `.env` from `.env.example`
2. Resolve environment variable references: `bash ./scripts/resolve_env.sh > .env.resolved`
3. Start services: `docker compose --env-file .env.resolved up -d`
4. Submit a run: `docker compose --env-file .env.resolved run --rm scheduler python /app/scripts/submit_extraction_task.py`

How to know it is running:

- Scheduler logs show `Enqueuing task=...`
- Worker logs show tasks executing
- Flower UI at `http://localhost:5555`
- Grafana dashboards at `http://localhost:3000` (admin/admin)
- Admin UI at `http://localhost:8080` (rescan triggers, system health)

See [Start-RepoAnalysis.sh](Start-RepoAnalysis.sh#L1-L50) for parameters and examples.

## First-launch checklist (new user)

After the stack starts and the first extraction completes:

1. **Grafana Home** — `http://localhost:3000/d/dashboard-home` — confirm summary stats are non-zero (Repositories, Contributors, Commits).
2. **Repository Overview** — verify your repos appear with correct metadata.
3. **Security dashboard** — confirm dependency vulnerabilities are populated. If empty, the enrichment worker may still be running; check Flower.
4. **Extraction Health** — `http://localhost:3000/d/extraction-health` — any invariant violations appear here within minutes of extraction finishing.
5. **Admin UI** — `http://localhost:8080` — trigger a rescan, confirm a toast appears with a `task_id` and the task shows in Flower.

If Grafana dashboards show "No data": check `docker compose logs worker` for errors. The most common cause is a missing or expired PAT — re-run `./Start-RepoAnalysis.sh --regenerate-env` to refresh credentials.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| All Grafana panels blank | Credentials missing/expired | Re-run `Start-RepoAnalysis.sh --regenerate-env`; check PAT scopes |
| Extraction stuck in Flower | Worker container crashed | `docker compose restart worker` |
| `psql` connection refused | TimescaleDB not ready | `docker compose up -d timescaledb && sleep 10` |
| Admin UI 502 / not reachable | nginx can't reach Flask API | `docker compose up -d api`; check port 5000 |
| Security dashboard empty | Enrichment worker still running | Wait 5–10 min; watch `docker compose logs enrichment-worker` |
| Grafana data source error | Wrong DB credentials in provisioning | Check `provisioning/datasources/` matches `.env.resolved` |
| `classify_extraction_error` function missing | Migration 020 not applied | `bash scripts/run-tests-docker.sh tests/contract/database/test_migration_tracking.py` |

## Documentation Structure

### Development Progress

- **[PROGRESS.md](PROGRESS.md)** — Session-by-session development log with key findings and technical insights

### How to navigate

- [docs/README.md](docs/README.md) — entry point with role-based navigation across strategy, architecture, operations, and implementation
- [docs/01-strategy/](docs/01-strategy/) — business requirements, status, and project rules
- [docs/02-architecture/](docs/02-architecture/) — system design, stack, data flow, storage, orchestration
- [docs/03-operations/](docs/03-operations/) — deployment plan, visualization, session continuity, Docker setup, extraction health monitoring
- [docs/04-implementation/README.md](docs/04-implementation/README.md) — implementation backlog and future work

### AI Agent Guides

The `agents/` directory contains comprehensive guides for AI-driven development:

- [.ai/principles.md](.ai/principles.md) - **START HERE** - 7 core development principles
- [agents/00-documentation-standards.md](agents/00-documentation-standards.md) - Documentation and code examples standards
- [agents/02a-architecture-guardian.md](agents/02a-architecture-guardian.md) - Architecture boundary validation
- [agents/04a-test-guardian.md](agents/04a-test-guardian.md) - Test integrity and contract testing
- [agents/07-session-continuity-agent.md](agents/07-session-continuity-agent.md) - Session tracking and progress

See [agents/](agents/) directory for complete guide collection.

## Session Start Guide

At the start of your session:

1. Give a greeting to your AI assistant (e.g., "good afternoon" or "hi, what's next?")
2. The agent will catch you up on prior work and show backlog priorities
3. When finished, say "let's wrap up this session" for a summary and commit prompts

## Quick Start

Start with [docs/README.md](docs/README.md) for role-based navigation, then review [docs/04-implementation/README.md](docs/04-implementation/README.md) for the current backlog and future work.

## Requirements

- Docker with Compose V2
- Bash 4.0+ for `Start-RepoAnalysis.sh`
- Azure DevOps organization access
- Personal Access Token (PAT) with appropriate permissions
- PostgreSQL 15+ with TimescaleDB
- Grafana 10+
- RabbitMQ 3.12+

## Repository Structure

```
azure-devops-analyzer/
├── docs/                    # Documentation (see docs/README.md for navigation)
├── src/
│   ├── analyzers/          # Platform-agnostic analysis modules
│   ├── api/                # Flask API entry points
│   ├── config/             # Runtime configuration
│   ├── database/           # Database models and storage layer
│   ├── extractors/         # GitHub and Azure DevOps data extraction
│   ├── scheduler/          # Job scheduling and task submission
│   ├── utils/              # Cross-cutting utilities (health checks, metrics)
│   └── workflows/          # Orchestration across extractors and analyzers
├── web/
│   └── admin-ui/           # React + Vite admin UI (served on :8080)
├── dashboards/             # Grafana dashboard JSON definitions
├── database/
│   ├── migrations/         # Numbered SQL migrations (apply in order)
│   └── views.sql           # All reporting views (sourced by contract tests)
├── tests/
│   ├── unit/               # Unit tests (no DB, no network)
│   ├── contract/
│   │   ├── database/       # View contract tests (require test DB)
│   │   ├── integration/    # Pipeline e2e tests (fixture- or live-API-backed)
│   │   └── api/            # Flask API contract tests
│   └── fixtures/
│       ├── scenarios/
│       │   ├── generated/  # 27 JSON fixture scenarios (auto-generated)
│       │   └── adversarial/# 10 edge-case scenarios (hand-crafted)
│       └── fixture_extractor.py  # Fake RepositoryExtractor backed by JSON
├── workers/                # Celery worker entrypoints
└── scripts/                # Run-tests, validate-docs, resolve-env helpers
```

## Developer Guide

### Running tests

```bash
# Full CI-equivalent suite (runs inside Docker — recommended)
bash scripts/run-tests-docker.sh

# Subset: database contract tests only
bash scripts/run-tests-docker.sh tests/contract/database/

# Subset: integration tests (fixture-backed, no live API)
bash scripts/run-tests-docker.sh tests/contract/integration/ -m 'not live_api'

# Unit tests only (no Docker needed)
pytest tests/unit/

# Frontend (React admin UI)
cd web/admin-ui && npm ci && npm run test && npm run typecheck
```

### Adding a unit test

Add a new file under `tests/unit/test_<module>.py`. Unit tests must not import from `src.database`, touch the network, or open files outside `tests/`. Use mocks for all external dependencies.

### Adding a database contract test

Contract tests verify that SQL views return correct data given seeded rows. They use a real PostgreSQL test database (started by Docker Compose).

1. Create or extend a file in `tests/contract/database/`.
2. Use the `db_session` fixture — each test gets a clean savepoint-isolated session.
3. Seed data with SQLAlchemy ORM models from `src.database.models`, or raw `text()` SQL.
4. Query the view with `db_session.execute(text("SELECT … FROM v_my_view"))`.
5. Assert on column names, row count, or specific values.

```python
from sqlalchemy import text

def test_my_view_returns_data(db_session):
    # seed
    db_session.execute(text("INSERT INTO repositories (repo_id, name, …) VALUES (…)"))
    db_session.flush()
    # assert
    rows = db_session.execute(text("SELECT * FROM v_my_view")).fetchall()
    assert len(rows) > 0
```

### Adding or extending e2e fixture scenarios

The fixture system in `tests/fixtures/scenarios/` drives the full parsing → import → view pipeline without live API credentials.

**Generated scenarios** (`tests/fixtures/scenarios/generated/*.json`) are created from `config.json` patterns. To add a new one:

1. Check `tests/fixtures/scenarios/config.json` for an existing pattern that fits, or add a new pattern following the JSON schema at `config.schema.json`.
2. Run the generator: `python scripts/generate_fixture_scenarios.py` (creates/updates JSON files).
3. Add the new scenario name to the `SCENARIOS` list in `tests/contract/integration/test_fixture_scenarios.py`.
4. Run `bash scripts/run-tests-docker.sh tests/contract/integration/test_fixture_scenarios.py` to verify.

**Adversarial scenarios** (`tests/fixtures/scenarios/adversarial/*.json`) are hand-crafted edge cases (bot committers, unicode names, force-pushed PRs, etc.). To add one, create a JSON file matching the schema and add a test in `tests/contract/integration/test_adversarial_scenarios.py`.

**Fixture JSON structure:**

```json
{
  "file_names": ["requirements.txt"],
  "manifests": { "requirements.txt": "flask==3.0.0\nrequests==2.31.0" },
  "languages": [{"language": "Python", "byte_count": 50000}],
  "branches": [{"name": "main", "is_default": true, "last_commit_sha": "abc123"}],
  "commits": [...],
  "pull_requests": [...]
}
```

### Resolving integration, import, or connectivity issues

| Issue | Diagnostic command |
|---|---|
| View returns wrong data | `bash scripts/run-tests-docker.sh tests/contract/database/test_<view_file>.py -v` |
| Import fails silently | `bash scripts/run-tests-docker.sh tests/contract/integration/test_fixture_scenarios.py -v` |
| Grafana shows no data | Check `docker compose logs worker`; check migration tracking: `bash scripts/run-tests-docker.sh tests/contract/database/test_migration_tracking.py` |
| Auth errors in extraction | `bash scripts/run-tests-docker.sh tests/contract/database/test_error_classification_taxonomy.py` |
| Data integrity violation | `bash scripts/run-tests-docker.sh tests/contract/database/test_extraction_health_integration.py` |
| Full pipeline smoke | `bash scripts/run-tests-docker.sh tests/contract/database/test_full_pipeline_e2e.py` |
