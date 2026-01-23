"""Pytest fixtures for database contract tests.

Provides clean database setup and teardown for each test.
"""

import os
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from pathlib import Path

from src.database.models.base import Base


@pytest.fixture(scope="session")
def test_database_url():
    """Get test database URL from environment or use SQLite in-memory."""
    test_db_url = os.environ.get("TEST_DATABASE_URL")
    if test_db_url:
        return test_db_url
    
    # Use SQLite in-memory database for fast tests
    return "sqlite:///:memory:"


@pytest.fixture(scope="session")
def test_engine(test_database_url):
    """Create SQLAlchemy engine for test database."""
    engine = create_engine(
        test_database_url,
        echo=False,  # Set to True for SQL debugging
    )
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    yield engine
    
    # Cleanup
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine):
    """Provide a clean database session for each test.
    
    This fixture:
    1. Creates a new database session
    2. Yields it to the test
    3. Rolls back any changes (tests don't persist)
    4. Closes the session
    
    This ensures test isolation - each test gets a fresh database state.
    """
    SessionLocal = sessionmaker(bind=test_engine)
    session = SessionLocal()
    
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def clean_database(db_session):
    """Provide a completely clean database by truncating all tables.
    
    Use this when you need to ensure no data from previous tests exists.
    For most tests, db_session fixture is sufficient.
    """
    # Get all table names
    tables = Base.metadata.tables.keys()
    
    # Truncate all tables (SQLite doesn't support TRUNCATE, use DELETE)
    for table in tables:
        try:
            db_session.execute(text(f"DELETE FROM {table}"))
            db_session.commit()
        except Exception:
            # Some tables might not exist yet or have constraints
            db_session.rollback()
    
    yield db_session
