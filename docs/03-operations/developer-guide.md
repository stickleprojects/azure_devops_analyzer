# Developer Guide

## Running tests

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

## Adding a unit test

Add a new file under `tests/unit/test_<module>.py`. Unit tests must not import from `src.database`, touch the network, or open files outside `tests/`. Use mocks for all external dependencies.

## Adding a database contract test

Contract tests verify that SQL views return correct data given seeded rows. They use a real PostgreSQL test database (started by Docker Compose).

1. Create or extend a file in `tests/contract/database/`.
2. Use the `db_session` fixture — each test gets a clean savepoint-isolated session.
3. Seed data with SQLAlchemy ORM models from `src.database.models`, or raw `text()` SQL.
4. Query the view with `db_session.execute(text("SELECT … FROM v_my_view"))`.
5. Assert on column names, row count, or specific values.

See [tests/contract/database/test_team_dashboard_views.py](../../tests/contract/database/test_team_dashboard_views.py) for a complete example covering seeding, querying, and asserting on multiple views.

## Adding or extending e2e fixture scenarios

The fixture system in `tests/fixtures/scenarios/` drives the full parsing → import → view pipeline without live API credentials.

**Important:** There is no persistent seed data in the CI database. The database starts empty on every run and all data is created within each test and rolled back automatically. The fixture JSON files below are the source of test data for integration tests.

**Generated scenarios** (`tests/fixtures/scenarios/generated/*.json`) are picked up automatically — the test file discovers all `.json` files in that folder at collection time, so **no list update is needed**. To add a new scenario:

1. Edit `scripts/generated/generate-fixture-scenarios.py` to add a new entry, then run it: `python scripts/generated/generate-fixture-scenarios.py` (produces a JSON file in `tests/fixtures/scenarios/generated/`).
2. Run `bash scripts/run-tests-docker.sh tests/contract/integration/test_fixture_scenarios.py` to verify — the new scenario is picked up automatically.

To regenerate all scenarios from config patterns (e.g. after changing `config.json`): `python scripts/generated/generate-repo-seeds.py`

**Adversarial scenarios** (`tests/fixtures/scenarios/adversarial/*.json`) are hand-crafted edge cases (bot committers, unicode names, force-pushed PRs, etc.). To add one, create a JSON file matching the schema and add a test in `tests/contract/integration/test_adversarial_scenarios.py`.

For the fixture JSON schema, see any file in `tests/fixtures/scenarios/generated/` as a reference.

## Resolving integration, import, or connectivity issues

| Issue | Diagnostic command |
|---|---|
| View returns wrong data | `bash scripts/run-tests-docker.sh tests/contract/database/test_<view_file>.py -v` |
| Import fails silently | `bash scripts/run-tests-docker.sh tests/contract/integration/test_fixture_scenarios.py -v` |
| Grafana shows no data | Check `docker compose logs worker`; check migration tracking: `bash scripts/run-tests-docker.sh tests/contract/database/test_migration_tracking.py` |
| Auth errors in extraction | `bash scripts/run-tests-docker.sh tests/contract/database/test_error_classification_taxonomy.py` |
| Data integrity violation | `bash scripts/run-tests-docker.sh tests/contract/database/test_extraction_health_integration.py` |
| Full pipeline smoke | `bash scripts/run-tests-docker.sh tests/contract/database/test_full_pipeline_e2e.py` |
