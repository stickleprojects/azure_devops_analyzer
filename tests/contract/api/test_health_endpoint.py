"""Contract tests for GET /health endpoint behavior."""

from unittest.mock import patch


def test_health_returns_200_when_celery_ping_succeeds(app_client):
    """Returns healthy when Celery inspect().ping() succeeds."""
    with patch("src.api.rescan.celery_app.control") as mock_control:
        mock_control.inspect.return_value.ping.return_value = {"celery@worker": {"ok": "pong"}}

        resp = app_client.get("/health")

    assert resp.status_code == 200
    assert resp.get_json() == {"status": "healthy", "service": "extraction-api"}
    mock_control.inspect.return_value.ping.assert_called_once_with()


def test_health_returns_503_when_celery_ping_raises(app_client):
    """Returns degraded when Celery inspect().ping() raises."""
    with patch("src.api.rescan.celery_app.control") as mock_control:
        mock_control.inspect.return_value.ping.side_effect = RuntimeError("celery unavailable")

        resp = app_client.get("/health")

    assert resp.status_code == 503
    assert resp.get_json() == {"status": "degraded", "service": "extraction-api"}
    mock_control.inspect.return_value.ping.assert_called_once_with()
