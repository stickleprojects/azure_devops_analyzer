"""
CONTRACT tests for GET /health endpoint.

Tests H1–H2 cover the two response paths of the health_check() view in
src/api/rescan.py:

  H1 — healthy path: Celery ping succeeds → 200 with { status: "healthy", service: "extraction-api" }
  H2 — degraded path: Celery ping raises → 503 with { status: "degraded", service: "extraction-api" }

All tests use the Flask test client and mock the Celery inspect call so they
are fully deterministic (no live broker or database needed).
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture()
def health_client():
    """/health does not touch the database, so we only need a bare Flask test
    client without the db_session / get_session machinery."""
    from src.api.rescan import app

    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.mark.integration
class TestHealthEndpoint:
    """Contract tests for GET /health."""

    def test_h1_healthy_returns_200_with_correct_shape(self, health_client):
        """H1: When Celery ping succeeds, /health returns 200 and the exact
        JSON shape the UI consumes: status == "healthy", service == "extraction-api"."""
        mock_celery = MagicMock()
        # Celery's Control.inspect().ping() returns a dict keyed by worker
        # hostname, each value being a list of {"ok": "pong"} dicts when the
        # worker is reachable.  The health_check() implementation only checks
        # that the call succeeds (no exception), so the exact value here does
        # not matter — the realistic shape is provided for documentation.
        mock_celery.Control.return_value.inspect.return_value.ping.return_value = {
            "celery@worker": [{"ok": "pong"}]
        }

        with patch("src.api.rescan.celery_app", mock_celery):
            resp = health_client.get("/health")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data is not None, "Response body must be valid JSON"
        assert data["status"] == "healthy"
        assert data["service"] == "extraction-api"

    def test_h2_degraded_returns_503_with_correct_shape(self, health_client):
        """H2: When Celery ping raises, /health returns 503 and
        status == "degraded", service == "extraction-api"."""
        mock_celery = MagicMock()
        mock_celery.Control.return_value.inspect.return_value.ping.side_effect = Exception(
            "Connection refused"
        )

        with patch("src.api.rescan.celery_app", mock_celery):
            resp = health_client.get("/health")

        assert resp.status_code == 503
        data = resp.get_json()
        assert data is not None, "Response body must be valid JSON"
        assert data["status"] == "degraded"
        assert data["service"] == "extraction-api"
