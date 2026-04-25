"""
CONTRACT tests for /api/packages/by-service endpoint.

Tests A1–A10 exercise the endpoint's query-parameter semantics: required name,
optional ecosystem/version filtering, service grouping, and ordering.

All tests use the Flask test client and a real PostgreSQL session (via the
app_client fixture in conftest.py which patches get_session).
"""

from datetime import datetime, UTC

import pytest

from src.database.models.package import Package
from src.database.models.dependency import RepositoryDependency
from src.database.models.service import RepositoryService
from src.database.storage import (
    get_or_create_service,
    store_organization,
    store_project,
    store_repository,
)
from tests.fixtures.sample_data import sample_organization_data, sample_repository_data


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _setup_service_repo(db_session, service_name, repo_id, repo_name):
    """Create org/project/repo/service and link them."""
    org_data = sample_organization_data(name=f"org-pkg-{repo_name}")
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


def _add_dep(db_session, repo_id, package_name, ecosystem, version,
             *, has_known_vulnerabilities=False):
    """Insert a RepositoryDependency row, ensure a Package row exists."""
    pkg = db_session.query(Package).filter_by(
        package_name=package_name, ecosystem=ecosystem
    ).first()
    if not pkg:
        pkg = Package(package_name=package_name, ecosystem=ecosystem)
        db_session.add(pkg)
        db_session.flush()

    dep = RepositoryDependency(
        repo_id=repo_id,
        package_name=package_name,
        ecosystem=ecosystem,
        version=version,
        has_known_vulnerabilities=has_known_vulnerabilities,
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
    )
    db_session.add(dep)
    db_session.flush()
    return dep


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestPackagesByServiceEndpoint:
    """Contract tests for GET /api/packages/by-service."""

    def test_a1_missing_name_returns_400(self, app_client):
        """A1: no name param → 400 with error body."""
        resp = app_client.get("/api/packages/by-service")
        assert resp.status_code == 400
        assert resp.get_json() == {"status": "error", "message": "name is required"}

    def test_a2_package_no_usage_returns_empty(self, app_client, db_session):
        """A2: package row exists but zero repo usage → []."""
        pkg = Package(package_name="unused-pkg-a2", ecosystem="npm")
        db_session.add(pkg)
        db_session.commit()

        resp = app_client.get("/api/packages/by-service?name=unused-pkg-a2")
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_a3_one_service_one_repo(self, app_client, db_session):
        """A3: one service, one repo → repo_count=1, versions_in_use=[version]."""
        repo, service = _setup_service_repo(
            db_session, "svc-a3", "org/a3-repo", "a3-repo"
        )
        _add_dep(db_session, repo.repo_id, "lodash-a3", "npm", "4.17.21")
        db_session.commit()

        resp = app_client.get("/api/packages/by-service?name=lodash-a3")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["service_name"] == "svc-a3"
        assert data[0]["repo_count"] == 1
        assert data[0]["versions_in_use"] == ["4.17.21"]

    def test_a4_one_service_three_repos_same_version(self, app_client, db_session):
        """A4: one service, three repos all on 1.2.3 → repo_count=3, versions deduplicated."""
        repo1, _ = _setup_service_repo(db_session, "svc-a4", "org/a4-repo1", "a4-repo1")
        repo2, _ = _setup_service_repo(db_session, "svc-a4", "org/a4-repo2", "a4-repo2")
        repo3, _ = _setup_service_repo(db_session, "svc-a4", "org/a4-repo3", "a4-repo3")
        for repo in (repo1, repo2, repo3):
            _add_dep(db_session, repo.repo_id, "react-a4", "npm", "1.2.3")
        db_session.commit()

        resp = app_client.get("/api/packages/by-service?name=react-a4")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["repo_count"] == 3
        assert data[0]["versions_in_use"] == ["1.2.3"]

    def test_a5_one_service_mixed_versions(self, app_client, db_session):
        """A5: one service, two repos on 1.2.3 and one on 4.17.21 → versions sorted."""
        repo1, _ = _setup_service_repo(db_session, "svc-a5", "org/a5-repo1", "a5-repo1")
        repo2, _ = _setup_service_repo(db_session, "svc-a5", "org/a5-repo2", "a5-repo2")
        repo3, _ = _setup_service_repo(db_session, "svc-a5", "org/a5-repo3", "a5-repo3")
        _add_dep(db_session, repo1.repo_id, "express-a5", "npm", "1.2.3")
        _add_dep(db_session, repo2.repo_id, "express-a5", "npm", "1.2.3")
        _add_dep(db_session, repo3.repo_id, "express-a5", "npm", "4.17.21")
        db_session.commit()

        resp = app_client.get("/api/packages/by-service?name=express-a5")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["repo_count"] == 3
        assert data[0]["versions_in_use"] == ["1.2.3", "4.17.21"]

    def test_a6_two_services_ordered_by_name(self, app_client, db_session):
        """A6: two services → two rows ordered by service_name."""
        repo1, _ = _setup_service_repo(db_session, "svc-a6-b", "org/a6-repo1", "a6-repo1")
        repo2, _ = _setup_service_repo(db_session, "svc-a6-a", "org/a6-repo2", "a6-repo2")
        _add_dep(db_session, repo1.repo_id, "axios-a6", "npm", "1.0.0")
        _add_dep(db_session, repo2.repo_id, "axios-a6", "npm", "1.0.0")
        db_session.commit()

        resp = app_client.get("/api/packages/by-service?name=axios-a6")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 2
        assert data[0]["service_name"] == "svc-a6-a"
        assert data[1]["service_name"] == "svc-a6-b"

    def test_a7_orphan_repo_not_in_result(self, app_client, db_session):
        """A7: repo using package but not linked to any service → []."""
        org_data = sample_organization_data(name="org-a7")
        org = store_organization(db_session, org_data)
        project = store_project(db_session, org, "proj-a7", "Test Project")
        repo_data = sample_repository_data(repo_id="org/a7-orphan-repo", name="a7-orphan-repo")
        repo = store_repository(db_session, project, repo_data)
        _add_dep(db_session, repo.repo_id, "moment-a7", "npm", "2.29.0")
        db_session.commit()

        resp = app_client.get("/api/packages/by-service?name=moment-a7")
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_a8_version_filter(self, app_client, db_session):
        """A8: ?version=1.2.3 on mixed-version service → repo_count=2, versions=[1.2.3]."""
        repo1, _ = _setup_service_repo(db_session, "svc-a8", "org/a8-repo1", "a8-repo1")
        repo2, _ = _setup_service_repo(db_session, "svc-a8", "org/a8-repo2", "a8-repo2")
        repo3, _ = _setup_service_repo(db_session, "svc-a8", "org/a8-repo3", "a8-repo3")
        _add_dep(db_session, repo1.repo_id, "chalk-a8", "npm", "1.2.3")
        _add_dep(db_session, repo2.repo_id, "chalk-a8", "npm", "1.2.3")
        _add_dep(db_session, repo3.repo_id, "chalk-a8", "npm", "4.17.21")
        db_session.commit()

        resp = app_client.get("/api/packages/by-service?name=chalk-a8&version=1.2.3")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["repo_count"] == 2
        assert data[0]["versions_in_use"] == ["1.2.3"]

    def test_a9_version_filter_no_match_returns_empty(self, app_client, db_session):
        """A9: ?version=9.9.9 when no repo is on that version → []."""
        repo, _ = _setup_service_repo(db_session, "svc-a9", "org/a9-repo", "a9-repo")
        _add_dep(db_session, repo.repo_id, "debug-a9", "npm", "1.2.3")
        db_session.commit()

        resp = app_client.get("/api/packages/by-service?name=debug-a9&version=9.9.9")
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_a10_ecosystem_filter(self, app_client, db_session):
        """A10: ?ecosystem=npm filters out pypi rows with same package name."""
        repo1, _ = _setup_service_repo(
            db_session, "svc-a10-npm", "org/a10-npm-repo", "a10-npm-repo"
        )
        repo2, _ = _setup_service_repo(
            db_session, "svc-a10-pypi", "org/a10-pypi-repo", "a10-pypi-repo"
        )
        _add_dep(db_session, repo1.repo_id, "requests-a10", "npm", "1.0.0")
        _add_dep(db_session, repo2.repo_id, "requests-a10", "pypi", "2.28.0")
        db_session.commit()

        resp = app_client.get("/api/packages/by-service?name=requests-a10&ecosystem=npm")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["service_name"] == "svc-a10-npm"
