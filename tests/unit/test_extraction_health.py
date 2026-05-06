"""
Unit tests for src/utils/extraction_health.py.

These tests run with a mocked / stubbed SQLAlchemy session and a temporary
invariants SQL file, so they do not require a running database.

Mock call ordering for ``compute_extraction_health``:
- An invariant WITHOUT ``requires_table``:
    1 × session.execute(main_query).mappings().all()
- An invariant WITH ``requires_table``:
    1 × session.execute(table_exists_query).scalar()
    [if True] 1 × session.execute(main_query).mappings().all()
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.utils.extraction_health import (
    HealthReport,
    InvariantResult,
    _parse_invariants_sql,
    compute_extraction_health,
)


# ---------------------------------------------------------------------------
# Helpers to build reusable mock results
# ---------------------------------------------------------------------------


def _make_rows_result(*rows: dict) -> MagicMock:
    """Return a mock execute() result whose .mappings().all() returns *rows*."""
    m = MagicMock()
    m.mappings.return_value.all.return_value = list(rows)
    return m


def _make_scalar_result(value: object) -> MagicMock:
    """Return a mock execute() result whose .scalar() returns *value*."""
    m = MagicMock()
    m.scalar.return_value = value
    return m


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def single_invariant_sql(tmp_path: Path) -> Path:
    """One invariant, no requires-table annotation."""
    p = tmp_path / "db_invariants.sql"
    p.write_text(
        textwrap.dedent(
            """\
            -- invariant: no_orphan_example
            -- Every foo row must have a bar_id that resolves.
            SELECT id FROM foo WHERE bar_id IS NULL;
            """
        ),
        encoding="utf-8",
    )
    return p


@pytest.fixture()
def two_invariant_sql(tmp_path: Path) -> Path:
    """Two invariants; the second has a requires-table annotation."""
    p = tmp_path / "db_invariants.sql"
    p.write_text(
        textwrap.dedent(
            """\
            -- invariant: no_orphan_example
            SELECT id FROM foo WHERE bar_id IS NULL;

            -- invariant: no_duplicate_example
            -- requires-table: baz
            SELECT name, count(*) FROM baz GROUP BY name HAVING count(*) > 1;
            """
        ),
        encoding="utf-8",
    )
    return p


@pytest.fixture()
def mock_session() -> MagicMock:
    """Return a bare MagicMock standing in for a SQLAlchemy Session."""
    return MagicMock()


# ---------------------------------------------------------------------------
# _parse_invariants_sql
# ---------------------------------------------------------------------------


class TestParseInvariantsSQL:
    def test_parses_two_invariants(self, two_invariant_sql: Path) -> None:
        results = _parse_invariants_sql(two_invariant_sql)
        assert len(results) == 2

    def test_first_invariant_name(self, two_invariant_sql: Path) -> None:
        results = _parse_invariants_sql(two_invariant_sql)
        assert results[0].name == "no_orphan_example"

    def test_first_invariant_no_requires_table(self, two_invariant_sql: Path) -> None:
        results = _parse_invariants_sql(two_invariant_sql)
        assert results[0].requires_table is None

    def test_second_invariant_requires_table(self, two_invariant_sql: Path) -> None:
        results = _parse_invariants_sql(two_invariant_sql)
        assert results[1].requires_table == "baz"

    def test_sql_contains_select(self, two_invariant_sql: Path) -> None:
        results = _parse_invariants_sql(two_invariant_sql)
        assert "SELECT" in results[0].sql.upper()
        assert "SELECT" in results[1].sql.upper()

    def test_descriptor_comment_not_in_sql(self, two_invariant_sql: Path) -> None:
        results = _parse_invariants_sql(two_invariant_sql)
        assert "Every foo row" not in results[0].sql

    def test_single_source_of_truth(self, tmp_path: Path) -> None:
        """Adding an invariant to the SQL file is picked up without code changes."""
        sql_file = tmp_path / "new_invariants.sql"
        sql_file.write_text(
            "-- invariant: brand_new_invariant\nSELECT 1 WHERE false;\n",
            encoding="utf-8",
        )
        results = _parse_invariants_sql(sql_file)
        assert len(results) == 1
        assert results[0].name == "brand_new_invariant"


# ---------------------------------------------------------------------------
# compute_extraction_health — basic shape (no violations)
# ---------------------------------------------------------------------------


class TestComputeExtractionHealthShape:
    def test_returns_health_report(
        self, mock_session: MagicMock, single_invariant_sql: Path
    ) -> None:
        # Single invariant, no requires-table → 1 execute call
        mock_session.execute.return_value = _make_rows_result()
        report = compute_extraction_health(
            mock_session, platform="github",
            invariants_sql_path=single_invariant_sql,
        )
        assert isinstance(report, HealthReport)

    def test_platform_stored(
        self, mock_session: MagicMock, single_invariant_sql: Path
    ) -> None:
        mock_session.execute.return_value = _make_rows_result()
        report = compute_extraction_health(
            mock_session, platform="azure-devops",
            invariants_sql_path=single_invariant_sql,
        )
        assert report.platform == "azure-devops"

    def test_repo_id_none_by_default(
        self, mock_session: MagicMock, single_invariant_sql: Path
    ) -> None:
        mock_session.execute.return_value = _make_rows_result()
        report = compute_extraction_health(
            mock_session, platform="github",
            invariants_sql_path=single_invariant_sql,
        )
        assert report.repo_id is None

    def test_repo_id_passed_through(
        self, mock_session: MagicMock, single_invariant_sql: Path
    ) -> None:
        mock_session.execute.return_value = _make_rows_result()
        report = compute_extraction_health(
            mock_session, platform="github", repo_id="repo-42",
            invariants_sql_path=single_invariant_sql,
        )
        assert report.repo_id == "repo-42"

    def test_is_healthy_when_no_violations(
        self, mock_session: MagicMock, single_invariant_sql: Path
    ) -> None:
        mock_session.execute.return_value = _make_rows_result()
        report = compute_extraction_health(
            mock_session, platform="github",
            invariants_sql_path=single_invariant_sql,
        )
        assert report.is_healthy is True

    def test_invariant_count_matches_file(
        self, mock_session: MagicMock, two_invariant_sql: Path
    ) -> None:
        # Invariant 1: 1 call (no requires-table)
        # Invariant 2: 2 calls (table_exists + query, table exists = True)
        mock_session.execute.side_effect = [
            _make_rows_result(),                     # invariant 1 query
            _make_scalar_result(True),               # invariant 2 table_exists → True
            _make_rows_result(),                     # invariant 2 query
        ]
        report = compute_extraction_health(
            mock_session, platform="github",
            invariants_sql_path=two_invariant_sql,
        )
        assert len(report.invariants) == 2


# ---------------------------------------------------------------------------
# compute_extraction_health — with violations
# ---------------------------------------------------------------------------


class TestComputeExtractionHealthViolations:
    def test_violations_counted(
        self, mock_session: MagicMock, single_invariant_sql: Path
    ) -> None:
        mock_session.execute.return_value = _make_rows_result(
            {"id": 101}, {"id": 202}
        )
        report = compute_extraction_health(
            mock_session, platform="github",
            invariants_sql_path=single_invariant_sql,
        )
        assert report.invariants[0].violations == 2

    def test_is_not_healthy_when_violations(
        self, mock_session: MagicMock, single_invariant_sql: Path
    ) -> None:
        mock_session.execute.return_value = _make_rows_result({"id": 1})
        report = compute_extraction_health(
            mock_session, platform="github",
            invariants_sql_path=single_invariant_sql,
        )
        assert report.is_healthy is False

    def test_sample_rows_populated(
        self, mock_session: MagicMock, single_invariant_sql: Path
    ) -> None:
        mock_session.execute.return_value = _make_rows_result(
            {"id": 101}, {"id": 202}
        )
        report = compute_extraction_health(
            mock_session, platform="github",
            invariants_sql_path=single_invariant_sql,
        )
        assert len(report.invariants[0].sample_rows) == 2
        assert report.invariants[0].sample_rows[0]["id"] == 101

    def test_sample_capped_at_five(
        self, tmp_path: Path, mock_session: MagicMock
    ) -> None:
        sql_file = tmp_path / "db_invariants.sql"
        sql_file.write_text(
            "-- invariant: many_violations\nSELECT id FROM t;\n",
            encoding="utf-8",
        )
        ten_rows = [{"id": i} for i in range(10)]
        mock_session.execute.return_value = _make_rows_result(*ten_rows)
        report = compute_extraction_health(
            mock_session, platform="github",
            invariants_sql_path=sql_file,
        )
        assert len(report.invariants[0].sample_rows) == 5


# ---------------------------------------------------------------------------
# requires-table skipping
# ---------------------------------------------------------------------------


class TestRequiresTableSkipping:
    def test_skipped_when_table_missing(
        self, mock_session: MagicMock, two_invariant_sql: Path
    ) -> None:
        """Invariant with requires-table yields 0 violations when table absent."""
        mock_session.execute.side_effect = [
            _make_rows_result(),         # invariant 1 query (no requires-table)
            _make_scalar_result(False),  # invariant 2 table_exists → False → skip
        ]
        report = compute_extraction_health(
            mock_session, platform="github",
            invariants_sql_path=two_invariant_sql,
        )
        second = next(r for r in report.invariants if r.name == "no_duplicate_example")
        assert second.violations == 0

    def test_executed_when_table_present(
        self, mock_session: MagicMock, two_invariant_sql: Path
    ) -> None:
        mock_session.execute.side_effect = [
            _make_rows_result(),                          # invariant 1 query
            _make_scalar_result(True),                   # invariant 2 table_exists → True
            _make_rows_result({"name": "dup", "cnt": 2}), # invariant 2 query returns 1 row
        ]
        report = compute_extraction_health(
            mock_session, platform="github",
            invariants_sql_path=two_invariant_sql,
        )
        second = next(r for r in report.invariants if r.name == "no_duplicate_example")
        assert second.violations == 1


# ---------------------------------------------------------------------------
# Error resilience
# ---------------------------------------------------------------------------


class TestErrorResilience:
    def test_query_failure_returns_zero_violations(
        self, mock_session: MagicMock, single_invariant_sql: Path
    ) -> None:
        """A query exception should not propagate — violations become 0."""
        mock_session.execute.side_effect = RuntimeError("connection lost")

        # Must not raise
        report = compute_extraction_health(
            mock_session, platform="github",
            invariants_sql_path=single_invariant_sql,
        )
        assert report.invariants[0].violations == 0

    def test_missing_sql_file_raises_file_not_found(
        self, mock_session: MagicMock
    ) -> None:
        with pytest.raises(FileNotFoundError):
            compute_extraction_health(
                mock_session, platform="github",
                invariants_sql_path=Path("/nonexistent/db_invariants.sql"),
            )
