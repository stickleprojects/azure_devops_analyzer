"""
CONTRACT Tests D1–D5: dependency vulnerability dashboard API endpoints (Plan 021 / FR-5).

  D1 — GET /api/packages/health → 200, all health_status keys present
  D2 — GET /api/packages/adoption?name=<pkg> → 200, timeline array sorted by date
  D3 — GET /api/packages/library/<name>/<ecosystem> → 200, cves + usage arrays
  D4 — GET /api/packages/health?team=<name> → 200, only that team's packages
  D5 — GET /api/packages/library — unknown package → 404
"""

import pytest
from datetime import datetime, UTC

from src.database.models.package import Package
from src.database.models.dependency import RepositoryDependency, Vulnerability
from src.database.models.service import RepositoryService
from src.database.storage import (
    get_or_create_service,
    store_organization,
    store_project,
    store_repository,
)
from tests.fixtures.sample_data import sample_organization_data, sample_repository_data


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_repo(db_session, repo_id, repo_name, org_suffix=None):
    suffix = org_suffix or repo_name
    org = store_organization(db_session, sample_organization_data(name=f"org-d-{suffix}"))
    proj = store_project(db_session, org, f"proj-{suffix}", "Test Project")
    repo = store_repository(db_session, proj, sample_repository_data(repo_id=repo_id, name=repo_name))
    return repo


def _make_package(db_session, name, ecosystem="npm", **kwargs):
    pkg = db_session.query(Package).filter_by(package_name=name, ecosystem=ecosystem).first()
    if not pkg:
        pkg = Package(package_name=name, ecosystem=ecosystem, **kwargs)
        db_session.add(pkg)
        db_session.flush()
    return pkg


def _make_dep(db_session, repo_id, package_name, ecosystem="npm", version="1.0.0",
              *, has_known_vulnerabilities=False):
    now = datetime.now(UTC)
    dep = RepositoryDependency(
        repo_id=repo_id,
        package_name=package_name,
        ecosystem=ecosystem,
        version=version,
        is_dev_dependency=False,
        has_known_vulnerabilities=has_known_vulnerabilities,
        first_seen_at=now,
        last_seen_at=now,
    )
    db_session.add(dep)
    db_session.flush()
    return dep


def _make_vuln(db_session, pkg, cve_id, severity, fixed_in_version="999.0.0"):
    vuln = Vulnerability(
        package_id=pkg.id,
        cve_id=cve_id,
        severity=severity,
        fixed_in_version=fixed_in_version,
    )
    db_session.add(vuln)
    db_session.flush()
    return vuln


# ---------------------------------------------------------------------------
# D1: GET /api/packages/health → 200, all health_status bucket keys present
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_d1_health_returns_all_buckets(app_client, db_session):
    """D1: /api/packages/health returns 200 with all five health bucket keys."""
    # Insert one package so the view has at least one row
    pkg = _make_package(db_session, "d1-express", "npm")
    _make_repo(db_session, "org/d1-repo", "d1-repo")
    _make_dep(db_session, "org/d1-repo", "d1-express")
    db_session.commit()

    resp = app_client.get("/api/packages/health")
    assert resp.status_code == 200
    data = resp.get_json()
    for key in ("healthy", "high_exposed", "critical_exposed", "eol", "approaching_eol"):
        assert key in data, f"Missing bucket key: {key}"
        assert "count" in data[key]
        assert "packages" in data[key]


# ---------------------------------------------------------------------------
# D2: GET /api/packages/adoption?name=<pkg> → 200, timeline sorted by date
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_d2_adoption_timeline_sorted(app_client, db_session):
    """D2: /api/packages/adoption?name=X returns 200 with dates in ascending order."""
    _make_package(db_session, "d2-lodash", "npm")
    now = datetime.now(UTC)
    for i in range(3):
        repo_id = f"org/d2-repo-{i}"
        _make_repo(db_session, repo_id, f"d2-repo-{i}")
        ts = datetime(now.year, now.month, max(1, now.day - i), tzinfo=UTC)
        dep = RepositoryDependency(
            repo_id=repo_id,
            package_name="d2-lodash",
            ecosystem="npm",
            version="4.17.21",
            is_dev_dependency=False,
            has_known_vulnerabilities=False,
            first_seen_at=ts,
            last_seen_at=ts,
        )
        db_session.add(dep)
    db_session.commit()

    resp = app_client.get("/api/packages/adoption?name=d2-lodash")
    assert resp.status_code == 200
    data = resp.get_json()
    dates = [row["adoption_date"] for row in data]
    assert dates == sorted(dates), "Adoption timeline must be sorted by date ascending"


