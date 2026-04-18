"""
Integration Tests: Fixture-Backed Scenario Pipeline

CONTRACT: FixtureExtractor + storage layer correctly persist generated scenario
data into the test database without requiring live API credentials.

Tests exercise the full extraction → storage pipeline using static JSON fixtures
from tests/fixtures/scenarios/generated/. Existing live-API tests are untouched.
"""

import pytest
from sqlalchemy.orm import Session

from tests.fixtures.fixture_extractor import FixtureExtractor
from tests.fixtures.sample_data import sample_repository_data
from src.database.storage import (
    store_project,
    store_repository,
    store_commit,
    store_pull_request,
    store_languages,
)
from src.database.models import Commit, PullRequest, RepositoryStack


SCENARIOS = [
    "go-microservice",        # Go, go.mod
    "java-maven-jenkins",     # Java, pom.xml, Jenkins CI
    "fullstack-monorepo",     # Python + TypeScript, dual manifests
    "dual-ci-analytics",      # Python, dual CI
    "deep-nested-manifests",  # Nested manifest paths
    "empty-stub",             # Edge case: no commits, no manifests
]

# Maps scenario name → a manifest filename that must resolve after generation
MANIFEST_LOOKUP = {
    "go-microservice": "go.mod",
    "java-maven-jenkins": "pom.xml",
    "fullstack-monorepo": "requirements.txt",
    "dual-ci-analytics": "requirements.txt",
}


def _create_fixture_repo(session: Session, organization, scenario_name: str):
    """Create a project + repository row for a given fixture scenario."""
    project = store_project(session, organization, name="fixture-project", description="")
    repo_data = sample_repository_data(
        repo_id=f"fixture/{scenario_name}",
        name=scenario_name,
        url=f"https://example.com/{scenario_name}",
    )
    repo = store_repository(session, project, repo_data)
    session.commit()
    return repo


class TestFixtureExtractorFileContent:
    """Unit tests for get_file_content — no DB or fixture files needed."""

    def test_flat_manifest_returns_content(self):
        extractor = FixtureExtractor({
            "file_names": ["go.mod"],
            "manifests": {"go.mod": "module example.com/myservice\n\ngo 1.18"},
        })
        assert extractor.get_file_content("repo", "go.mod") == "module example.com/myservice\n\ngo 1.18"

    def test_unknown_file_returns_none(self):
        extractor = FixtureExtractor({
            "file_names": [],
            "manifests": {"go.mod": "module foo"},
        })
        assert extractor.get_file_content("repo", "requirements.txt") is None

    def test_empty_manifests_returns_none(self):
        extractor = FixtureExtractor({"file_names": [], "manifests": {}})
        assert extractor.get_file_content("repo", "go.mod") is None

    def test_missing_manifests_key_returns_none(self):
        extractor = FixtureExtractor({"file_names": []})
        assert extractor.get_file_content("repo", "go.mod") is None

    def test_multiple_manifests_each_resolvable(self):
        extractor = FixtureExtractor({
            "file_names": ["requirements.txt", "package.json"],
            "manifests": {
                "requirements.txt": "Flask==2.3.0",
                "package.json": '{"name": "app"}',
            },
        })
        assert extractor.get_file_content("repo", "requirements.txt") == "Flask==2.3.0"
        assert extractor.get_file_content("repo", "package.json") == '{"name": "app"}'


@pytest.mark.integration
class TestFixtureScenarioPipeline:

    @pytest.mark.parametrize("scenario_name", SCENARIOS)
    def test_commits_stored(self, scenario_name, test_session, organization):
        extractor = FixtureExtractor(scenario_name)
        repo = _create_fixture_repo(test_session, organization, scenario_name)

        commits = extractor.get_commits(repo.repo_id)
        for commit_data in commits:
            store_commit(test_session, repo.repo_id, "main", commit_data)
        test_session.commit()

        stored = test_session.query(Commit).filter_by(repo_id=repo.repo_id).all()
        assert len(stored) == len(commits), (
            f"{scenario_name}: expected {len(commits)} commits, got {len(stored)}"
        )

    @pytest.mark.parametrize("scenario_name", SCENARIOS)
    def test_pull_requests_stored(self, scenario_name, test_session, organization):
        extractor = FixtureExtractor(scenario_name)
        repo = _create_fixture_repo(test_session, organization, scenario_name)

        prs = extractor.get_pull_requests(repo.repo_id)
        for pr_data in prs:
            store_pull_request(test_session, repo.repo_id, pr_data)
        test_session.commit()

        stored = test_session.query(PullRequest).filter_by(repo_id=repo.repo_id).all()
        assert len(stored) == len(prs), (
            f"{scenario_name}: expected {len(prs)} PRs, got {len(stored)}"
        )

    @pytest.mark.parametrize("scenario_name", SCENARIOS)
    def test_languages_stored(self, scenario_name, test_session, organization):
        extractor = FixtureExtractor(scenario_name)
        repo = _create_fixture_repo(test_session, organization, scenario_name)

        languages = extractor.get_languages(repo.repo_id)
        store_languages(test_session, repo.repo_id, languages)
        test_session.commit()

        stored = (
            test_session.query(RepositoryStack)
            .filter_by(repo_id=repo.repo_id, category="language")
            .all()
        )
        assert len(stored) == len(languages), (
            f"{scenario_name}: expected {len(languages)} languages, got {len(stored)}"
        )

    @pytest.mark.parametrize("scenario_name,expected_file", MANIFEST_LOOKUP.items())
    def test_file_content_returned(self, scenario_name, expected_file):
        extractor = FixtureExtractor(scenario_name)
        result = extractor.get_file_content("repo", expected_file)
        assert result is not None, (
            f"{scenario_name}: get_file_content('{expected_file}') returned None — "
            "manifests may be in wrong format (expected flat {{filename: content}} dict)"
        )
        assert isinstance(result, str) and len(result) > 0, (
            f"{scenario_name}: content for '{expected_file}' is empty"
        )

    def test_empty_stub_has_no_manifest_content(self):
        extractor = FixtureExtractor("empty-stub")
        assert extractor.get_file_content("repo", "go.mod") is None
        assert extractor.get_file_content("repo", "requirements.txt") is None
