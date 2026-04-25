"""Pytest fixtures for API contract tests.

Provides a Flask test client wired to the same database session used by tests,
so that test-inserted data is visible to endpoint handlers without committing
to the real database.

Shared fixtures (test_database_url, test_engine, db_session) are provided by
tests/contract/conftest.py and are available here via pytest's conftest
discovery hierarchy.
"""

from contextlib import contextmanager
from unittest.mock import patch

import pytest


@pytest.fixture(scope="function")
def app_client(db_session):
    """Flask test client with get_session patched to use the test db_session.

    Both src.api.rescan.get_session and src.api.stack.get_session are patched
    so that any endpoint — including those registered via the stack blueprint —
    uses the test transaction rather than a live database connection.
    """
    @contextmanager
    def mock_get_session():
        yield db_session

    with patch("src.api.rescan.get_session", mock_get_session), \
         patch("src.api.stack.get_session", mock_get_session):
        from src.api.rescan import app
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client
