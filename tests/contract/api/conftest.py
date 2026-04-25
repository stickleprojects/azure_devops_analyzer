"""Pytest fixtures for API contract tests.

Provides a Flask test client wired to the same database session used by tests,
so that test-inserted data is visible to endpoint handlers without committing
to the real database.
"""

import os
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session

from src.database.models.base import Base


def _iter_sql_statements(sql_text: str):
    """Yield semicolon-terminated SQL statements from a SQL script."""
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
    """Ensure time_bucket is available for reporting views."""
    try:
        conn.execute(text("SAVEPOINT sp_timescale_ext"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb;"))
        conn.execute(text("RELEASE SAVEPOINT sp_timescale_ext"))
    except Exception as exc:
        conn.execute(text("ROLLBACK TO SAVEPOINT sp_timescale_ext"))

    has_time_bucket = conn.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1 FROM pg_proc p
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


@pytest.fixture(scope="session")
def test_database_url():
    """Get test database URL from environment or use default Docker PostgreSQL."""
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
    """Create SQLAlchemy engine for the API contract tests."""
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
        finally:
            admin_engine.dispose()

    engine = create_engine(test_database_url, echo=False, pool_pre_ping=True)
    Base.metadata.create_all(engine)

    project_root = Path(__file__).parent.parent.parent.parent
    views_file = project_root / "database" / "views.sql"
    if views_file.exists():
        with engine.begin() as conn:
            _ensure_time_bucket_support(conn)
            with open(views_file) as f:
                for statement in _iter_sql_statements(f.read()):
                    conn.execute(text(statement))

    yield engine

    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine):
    """Provide a clean database session for each test with automatic rollback."""
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


@pytest.fixture(scope="function")
def app_client(db_session):
    """Flask test client with get_session patched to use the test db_session."""
    @contextmanager
    def mock_get_session():
        yield db_session

    with patch("src.api.rescan.get_session", mock_get_session):
        from src.api.rescan import app
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client