# ---------------------------------------------------------------------------
# D3: GET /api/packages/library/<name>/<ecosystem> → 200, cves + usage
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_d3_library_detail_structure(app_client, db_session):
    """D3: /api/packages/library/d3-axios/npm returns 200 with metadata/cves/usage/by_team."""
    pkg = _make_package(db_session, "d3-axios", "npm", latest_version="1.4.0")
    _make_vuln(db_session, pkg, "CVE-2023-D3", "HIGH")
    repo = _make_repo(db_session, "org/d3-repo", "d3-repo")
    _make_dep(db_session, "org/d3-repo", "d3-axios", has_known_vulnerabilities=True)
    db_session.commit()

    resp = app_client.get("/api/packages/library/d3-axios/npm")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "metadata" in data
    assert data["metadata"]["package_name"] == "d3-axios"
    assert data["metadata"]["ecosystem"] == "npm"
    assert "cves" in data
    assert len(data["cves"]) == 1
    assert data["cves"][0]["cve_id"] == "CVE-2023-D3"
    assert "usage" in data
    assert len(data["usage"]) == 1
    assert "by_team" in data


# ---------------------------------------------------------------------------
# D4: GET /api/packages/health?team=<name> → 200, filter scoped to team
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_d4_health_team_filter(app_client, db_session):
    """D4: ?team=billing returns only packages used by repos in the billing team."""
    from src.database.models.team import Team

    now = datetime.now(UTC)

    # Billing team + repo + package
    org_b = store_organization(db_session, sample_organization_data(name="org-d4-billing"))
    proj_b = store_project(db_session, org_b, "proj-d4-billing", "Billing Proj")
    team_b = Team(name="d4-billing", organization_id=org_b.organization_id, created_at=now)
    db_session.add(team_b)
    db_session.flush()
    repo_b = store_repository(
        db_session, proj_b, sample_repository_data(repo_id="org/d4-repo-b", name="d4-repo-b")
    )
    repo_b.team_id = team_b.team_id
    _make_package(db_session, "d4-billing-only-pkg", "npm")
    _make_dep(db_session, "org/d4-repo-b", "d4-billing-only-pkg")

    # Unrelated package in a different team
    org_x = store_organization(db_session, sample_organization_data(name="org-d4-other"))
    proj_x = store_project(db_session, org_x, "proj-d4-other", "Other Proj")
    team_x = Team(name="d4-other-team", organization_id=org_x.organization_id, created_at=now)
    db_session.add(team_x)
    db_session.flush()
    repo_x = store_repository(
        db_session, proj_x, sample_repository_data(repo_id="org/d4-repo-x", name="d4-repo-x")
    )
    repo_x.team_id = team_x.team_id
    _make_package(db_session, "d4-other-pkg", "npm")
    _make_dep(db_session, "org/d4-repo-x", "d4-other-pkg")
    db_session.commit()

    resp = app_client.get("/api/packages/health?team=d4-billing")
    assert resp.status_code == 200
    data = resp.get_json()
    all_pkgs = []
    for bucket in data.values():
        all_pkgs.extend(p["package_name"] for p in bucket.get("packages", []))
    assert "d4-billing-only-pkg" in all_pkgs
    assert "d4-other-pkg" not in all_pkgs


# ---------------------------------------------------------------------------
# D5: GET /api/packages/library/<unknown>/<eco> → 404
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_d5_library_unknown_package_returns_404(app_client, db_session):
    """D5: Requesting a non-existent library returns 404."""
    resp = app_client.get("/api/packages/library/no-such-package/npm")
    assert resp.status_code == 404
