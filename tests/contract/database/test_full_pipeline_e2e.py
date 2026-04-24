"""
Full Pipeline E2E Tests: Generated Data → Extraction → Enrichment → Dashboard Views

CONTRACT: Fixture scenarios correctly flow through the full extraction and storage
pipeline, and Grafana dashboard views return correct, non-trivial results.

Tests exercise three layers end-to-end without any live API credentials:
1. Extraction pipeline  – FixtureExtractor → store_* functions
2. Dependency pipeline  – FixtureExtractor → DependencyAnalyzer → store_dependencies
3. Dashboard contracts  – shared multi-scenario dataset → all key reporting views

Runs in CI under `-m 'not live_api'` (the standard test-runner command).
"""

import pytest
from datetime import datetime, timezone, timedelta, date
from sqlalchemy import text

from tests.fixtures.fixture_extractor import FixtureExtractor
from tests.fixtures.sample_data import sample_organization_data, sample_repository_data
from src.database.storage import (
    store_organization,
    store_project,
    store_repository,
    store_branch,
    store_commit,
    store_pull_request,
    store_languages,
    store_dependencies,
    store_detections,
    store_package_metadata,
    store_repo_dependencies,
    store_technology_eol,
)
from src.analyzers.dependency_analyzer import DependencyAnalyzer
from src.analyzers.dependency_enricher import EnrichedDependency
from src.analyzers.technology_detector import TechnologyDetection
from src.database.models import Commit, PullRequest, RepositoryStack, RepositoryDependency
from src.extractors.base import Platform


# =============================================================================
# Helper
# =============================================================================

def _load_scenario(db_session, scenario_name: str):
    """
    Load a generated fixture scenario into the database.

    Creates org → project → repo, then stores all branches, commits,
    pull requests, and languages from the fixture JSON.  Returns the
    created Repository ORM instance.
    """
    extractor = FixtureExtractor(scenario_name)

    org_data = sample_organization_data(
        name=f"fixture-org-{scenario_name}",
        platform=Platform.GITHUB,
    )
    org = store_organization(db_session, org_data)

    project = store_project(db_session, org, name=f"project-{scenario_name}")

    repo_data = sample_repository_data(
        repo_id=f"fixture/{scenario_name}",
        name=scenario_name,
        url=f"https://example.com/{scenario_name}",
    )
    repo = store_repository(db_session, project, repo_data)
    db_session.flush()

    # Branches
    for branch in extractor.get_branches(repo.repo_id):
        store_branch(db_session, repo.repo_id, branch)
    db_session.flush()

    # Commits (stored against the first branch or "main")
    branches = extractor.get_branches(repo.repo_id)
    default_branch = branches[0].name if branches else "main"
    for commit in extractor.get_commits(repo.repo_id):
        store_commit(db_session, repo.repo_id, default_branch, commit)
    db_session.flush()

    # Pull requests
    for pr in extractor.get_pull_requests(repo.repo_id):
        store_pull_request(db_session, repo.repo_id, pr)
    db_session.flush()

    # Languages
    languages = extractor.get_languages(repo.repo_id)
    if languages:
        store_languages(db_session, repo.repo_id, languages)
        db_session.flush()

    # Technology stack (heuristic detections + EOL metadata from fixture)
    tech_stack = extractor.get_technology_stack()
    if tech_stack:
        detection = TechnologyDetection(
            programming_languages=[],
            frameworks=tech_stack.get("frameworks", []),
            databases=tech_stack.get("databases", []),
            deployment_platforms=tech_stack.get("deployment_platforms", []),
            build_tools=tech_stack.get("build_tools", []),
            testing_frameworks=tech_stack.get("testing_frameworks", []),
            ci_cd_platforms=tech_stack.get("ci_cd_platforms", []),
            documentation_tools=tech_stack.get("documentation_tools", []),
            language_confidence=tech_stack.get("confidence", 0.8),
            framework_confidence=tech_stack.get("confidence", 0.8),
            overall_confidence=tech_stack.get("confidence", 0.8),
            all_technologies=[],
            primary_language=None,
            analyzed_at=datetime.now(timezone.utc),
        )
        store_detections(db_session, repo.repo_id, detection)
        db_session.flush()

        for eol_entry in tech_stack.get("eol_technologies", []):
            raw_eol_date = eol_entry.get("eol_date")
            eol_date = date.fromisoformat(raw_eol_date) if raw_eol_date else None
            store_technology_eol(
                db_session,
                name=eol_entry["name"],
                category=eol_entry["category"],
                is_eol=eol_entry.get("is_eol", False),
                eol_date=eol_date,
                latest_supported_version=eol_entry.get("latest_supported_version"),
            )
        db_session.flush()

    db_session.commit()
    return repo


# =============================================================================
# 1. Extraction Pipeline E2E
# =============================================================================

EXTRACTION_SCENARIOS = [
    "go-microservice",
    "python-docker-billing",
    "fullstack-monorepo",
    "dual-ci-analytics",
    "java-maven-jenkins",
    "empty-stub",
]


