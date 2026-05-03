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

    def test_synthetic_orphan_pr_author_detected(self, db_session) -> None:
        """Inserting a PR with a non-existent author_id triggers no_orphan_pr_author_fk."""
        # Insert a minimal organization, project, repository, then an orphan PR.
        db_session.execute(
            text(
                "INSERT INTO organizations (name, url, platform) "
                "VALUES ('health-test-org', 'https://github.com/health-test-org', 'github') "
                "ON CONFLICT DO NOTHING"
            )
        )
        db_session.flush()

        db_session.execute(
            text(
                "INSERT INTO projects (organization_id, name) "
                "SELECT organization_id, 'health-test-project' "
                "FROM organizations WHERE name = 'health-test-org' AND platform = 'github' "
                "ON CONFLICT DO NOTHING"
            )
        )
        db_session.flush()

        db_session.execute(
            text(
                "INSERT INTO repositories (repo_id, project_id, name, url) "
                "SELECT 'health-test-repo-001', p.project_id, 'health-test-repo', "
                "       'https://github.com/health-test-org/health-test-repo' "
                "FROM projects p "
                "JOIN organizations o ON o.organization_id = p.organization_id "
                "WHERE o.name = 'health-test-org' AND o.platform = 'github' "
                "ON CONFLICT DO NOTHING"
            )
        )
        db_session.flush()

        # Insert a PR whose author_id (999999) does not exist in the contributors table.
        db_session.execute(
            text(
                "INSERT INTO pull_requests "
                "  (repo_id, pr_number, title, created_at, author_id) "
                "VALUES "
                "  ('health-test-repo-001', 9999, 'Orphan PR', NOW(), 999999) "
                "ON CONFLICT DO NOTHING"
            )
        )
        db_session.flush()

        report = compute_extraction_health(db_session, platform="github")

        orphan_result = next(
            (r for r in report.invariants if r.name == "no_orphan_pr_author_fk"),
            None,
        )
        assert orphan_result is not None, "no_orphan_pr_author_fk invariant not in report"
        assert orphan_result.violations > 0, (
            "Expected violations > 0 for orphan PR author"
        )
        assert len(orphan_result.sample_rows) > 0, "Expected sample_rows populated"

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

    def test_new_invariant_picked_up_without_code_changes(
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
