"""Unit tests for extraction metric storage helpers."""

from datetime import UTC, datetime
import uuid
from unittest.mock import MagicMock

from src.database.models import ExtractionMetric
from src.database.storage import (
    complete_repository_extraction,
    fail_repository_extraction,
)


def _make_metric() -> ExtractionMetric:
    return ExtractionMetric(
        run_id=uuid.uuid4(),
        repository_id="repo-123",
        platform="azure_devops",
        status="started",
        extraction_started_at=datetime.now(UTC),
    )


def _make_session_with_metric(metric: ExtractionMetric) -> MagicMock:
    session = MagicMock()
    session.query.return_value.filter_by.return_value.one_or_none.return_value = metric
    return session


class TestExtractionMetricStorage:
    def test_complete_repository_extraction_queries_by_id(self):
        metric = _make_metric()
        session = _make_session_with_metric(metric)

        complete_repository_extraction(
            session,
            metric_id=42,
            commits_extracted=3,
            pull_requests_extracted=2,
            branches_extracted=1,
            cache_hits=5,
            cache_misses=1,
        )

        session.query.assert_called_once_with(ExtractionMetric)
        session.query.return_value.filter_by.assert_called_once_with(id=42)
        assert metric.status == "completed"
        assert metric.commits_extracted == 3
        assert metric.pull_requests_extracted == 2
        assert metric.branches_extracted == 1
        assert metric.cache_hits == 5
        assert metric.cache_misses == 1
        assert metric.extraction_completed_at is not None
        session.flush.assert_called_once()

    def test_fail_repository_extraction_queries_by_id(self):
        metric = _make_metric()
        session = _make_session_with_metric(metric)

        fail_repository_extraction(session, metric_id=7, error_message="boom")

        session.query.assert_called_once_with(ExtractionMetric)
        session.query.return_value.filter_by.assert_called_once_with(id=7)
        assert metric.status == "failed"
        assert metric.error_message == "boom"
        assert metric.extraction_completed_at is not None
        session.flush.assert_called_once()