@pytest.mark.integration
class TestExtractionPipelineE2E:
    """
    CONTRACT: FixtureExtractor data flows correctly through store_* functions
    and is reflected accurately in repository-level reporting views.
    """

    @pytest.mark.parametrize("scenario_name", EXTRACTION_SCENARIOS)
    def test_commits_stored_match_fixture(self, scenario_name, db_session):
        """Stored commit count equals the fixture commit count."""
        extractor = FixtureExtractor(scenario_name)
        repo = _load_scenario(db_session, scenario_name)

        expected = len(extractor.get_commits(repo.repo_id))
        stored = db_session.query(Commit).filter_by(repo_id=repo.repo_id).count()
        assert stored == expected, (
            f"{scenario_name}: expected {expected} commits stored, got {stored}"
        )

    @pytest.mark.parametrize("scenario_name", EXTRACTION_SCENARIOS)
    def test_pull_requests_stored_match_fixture(self, scenario_name, db_session):
        """Stored PR count equals the fixture PR count."""
        extractor = FixtureExtractor(scenario_name)
        repo = _load_scenario(db_session, scenario_name)

        expected = len(extractor.get_pull_requests(repo.repo_id))
        stored = db_session.query(PullRequest).filter_by(repo_id=repo.repo_id).count()
        assert stored == expected, (
            f"{scenario_name}: expected {expected} PRs stored, got {stored}"
        )

    @pytest.mark.parametrize("scenario_name", EXTRACTION_SCENARIOS)
    def test_languages_stored_match_fixture(self, scenario_name, db_session):
        """Stored language count equals the fixture language count."""
        extractor = FixtureExtractor(scenario_name)
        repo = _load_scenario(db_session, scenario_name)

        expected = len(extractor.get_languages(repo.repo_id))
        stored = (
            db_session.query(RepositoryStack).filter_by(
                repo_id=repo.repo_id, category="language"
            ).count()
        )
        assert stored == expected, (
            f"{scenario_name}: expected {expected} languages stored, got {stored}"
        )

    @pytest.mark.parametrize("scenario_name", EXTRACTION_SCENARIOS)
    def test_v_commits_total_reflects_stored_data(self, scenario_name, db_session):
        """v_commits_total count is at least the number of commits stored for this scenario."""
        extractor = FixtureExtractor(scenario_name)
        repo = _load_scenario(db_session, scenario_name)

        expected = len(extractor.get_commits(repo.repo_id))
        total = db_session.execute(text("SELECT total FROM v_commits_total")).scalar()
        assert total >= expected, (
            f"{scenario_name}: v_commits_total={total} < expected {expected}"
        )

    @pytest.mark.parametrize("scenario_name", EXTRACTION_SCENARIOS)
    def test_v_pull_requests_total_reflects_stored_data(self, scenario_name, db_session):
        """v_pull_requests_total count is at least the number of PRs stored for this scenario."""
        extractor = FixtureExtractor(scenario_name)
        repo = _load_scenario(db_session, scenario_name)

        expected = len(extractor.get_pull_requests(repo.repo_id))
        total = db_session.execute(text("SELECT total FROM v_pull_requests_total")).scalar()
        assert total >= expected, (
            f"{scenario_name}: v_pull_requests_total={total} < expected {expected}"
        )

    @pytest.mark.parametrize("scenario_name", EXTRACTION_SCENARIOS)
    def test_v_active_repositories_total_includes_scenario(self, scenario_name, db_session):
        """v_active_repositories_total increases by 1 after loading the scenario."""
        before = db_session.execute(
            text("SELECT total FROM v_active_repositories_total")
        ).scalar()

        _load_scenario(db_session, scenario_name)

        after = db_session.execute(
            text("SELECT total FROM v_active_repositories_total")
        ).scalar()
        assert after == before + 1, (
            f"{scenario_name}: expected active repos to go from {before} to {before + 1}, got {after}"
        )

    @pytest.mark.parametrize("scenario_name", EXTRACTION_SCENARIOS)
    def test_v_contributors_total_includes_scenario_contributors(
        self, scenario_name, db_session
    ):
        """v_contributors_total is at least 1 for non-empty scenarios, 0 for empty."""
        repo = _load_scenario(db_session, scenario_name)
        extractor = FixtureExtractor(scenario_name)
        expected_commits = len(extractor.get_commits(repo.repo_id))

        total = db_session.execute(
            text("SELECT total FROM v_contributors_total")
        ).scalar()
        if expected_commits > 0:
            assert total >= 1, (
                f"{scenario_name}: expected at least 1 contributor, got {total}"
            )
        else:
            assert total >= 0  # empty-stub may contribute 0 contributors

    @pytest.mark.parametrize("scenario_name", EXTRACTION_SCENARIOS)
    def test_v_repository_summary_row_exists(self, scenario_name, db_session):
        """v_repository_summary has a row for the loaded repository."""
        repo = _load_scenario(db_session, scenario_name)

        row = db_session.execute(
            text("SELECT total_commits, total_prs FROM v_repository_summary WHERE repo_id = :rid"),
            {"rid": repo.repo_id},
        ).fetchone()

        assert row is not None, (
            f"{scenario_name}: no row in v_repository_summary for {repo.repo_id}"
        )
        extractor = FixtureExtractor(scenario_name)
        assert row.total_commits == len(extractor.get_commits(repo.repo_id))
        assert row.total_prs == len(extractor.get_pull_requests(repo.repo_id))

    @pytest.mark.parametrize("scenario_name", EXTRACTION_SCENARIOS)
    def test_v_language_summary_matches_fixture(self, scenario_name, db_session):
        """v_language_summary rows for this repo match fixture languages."""
        extractor = FixtureExtractor(scenario_name)
        repo = _load_scenario(db_session, scenario_name)

        expected_langs = {ld.language for ld in extractor.get_languages(repo.repo_id)}
        rows = db_session.execute(
            text("SELECT language FROM v_language_summary WHERE repo_id = :rid"),
            {"rid": repo.repo_id},
        ).fetchall()
        stored_langs = {r.language for r in rows}
        assert stored_langs == expected_langs, (
            f"{scenario_name}: language mismatch. expected={expected_langs}, got={stored_langs}"
        )

    @pytest.mark.parametrize("scenario_name", EXTRACTION_SCENARIOS)
    def test_v_repository_overview_table_row_exists(self, scenario_name, db_session):
        """v_repository_overview_table has a row for the loaded repository."""
        repo = _load_scenario(db_session, scenario_name)

        row = db_session.execute(
            text(
                "SELECT repository, total_commits, total_prs "
                "FROM v_repository_overview_table WHERE repo_id = :rid"
            ),
            {"rid": repo.repo_id},
        ).fetchone()

        assert row is not None, (
            f"{scenario_name}: no row in v_repository_overview_table for {repo.repo_id}"
        )
        assert row.repository == scenario_name


# =============================================================================
# 2. Dependency Enrichment Pipeline E2E (fixture-based, no live APIs)
# =============================================================================

