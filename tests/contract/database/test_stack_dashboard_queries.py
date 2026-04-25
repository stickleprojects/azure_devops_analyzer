"""
CONTRACT Tests for technology stack dashboard queries.

These tests define the expected SQL query behavior for the Technology
Landscape dashboard panels and existing dashboard updates.

All queries target repository_stack (and technologies for EOL data).
These tests run against a real PostgreSQL database (same setup as
other database contract tests).
"""

import pytest
from datetime import date, datetime, UTC
from sqlalchemy import text

from src.database.models.service import RepositoryService
from src.database.storage import (
    get_or_create_service,
    store_organization,
    store_project,
    store_repository,
    store_languages,
    store_detections,
    store_technology_eol,
)
from src.analyzers.technology_detector import TechnologyDetection
from src.extractors.base import Platform, LanguageData
from tests.fixtures.sample_data import (
    sample_organization_data,
    sample_repository_data,
)


def _make_detection(
    frameworks=None,
    databases=None,
    deployment_platforms=None,
    build_tools=None,
    testing_frameworks=None,
    ci_cd_platforms=None,
    documentation_tools=None,
    confidence=0.85,
):
    """Build a minimal TechnologyDetection instance for tests."""
    return TechnologyDetection(
        programming_languages=[],
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


def _setup_repo(db_session, repo_id="org/test-repo", name="test-repo"):
    """Helper: create org + project + repository, return repository."""
    org_data = sample_organization_data(name="test-org-stack")
    org = store_organization(db_session, org_data)
    project = store_project(db_session, org, "test-project-stack", "Test Project")
    repo_data = sample_repository_data(repo_id=repo_id, name=name)
    return store_repository(db_session, project, repo_data)


# =============================================================================
# Language panel queries
# =============================================================================

@pytest.mark.integration
class TestLanguagePanelQueries:
    """Queries for the Language & Framework Overview dashboard row."""

    def test_top_languages_by_repo_count(self, db_session):
        """Dashboard query: top languages by distinct repo count."""
        repo = _setup_repo(db_session)
        langs = [
            LanguageData(language="Python", byte_count=10000, percentage=70.0),
            LanguageData(language="TypeScript", byte_count=5000, percentage=30.0),
        ]
        store_languages(db_session, repo.repo_id, langs)
        db_session.commit()

        result = db_session.execute(text("""
            SELECT name AS language, COUNT(DISTINCT repo_id) AS repo_count
            FROM repository_stack
            WHERE category = 'language'
            GROUP BY name
            ORDER BY repo_count DESC, name
        """)).fetchall()

        assert len(result) == 2
        names = [r.language for r in result]
        assert "Python" in names
        assert "TypeScript" in names

    def test_top_frameworks_by_repo_count(self, db_session):
        """Dashboard query: top frameworks by distinct repo count."""
        repo = _setup_repo(db_session, repo_id="org/fw-repo", name="fw-repo")
        detection = _make_detection(frameworks=["React", "FastAPI"])
        store_detections(db_session, repo.repo_id, detection)
        db_session.commit()

        result = db_session.execute(text("""
            SELECT name AS framework, COUNT(DISTINCT repo_id) AS repo_count
            FROM repository_stack
            WHERE category = 'framework'
            GROUP BY name
            ORDER BY repo_count DESC, name
        """)).fetchall()

        assert len(result) == 2
        names = [r.framework for r in result]
        assert "React" in names
        assert "FastAPI" in names

    def test_distinct_non_language_entries_count(self, db_session):
        """Dashboard stat: count of distinct non-language stack entries."""
        repo = _setup_repo(db_session, repo_id="org/tech-repo", name="tech-repo")
        detection = _make_detection(
            frameworks=["Django"],
            databases=["PostgreSQL"],
            ci_cd_platforms=["GitHub Actions"],
        )
        store_detections(db_session, repo.repo_id, detection)
        db_session.commit()

        result = db_session.execute(text("""
            SELECT COUNT(DISTINCT name) AS non_language_count
            FROM repository_stack
            WHERE category != 'language'
        """)).scalar()

        assert result >= 3

    def test_eol_technology_count_stat(self, db_session):
        """Dashboard stat: count of EOL technologies."""
        from datetime import date
        store_technology_eol(
            db_session,
            name="Python",
            category="language",
            is_eol=True,
            eol_date=date(2020, 1, 1),
            latest_supported_version=None,
        )
        store_technology_eol(
            db_session,
            name="Go",
            category="language",
            is_eol=False,
            eol_date=None,
            latest_supported_version="1.22",
        )
        db_session.commit()

        result = db_session.execute(text("""
            SELECT COUNT(*) FROM technologies WHERE is_eol = TRUE
        """)).scalar()

        assert result >= 1


# =============================================================================
# EOL risk queries
# =============================================================================

@pytest.mark.integration
class TestEolRiskQueries:
    """Queries for the EOL & Risk dashboard row."""

    def test_eol_technologies_with_affected_repo_count(self, db_session):
        """EOL table query: name, category, eol_date, affected_repos."""
        from datetime import date
        repo = _setup_repo(db_session, repo_id="org/eol-repo", name="eol-repo")
        langs = [LanguageData(language="Python", byte_count=5000, percentage=100.0)]
        store_languages(db_session, repo.repo_id, langs)
        store_technology_eol(
            db_session,
            name="Python",
            category="language",
            is_eol=True,
            eol_date=date(2020, 1, 1),
            latest_supported_version=None,
        )
        db_session.commit()

        result = db_session.execute(text("""
            SELECT t.name, t.category, t.eol_date,
                   COUNT(DISTINCT rs.repo_id) AS affected_repos
            FROM technologies t
            JOIN repository_stack rs ON rs.name = t.name AND rs.category = t.category
            WHERE t.is_eol = TRUE
            GROUP BY t.name, t.category, t.eol_date
        """)).fetchall()

        assert len(result) >= 1
        python_row = next((r for r in result if r.name == "Python"), None)
        assert python_row is not None
        assert python_row.affected_repos >= 1

    def test_repos_using_eol_technology_count(self, db_session):
        """Dashboard stat: repos using at least one EOL technology."""
        from datetime import date
        repo = _setup_repo(db_session, repo_id="org/eol2-repo", name="eol2-repo")
        langs = [LanguageData(language="Python", byte_count=5000, percentage=100.0)]
        store_languages(db_session, repo.repo_id, langs)
        store_technology_eol(
            db_session,
            name="Python",
            category="language",
            is_eol=True,
            eol_date=date(2020, 1, 1),
            latest_supported_version=None,
        )
        db_session.commit()

        result = db_session.execute(text("""
            SELECT COUNT(DISTINCT rs.repo_id) AS affected_repo_count
            FROM repository_stack rs
            JOIN technologies t ON t.name = rs.name AND t.category = rs.category
            WHERE t.is_eol = TRUE
        """)).scalar()

        assert result >= 1


# =============================================================================
# Repository stack heatmap queries
# =============================================================================

@pytest.mark.integration
class TestStackHeatmapQueries:
    """Queries for the Repository Stack Heatmap dashboard row."""

    def test_per_repo_stack_entries(self, db_session):
        """Per-repo stack query returns entries grouped by category."""
        repo = _setup_repo(db_session, repo_id="org/heatmap-repo", name="heatmap-repo")
        langs = [LanguageData(language="C#", byte_count=10000, percentage=100.0)]
        detection = _make_detection(ci_cd_platforms=["Azure Pipelines"])
        store_languages(db_session, repo.repo_id, langs)
        store_detections(db_session, repo.repo_id, detection)
        db_session.commit()

        result = db_session.execute(text("""
            SELECT rs.category, rs.name, rs.source,
                   t.is_eol
            FROM repository_stack rs
            LEFT JOIN technologies t ON t.name = rs.name AND t.category = rs.category
            WHERE rs.repo_id = :repo_id
            ORDER BY rs.category, rs.name
        """), {"repo_id": repo.repo_id}).fetchall()

        assert len(result) >= 2
        categories = {r.category for r in result}
        assert "language" in categories
        assert "ci_cd" in categories

    def test_eol_affected_flag_per_repo(self, db_session):
        """Per-repo eol_affected flag: True when repo uses at least one EOL technology."""
        from datetime import date
        repo = _setup_repo(db_session, repo_id="org/affected-repo", name="affected-repo")
        langs = [LanguageData(language="Python", byte_count=5000, percentage=100.0)]
        store_languages(db_session, repo.repo_id, langs)
        store_technology_eol(
            db_session,
            name="Python",
            category="language",
            is_eol=True,
            eol_date=date(2020, 1, 1),
            latest_supported_version=None,
        )
        db_session.commit()

        result = db_session.execute(text("""
            SELECT r.repo_id,
                   EXISTS (
                       SELECT 1 FROM repository_stack rs2
                       JOIN technologies t ON t.name = rs2.name AND t.category = rs2.category
                       WHERE rs2.repo_id = r.repo_id AND t.is_eol = TRUE
                   ) AS eol_affected
            FROM repositories r
            WHERE r.repo_id = :repo_id
        """), {"repo_id": repo.repo_id}).fetchone()

        assert result is not None
        assert result.eol_affected is True


# =============================================================================
# Source separation query
# =============================================================================

@pytest.mark.integration
class TestStackSourceSeparation:
    """repository_stack correctly separates platform_api and heuristic sources."""

    def test_platform_api_and_heuristic_rows_coexist(self, db_session):
        """Both sources can coexist in repository_stack for the same repo."""
        repo = _setup_repo(db_session, repo_id="org/mixed-repo", name="mixed-repo")
        langs = [LanguageData(language="TypeScript", byte_count=8000, percentage=100.0)]
        detection = _make_detection(frameworks=["Angular"])
        store_languages(db_session, repo.repo_id, langs)
        store_detections(db_session, repo.repo_id, detection)
        db_session.commit()

        api_rows = db_session.execute(text("""
            SELECT COUNT(*) FROM repository_stack
            WHERE repo_id = :repo_id AND source = 'platform_api'
        """), {"repo_id": repo.repo_id}).scalar()

        heuristic_rows = db_session.execute(text("""
            SELECT COUNT(*) FROM repository_stack
            WHERE repo_id = :repo_id AND source = 'heuristic'
        """), {"repo_id": repo.repo_id}).scalar()

        assert api_rows >= 1
        assert heuristic_rows >= 1


# =============================================================================
# Service Overview — Technology Stack row queries (R1)
# =============================================================================

@pytest.mark.integration
class TestServiceOverviewTechStackQueries:
    """SQL queries backing the service-overview Technology Stack row."""

    def _setup_service_repo(self, db_session, service_name, repo_id, repo_name):
        """Create org/project/repo/service and link them."""
        org_data = sample_organization_data(name=f"org-svc-{repo_name}")
        org = store_organization(db_session, org_data)
        project = store_project(db_session, org, f"proj-{repo_name}", "Test Project")
        repo_data = sample_repository_data(repo_id=repo_id, name=repo_name)
        repo = store_repository(db_session, project, repo_data)

        service = get_or_create_service(db_session, service_name)
        existing = db_session.query(RepositoryService).filter_by(
            repo_id=repo.repo_id, service_id=service.service_id
        ).first()
        if not existing:
            link = RepositoryService(
                repo_id=repo.repo_id,
                service_id=service.service_id,
                linked_at=datetime.now(UTC),
            )
            db_session.add(link)
            db_session.flush()

        return repo, service

    def test_service_tech_stack_table_query(self, db_session):
        """Panel: Technology Stack by Service — service, languages, frameworks, eol_count."""
        repo, service = self._setup_service_repo(
            db_session, "svc-stack-test", "org/svc-stack-repo", "svc-stack-repo"
        )
        langs = [LanguageData(language="Python", byte_count=8000, percentage=100.0)]
        detection = _make_detection(frameworks=["Django"])
        store_languages(db_session, repo.repo_id, langs)
        store_detections(db_session, repo.repo_id, detection)
        db_session.commit()

        result = db_session.execute(text("""
            SELECT
              s.name AS service,
              COALESCE(STRING_AGG(DISTINCT CASE WHEN rs.category = 'language' THEN rs.name END, ', '), '-') AS languages,
              COALESCE(STRING_AGG(DISTINCT CASE WHEN rs.category = 'framework' THEN rs.name END, ', '), '-') AS frameworks,
              COUNT(DISTINCT CASE WHEN t.is_eol = true THEN rs.name || '|' || rs.category END) AS eol_count
            FROM services s
            JOIN repository_services rsvc ON rsvc.service_id = s.service_id
            JOIN repository_stack rs ON rs.repo_id = rsvc.repo_id
            LEFT JOIN technologies t ON t.name = rs.name AND t.category = rs.category
            WHERE s.name = :service_name
            GROUP BY s.name
            ORDER BY s.name
        """), {"service_name": service.name}).fetchall()

        assert len(result) == 1
        row = result[0]
        assert row.service == service.name
        assert "Python" in row.languages
        assert "Django" in row.frameworks
        assert row.eol_count == 0

    def test_service_tech_stack_eol_count(self, db_session):
        """Panel: eol_count increments when service repos use EOL technologies."""
        repo, service = self._setup_service_repo(
            db_session, "svc-eol-test", "org/svc-eol-repo", "svc-eol-repo"
        )
        langs = [LanguageData(language="Python", byte_count=5000, percentage=100.0)]
        store_languages(db_session, repo.repo_id, langs)
        store_technology_eol(
            db_session,
            name="Python",
            category="language",
            is_eol=True,
            eol_date=date(2020, 1, 1),
            latest_supported_version=None,
        )
        db_session.commit()

        result = db_session.execute(text("""
            SELECT
              s.name AS service,
              COUNT(DISTINCT CASE WHEN t.is_eol = true THEN rs.name || '|' || rs.category END) AS eol_count
            FROM services s
            JOIN repository_services rsvc ON rsvc.service_id = s.service_id
            JOIN repository_stack rs ON rs.repo_id = rsvc.repo_id
            LEFT JOIN technologies t ON t.name = rs.name AND t.category = rs.category
            WHERE s.name = :service_name
            GROUP BY s.name
        """), {"service_name": service.name}).fetchone()

        assert result is not None
        assert result.eol_count >= 1

    def test_top_non_language_entries_across_service(self, db_session):
        """Panel: Bar chart — top 10 non-language entries across selected services."""
        repo, service = self._setup_service_repo(
            db_session, "svc-bar-test", "org/svc-bar-repo", "svc-bar-repo"
        )
        detection = _make_detection(
            frameworks=["FastAPI"],
            databases=["Redis"],
            ci_cd_platforms=["GitHub Actions"],
        )
        store_detections(db_session, repo.repo_id, detection)
        db_session.commit()

        result = db_session.execute(text("""
            SELECT rs.name, COUNT(DISTINCT rs.repo_id) AS repo_count
            FROM repository_stack rs
            JOIN repository_services rsvc ON rsvc.repo_id = rs.repo_id
            JOIN services s ON s.service_id = rsvc.service_id
            WHERE rs.category != 'language'
              AND s.name = :service_name
            GROUP BY rs.name
            ORDER BY repo_count DESC
            LIMIT 10
        """), {"service_name": service.name}).fetchall()

        assert len(result) >= 3
        names = [r.name for r in result]
        assert "FastAPI" in names
        assert "Redis" in names
        assert "GitHub Actions" in names

    def test_service_deduplication(self, db_session):
        """Service with multiple repos using same tech counts once per service."""
        service_name = "svc-dedup-test"
        org_data = sample_organization_data(name="org-dedup")
        org = store_organization(db_session, org_data)
        project = store_project(db_session, org, "proj-dedup", "Test Project")
        service = get_or_create_service(db_session, service_name)

        for i in range(2):
            repo_data = sample_repository_data(
                repo_id=f"org/dedup-repo-{i}", name=f"dedup-repo-{i}"
            )
            repo = store_repository(db_session, project, repo_data)
            link = RepositoryService(
                repo_id=repo.repo_id,
                service_id=service.service_id,
                linked_at=datetime.now(UTC),
            )
            db_session.add(link)
            db_session.flush()

            detection = _make_detection(frameworks=["Django"])
            store_detections(db_session, repo.repo_id, detection)

        db_session.commit()

        result = db_session.execute(text("""
            SELECT rs.name, COUNT(DISTINCT rs.repo_id) AS repo_count
            FROM repository_stack rs
            JOIN repository_services rsvc ON rsvc.repo_id = rs.repo_id
            JOIN services s ON s.service_id = rsvc.service_id
            WHERE rs.category != 'language'
              AND s.name = :service_name
            GROUP BY rs.name
            ORDER BY repo_count DESC
            LIMIT 10
        """), {"service_name": service_name}).fetchone()

        assert result is not None
        assert result.name == "Django"
        assert result.repo_count == 2


# =============================================================================
# Repository Deep-Dive — Technologies section queries (R2)
# =============================================================================

@pytest.mark.integration
class TestRepoDeepDiveTechQueries:
    """SQL queries backing the repository-deep-dive Technologies panel."""

    def test_non_language_stack_entries_with_eol(self, db_session):
        """Technologies panel: non-language stack entries with EOL status."""
        repo = _setup_repo(db_session, repo_id="org/rddt-repo", name="rddt-repo")
        detection = _make_detection(
            frameworks=["Django"],
            databases=["PostgreSQL"],
            ci_cd_platforms=["GitHub Actions"],
        )
        store_detections(db_session, repo.repo_id, detection)
        store_technology_eol(
            db_session,
            name="Django",
            category="framework",
            is_eol=False,
            eol_date=None,
            latest_supported_version="4.2",
        )
        db_session.commit()

        result = db_session.execute(text("""
            SELECT
              rs.category,
              rs.name,
              rs.source,
              COALESCE(t.is_eol, false) AS is_eol,
              to_char(t.eol_date, 'YYYY-MM-DD') AS eol_date,
              t.latest_supported_version
            FROM repository_stack rs
            LEFT JOIN technologies t ON t.name = rs.name AND t.category = rs.category
            WHERE rs.repo_id = :repo_id
              AND rs.category != 'language'
            ORDER BY rs.category, rs.name
        """), {"repo_id": repo.repo_id}).fetchall()

        assert len(result) >= 3
        categories = {r.category for r in result}
        assert "framework" in categories
        assert "database" in categories
        assert "ci_cd" in categories

        django_row = next((r for r in result if r.name == "Django"), None)
        assert django_row is not None
        assert django_row.is_eol is False
        assert django_row.latest_supported_version == "4.2"

    def test_language_panel_still_uses_repository_stack(self, db_session):
        """Language Distribution panel: data comes from repository_stack, category='language'."""
        repo = _setup_repo(db_session, repo_id="org/rddt-lang-repo", name="rddt-lang-repo")
        langs = [
            LanguageData(language="TypeScript", byte_count=9000, percentage=90.0),
            LanguageData(language="CSS", byte_count=1000, percentage=10.0),
        ]
        store_languages(db_session, repo.repo_id, langs)
        db_session.commit()

        result = db_session.execute(text("""
            SELECT name AS language, percentage
            FROM repository_stack
            WHERE repo_id = :repo_id
              AND category = 'language'
            ORDER BY percentage DESC
        """), {"repo_id": repo.repo_id}).fetchall()

        assert len(result) == 2
        assert result[0].language == "TypeScript"
        assert float(result[0].percentage) == 90.0

    def test_eol_technology_highlighted_in_technologies_panel(self, db_session):
        """Technologies panel: EOL technology is flagged is_eol=true."""
        repo = _setup_repo(db_session, repo_id="org/rddt-eol-repo", name="rddt-eol-repo")
        detection = _make_detection(frameworks=["ASP.NET"])
        store_detections(db_session, repo.repo_id, detection)
        store_technology_eol(
            db_session,
            name="ASP.NET",
            category="framework",
            is_eol=True,
            eol_date=date(2022, 4, 26),
            latest_supported_version=None,
        )
        db_session.commit()

        results = db_session.execute(text("""
            SELECT
              rs.name,
              COALESCE(t.is_eol, false) AS is_eol,
              to_char(t.eol_date, 'YYYY-MM-DD') AS eol_date
            FROM repository_stack rs
            LEFT JOIN technologies t ON t.name = rs.name AND t.category = rs.category
            WHERE rs.repo_id = :repo_id
              AND rs.category = 'framework'
            ORDER BY rs.name
        """), {"repo_id": repo.repo_id}).fetchall()

        assert len(results) == 1
        result = results[0]
        assert result.name == "ASP.NET"
        assert result.is_eol is True
        assert result.eol_date == "2022-04-26"
