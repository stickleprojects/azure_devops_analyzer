"""Integration tests for extraction health checking.

These tests run against a real PostgreSQL database (provided by the
``db_session`` fixture from ``tests/contract/conftest.py``) to verify that
``compute_extraction_health`` correctly:

1. Reports zero violations when the database is clean.
2. Detects a synthetic violation injected into the database.
3. Picks up a new invariant added to the SQL file at runtime (single-source-of-truth).
4. All invariants from tests/db_invariants.sql appear in the report.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from sqlalchemy import text

from src.utils.extraction_health import compute_extraction_health


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestExtractionHealthIntegration:
    """Integration tests for compute_extraction_health against PostgreSQL."""

    def test_clean_database_reports_healthy(self, db_session) -> None:
        """A database with no data should pass all invariants."""
        report = compute_extraction_health(db_session, platform="github")
        assert report.is_healthy, (
            f"Expected healthy report on empty DB; violations: "
            f"{[r for r in report.invariants if r.violations > 0]}"
        )

    def test_synthetic_violation_detected(self, db_session) -> None:
        """Inserting two contributors with the same normalised email triggers
        no_case_variant_contributor_twins — the invariant most easily exercised
        in tests since the contributors table has only a case-sensitive UNIQUE
        constraint on email, not a normalised-email constraint."""
        # Insert two contributors whose emails differ only in case/whitespace.
        # The unique constraint allows both (exact match); the invariant catches them.
        db_session.execute(
            text(
                "INSERT INTO contributors (email, name) "
                "VALUES ('health-twin@example.com', 'Alice Lower') "
                "ON CONFLICT (email) DO NOTHING"
            )
        )
        db_session.execute(
            text(
                "INSERT INTO contributors (email, name) "
                "VALUES ('HEALTH-TWIN@EXAMPLE.COM', 'Alice Upper') "
                "ON CONFLICT (email) DO NOTHING"
            )
        )
        db_session.flush()

        report = compute_extraction_health(db_session, platform="github")

        twin_result = next(
            (
                r
                for r in report.invariants
                if r.name == "no_case_variant_contributor_twins"
            ),
            None,
        )
        assert twin_result is not None, (
            "no_case_variant_contributor_twins invariant not in report"
        )
        assert twin_result.violations > 0, (
            "Expected violations > 0 for case-variant contributor twins"
        )
        assert len(twin_result.sample_rows) > 0, "Expected sample_rows populated"

    def test_all_invariants_checked(self, db_session) -> None:
        """All invariants from tests/db_invariants.sql must appear in the report."""
        from src.utils.extraction_health import (
            _find_invariants_sql,
            _parse_invariants_sql,
        )

        sql_path = _find_invariants_sql()
        expected_names = {inv.name for inv in _parse_invariants_sql(sql_path)}

        report = compute_extraction_health(db_session, platform="github")
        reported_names = {r.name for r in report.invariants}

        assert expected_names == reported_names, (
            f"Invariant mismatch — expected: {expected_names}, got: {reported_names}"
        )

    def test_single_source_of_truth_property(
        self, db_session, tmp_path: Path
    ) -> None:
        """Monkey-patching the invariants SQL path proves the single-source-of-truth property.

        Adding a new invariant to the SQL file is automatically picked up by
        ``compute_extraction_health`` — no production code changes needed.
        """
        stub_sql = tmp_path / "custom_invariants.sql"
        stub_sql.write_text(
            textwrap.dedent(
                """\
                -- invariant: custom_runtime_invariant
                SELECT 1 WHERE false;
                """
            ),
            encoding="utf-8",
        )

        report = compute_extraction_health(
            db_session,
            platform="github",
            invariants_sql_path=stub_sql,
        )
        names = {r.name for r in report.invariants}
        assert "custom_runtime_invariant" in names
        assert len(names) == 1
        assert report.is_healthy