# Scenarios that have manifest files yielding parseable dependencies.
# All three use pypi/requirements.txt but are kept as separate entries because each
# exercises a distinct fixture file (different commit histories, PR distributions, and
# manifest content) — ensuring the full storage pipeline is verified for each.
DEPENDENCY_SCENARIOS = {
    "python-docker-billing": {"ecosystem": "pypi", "min_deps": 1},
    "dual-ci-analytics": {"ecosystem": "pypi", "min_deps": 1},
    "fullstack-monorepo": {"ecosystem": "pypi", "min_deps": 1},
}

def _enrich_from_fixture(session, repo_id: str, scenario_name: str) -> None:
    """
    Store package metadata + per-repo enriched dependencies from the scenario's
    fixture JSON (vulnerability_data field).

    Each entry in vulnerability_data is passed directly to store_package_metadata
    and store_repo_dependencies — no HTTP calls, no mocking.

    The eol_date field is stored as an ISO-8601 date string in JSON ('YYYY-MM-DD');
    it is parsed back to a date object before being stored.
    """
    packages = FixtureExtractor(scenario_name).get_vulnerability_data()

    enriched_deps = []
    for pkg_data in packages:
        raw_eol_date = pkg_data.get("eol_date")
        eol_date = date.fromisoformat(raw_eol_date) if raw_eol_date else None
        store_package_metadata(
            session,
            package_name=pkg_data["package_name"],
            ecosystem=pkg_data["ecosystem"],
            latest_version=pkg_data["latest_version"],
            is_eol=pkg_data["is_eol"],
            eol_date=eol_date,
            vulnerabilities=pkg_data["vulnerabilities"],
        )
        enriched_deps.append(
            EnrichedDependency(
                package_name=pkg_data["package_name"],
                version=pkg_data["pinned_version"],
                ecosystem=pkg_data["ecosystem"],
                is_dev_dependency=False,
                source_file="requirements.txt",
                version_constraint=None,
                has_known_vulnerabilities=len(pkg_data["vulnerabilities"]) > 0,
            )
        )
    store_repo_dependencies(session, repo_id, enriched_deps)
    session.commit()


@pytest.mark.integration
class TestDependencyEnrichmentPipelineE2E:
    """
    CONTRACT: DependencyAnalyzer + store_dependencies persist fixture manifest
    data into dependency views without requiring live external API credentials.
    """

    @pytest.mark.parametrize(
        "scenario_name,config",
        [(name, cfg) for name, cfg in DEPENDENCY_SCENARIOS.items()],
    )
    def test_dependencies_stored_and_viewable(self, scenario_name, config, db_session):
        """
        CONTRACT: After running DependencyAnalyzer over a fixture extractor,
        store_dependencies populates v_dependency_snapshot_latest for the repo.
        """
        repo = _load_scenario(db_session, scenario_name)
        extractor = FixtureExtractor(scenario_name)

        analyzer = DependencyAnalyzer(enrich=False)
        result = analyzer.analyze(extractor, repo.repo_id)

        assert result.total_dependencies >= config["min_deps"], (
            f"{scenario_name}: expected ≥{config['min_deps']} deps, "
            f"got {result.total_dependencies}"
        )
        assert config["ecosystem"] in result.ecosystems, (
            f"{scenario_name}: expected ecosystem '{config['ecosystem']}' in {result.ecosystems}"
        )

        store_dependencies(db_session, repo.repo_id, result.dependencies)
        db_session.commit()

        stored = (
            db_session.query(RepositoryDependency).filter_by(repo_id=repo.repo_id).count()
        )
        assert stored == result.total_dependencies, (
            f"{scenario_name}: stored {stored} deps, expected {result.total_dependencies}"
        )

    @pytest.mark.parametrize(
        "scenario_name,config",
        [(name, cfg) for name, cfg in DEPENDENCY_SCENARIOS.items()],
    )
    def test_v_dependency_snapshot_latest_populated(
        self, scenario_name, config, db_session
    ):
        """v_dependency_snapshot_latest returns rows for the repo after storing deps."""
        repo = _load_scenario(db_session, scenario_name)
        extractor = FixtureExtractor(scenario_name)

        analyzer = DependencyAnalyzer(enrich=False)
        result = analyzer.analyze(extractor, repo.repo_id)
        store_dependencies(db_session, repo.repo_id, result.dependencies)
        db_session.commit()

        rows = db_session.execute(
            text(
                "SELECT COUNT(*) AS cnt FROM v_dependency_snapshot_latest "
                "WHERE repo_id = :rid"
            ),
            {"rid": repo.repo_id},
        ).scalar()
        assert rows >= config["min_deps"], (
            f"{scenario_name}: v_dependency_snapshot_latest returned {rows} rows, "
            f"expected ≥{config['min_deps']}"
        )

    @pytest.mark.parametrize(
        "scenario_name,config",
        [(name, cfg) for name, cfg in DEPENDENCY_SCENARIOS.items()],
    )
    def test_v_repo_dependency_rollup_latest_counts(
        self, scenario_name, config, db_session
    ):
        """v_repo_dependency_rollup_latest total_dependencies matches stored count."""
        repo = _load_scenario(db_session, scenario_name)
        extractor = FixtureExtractor(scenario_name)

        analyzer = DependencyAnalyzer(enrich=False)
        result = analyzer.analyze(extractor, repo.repo_id)
        store_dependencies(db_session, repo.repo_id, result.dependencies)
        db_session.commit()

        row = db_session.execute(
            text(
                "SELECT total_dependencies FROM v_repo_dependency_rollup_latest "
                "WHERE repo_id = :rid"
            ),
            {"rid": repo.repo_id},
        ).fetchone()

        assert row is not None, (
            f"{scenario_name}: no row in v_repo_dependency_rollup_latest"
        )
        assert row.total_dependencies == result.total_dependencies

    @pytest.mark.parametrize(
        "scenario_name,config",
        [(name, cfg) for name, cfg in DEPENDENCY_SCENARIOS.items()],
    )
    def test_v_repo_dependency_ecosystems_latest_correct(
        self, scenario_name, config, db_session
    ):
        """v_repo_dependency_ecosystems_latest lists the expected ecosystem."""
        repo = _load_scenario(db_session, scenario_name)
        extractor = FixtureExtractor(scenario_name)

        analyzer = DependencyAnalyzer(enrich=False)
        result = analyzer.analyze(extractor, repo.repo_id)
        store_dependencies(db_session, repo.repo_id, result.dependencies)
        db_session.commit()

        rows = db_session.execute(
            text(
                "SELECT ecosystem FROM v_repo_dependency_ecosystems_latest "
                "WHERE repo_id = :rid"
            ),
            {"rid": repo.repo_id},
        ).fetchall()
        ecosystems = {r.ecosystem for r in rows}
        assert config["ecosystem"] in ecosystems, (
            f"{scenario_name}: expected '{config['ecosystem']}' in {ecosystems}"
        )



