"""Pytest fixtures for database contract tests.

Provides clean database setup and teardown for each test.
Uses PostgreSQL via Docker for realistic testing.

SETUP INSTRUCTIONS:
1. Start PostgreSQL: docker compose up -d timescaledb
2. Set TEST_DATABASE_URL environment variable (or use default)
3. Run tests: pytest tests/contract/database/

The default test database URL uses the PostgreSQL instance from docker-compose.yml.
"""

import os
import pytest
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import Session, sessionmaker
from pathlib import Path

from src.database.models.base import Base


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
    
    # Default: Use PostgreSQL from docker-compose with test database
    # For tests running on host (not in container), use localhost
    # For tests running inside Docker, POSTGRES_HOST should be set to "timescaledb"
    postgres_host = os.environ.get("POSTGRES_HOST", "localhost")
    postgres_port = os.environ.get("POSTGRES_PORT", "5432")
    postgres_user = os.environ.get("POSTGRES_USER", "postgres")
    postgres_password = os.environ.get("POSTGRES_PASSWORD", "postgres")
    
    return f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/repo_analyzer_test"


@pytest.fixture(scope="session")
def test_engine(test_database_url):
    """Create SQLAlchemy engine for test database.
    
    Creates the test database if it doesn't exist, then creates all tables.
    """
    # First, connect to default postgres database to create test database if needed
    if "postgresql" in test_database_url:
        # Extract connection params
        base_url = test_database_url.rsplit("/", 1)[0]
        test_db_name = test_database_url.rsplit("/", 1)[1]
        
        # Connect to default postgres database
        admin_engine = create_engine(f"{base_url}/postgres", isolation_level="AUTOCOMMIT")
        
        try:
            with admin_engine.connect() as conn:
                # Check if test database exists
                result = conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
                    {"dbname": test_db_name}
                )
                if not result.fetchone():
                    # Create test database
                    conn.execute(text(f'CREATE DATABASE "{test_db_name}"'))
                    print(f"\n✓ Created test database: {test_db_name}")
        finally:
            admin_engine.dispose()
    
    # Now connect to test database
    engine = create_engine(
        test_database_url,
        echo=False,  # Set to True for SQL debugging
        pool_pre_ping=True,  # Verify connections before using
    )
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    yield engine
    
    # Cleanup: Drop all tables but keep database
    # Suppress TimescaleDB internal schema errors during teardown
    try:
        Base.metadata.drop_all(engine)
    except Exception as e:
        # Ignore TimescaleDB schema errors during cleanup
        if "_timescaledb" not in str(e):
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
    
    This means tests can call session.commit() freely - it only commits to the
    SAVEPOINT, and the outer transaction is always rolled back after the test.
    """
    # Create a connection and begin a transaction
    connection = test_engine.connect()
    transaction = connection.begin()
    
    # Bind session to this transaction
    session = Session(bind=connection)
    
    # Begin a nested transaction (savepoint)
    nested = connection.begin_nested()
    
    # If the application code calls session.commit(), it will only commit
    # to the savepoint. We automatically start a new savepoint after each commit.
    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        if transaction.nested and not transaction._parent.nested:
            session.begin_nested()
    
    try:
        yield session
    finally:
        session.close()
        # Roll back the outer transaction (discards all changes)
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def clean_database(db_session):
    """Provide a completely clean database by truncating all tables.
    
    Use this when you need to ensure no data from previous tests exists.
    For most tests, db_session fixture is sufficient.
    """
    # Get all table names in reverse dependency order
    tables = reversed(Base.metadata.sorted_tables)
    
    # Truncate all tables with CASCADE for PostgreSQL
    for table in tables:
        try:
            # PostgreSQL supports TRUNCATE CASCADE
            db_session.execute(text(f"TRUNCATE TABLE {table.name} CASCADE"))
            db_session.commit()
        except Exception:
            # Fallback to DELETE if TRUNCATE not supported
            try:
                db_session.execute(text(f"DELETE FROM {table.name}"))
                db_session.commit()
            except Exception:
                # Some tables might not exist yet or have constraints
                db_session.rollback()
    
    yield db_session
