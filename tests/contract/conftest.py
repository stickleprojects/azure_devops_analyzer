"""Shared pytest fixtures for all contract tests (database + API).

Provides database setup/teardown and a per-test session with savepoint-based
rollback so individual tests never persist data to the real database.

All sub-packages (tests/contract/database/, tests/contract/api/) inherit
these fixtures automatically via pytest's conftest discovery.
"""

import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session

from src.database.models.base import Base


def _iter_sql_statements(sql_text: str):
    """Yield semicolon-terminated SQL statements from a SQL script.

    The reporting views script is a sequence of CREATE VIEW statements, so a
    lightweight splitter is sufficient and avoids driver issues with executing
    very large multi-statement blobs in a single call.
    """
    chunks = []
    for line in sql_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        chunks.append(line)
        if stripped.endswith(";"):
            statement = "\n".join(chunks).strip()
            if statement:
                yield statement
            chunks = []

    trailing = "\n".join(chunks).strip()
    if trailing:
        yield trailing


def _ensure_time_bucket_support(conn):
    """Ensure time_bucket is available for reporting views.

    Preferred path is enabling TimescaleDB extension. If extension activation is
    unavailable in the current test environment, fall back to a compatible
    SQL shim based on date_bin.

    A SAVEPOINT wraps the CREATE EXTENSION attempt so that if TimescaleDB is
    not installed (e.g. plain postgres:16 in local dev), the outer transaction
    is not left in an aborted state and subsequent SQL statements still work.
    """
    try:
        conn.execute(text("SAVEPOINT sp_timescale_ext"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb;"))
        conn.execute(text("RELEASE SAVEPOINT sp_timescale_ext"))
        print("\n✓ Ensured TimescaleDB extension")
    except Exception as exc:
        conn.execute(text("ROLLBACK TO SAVEPOINT sp_timescale_ext"))
        print(f"\n⚠ Could not enable TimescaleDB extension ({exc}); checking fallback")

    has_time_bucket = conn.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM pg_proc p
                WHERE p.proname = 'time_bucket'
                  AND pg_function_is_visible(p.oid)
            )
            """
        )
    ).scalar()

    if not has_time_bucket:
        conn.execute(
            text(
                """
                CREATE OR REPLACE FUNCTION public.time_bucket(
                    bucket_width INTERVAL,
                    ts TIMESTAMPTZ
                )
                RETURNS TIMESTAMPTZ
                LANGUAGE SQL
                IMMUTABLE
                AS $$
                    SELECT date_bin(bucket_width, ts, TIMESTAMPTZ '2000-01-01 00:00:00+00')
                $$;
                """
            )
        )
        print("\n✓ Installed compatibility time_bucket shim using date_bin")


@pytest.fixture(scope="session")
def test_database_url():
    """Get test database URL from environment or use Docker PostgreSQL.

    Priority:
    1. TEST_DATABASE_URL environment variable
    2. Default: PostgreSQL from docker-compose.yml (test database)

    The test database 'repo_analyzer_test' is automatically created if it doesn't exist.

    Note: When running outside Docker, POSTGRES_HOST defaults to "localhost" to
    connect to the containerized PostgreSQL via the mapped port 5432.
    """
    test_db_url = os.environ.get("TEST_DATABASE_URL")
    if test_db_url:
        return test_db_url

    postgres_host = os.environ.get("POSTGRES_HOST", "localhost")
    postgres_port = os.environ.get("POSTGRES_PORT", "5432")
    postgres_user = os.environ.get("POSTGRES_USER", "postgres")
    postgres_password = os.environ.get("POSTGRES_PASSWORD", "postgres")

    return f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/repo_analyzer_test"


@pytest.fixture(scope="session")
def test_engine(test_database_url):
    """Create SQLAlchemy engine for test database.

    Creates the test database if it doesn't exist, then creates all tables
    and SQL views.  At session teardown drops and recreates the public schema
    so that dependent views and hypertables don't block table drops.
    """
    if "postgresql" in test_database_url:
        base_url = test_database_url.rsplit("/", 1)[0]
        test_db_name = test_database_url.rsplit("/", 1)[1]

        admin_engine = create_engine(f"{base_url}/postgres", isolation_level="AUTOCOMMIT")
        try:
            with admin_engine.connect() as conn:
                result = conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
                    {"dbname": test_db_name},
                )
                if not result.fetchone():
                    conn.execute(text(f'CREATE DATABASE "{test_db_name}"'))
                    print(f"\n✓ Created test database: {test_db_name}")
        finally:
            admin_engine.dispose()

    engine = create_engine(test_database_url, echo=False, pool_pre_ping=True)
    Base.metadata.create_all(engine)

    project_root = Path(__file__).parent.parent.parent
    views_file = project_root / "database" / "views.sql"

    if views_file.exists():
        with engine.begin() as conn:
            _ensure_time_bucket_support(conn)
            with open(views_file, encoding="utf-8") as f:
                views_sql = f.read()
                statements = list(_iter_sql_statements(views_sql))
                for statement in statements:
                    conn.execute(text(statement))
                print(f"\n✓ Created database views from {views_file.name} ({len(statements)} statements)")

    yield engine

    # Cleanup: drop/recreate public schema so dependent views don't block table drops.
    try:
        with engine.begin() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE;"))
            conn.execute(text("CREATE SCHEMA public;"))
    except Exception:
        try:
            Base.metadata.drop_all(engine)
        except Exception as drop_error:
            if "_timescaledb" not in str(drop_error):
                raise
    finally:
        engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine):
    """Provide a clean database session for each test with automatic rollback.

    This fixture uses a nested transaction to ensure test isolation:
    1. Creates a connection and begins a transaction
    2. Creates a session bound to that transaction
    3. Uses SAVEPOINT for nested transactions
    4. Always rolls back the outer transaction (even if test commits)
    5. Ensures tests never persist data to the database
    """
    connection = test_engine.connect()
    transaction = connection.begin()

    session = Session(bind=connection)
    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        if transaction.nested and not transaction._parent.nested:
            session.begin_nested()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
