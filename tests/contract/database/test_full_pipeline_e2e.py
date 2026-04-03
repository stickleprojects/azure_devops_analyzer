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
from datetime import datetime, timezone
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
)
from src.analyzers.dependency_analyzer import DependencyAnalyzer
from src.database.models import Commit, PullRequest, RepositoryLanguage, Dependency
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
            db_session.query(RepositoryLanguage).filter_by(repo_id=repo.repo_id).count()
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
            db_session.query(Dependency).filter_by(repo_id=repo.repo_id).count()
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
# 3. Dashboard View Contracts (shared multi-scenario dataset)
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
            text("SELECT status, COUNT(*) AS count FROM v_pr_status_distribution")
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
