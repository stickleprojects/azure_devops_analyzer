"""
Unit tests for technology stack storage functions.

Tests store_languages(), store_detections(), and store_technology_eol()
in isolation using mocked sessions. Verifies:

- store_languages() creates rows with source='platform_api', category='language'
- store_detections() creates rows for all 7 non-language categories, source='heuristic'
- store_detections() does NOT create rows with category='language'
- Language upsert updates percentage and byte_count; detection upsert updates confidence
- first_seen_at is preserved on second upsert; last_seen_at is updated
- store_technology_eol() upserts into technologies table, not repository_stack
- Empty category lists produce no rows
- Both store_languages and store_detections write to the same repository_stack table
"""

import pytest
from datetime import date, datetime, UTC, timedelta
from unittest.mock import MagicMock, call, patch

from src.database.storage import store_languages, store_detections, store_technology_eol
from src.analyzers.technology_detector import TechnologyDetection
from src.extractors.base import LanguageData


def _make_session():
    """Return a minimal mock session."""
    session = MagicMock()
    return session


def _make_detection(
    frameworks=None,
    databases=None,
    deployment_platforms=None,
    build_tools=None,
    testing_frameworks=None,
    ci_cd_platforms=None,
    documentation_tools=None,
    programming_languages=None,
    confidence=0.9,
):
    """Build a minimal TechnologyDetection instance."""
    return TechnologyDetection(
        programming_languages=programming_languages or [],
        frameworks=frameworks or [],
        databases=databases or [],
        deployment_platforms=deployment_platforms or [],
        build_tools=build_tools or [],
        testing_frameworks=testing_frameworks or [],
        ci_cd_platforms=ci_cd_platforms or [],
        documentation_tools=documentation_tools or [],
        language_confidence=confidence,
        framework_confidence=confidence,
        overall_confidence=confidence,
        all_technologies=[],
        primary_language=None,
        analyzed_at=datetime.now(UTC),
    )


# =============================================================================
# Tests: store_languages
# =============================================================================

class TestStoreLanguages:

    def test_creates_new_rows_with_platform_api_source(self):
        """store_languages() inserts rows with source='platform_api', category='language'."""
        session = _make_session()
        session.query.return_value.filter_by.return_value.first.return_value = None

        langs = [
            LanguageData(language="Python", byte_count=10000, percentage=80.0),
        ]
        results = store_languages(session, "org/repo", langs)

        session.add.assert_called_once()
        added = session.add.call_args[0][0]
        assert added.source == "platform_api"
        assert added.category == "language"
        assert added.name == "Python"
        assert added.byte_count == 10000
        assert added.percentage == 80.0
        assert len(results) == 1

    def test_updates_existing_row_stats(self):
        """store_languages() updates percentage and byte_count on upsert."""
        from src.database.models.repository_stack import RepositoryStack
        existing = RepositoryStack(
            repo_id="org/repo",
            category="language",
            name="Python",
            source="platform_api",
            byte_count=5000,
            percentage=50.0,
            first_seen_at=datetime(2025, 1, 1, tzinfo=UTC),
            last_seen_at=datetime(2025, 1, 1, tzinfo=UTC),
        )
        session = _make_session()
        session.query.return_value.filter_by.return_value.first.return_value = existing

        langs = [LanguageData(language="Python", byte_count=10000, percentage=80.0)]
        store_languages(session, "org/repo", langs)

        assert existing.percentage == 80.0
        assert existing.byte_count == 10000
        # last_seen_at is updated
        assert existing.last_seen_at > datetime(2025, 1, 1, tzinfo=UTC)
        # first_seen_at is NOT changed
        assert existing.first_seen_at == datetime(2025, 1, 1, tzinfo=UTC)
        session.add.assert_not_called()

    def test_empty_list_produces_no_rows(self):
        """store_languages() with empty list returns [] and calls no add."""
        session = _make_session()
        results = store_languages(session, "org/repo", [])
        assert results == []
        session.add.assert_not_called()

    def test_multiple_languages_produce_multiple_rows(self):
        """store_languages() creates one row per language."""
        session = _make_session()
        session.query.return_value.filter_by.return_value.first.return_value = None

        langs = [
            LanguageData(language="Python", byte_count=5000, percentage=50.0),
            LanguageData(language="TypeScript", byte_count=5000, percentage=50.0),
        ]
        results = store_languages(session, "org/repo", langs)
        assert len(results) == 2
        assert session.add.call_count == 2


# =============================================================================
# Tests: store_detections
# =============================================================================