# =============================================================================
# 3. Security Enrichment Contracts (synthetic data, no external API calls)
# =============================================================================


@pytest.mark.integration
class TestSecurityEnrichmentContractsE2E:
    """
    CONTRACT: Security dashboard views return correct non-zero results after
    storing synthetic enrichment data via store_package_metadata +
    store_repo_dependencies.

    All tests are CI-safe — no external network calls are made.
    """

    def test_v_security_overview_latest_non_zero_after_enrichment(self, db_session):
        """
        CONTRACT: v_security_overview_latest reflects stored vulnerability and EOL data.
        """
        repo = _load_scenario(db_session, "python-docker-billing")
        _enrich_from_fixture(db_session, repo.repo_id, "python-docker-billing")

        row = db_session.execute(
            text(
                "SELECT total_vulnerabilities, total_eol_deps, "
                "repos_with_vulns, repos_with_eol "
                "FROM v_security_overview_latest"
            )
        ).fetchone()

        assert row is not None
        assert row.total_vulnerabilities >= 2, (
            f"expected >= 2 vulnerabilities, got {row.total_vulnerabilities}"
        )
        assert row.total_eol_deps >= 1, (
            f"expected >= 1 EOL dep (certifi), got {row.total_eol_deps}"
        )
        assert row.repos_with_vulns >= 1, (
            f"expected >= 1 repo with vulns, got {row.repos_with_vulns}"
        )
        assert row.repos_with_eol >= 1, (
            f"expected >= 1 repo with EOL deps, got {row.repos_with_eol}"
        )

    def test_v_security_repository_overview_per_repo_vuln_counts(self, db_session):
        """
        CONTRACT: v_security_repository_overview has correct severity breakdown for the enriched repo.
        """
        repo = _load_scenario(db_session, "python-docker-billing")
        _enrich_from_fixture(db_session, repo.repo_id, "python-docker-billing")

        row = db_session.execute(
            text(
                "SELECT critical_vulns, high_vulns, eol_deps "
                "FROM v_security_repository_overview "
                "WHERE repo_id = :rid"
            ),
            {"rid": repo.repo_id},
        ).fetchone()

        assert row is not None, "no row in v_security_repository_overview for enriched repo"
        assert row.critical_vulns >= 1, (
            f"expected >= 1 CRITICAL vuln (urllib3), got {row.critical_vulns}"
        )
        assert row.high_vulns >= 1, (
            f"expected >= 1 HIGH vuln (requests), got {row.high_vulns}"
        )
        assert row.eol_deps >= 1, (
            f"expected >= 1 EOL dep (certifi), got {row.eol_deps}"
        )

    def test_v_repo_dependency_rollup_latest_vulnerabilities_counted(self, db_session):
        """
        CONTRACT: v_repo_dependency_rollup_latest.vulnerabilities > 0 for the enriched repo.
        Also verifies outdated_dependencies and eol_dependencies are counted.
        """
        repo = _load_scenario(db_session, "python-docker-billing")
        _enrich_from_fixture(db_session, repo.repo_id, "python-docker-billing")

        row = db_session.execute(
            text(
                "SELECT vulnerabilities, outdated_dependencies, eol_dependencies "
                "FROM v_repo_dependency_rollup_latest "
                "WHERE repo_id = :rid"
            ),
            {"rid": repo.repo_id},
        ).fetchone()

        assert row is not None, "no row in v_repo_dependency_rollup_latest for enriched repo"
        assert row.vulnerabilities >= 2, (
            f"expected >= 2 vulnerabilities, got {row.vulnerabilities}"
        )
        assert row.outdated_dependencies >= 2, (
            f"expected >= 2 outdated deps (requests + urllib3), got {row.outdated_dependencies}"
        )
        assert row.eol_dependencies >= 1, (
            f"expected >= 1 EOL dep (certifi), got {row.eol_dependencies}"
        )

    def test_v_security_top_vulnerable_dependencies_contains_urllib3(self, db_session):
        """
        CONTRACT: v_security_top_vulnerable_dependencies lists the most severe package.
        urllib3 must appear with severity = 'CRITICAL'.
        """
        repo = _load_scenario(db_session, "python-docker-billing")
        _enrich_from_fixture(db_session, repo.repo_id, "python-docker-billing")

        rows = db_session.execute(
            text("SELECT package_name, severity FROM v_security_top_vulnerable_dependencies")
        ).fetchall()

        package_names = [r.package_name for r in rows]
        assert "urllib3" in package_names, (
            f"urllib3 not found in v_security_top_vulnerable_dependencies: {package_names}"
        )

        urllib3_row = next(r for r in rows if r.package_name == "urllib3")
        assert urllib3_row.severity == "CRITICAL", (
            f"expected urllib3 severity='CRITICAL', got '{urllib3_row.severity}'"
        )

    def test_v_repo_vulnerability_details_latest_has_cve_ids(self, db_session):
        """
        CONTRACT: v_repo_vulnerability_details_latest returns CVE IDs for the enriched repo.
        """
        repo = _load_scenario(db_session, "python-docker-billing")
        _enrich_from_fixture(db_session, repo.repo_id, "python-docker-billing")

        rows = db_session.execute(
            text(
                "SELECT cve_id FROM v_repo_vulnerability_details_latest "
                "WHERE repo_id = :rid"
            ),
            {"rid": repo.repo_id},
        ).fetchall()

        cve_ids = {r.cve_id for r in rows}
        assert "CVE-2018-18074" in cve_ids, (
            f"CVE-2018-18074 (requests) not found in v_repo_vulnerability_details_latest: {cve_ids}"
        )
        assert "CVE-2021-33503" in cve_ids, (
            f"CVE-2021-33503 (urllib3) not found in v_repo_vulnerability_details_latest: {cve_ids}"
        )

    def test_v_security_eol_status_latest_shows_expired(self, db_session):
        """
        CONTRACT: v_security_eol_status_latest shows certifi as 'Expired'.
        """
        repo = _load_scenario(db_session, "python-docker-billing")
        _enrich_from_fixture(db_session, repo.repo_id, "python-docker-billing")

        rows = db_session.execute(
            text("SELECT category, count FROM v_security_eol_status_latest")
        ).fetchall()

        categories = {r.category: r.count for r in rows}
        assert "Expired" in categories, (
            f"'Expired' category not found in v_security_eol_status_latest: {list(categories.keys())}"
        )
        assert categories["Expired"] >= 1, (
            f"expected >= 1 Expired dep, got {categories['Expired']}"
        )

    def test_v_repo_vulnerabilities_by_severity_latest_correct_severities(self, db_session):
        """
        CONTRACT: v_repo_vulnerabilities_by_severity_latest lists CRITICAL and HIGH for the enriched repo.
        """
        repo = _load_scenario(db_session, "python-docker-billing")
        _enrich_from_fixture(db_session, repo.repo_id, "python-docker-billing")

        rows = db_session.execute(
            text(
                "SELECT severity FROM v_repo_vulnerabilities_by_severity_latest "
                "WHERE repo_id = :rid"
            ),
            {"rid": repo.repo_id},
        ).fetchall()

        severities = {r.severity for r in rows}
        assert "CRITICAL" in severities, (
            f"'CRITICAL' not found in v_repo_vulnerabilities_by_severity_latest: {severities}"
        )
        assert "HIGH" in severities, (
            f"'HIGH' not found in v_repo_vulnerabilities_by_severity_latest: {severities}"
        )

    # ---- Multi-severity parametrized tests ----------------------------------------

    # Scenarios and the specific severity levels expected in each repo's profile.
    # python-docker → CRITICAL + HIGH + EOL
    # dual-ci       → HIGH + MEDIUM
    # fullstack     → MEDIUM + LOW
    _SEVERITY_SCENARIOS = [
        ("python-docker-billing", {"CRITICAL", "HIGH"}),
        ("dual-ci-analytics",     {"HIGH", "MEDIUM"}),
        ("fullstack-monorepo",    {"MEDIUM", "LOW"}),
    ]

    @pytest.mark.parametrize("scenario_name,expected_severities", _SEVERITY_SCENARIOS)
    def test_per_repo_severity_profile_from_fixture(
        self, scenario_name, expected_severities, db_session
    ):
        """
        CONTRACT: v_repo_vulnerabilities_by_severity_latest contains the expected
        severity levels for each fixture-enriched scenario.

        Covers all four severity tiers across three scenarios:
          python-docker-billing → CRITICAL + HIGH
          dual-ci-analytics     → HIGH + MEDIUM
          fullstack-monorepo    → MEDIUM + LOW
        """
        repo = _load_scenario(db_session, scenario_name)
        _enrich_from_fixture(db_session, repo.repo_id, scenario_name)

        rows = db_session.execute(
            text(
                "SELECT severity FROM v_repo_vulnerabilities_by_severity_latest "
                "WHERE repo_id = :rid"
            ),
            {"rid": repo.repo_id},
        ).fetchall()
        actual_severities = {r.severity for r in rows}

        for sev in expected_severities:
            assert sev in actual_severities, (
                f"{scenario_name}: expected severity '{sev}' in "
                f"v_repo_vulnerabilities_by_severity_latest, got {actual_severities}"
            )

    def test_all_four_severities_represented_across_enriched_repos(self, db_session):
        """
        CONTRACT: When multiple repos with different vulnerability profiles are enriched,
        v_security_vulnerabilities_by_severity_latest shows all four severity levels.

        python-docker-billing → CRITICAL + HIGH
        dual-ci-analytics     → HIGH + MEDIUM
        fullstack-monorepo    → MEDIUM + LOW
        Combined              → CRITICAL + HIGH + MEDIUM + LOW
        """
        for scenario_name in [
            "python-docker-billing",
            "dual-ci-analytics",
            "fullstack-monorepo",
        ]:
            repo = _load_scenario(db_session, scenario_name)
            _enrich_from_fixture(db_session, repo.repo_id, scenario_name)

        rows = db_session.execute(
            text("SELECT DISTINCT severity FROM v_security_vulnerabilities_by_severity_latest")
        ).fetchall()
        severities = {r.severity for r in rows}

        for expected in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
            assert expected in severities, (
                f"Severity '{expected}' missing from v_security_vulnerabilities_by_severity_latest "
                f"after enriching python-docker-billing + dual-ci-analytics + fullstack-monorepo. "
                f"Got: {severities}"
            )


