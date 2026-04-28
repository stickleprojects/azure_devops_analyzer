"""Contract tests for migration version tracking in run_migrations.sh.

Verifies that the migration runner creates and uses the schema_migrations table
to track applied files, supports bootstrap for pre-existing deployments, and
never re-applies a migration that is already recorded.

These tests invoke the actual shell script via subprocess against temporary
PostgreSQL databases so that the full runner logic (not a re-implementation)
is exercised.
"""

import glob
import os
import subprocess

import pytest

_POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
_POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
_POSTGRES_USER = os.environ.get("POSTGRES_USER", "postgres")
_POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "postgres")

_MIGRATION_SCRIPT = "/app/docker/scripts/run_migrations.sh"
_MIGRATIONS_DIR = "/app/database/migrations"


def _psql(db, sql, *, check=True):
    env = {**os.environ, "PGPASSWORD": _POSTGRES_PASSWORD}
    return subprocess.run(
        [
            "psql",
            "-h", _POSTGRES_HOST,
            "-p", str(_POSTGRES_PORT),
            "-U", _POSTGRES_USER,
            "-d", db,
            "-c", sql,
        ],
        env=env,
        capture_output=True,
        text=True,
        check=check,
    )


def _psql_query(db, sql):
    """Run a query and return the first field of the first row, stripped."""
    env = {**os.environ, "PGPASSWORD": _POSTGRES_PASSWORD}
    result = subprocess.run(
        [
            "psql",
            "-h", _POSTGRES_HOST,
            "-p", str(_POSTGRES_PORT),
            "-U", _POSTGRES_USER,
            "-d", db,
            "-t",
            "-c", sql,
        ],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _run_migration_script(db):
    """Run run_migrations.sh against *db* and return CompletedProcess."""
    env = {
        **os.environ,
        "POSTGRES_HOST": _POSTGRES_HOST,
        "POSTGRES_PORT": str(_POSTGRES_PORT),
        "POSTGRES_USER": _POSTGRES_USER,
        "POSTGRES_PASSWORD": _POSTGRES_PASSWORD,
        "POSTGRES_DB": db,
    }
    return subprocess.run(
        ["bash", _MIGRATION_SCRIPT],
        env=env,
        capture_output=True,
        text=True,
    )


def _count_migration_files():
    return len(glob.glob(f"{_MIGRATIONS_DIR}/*.sql"))


@pytest.fixture()
def temp_db(request):
    """Create and tear down an isolated database for each migration test."""
    safe = "mig_" + "".join(c if c.isalnum() else "_" for c in request.node.name)
    db = safe[:50].lower()
    # Enforce the sanitization: only [a-z0-9_] allowed (guards DDL identifier usage below).
    assert db.replace("_", "").isalnum(), f"Unexpected characters in test db name: {db}"

    admin_env = {**os.environ, "PGPASSWORD": _POSTGRES_PASSWORD}

    def _admin(sql, check=False):
        subprocess.run(
            [
                "psql",
                "-h", _POSTGRES_HOST,
                "-p", str(_POSTGRES_PORT),
                "-U", _POSTGRES_USER,
                "-d", "postgres",
                "-c", sql,
            ],
            env=admin_env,
            capture_output=True,
            text=True,
            check=check,
        )

    _admin(f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='{db}';")
    _admin(f"DROP DATABASE IF EXISTS {db};")
    _admin(f"CREATE DATABASE {db};", check=True)

    yield db

    _admin(f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='{db}';")
    _admin(f"DROP DATABASE IF EXISTS {db};")


class TestMigrationTracking:
    """CONTRACT: run_migrations.sh tracks applied migrations via schema_migrations."""

    def test_fresh_db_all_migrations_recorded(self, temp_db):
        """Fresh DB: all migrations are applied and recorded in schema_migrations."""
        result = _run_migration_script(temp_db)
        assert result.returncode == 0, (
            f"Runner failed on fresh database.\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )

        count = int(_psql_query(temp_db, "SELECT COUNT(*) FROM schema_migrations;"))
        expected = _count_migration_files()
        assert count == expected, (
            f"Expected {expected} rows in schema_migrations after fresh run, got {count}"
        )

    def test_rerun_on_migrated_db_is_noop(self, temp_db):
        """Fully-migrated DB: re-running the runner produces no errors and no duplicate rows."""
        first = _run_migration_script(temp_db)
        assert first.returncode == 0

        count_before = _psql_query(temp_db, "SELECT COUNT(*) FROM schema_migrations;")

        second = _run_migration_script(temp_db)
        assert second.returncode == 0, (
            f"Second run failed.\nstdout:\n{second.stdout}\nstderr:\n{second.stderr}"
        )

        count_after = _psql_query(temp_db, "SELECT COUNT(*) FROM schema_migrations;")
        assert count_before == count_after, (
            f"schema_migrations row count changed on re-run: {count_before} → {count_after}"
        )

    def test_new_migration_applied_once(self, temp_db):
        """New migration: only the unrecorded file is applied; schema_migrations gains one row."""
        result = _run_migration_script(temp_db)
        assert result.returncode == 0

        # Simulate a "new" migration by removing 018's tracking record.
        # Migration 018 uses IF NOT EXISTS guards so re-applying it is safe.
        _psql(temp_db, "DELETE FROM schema_migrations WHERE version = '018_tech_radar_schema.sql';")
        count_before = int(_psql_query(temp_db, "SELECT COUNT(*) FROM schema_migrations;"))

        rerun = _run_migration_script(temp_db)
        assert rerun.returncode == 0, (
            f"Runner failed after removing one tracking row.\nstdout:\n{rerun.stdout}\nstderr:\n{rerun.stderr}"
        )

        count_after = int(_psql_query(temp_db, "SELECT COUNT(*) FROM schema_migrations;"))
        assert count_after == count_before + 1, (
            f"Expected exactly one new row in schema_migrations; "
            f"got {count_before} → {count_after}"
        )
        recorded = _psql_query(
            temp_db,
            "SELECT version FROM schema_migrations WHERE version = '018_tech_radar_schema.sql';"
        )
        assert "018_tech_radar_schema.sql" in recorded

    def test_bootstrap_backfills_existing_schema(self, temp_db):
        """Bootstrap: an existing schema without schema_migrations gets all filenames backfilled.

        Simulates a real deployment that was migrated before tracking was introduced.
        """
        # Apply all migrations normally to produce a fully-migrated schema.
        first = _run_migration_script(temp_db)
        assert first.returncode == 0

        # Remove the tracking table to simulate the pre-tracking deployment state.
        _psql(temp_db, "DROP TABLE schema_migrations;")

        has_table = int(_psql_query(
            temp_db,
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'schema_migrations';"
        ))
        assert has_table == 0, "schema_migrations should not exist before bootstrap run"

        rerun = _run_migration_script(temp_db)
        assert rerun.returncode == 0, (
            f"Bootstrap run failed.\nstdout:\n{rerun.stdout}\nstderr:\n{rerun.stderr}"
        )

        count = int(_psql_query(temp_db, "SELECT COUNT(*) FROM schema_migrations;"))
        expected = _count_migration_files()
        assert count == expected, (
            f"Bootstrap should record {expected} filenames; got {count}"
        )

    def test_regression_011_skipped_after_014_renames_dependencies(self, temp_db):
        """Regression: runner skips 011 on a schema where 014 has renamed 'dependencies'.

        Migration 011 creates views that join the 'dependencies' table.  Migration 014
        renames that table to 'repository_dependencies'.  Re-applying 011 against a
        014-migrated schema would fail with 'relation "dependencies" does not exist'.

        The runner must bootstrap the tracking table and record 011 as already applied
        so it is never re-executed.
        """
        # Build a fully-migrated schema via the runner.
        first = _run_migration_script(temp_db)
        assert first.returncode == 0

        # Confirm the regression precondition: 'dependencies' table was renamed by 014.
        has_old_table = int(_psql_query(
            temp_db,
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'dependencies';"
        ))
        assert has_old_table == 0, (
            "Precondition failed: 'dependencies' table still exists after all migrations"
        )

        # Simulate the pre-tracking deployment: drop schema_migrations.
        _psql(temp_db, "DROP TABLE schema_migrations;")

        # Re-run — the runner must bootstrap (not re-apply 011 which would break).
        rerun = _run_migration_script(temp_db)
        assert rerun.returncode == 0, (
            "Runner failed — it likely tried to re-apply 011 against the 014-migrated schema.\n"
            f"stdout:\n{rerun.stdout}\nstderr:\n{rerun.stderr}"
        )

        recorded_011 = _psql_query(
            temp_db,
            "SELECT version FROM schema_migrations WHERE version = '011_add_reporting_views.sql';"
        )
        assert "011_add_reporting_views.sql" in recorded_011, (
            "011_add_reporting_views.sql must be recorded in schema_migrations after bootstrap"
        )
