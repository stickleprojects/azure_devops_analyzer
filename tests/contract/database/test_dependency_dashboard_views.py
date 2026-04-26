"""
CONTRACT Tests T1–T6: dependency vulnerability dashboard views (Plan 021 / FR-5).

These tests guard the five new portfolio-level views introduced in migration 017:
  T1 — v_package_portfolio_latest: 3 repos, 1 vulnerable → repo_count=3, exposed_repos=1
  T2 — v_package_health_latest: EOL package → health_status='EOL'
  T3 — v_package_health_latest: CRITICAL exposed CVE → health_status='CRITICAL_EXPOSED'
  T4 — v_package_adoption_timeline: 3 different dates → 3 date rows
  T5 — v_package_by_team_latest: same package, 2 teams → 2 rows
  T6 — v_package_vulnerabilities_detail: multiple exposed repos counted accurately
"""

import pytest
from datetime import datetime, date, timedelta, UTC

from sqlalchemy import text

from src.database.models.dependency import RepositoryDependency, Vulnerability
from src.database.models.package import Package
from src.database.storage import (
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

def _make_repo(db_session, repo_id: str, repo_name: str, org_suffix: str = ""):
    """Create org → project → repo and return the repo."""
    suffix = org_suffix or repo_name
    org = store_organization(
        db_session,
        sample_organization_data(name=f"org-t-{suffix}", platform=Platform.GITHUB),
    )
    proj = store_project(db_session, org, f"proj-{suffix}", f"Proj {suffix}")
    repo = store_repository(
        db_session, proj, sample_repository_data(repo_id=repo_id, name=repo_name)
    )
    return repo


def _make_package(db_session, name: str, ecosystem: str = "npm", **kwargs) -> Package:
    pkg = db_session.query(Package).filter_by(
        package_name=name, ecosystem=ecosystem
    ).first()
    if not pkg:
        pkg = Package(package_name=name, ecosystem=ecosystem, **kwargs)
        db_session.add(pkg)
        db_session.flush()
    return pkg


def _make_dep(
    db_session,
    repo_id: str,
    package_name: str,
    ecosystem: str = "npm",
    version: str = "1.0.0",
    *,
    has_known_vulnerabilities: bool = False,
    last_seen_at: datetime | None = None,
) -> RepositoryDependency:
    now = last_seen_at or datetime.now(UTC)
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


def _make_vuln(
    db_session,
    pkg: Package,
    cve_id: str,
    severity: str,
    fixed_in_version: str = "999.0.0",
) -> Vulnerability:
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
# T1: v_package_portfolio_latest — 3 repos, 1 vulnerable → repo_count=3, exposed_repos=1
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_t1_portfolio_repo_and_exposed_counts(db_session):
    """T1: Package used by 3 repos; 1 marked vulnerable → repo_count=3, exposed_repos=1."""
    pkg = _make_package(db_session, "t1-lodash", "npm")
    for i in range(3):
        repo_id = f"org/t1-repo-{i}"
        _make_repo(db_session, repo_id, f"t1-repo-{i}")
        _make_dep(
            db_session,
            repo_id,
            "t1-lodash",
            has_known_vulnerabilities=(i == 0),
        )
    db_session.commit()

    row = db_session.execute(
        text(
            "SELECT repo_count, exposed_repos "
            "FROM v_package_portfolio_latest "
            "WHERE package_name = 't1-lodash' AND ecosystem = 'npm'"
        )
    ).fetchone()

    assert row is not None, "Expected a row in v_package_portfolio_latest"
    assert row.repo_count == 3
    assert row.exposed_repos == 1


# ---------------------------------------------------------------------------
# T2: v_package_health_latest — EOL package → health_status='EOL'
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_t2_health_eol_classification(db_session):
    """T2: Package flagged is_eol=True → health_status='EOL'."""
    pkg = _make_package(db_session, "t2-python2", "pypi", is_eol=True)
    _make_repo(db_session, "org/t2-repo", "t2-repo")
    _make_dep(db_session, "org/t2-repo", "t2-python2", "pypi")
    db_session.commit()

    row = db_session.execute(
        text(
            "SELECT health_status "
            "FROM v_package_health_latest "
            "WHERE package_name = 't2-python2' AND ecosystem = 'pypi'"
        )
    ).fetchone()

    assert row is not None
    assert row.health_status == "EOL"


# ---------------------------------------------------------------------------
# T3: v_package_health_latest — CRITICAL exposed → health_status='CRITICAL_EXPOSED'
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_t3_health_critical_exposed_classification(db_session):
    """T3: Package with CRITICAL CVE and 1 exposed repo → health_status='CRITICAL_EXPOSED'."""
    pkg = _make_package(db_session, "t3-axios", "npm")
    _make_vuln(db_session, pkg, "CVE-2021-CRIT", "CRITICAL")
    _make_repo(db_session, "org/t3-repo", "t3-repo")
    _make_dep(db_session, "org/t3-repo", "t3-axios", has_known_vulnerabilities=True)
    db_session.commit()

    row = db_session.execute(
        text(
            "SELECT health_status "
            "FROM v_package_health_latest "
            "WHERE package_name = 't3-axios' AND ecosystem = 'npm'"
        )
    ).fetchone()

    assert row is not None
    assert row.health_status == "CRITICAL_EXPOSED"


# ---------------------------------------------------------------------------
# T4: v_package_adoption_timeline — 3 dates → 3 rows with correct date grouping
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_t4_adoption_timeline_date_grouping(db_session):
    """T4: 3 repos each on a distinct date → 3 adoption_date rows, 1 repo each."""
    pkg = _make_package(db_session, "t4-react", "npm")
    base = datetime.now(UTC)
    # Use days 1, 2, 3 to guarantee 3 distinct dates within the 90-day window.
    distinct_days = [1, 2, 3]
    for i, day in enumerate(distinct_days):
        repo_id = f"org/t4-repo-{i}"
        _make_repo(db_session, repo_id, f"t4-repo-{i}")
        _make_dep(
            db_session,
            repo_id,
            "t4-react",
            last_seen_at=datetime(base.year, base.month, day, tzinfo=UTC),
        )
    db_session.commit()

    rows = db_session.execute(
        text(
            "SELECT adoption_date, repo_count "
            "FROM v_package_adoption_timeline "
            "WHERE package_name = 't4-react' AND ecosystem = 'npm' "
            "ORDER BY adoption_date"
        )
    ).fetchall()

    assert len(rows) == 3, f"Expected 3 date rows, got {len(rows)}"
    assert all(r.repo_count == 1 for r in rows), "Each date should have exactly 1 repo"


# ---------------------------------------------------------------------------
# T5: v_package_by_team_latest — 2 teams → 2 rows, one per team
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_t5_by_team_two_teams(db_session):
    """T5: Same package used by repos from 2 teams → 2 rows in v_package_by_team_latest."""
    from src.database.models.team import Team
    from src.database.models.organization import Organization

    pkg = _make_package(db_session, "t5-express", "npm")

    now = datetime.now(UTC)

    # Team A
    org_a = store_organization(
        db_session, sample_organization_data(name="org-t5a", platform=Platform.GITHUB)
    )
    proj_a = store_project(db_session, org_a, "proj-t5a", "Proj T5A")
    team_a = Team(name="team-t5-alpha", organization_id=org_a.organization_id, created_at=now)
    db_session.add(team_a)
    db_session.flush()
    repo_a = store_repository(
        db_session, proj_a, sample_repository_data(repo_id="org/t5-repo-a", name="t5-repo-a")
    )
    repo_a.team_id = team_a.team_id
    _make_dep(db_session, "org/t5-repo-a", "t5-express")

    # Team B
    org_b = store_organization(
        db_session, sample_organization_data(name="org-t5b", platform=Platform.GITHUB)
    )
    proj_b = store_project(db_session, org_b, "proj-t5b", "Proj T5B")
    team_b = Team(name="team-t5-beta", organization_id=org_b.organization_id, created_at=now)
    db_session.add(team_b)
    db_session.flush()
    repo_b = store_repository(
        db_session, proj_b, sample_repository_data(repo_id="org/t5-repo-b", name="t5-repo-b")
    )
    repo_b.team_id = team_b.team_id
    _make_dep(db_session, "org/t5-repo-b", "t5-express")

    db_session.commit()

    rows = db_session.execute(
        text(
            "SELECT team_name, repo_count "
            "FROM v_package_by_team_latest "
            "WHERE package_name = 't5-express' AND ecosystem = 'npm' "
            "ORDER BY team_name"
        )
    ).fetchall()

    team_names = [r.team_name for r in rows]
    assert "team-t5-alpha" in team_names
    assert "team-t5-beta" in team_names
    assert all(r.repo_count == 1 for r in rows)


# ---------------------------------------------------------------------------
# T6: v_package_vulnerabilities_detail — multiple exposed repos → accurate count
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_t6_vulnerability_detail_exposed_count(db_session):
    """T6: CVE with 2 exposed repos and 1 patched → exposed_repo_count=2."""
    pkg = _make_package(db_session, "t6-semver", "npm")
    _make_vuln(db_session, pkg, "CVE-2022-T6", "HIGH")

    for i in range(2):
        repo_id = f"org/t6-repo-exp-{i}"
        _make_repo(db_session, repo_id, f"t6-repo-exp-{i}")
        _make_dep(db_session, repo_id, "t6-semver", has_known_vulnerabilities=True)

    _make_repo(db_session, "org/t6-repo-pat", "t6-repo-pat")
    _make_dep(db_session, "org/t6-repo-pat", "t6-semver", has_known_vulnerabilities=False)

    db_session.commit()

    row = db_session.execute(
        text(
            "SELECT cve_id, exposed_repo_count "
            "FROM v_package_vulnerabilities_detail "
            "WHERE package_name = 't6-semver' AND ecosystem = 'npm' "
            "AND cve_id = 'CVE-2022-T6'"
        )
    ).fetchone()

    assert row is not None
    assert row.exposed_repo_count == 2