# =============================================================================
# 4. Dashboard View Contracts (shared multi-scenario dataset)
# =============================================================================

# Scenarios that collectively cover all three PR statuses and multiple languages
DASHBOARD_SCENARIOS = [
    "go-microservice",        # Go, open + merged PRs
    "python-docker-billing",  # Python, merged PRs
    "fullstack-monorepo",     # Python + TypeScript, mixed PR statuses
    "dual-ci-analytics",      # Python, open + merged PRs
    "java-maven-jenkins",     # Java, open + merged PRs
]


@pytest.fixture()
def full_dataset(db_session):
    """
    Shared fixture: loads DASHBOARD_SCENARIOS into the database and returns
    a mapping of scenario_name → Repository.
    """
    repos = {}
    for scenario_name in DASHBOARD_SCENARIOS:
        repos[scenario_name] = _load_scenario(db_session, scenario_name)
    return repos


@pytest.mark.integration
class TestDashboardViewContracts:
    """
    CONTRACT: Grafana dashboard views return correct, non-trivial results after
    loading a representative multi-scenario dataset.

    Each test asserts:
      (a) the view is queryable without SQL errors, and
      (b) the returned values are internally consistent with the input data.
    """

    # ---- Repository Overview dashboard ----------------------------------------

    def test_repository_overview_totals(self, full_dataset, db_session):
        """v_active_repositories_total, v_commits_total, v_pull_requests_total."""
        expected_repos = len(DASHBOARD_SCENARIOS)
        # FixtureExtractor.get_commits/get_pull_requests ignores repo_id; use the
        # scenario name as a self-documenting placeholder.
        expected_commits = sum(
            len(FixtureExtractor(s).get_commits(f"fixture/{s}"))
            for s in DASHBOARD_SCENARIOS
        )
        expected_prs = sum(
            len(FixtureExtractor(s).get_pull_requests(f"fixture/{s}"))
            for s in DASHBOARD_SCENARIOS
        )

        active = db_session.execute(
            text("SELECT total FROM v_active_repositories_total")
        ).scalar()
        total_commits = db_session.execute(
            text("SELECT total FROM v_commits_total")
        ).scalar()
        total_prs = db_session.execute(
            text("SELECT total FROM v_pull_requests_total")
        ).scalar()

        assert active == expected_repos
        assert total_commits == expected_commits
        assert total_prs == expected_prs

    def test_v_contributors_total_positive(self, full_dataset, db_session):
        """v_contributors_total > 0 after loading non-empty scenarios."""
        total = db_session.execute(
            text("SELECT total FROM v_contributors_total")
        ).scalar()
        assert total > 0

    def test_v_repository_overview_table_all_repos_present(
        self, full_dataset, db_session
    ):
        """v_repository_overview_table has a row for every loaded repository."""
        rows = db_session.execute(
            text("SELECT repo_id FROM v_repository_overview_table")
        ).fetchall()
        stored_ids = {r.repo_id for r in rows}
        for repo in full_dataset.values():
            assert repo.repo_id in stored_ids, (
                f"{repo.repo_id} missing from v_repository_overview_table"
            )

    def test_v_top_repositories_by_commits_30d_queryable(self, full_dataset, db_session):
        """v_top_repositories_by_commits_30d runs without error."""
        rows = db_session.execute(
            text("SELECT repo_id, repository, commits FROM v_top_repositories_by_commits_30d")
        ).fetchall()
        # Result may be empty (all commits older than 30 days) — that's fine.
        # The view must be queryable without error.
        assert rows is not None

    # ---- Pull Requests dashboard -----------------------------------------------

    def test_v_pr_status_distribution_covers_open_and_merged(
        self, full_dataset, db_session
    ):
        """
        v_pr_status_distribution includes at least 'open' and 'merged' statuses
        across all loaded scenarios.
        """
        rows = db_session.execute(
            text("SELECT status, count FROM v_pr_status_distribution")
        ).fetchall()
        statuses = {r.status for r in rows}
        assert "open" in statuses, f"Expected 'open' in {statuses}"
        assert "merged" in statuses, f"Expected 'merged' in {statuses}"

    def test_v_pr_status_distribution_sum_equals_total(self, full_dataset, db_session):
        """Sum of all PR status counts equals v_pull_requests_total."""
        total_prs = db_session.execute(
            text("SELECT total FROM v_pull_requests_total")
        ).scalar()
        distribution_sum = db_session.execute(
            text(
                "SELECT COALESCE(SUM(count), 0) AS s "
                "FROM v_pr_status_distribution"
            )
        ).scalar()
        assert distribution_sum == total_prs

    def test_v_pr_avg_changes_30d_queryable(self, full_dataset, db_session):
        """v_pr_avg_changes_30d returns a non-negative integer."""
        avg = db_session.execute(
            text("SELECT avg_changes FROM v_pr_avg_changes_30d")
        ).scalar()
        assert avg is not None
        assert avg >= 0

    def test_v_pr_size_distribution_30d_queryable(self, full_dataset, db_session):
        """v_pr_size_distribution_30d runs without error."""
        rows = db_session.execute(
            text("SELECT size_category, count FROM v_pr_size_distribution_30d")
        ).fetchall()
        assert rows is not None

    def test_v_pr_recent_details_queryable(self, full_dataset, db_session):
        """v_pr_recent_details runs without error."""
        rows = db_session.execute(
            text("SELECT repo_id, pr_number, status FROM v_pr_recent_details LIMIT 20")
        ).fetchall()
        assert rows is not None

    # ---- Contributor Analytics dashboard ----------------------------------------

    def test_v_active_contributors_30d_total_queryable(self, full_dataset, db_session):
        """v_active_contributors_30d_total returns a non-negative integer."""
        val = db_session.execute(
            text("SELECT contributors FROM v_active_contributors_30d_total")
        ).scalar()
        assert val is not None
        assert val >= 0

    def test_v_top_contributors_30d_queryable(self, full_dataset, db_session):
        """v_top_contributors_30d runs without error."""
        rows = db_session.execute(
            text("SELECT contributor, commits FROM v_top_contributors_30d")
        ).fetchall()
        assert rows is not None

    def test_v_contributor_activity_30d_queryable(self, full_dataset, db_session):
        """v_contributor_activity_30d runs without error."""
        rows = db_session.execute(
            text(
                "SELECT contributor, commits, lines_added, lines_removed "
                "FROM v_contributor_activity_30d"
            )
        ).fetchall()
        assert rows is not None

    # ---- Repository Deep Dive dashboard -----------------------------------------

    def test_v_repository_summary_per_repo(self, full_dataset, db_session):
        """v_repository_summary row per repo has correct commit and PR counts."""
        for scenario_name, repo in full_dataset.items():
            extractor = FixtureExtractor(scenario_name)
            expected_commits = len(extractor.get_commits(repo.repo_id))
            expected_prs = len(extractor.get_pull_requests(repo.repo_id))

            row = db_session.execute(
                text(
                    "SELECT total_commits, total_prs "
                    "FROM v_repository_summary WHERE repo_id = :rid"
                ),
                {"rid": repo.repo_id},
            ).fetchone()

            assert row is not None, f"No row in v_repository_summary for {repo.repo_id}"
            assert row.total_commits == expected_commits, (
                f"{scenario_name}: v_repository_summary.total_commits="
                f"{row.total_commits}, expected {expected_commits}"
            )
            assert row.total_prs == expected_prs, (
                f"{scenario_name}: v_repository_summary.total_prs="
                f"{row.total_prs}, expected {expected_prs}"
            )

    def test_v_repo_language_distribution_latest_correct(
        self, full_dataset, db_session
    ):
        """v_repo_language_distribution_latest has expected languages per repo."""
        for scenario_name, repo in full_dataset.items():
            extractor = FixtureExtractor(scenario_name)
            expected_langs = {
                ld.language for ld in extractor.get_languages(repo.repo_id)
            }

            rows = db_session.execute(
                text(
                    "SELECT language FROM v_repo_language_distribution_latest "
                    "WHERE repo_id = :rid"
                ),
                {"rid": repo.repo_id},
            ).fetchall()
            stored_langs = {r.language for r in rows}
            assert stored_langs == expected_langs, (
                f"{scenario_name}: language mismatch "
                f"expected={expected_langs}, got={stored_langs}"
            )

    def test_v_repo_recent_commits_queryable(self, full_dataset, db_session):
        """v_repo_recent_commits has rows for repos that have commits."""
        for scenario_name, repo in full_dataset.items():
            extractor = FixtureExtractor(scenario_name)
            expected_count = len(extractor.get_commits(repo.repo_id))
            if expected_count == 0:
                continue

            rows = db_session.execute(
                text(
                    "SELECT sha, author, message FROM v_repo_recent_commits "
                    "WHERE repo_id = :rid LIMIT 50"
                ),
                {"rid": repo.repo_id},
            ).fetchall()
            assert len(rows) == expected_count, (
                f"{scenario_name}: v_repo_recent_commits returned {len(rows)}, "
                f"expected {expected_count}"
            )

    def test_v_repo_recent_prs_queryable(self, full_dataset, db_session):
        """v_repo_recent_prs has rows for repos that have PRs."""
        for scenario_name, repo in full_dataset.items():
            extractor = FixtureExtractor(scenario_name)
            expected_count = len(extractor.get_pull_requests(repo.repo_id))
            if expected_count == 0:
                continue

            rows = db_session.execute(
                text(
                    "SELECT pr_number, title, status FROM v_repo_recent_prs "
                    "WHERE repo_id = :rid LIMIT 50"
                ),
                {"rid": repo.repo_id},
            ).fetchall()
            assert len(rows) == expected_count, (
                f"{scenario_name}: v_repo_recent_prs returned {len(rows)}, "
                f"expected {expected_count}"
            )

    def test_v_repo_pr_health_summary_queryable(self, full_dataset, db_session):
        """v_repo_pr_health_summary has a row for every repo that has PRs."""
        for scenario_name, repo in full_dataset.items():
            extractor = FixtureExtractor(scenario_name)
            if len(extractor.get_pull_requests(repo.repo_id)) == 0:
                continue

            row = db_session.execute(
                text(
                    "SELECT days_to_merge, avg_comments "
                    "FROM v_repo_pr_health_summary WHERE repo_id = :rid"
                ),
                {"rid": repo.repo_id},
            ).fetchone()
            assert row is not None, (
                f"{scenario_name}: no row in v_repo_pr_health_summary for {repo.repo_id}"
            )

    # ---- Security Dashboard ------------------------------------------------------

    def test_v_security_overview_latest_queryable_and_structured(
        self, full_dataset, db_session
    ):
        """
        v_security_overview_latest is queryable and returns the expected columns.
        No enrichment is done, so vulnerabilities = 0 is expected.
        """
        # This test verifies the view is queryable when no enrichment has been run.
        # For non-zero enrichment coverage see TestSecurityEnrichmentContractsE2E.
        row = db_session.execute(
            text(
                "SELECT total_vulnerabilities, total_eol_deps, "
                "repos_with_vulns, repos_with_eol "
                "FROM v_security_overview_latest"
            )
        ).fetchone()

        assert row is not None
        # No enrichment was performed, so all should be 0
        assert row.total_vulnerabilities == 0
        assert row.total_eol_deps == 0
        assert row.repos_with_vulns == 0
        assert row.repos_with_eol == 0

    # ---- Home Dashboard ----------------------------------------------------------

    def test_v_commits_30d_total_queryable(self, full_dataset, db_session):
        """v_commits_30d_total returns a non-negative integer."""
        val = db_session.execute(
            text("SELECT commits FROM v_commits_30d_total")
        ).scalar()
        assert val is not None
        assert val >= 0

    def test_v_stale_repositories_queryable(self, full_dataset, db_session):
        """
        v_stale_repositories runs without error.

        Freshly stored repos have last_analyzed_at=NULL so they appear in
        v_unanalyzed_repositories, not v_stale_repositories.  The view
        may be empty — that is valid behaviour.
        """
        rows = db_session.execute(
            text("SELECT repo_id, name FROM v_stale_repositories")
        ).fetchall()
        assert rows is not None

    def test_v_unanalyzed_repositories_contains_loaded_repos(
        self, full_dataset, db_session
    ):
        """
        Freshly loaded repos have last_analyzed_at=NULL, so they appear in
        v_unanalyzed_repositories.
        """
        rows = db_session.execute(
            text("SELECT repo_id FROM v_unanalyzed_repositories")
        ).fetchall()
        unanalyzed_ids = {r.repo_id for r in rows}

        for scenario_name, repo in full_dataset.items():
            assert repo.repo_id in unanalyzed_ids, (
                f"{scenario_name}: {repo.repo_id} not in v_unanalyzed_repositories "
                f"(last_analyzed_at should be NULL for a freshly loaded repo)"
            )


