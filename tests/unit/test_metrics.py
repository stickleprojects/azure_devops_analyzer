"""Unit tests for src/utils/metrics.py."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from src.utils.extraction_health import HealthReport, InvariantResult
from src.utils.metrics import emit_health_report, _emit_logs


def _make_clean_report() -> HealthReport:
    return HealthReport(
        platform="github",
        repo_id=None,
        timestamp=datetime.now(tz=timezone.utc),
        invariants=[
            InvariantResult(name="no_orphan_pr_author_fk", violations=0),
        ],
    )


def _make_violated_report() -> HealthReport:
    return HealthReport(
        platform="github",
        repo_id="repo-1",
        timestamp=datetime.now(tz=timezone.utc),
        invariants=[
            InvariantResult(
                name="no_orphan_pr_author_fk",
                violations=3,
                sample_rows=[{"id": 1}, {"id": 2}, {"id": 3}],
            ),
        ],
    )


class TestEmitHealthReport:
    def test_emit_does_not_raise_when_db_unavailable(self) -> None:
        """emit_health_report must never raise even when _persist_to_db fails."""
        report = _make_clean_report()
        with patch(
            "src.utils.metrics._persist_to_db",
            side_effect=RuntimeError("DB unavailable"),
        ):
            # Should not raise
            emit_health_report(report)

    def test_emit_does_not_raise_when_emit_logs_fails(self) -> None:
        """emit_health_report must never raise even when _emit_logs fails."""
        report = _make_clean_report()
        with patch(
            "src.utils.metrics._emit_logs",
            side_effect=RuntimeError("log failure"),
        ):
            # Should not raise
            emit_health_report(report)

    def test_emit_calls_emit_logs(self) -> None:
        report = _make_clean_report()
        with (
            patch("src.utils.metrics._emit_logs") as mock_logs,
            patch("src.utils.metrics._persist_to_db"),
        ):
            emit_health_report(report)
            mock_logs.assert_called_once_with(report)


class TestEmitLogs:
    def test_summary_logged_for_clean_report(self, caplog) -> None:
        import logging

        report = _make_clean_report()
        with caplog.at_level(logging.INFO, logger="src.utils.metrics"):
            _emit_logs(report)
        assert any("extraction-health summary" in r.message for r in caplog.records)

    def test_warning_emitted_for_violations(self, caplog) -> None:
        import logging

        report = _make_violated_report()
        with caplog.at_level(logging.WARNING, logger="src.utils.metrics"):
            _emit_logs(report)
        assert any("violation" in r.message for r in caplog.records)

    def test_no_warning_for_clean_report(self, caplog) -> None:
        import logging

        report = _make_clean_report()
        with caplog.at_level(logging.WARNING, logger="src.utils.metrics"):
            _emit_logs(report)
        warning_msgs = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert not warning_msgs
