"""
CONTRACT Tests B1–B8: dependency dashboard queries using has_known_vulnerabilities flag.

These tests guard the semantic change introduced in plan 012 R-B:
vulnerability counts are now driven by the pre-computed
``repository_dependencies.has_known_vulnerabilities`` flag rather than an
expensive LEFT JOIN to the vulnerabilities table.

B1–B4: query v_repo_dependency_rollup_latest directly.
B5:    call _aggregate_security_metrics via compute_service_metrics.
B6–B7: query v_service_vulnerabilities_by_severity directly.
B8:    EOL regression guard — eol_dependencies must still work correctly.
"""

import pytest
from datetime import datetime, UTC
from sqlalchemy import text

from src.database.models.dependency import RepositoryDependency, Vulnerability
from src.database.models.package import Package
from src.database.models.service import RepositoryService, Service
from src.database.service_analytics import _aggregate_security_metrics
from src.database.storage import (
    get_or_create_service,
    store_organization,
    store_project,
    store_repository,
)
from src.extractors.base import Platform
from tests.fixtures.sample_data import (
    sample_organization_data,
    sample_repository_data,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _setup_repo_with_dep(
    db_session,
    repo_id: str,
    repo_name: str,
    package_name: str,
    version: str,
    *,
    has_known_vulnerabilities: bool,
    ecosystem: str = "npm",
) -> RepositoryDependency:
    """Create repo + package + repository_dependency with flag pre-set."""
    org_data = sample_organization_data(name=f"test-org-{repo_name}", platform=Platform.GITHUB)
    org = store_organization(db_session, org_data)
    project = store_project(db_session, org, f"proj-{repo_name}", f"Proj {repo_name}")
    repo_data = sample_repository_data(repo_id=repo_id, name=repo_name)
    store_repository(db_session, project, repo_data)

    now = datetime.now(UTC)
    dep = RepositoryDependency(
        repo_id=repo_id,
        package_name=package_name,
        version=version,
        ecosystem=ecosystem,
        is_dev_dependency=False,
        has_known_vulnerabilities=has_known_vulnerabilities,
        first_seen_at=now,
        last_seen_at=now,
    )
    db_session.add(dep)
    db_session.flush()
    return dep


def _add_cve(
    db_session,
    package_name: str,
    ecosystem: str,
    cve_id: str,
    severity: str,
    fixed_in_version: str,
) -> Vulnerability:
    """Insert a vulnerability row attached to a package (upsert the package first)."""
    pkg = (
        db_session.query(Package)
        .filter_by(package_name=package_name, ecosystem=ecosystem)
        .first()
    )
    if not pkg:
        pkg = Package(
            package_name=package_name,
            ecosystem=ecosystem,
        )
        db_session.add(pkg)
        db_session.flush()

    vuln = Vulnerability(
        package_id=pkg.id,
        cve_id=cve_id,
        severity=severity,
        fixed_in_version=fixed_in_version,
    )
    db_session.add(vuln)
    db_session.flush()
    return vuln


def _link_repo_to_service(db_session, repo_id: str, service: Service) -> None:
    """Add a repo → service mapping."""
    rs = RepositoryService(
        repo_id=repo_id,
        service_id=service.service_id,
        linked_at=datetime.now(UTC),
    )
    db_session.add(rs)
    db_session.flush()


# ---------------------------------------------------------------------------
# B1: Repo on vulnerable version, 1 CVE → vulnerabilities = 1
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_b1_vulnerable_repo_counts_one(db_session):
    """B1: Repo on a vulnerable version with 1 CVE shows vulnerabilities=1."""
    _setup_repo_with_dep(
        db_session,
        repo_id="org/b1-repo",
        repo_name="b1-repo",
        package_name="lodash",
        version="4.17.10",
        has_known_vulnerabilities=True,
    )
    _add_cve(db_session, "lodash", "npm", "CVE-2021-1001", "HIGH", "4.17.21")
    db_session.commit()

    row = db_session.execute(
        text("SELECT vulnerabilities FROM v_repo_dependency_rollup_latest WHERE repo_id = 'org/b1-repo'")
    ).fetchone()

    assert row is not None
    assert row.vulnerabilities == 1


# ---------------------------------------------------------------------------
# B2: Repo on patched version, CVE exists → vulnerabilities = 0 (regression guard)
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_b2_patched_repo_counts_zero(db_session):
    """B2: Repo on a patched version is NOT counted even though a CVE exists for the package."""
    _setup_repo_with_dep(
        db_session,
        repo_id="org/b2-repo",
        repo_name="b2-repo",
        package_name="lodash",
        version="4.17.21",  # patched version
        has_known_vulnerabilities=False,
    )
    _add_cve(db_session, "lodash", "npm", "CVE-2021-1002", "HIGH", "4.17.21")
    db_session.commit()

    row = db_session.execute(
        text("SELECT vulnerabilities FROM v_repo_dependency_rollup_latest WHERE repo_id = 'org/b2-repo'")
    ).fetchone()

    assert row is not None
    assert row.vulnerabilities == 0


# ---------------------------------------------------------------------------
# B3: Two deps on same repo, one flagged true / one false → vulnerabilities = 1
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_b3_mixed_deps_counts_only_flagged(db_session):
    """B3: Only deps with flag=true are counted; flag=false deps are ignored."""
    org_data = sample_organization_data(name="test-org-b3", platform=Platform.GITHUB)
    org = store_organization(db_session, org_data)
    project = store_project(db_session, org, "proj-b3", "Proj B3")
    repo_data = sample_repository_data(repo_id="org/b3-repo", name="b3-repo")
    store_repository(db_session, project, repo_data)

    now = datetime.now(UTC)
    dep_vuln = RepositoryDependency(
        repo_id="org/b3-repo",
        package_name="vulnerable-pkg",
        version="1.0.0",
        ecosystem="npm",
        is_dev_dependency=False,
        has_known_vulnerabilities=True,
        first_seen_at=now,
        last_seen_at=now,
    )
    dep_safe = RepositoryDependency(
        repo_id="org/b3-repo",
        package_name="safe-pkg",
        version="2.0.0",
        ecosystem="npm",
        is_dev_dependency=False,
        has_known_vulnerabilities=False,
        first_seen_at=now,
        last_seen_at=now,
    )
    db_session.add_all([dep_vuln, dep_safe])
    db_session.commit()

    row = db_session.execute(
        text("SELECT vulnerabilities FROM v_repo_dependency_rollup_latest WHERE repo_id = 'org/b3-repo'")
    ).fetchone()

    assert row is not None
    assert row.vulnerabilities == 1


# ---------------------------------------------------------------------------
# B4: Repo with no deps → vulnerabilities = 0
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_b4_no_deps_zero_vulnerabilities(db_session):
    """B4: Repo with no dependencies at all shows 0 vulnerabilities (no row, or 0)."""
    org_data = sample_organization_data(name="test-org-b4", platform=Platform.GITHUB)
    org = store_organization(db_session, org_data)
    project = store_project(db_session, org, "proj-b4", "Proj B4")
    repo_data = sample_repository_data(repo_id="org/b4-repo", name="b4-repo")
    store_repository(db_session, project, repo_data)
    db_session.commit()

    row = db_session.execute(
        text("SELECT vulnerabilities FROM v_repo_dependency_rollup_latest WHERE repo_id = 'org/b4-repo'")
    ).fetchone()

    # Row won't exist if no dependencies recorded — that's acceptable.
    if row is not None:
        assert row.vulnerabilities == 0


# ---------------------------------------------------------------------------
# B5: _aggregate_security_metrics — exposed repo counted, patched repo not
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_b5_aggregate_security_metrics_exposed_vs_patched(db_session):
    """B5: Service with two repos (one exposed, one patched) → total_vulnerabilities=1."""
    now = datetime.now(UTC)

    # Repo A — vulnerable
    org_a = store_organization(db_session, sample_organization_data(name="org-b5a"))
    proj_a = store_project(db_session, org_a, "proj-b5a", "Proj B5A")
    store_repository(db_session, proj_a, sample_repository_data(repo_id="org/b5-repo-a", name="b5-repo-a"))
    dep_a = RepositoryDependency(
        repo_id="org/b5-repo-a",
        package_name="axios",
        version="0.21.0",
        ecosystem="npm",
        is_dev_dependency=False,
        has_known_vulnerabilities=True,
        first_seen_at=now,
        last_seen_at=now,
    )
    db_session.add(dep_a)

    # Repo B — patched
    org_b = store_organization(db_session, sample_organization_data(name="org-b5b"))
    proj_b = store_project(db_session, org_b, "proj-b5b", "Proj B5B")
    store_repository(db_session, proj_b, sample_repository_data(repo_id="org/b5-repo-b", name="b5-repo-b"))
    dep_b = RepositoryDependency(
        repo_id="org/b5-repo-b",
        package_name="axios",
        version="0.21.4",  # patched
        ecosystem="npm",
        is_dev_dependency=False,
        has_known_vulnerabilities=False,
        first_seen_at=now,
        last_seen_at=now,
    )
    db_session.add(dep_b)

    # Package + CVE
    pkg = Package(package_name="axios", ecosystem="npm")
    db_session.add(pkg)
    db_session.flush()
    vuln = Vulnerability(package_id=pkg.id, cve_id="CVE-2021-3749", severity="HIGH", fixed_in_version="0.21.4")
    db_session.add(vuln)
    db_session.commit()

    result = _aggregate_security_metrics(
        db_session, ["org/b5-repo-a", "org/b5-repo-b"]
    )

    assert result["total_vulnerabilities"] == 1


# ---------------------------------------------------------------------------
# B6: Service severity rollup — exposed + patched on same CVE → count = 1
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_b6_service_severity_rollup_exposed_only(db_session):
    """B6: v_service_vulnerabilities_by_severity counts CVE only for exposed repo."""
    now = datetime.now(UTC)

    # Service
    service = get_or_create_service(db_session, "b6-service")
    db_session.flush()

    # Repo A — vulnerable
    org_a = store_organization(db_session, sample_organization_data(name="org-b6a"))
    proj_a = store_project(db_session, org_a, "proj-b6a", "Proj B6A")
    store_repository(db_session, proj_a, sample_repository_data(repo_id="org/b6-repo-a", name="b6-repo-a"))
    dep_a = RepositoryDependency(
        repo_id="org/b6-repo-a",
        package_name="moment",
        version="2.29.0",
        ecosystem="npm",
        is_dev_dependency=False,
        has_known_vulnerabilities=True,
        first_seen_at=now,
        last_seen_at=now,
    )
    db_session.add(dep_a)
    _link_repo_to_service(db_session, "org/b6-repo-a", service)

    # Repo B — patched
    org_b = store_organization(db_session, sample_organization_data(name="org-b6b"))
    proj_b = store_project(db_session, org_b, "proj-b6b", "Proj B6B")
    store_repository(db_session, proj_b, sample_repository_data(repo_id="org/b6-repo-b", name="b6-repo-b"))
    dep_b = RepositoryDependency(
        repo_id="org/b6-repo-b",
        package_name="moment",
        version="2.29.4",  # patched
        ecosystem="npm",
        is_dev_dependency=False,
        has_known_vulnerabilities=False,
        first_seen_at=now,
        last_seen_at=now,
    )
    db_session.add(dep_b)
    _link_repo_to_service(db_session, "org/b6-repo-b", service)

    # Package + CVE
    pkg = Package(package_name="moment", ecosystem="npm")
    db_session.add(pkg)
    db_session.flush()
    vuln = Vulnerability(package_id=pkg.id, cve_id="CVE-2022-24785", severity="HIGH", fixed_in_version="2.29.4")
    db_session.add(vuln)
    db_session.commit()

    rows = db_session.execute(
        text(
            "SELECT service, severity, count "
            "FROM v_service_vulnerabilities_by_severity "
            "WHERE service = 'b6-service'"
        )
    ).fetchall()

    assert len(rows) == 1, f"Expected 1 severity row, got {len(rows)}"
    assert rows[0].count == 1


# ---------------------------------------------------------------------------
# B7: CVE exists but no repo is exposed → no row returned
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_b7_no_exposed_repo_no_row(db_session):
    """B7: When all repos are on a patched version, the severity view returns no rows."""
    now = datetime.now(UTC)

    service = get_or_create_service(db_session, "b7-service")
    db_session.flush()

    org = store_organization(db_session, sample_organization_data(name="org-b7"))
    proj = store_project(db_session, org, "proj-b7", "Proj B7")
    store_repository(db_session, proj, sample_repository_data(repo_id="org/b7-repo", name="b7-repo"))
    dep = RepositoryDependency(
        repo_id="org/b7-repo",
        package_name="semver",
        version="7.5.4",  # patched
        ecosystem="npm",
        is_dev_dependency=False,
        has_known_vulnerabilities=False,
        first_seen_at=now,
        last_seen_at=now,
    )
    db_session.add(dep)
    _link_repo_to_service(db_session, "org/b7-repo", service)

    pkg = Package(package_name="semver", ecosystem="npm")
    db_session.add(pkg)
    db_session.flush()
    vuln = Vulnerability(package_id=pkg.id, cve_id="CVE-2022-25883", severity="HIGH", fixed_in_version="7.5.4")
    db_session.add(vuln)
    db_session.commit()

    rows = db_session.execute(
        text(
            "SELECT count FROM v_service_vulnerabilities_by_severity "
            "WHERE service = 'b7-service'"
        )
    ).fetchall()

    assert len(rows) == 0, f"Expected no rows, got {len(rows)}"


# ---------------------------------------------------------------------------
# B8: EOL regression guard — eol_dependencies count unaffected by this change
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_b8_eol_count_unaffected(db_session):
    """B8: EOL dep is still counted correctly; the flag change must not break EOL logic."""
    now = datetime.now(UTC)

    org = store_organization(db_session, sample_organization_data(name="org-b8"))
    proj = store_project(db_session, org, "proj-b8", "Proj B8")
    store_repository(db_session, proj, sample_repository_data(repo_id="org/b8-repo", name="b8-repo"))
    dep = RepositoryDependency(
        repo_id="org/b8-repo",
        package_name="python2",
        version="2.7.18",
        ecosystem="pypi",
        is_dev_dependency=False,
        has_known_vulnerabilities=False,  # not flagged as vulnerable
        first_seen_at=now,
        last_seen_at=now,
    )
    db_session.add(dep)

    # Create EOL package entry
    pkg = Package(
        package_name="python2",
        ecosystem="pypi",
        is_eol=True,
    )
    db_session.add(pkg)
    db_session.commit()

    row = db_session.execute(
        text(
            "SELECT eol_dependencies, vulnerabilities "
            "FROM v_repo_dependency_rollup_latest "
            "WHERE repo_id = 'org/b8-repo'"
        )
    ).fetchone()

    assert row is not None
    assert row.eol_dependencies == 1, "EOL dependency must still be counted"
    assert row.vulnerabilities == 0, "Non-flagged dep must not appear as vulnerable"