# =============================================================================
# 4. 30-day Contributor Filtering Regression
# =============================================================================


def _make_dated_scenario(now: datetime) -> dict:
    """
    Build an inline scenario dict with three contributors and controlled dates:

      alice@example.com  – one commit 730 days ago  + one commit 10 days ago  (recent)
      bob@example.com    – one commit 720 days ago only                        (historical)
      carol@example.com  – one commit 5 days ago only                          (recent)

    This lets tests assert that only Alice and Carol appear in the 30-day views
    and that Bob — who has genuine historical activity — is correctly excluded.

    Returns:
        dict with keys 'branches', 'languages', 'file_names', 'pull_requests',
        and 'commits' suitable for passing directly to FixtureExtractor.
    """

    def _iso(dt: datetime) -> str:
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "branches": ["main"],
        "languages": [],
        "file_names": [],
        "pull_requests": [],
        "commits": [
            {
                "commit_hash": "aa0001",
                "author_name": "Alice",
                "author_email": "alice@example.com",
                "committer_name": "Alice",
                "committer_email": "alice@example.com",
                "message": "Alice old commit",
                "commit_date": _iso(now - timedelta(days=730)),
                "files_changed": 1,
                "lines_added": 10,
                "lines_removed": 2,
            },
            {
                "commit_hash": "aa0002",
                "author_name": "Alice",
                "author_email": "alice@example.com",
                "committer_name": "Alice",
                "committer_email": "alice@example.com",
                "message": "Alice recent commit",
                "commit_date": _iso(now - timedelta(days=10)),
                "files_changed": 2,
                "lines_added": 20,
                "lines_removed": 5,
            },
            {
                "commit_hash": "bb0001",
                "author_name": "Bob",
                "author_email": "bob@example.com",
                "committer_name": "Bob",
                "committer_email": "bob@example.com",
                "message": "Bob old commit",
                "commit_date": _iso(now - timedelta(days=720)),
                "files_changed": 3,
                "lines_added": 30,
                "lines_removed": 10,
            },
            {
                "commit_hash": "cc0001",
                "author_name": "Carol",
                "author_email": "carol@example.com",
                "committer_name": "Carol",
                "committer_email": "carol@example.com",
                "message": "Carol recent commit",
                "commit_date": _iso(now - timedelta(days=5)),
                "files_changed": 1,
                "lines_added": 5,
                "lines_removed": 1,
            },
        ],
    }


