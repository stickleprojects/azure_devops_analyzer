"""
Integration Tests: Fixture-Backed Scenario Pipeline

CONTRACT: FixtureExtractor + storage layer correctly persist generated scenario
data into the test database without requiring live API credentials.

Tests exercise the full extraction → storage pipeline using static JSON fixtures
from tests/fixtures/scenarios/generated/. Existing live-API tests are untouched.
"""

import json
import pathlib

import pytest
from sqlalchemy import text
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
from src.database.models import Commit, Contributor, PullRequest, PRReview, RepositoryStack


_SCENARIOS_DIR = (
    pathlib.Path(__file__).parent.parent.parent / "fixtures" / "scenarios" / "generated"
)

# All JSON files in the generated/ folder are exercised automatically.
# To add a new scenario: drop a .json file into tests/fixtures/scenarios/generated/
# and it will be picked up by CI on the next run — no list update required.
SCENARIOS = sorted(p.stem for p in _SCENARIOS_DIR.glob("*.json"))


def _build_manifest_lookup() -> dict[str, str]:
    """Return {scenario_name: first_manifest_filename} for every scenario that has manifests."""
    lookup: dict[str, str] = {}
    for path in sorted(_SCENARIOS_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        manifests = data.get("manifests", {})
        if isinstance(manifests, dict) and manifests:
            lookup[path.stem] = next(iter(manifests))
        elif isinstance(manifests, list) and manifests:
            first = manifests[0]
            if isinstance(first, dict):
                lookup[path.stem] = first.get("file_path", "")
    return lookup


# Maps scenario name → a manifest filename that must resolve — derived from the
# scenario JSON itself, so it stays in sync automatically.
MANIFEST_LOOKUP = _build_manifest_lookup()


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
    def test_pull_requests_author_links_are_sound(self, scenario_name, test_session, organization):
        """CONTRACT: Every stored PR's author_id must resolve to the correct contributor.

        Regression guard for DASH-CONTRIB-002: PR→contributor FK must be non-null,
        must point at an existing contributors row, and that row's email must match
        the normalised source email from the fixture.  Zero orphans are permitted.
        """
        extractor = FixtureExtractor(scenario_name)
        repo = _create_fixture_repo(test_session, organization, scenario_name)

        prs = extractor.get_pull_requests(repo.repo_id)
        for pr_data in prs:
            store_pull_request(test_session, repo.repo_id, pr_data)
        test_session.commit()

        # No orphaned author FKs across any PR in this scenario
        orphan_count = test_session.execute(
            text(
                """
                SELECT count(*) FROM pull_requests
                WHERE repo_id = :repo_id
                  AND (author_id IS NULL
                       OR author_id NOT IN (SELECT id FROM contributors))
                """
            ),
            {"repo_id": repo.repo_id},
        ).scalar()
        assert orphan_count == 0, (
            f"{scenario_name}: found {orphan_count} pull_requests rows with "
            "NULL or dangling author_id"
        )

        # Each PR's author resolves to the normalised source email
        for pr_data in prs:
            stored = test_session.query(PullRequest).filter_by(
                repo_id=repo.repo_id, pr_number=pr_data.pr_number
            ).one()
            contributor = test_session.get(Contributor, stored.author_id)
            assert contributor is not None, (
                f"{scenario_name} PR#{pr_data.pr_number}: author_id {stored.author_id} "
                "resolves to no contributor row"
            )
            expected_email = pr_data.author_email.strip().lower()
            assert contributor.email == expected_email, (
                f"{scenario_name} PR#{pr_data.pr_number}: contributor.email "
                f"'{contributor.email}' != expected '{expected_email}'"
            )

        # Reviews: each review's reviewer_id resolves to the correct contributor
        for pr_data in prs:
            if not pr_data.reviews:
                continue
            stored_pr = test_session.query(PullRequest).filter_by(
                repo_id=repo.repo_id, pr_number=pr_data.pr_number
            ).one()
            stored_reviews = test_session.query(PRReview).filter_by(pr_id=stored_pr.id).all()
            assert len(stored_reviews) == len(pr_data.reviews), (
                f"{scenario_name} PR#{pr_data.pr_number}: expected {len(pr_data.reviews)} "
                f"reviews stored, got {len(stored_reviews)}"
            )
            for review_data, stored_review in zip(pr_data.reviews, stored_reviews):
                reviewer = test_session.get(Contributor, stored_review.reviewer_id)
                assert reviewer is not None, (
                    f"{scenario_name} PR#{pr_data.pr_number}: reviewer_id "
                    f"{stored_review.reviewer_id} resolves to no contributor row"
                )
                expected_reviewer_email = review_data.reviewer_email.strip().lower()
                assert reviewer.email == expected_reviewer_email, (
                    f"{scenario_name} PR#{pr_data.pr_number}: reviewer.email "
                    f"'{reviewer.email}' != expected '{expected_reviewer_email}'"
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