class TestStoreDetections:

    def test_creates_rows_for_all_7_non_language_categories(self):
        """store_detections() covers framework, database, deployment_platform,
        build_tool, testing_framework, ci_cd, documentation."""
        session = _make_session()
        session.query.return_value.filter_by.return_value.first.return_value = None

        detection = _make_detection(
            frameworks=["React"],
            databases=["PostgreSQL"],
            deployment_platforms=["Docker"],
            build_tools=["Webpack"],
            testing_frameworks=["Jest"],
            ci_cd_platforms=["GitHub Actions"],
            documentation_tools=["MkDocs"],
        )
        results = store_detections(session, "org/repo", detection)

        assert session.add.call_count == 7
        categories = {r.category for r in results}
        assert categories == {
            "framework",
            "database",
            "deployment_platform",
            "build_tool",
            "testing_framework",
            "ci_cd",
            "documentation",
        }

    def test_does_not_create_language_rows(self):
        """store_detections() skips programming_languages — language data comes
        from the platform API."""
        session = _make_session()
        session.query.return_value.filter_by.return_value.first.return_value = None

        detection = _make_detection(
            frameworks=["React"],
            programming_languages=["Python", "JavaScript"],
        )
        results = store_detections(session, "org/repo", detection)

        lang_rows = [r for r in results if r.category == "language"]
        assert lang_rows == [], "store_detections must not write category='language' rows"

    def test_source_is_heuristic(self):
        """store_detections() sets source='heuristic'."""
        session = _make_session()
        session.query.return_value.filter_by.return_value.first.return_value = None

        detection = _make_detection(frameworks=["Django"])
        results = store_detections(session, "org/repo", detection)
        assert all(r.source == "heuristic" for r in results)

    def test_updates_confidence_on_upsert(self):
        """store_detections() updates confidence and last_seen_at on existing rows."""
        from src.database.models.repository_stack import RepositoryStack
        existing = RepositoryStack(
            repo_id="org/repo",
            category="framework",
            name="Django",
            source="heuristic",
            confidence=0.5,
            first_seen_at=datetime(2025, 1, 1, tzinfo=UTC),
            last_seen_at=datetime(2025, 1, 1, tzinfo=UTC),
        )
        session = _make_session()
        session.query.return_value.filter_by.return_value.first.return_value = existing

        detection = _make_detection(frameworks=["Django"], confidence=0.95)
        store_detections(session, "org/repo", detection)

        assert float(existing.confidence) == pytest.approx(0.95)
        assert existing.last_seen_at > datetime(2025, 1, 1, tzinfo=UTC)
        assert existing.first_seen_at == datetime(2025, 1, 1, tzinfo=UTC)
        session.add.assert_not_called()

    def test_empty_category_lists_produce_no_rows(self):
        """store_detections() with all empty lists returns [] and calls no add."""
        session = _make_session()
        detection = _make_detection()
        results = store_detections(session, "org/repo", detection)
        assert results == []
        session.add.assert_not_called()

    def test_both_functions_write_to_repository_stack(self):
        """store_languages and store_detections both write to repository_stack."""
        from src.database.models.repository_stack import RepositoryStack

        session = _make_session()
        session.query.return_value.filter_by.return_value.first.return_value = None

        langs = [LanguageData(language="Python", byte_count=1000, percentage=100.0)]
        detection = _make_detection(frameworks=["Flask"])

        lang_results = store_languages(session, "org/repo", langs)
        det_results = store_detections(session, "org/repo", detection)

        all_added = [call_args[0][0] for call_args in session.add.call_args_list]
        assert all(isinstance(obj, RepositoryStack) for obj in all_added)
        assert len(all_added) == 2


# =============================================================================
# Tests: store_technology_eol
# =============================================================================

class TestStoreTechnologyEol:

    def test_creates_new_technology_row(self):
        """store_technology_eol() inserts a Technology when none exists."""
        from src.database.models.technology import Technology

        session = _make_session()
        session.query.return_value.filter_by.return_value.first.return_value = None

        result = store_technology_eol(
            session,
            name="Python",
            category="language",
            is_eol=False,
            eol_date=None,
            latest_supported_version="3.12",
        )

        session.add.assert_called_once()
        added = session.add.call_args[0][0]
        assert isinstance(added, Technology)
        assert added.name == "Python"
        assert added.category == "language"
        assert added.is_eol is False
        assert added.latest_supported_version == "3.12"
        assert added.eol_enriched_at is not None

    def test_updates_existing_technology_row(self):
        """store_technology_eol() updates all EOL fields on existing row."""
        from src.database.models.technology import Technology
        existing = Technology(
            name="Java",
            category="language",
            is_eol=False,
            eol_date=None,
        )
        session = _make_session()
        session.query.return_value.filter_by.return_value.first.return_value = existing

        eol_date = date(2024, 9, 30)
        store_technology_eol(
            session,
            name="Java",
            category="language",
            is_eol=True,
            eol_date=eol_date,
            latest_supported_version=None,
        )

        assert existing.is_eol is True
        assert existing.eol_date == eol_date
        assert existing.eol_enriched_at is not None
        session.add.assert_not_called()

    def test_writes_to_technologies_table_not_repository_stack(self):
        """store_technology_eol() only writes to technologies, not repository_stack."""
        from src.database.models.technology import Technology
        from src.database.models.repository_stack import RepositoryStack

        session = _make_session()
        session.query.return_value.filter_by.return_value.first.return_value = None

        store_technology_eol(
            session,
            name="React",
            category="framework",
            is_eol=False,
            eol_date=None,
            latest_supported_version=None,
        )

        added = session.add.call_args[0][0]
        assert isinstance(added, Technology)
        assert not isinstance(added, RepositoryStack)