@pytest.fixture()
def contributor_filtering_repo(db_session):
    """
    Load a single repository containing three contributors with controlled commit
    dates into the test database.  See _make_dated_scenario for the full layout.
    """
    now = datetime.now(timezone.utc)
    scenario = _make_dated_scenario(now)

    extractor = FixtureExtractor(scenario)

    org = store_organization(
        db_session,
        sample_organization_data(name="30d-filter-org", platform=Platform.GITHUB),
    )
    project = store_project(db_session, org, name="30d-filter-project")
    repo = store_repository(
        db_session,
        project,
        sample_repository_data(
            repo_id="fixture/30d-filter-test",
            name="30d-filter-test",
            url="https://example.com/30d-filter-test",
        ),
    )
    db_session.flush()

    for branch in extractor.get_branches(repo.repo_id):
        store_branch(db_session, repo.repo_id, branch)
    db_session.flush()

    for commit in extractor.get_commits(repo.repo_id):
        store_commit(db_session, repo.repo_id, "main", commit)
    db_session.flush()

    db_session.commit()
    return repo


@pytest.mark.integration
class TestContributor30dFiltering:
    """
    Regression suite for the bug where repositories with years of history showed
    historical-only contributors as having commits in the last 30 days.

    Each test loads a repo with three contributors (Alice: old + recent commits,
    Bob: old commits only, Carol: recent commits only) and verifies that the
    30-day reporting views surface only Alice and Carol.
    """

    def test_v_top_contributors_30d_excludes_stale_contributors(
        self, contributor_filtering_repo, db_session
    ):
        """
        v_top_contributors_30d must not include contributors whose most recent
        commit predates the 30-day window, even when they have many historical
        commits.
        """
        rows = db_session.execute(
            text("SELECT contributor, commits FROM v_top_contributors_30d")
        ).fetchall()
        names = {r.contributor for r in rows}

        assert "Alice" in names, (
            f"Alice (commit 10 days ago) is missing from v_top_contributors_30d: {names}"
        )
        assert "Carol" in names, (
            f"Carol (commit 5 days ago) is missing from v_top_contributors_30d: {names}"
        )
        assert "Bob" not in names, (
            f"Bob (last commit 720 days ago) incorrectly appears in "
            f"v_top_contributors_30d: {names}"
        )

    def test_v_active_contributors_30d_total_counts_only_recent(
        self, contributor_filtering_repo, db_session
    ):
        """
        v_active_contributors_30d_total must count only contributors with at
        least one commit in the last 30 days.  With our three-contributor repo
        that is exactly 2 (Alice + Carol).
        """
        total = db_session.execute(
            text("SELECT contributors FROM v_active_contributors_30d_total")
        ).scalar()

        assert total == 2, (
            f"Expected 2 active contributors (Alice + Carol), got {total}. "
            f"Bob has no commits in the 30-day window and must not be counted."
        )

    def test_v_contributor_activity_30d_excludes_stale_contributors(
        self, contributor_filtering_repo, db_session
    ):
        """
        v_contributor_activity_30d must not surface contributors who have zero
        commits, PRs, and reviews within the 30-day window.

        Regression: a LEFT JOIN without a HAVING clause would cause
        historical-only contributors to appear in the view with commits=0,
        making them indistinguishable from genuinely active contributors.
        """
        rows = db_session.execute(
            text(
                "SELECT contributor, commits FROM v_contributor_activity_30d"
            )
        ).fetchall()
        names = {r.contributor for r in rows}

        assert "Alice" in names, (
            f"Alice (recent commit) is missing from v_contributor_activity_30d: {names}"
        )
        assert "Carol" in names, (
            f"Carol (recent commit) is missing from v_contributor_activity_30d: {names}"
        )
        assert "Bob" not in names, (
            f"Bob (historical-only) incorrectly appears in "
            f"v_contributor_activity_30d: {names}. "
            f"The view must exclude contributors with no recent activity."
        )
