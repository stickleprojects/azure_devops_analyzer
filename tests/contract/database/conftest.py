"""Pytest fixtures for database contract tests.

Provides the ``clean_database`` fixture for tests that need a fully empty
schema at the start of each test case.

Shared infrastructure (test_database_url, test_engine, db_session) is provided
by tests/contract/conftest.py and is available here via pytest's conftest
discovery hierarchy.

SETUP INSTRUCTIONS:
1. Start PostgreSQL: docker compose up -d timescaledb
2. Set TEST_DATABASE_URL environment variable (or use default)
3. Run tests: pytest tests/contract/database/
"""

import pytest
from sqlalchemy import text

from src.database.models.base import Base


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
