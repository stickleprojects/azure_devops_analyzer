"""Pytest fixtures for unit tests.

Provides a lightweight in-memory SQLite ``db_session`` fixture so that
property-based tests can exercise functions that accept a SQLAlchemy Session
without requiring a running PostgreSQL instance.

Only the ``contributors`` table is created — sufficient for identity tests.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.database.models.contributor import Contributor


@pytest.fixture()
def db_session():
    """Return a SQLAlchemy Session backed by a fresh in-memory SQLite database.

    Each test function gets its own engine and schema, so tests are fully
    isolated from one another.
    """
    engine = create_engine("sqlite:///:memory:", echo=False)
    Contributor.__table__.create(engine)

    with Session(engine) as session:
        yield session

    engine.dispose()
