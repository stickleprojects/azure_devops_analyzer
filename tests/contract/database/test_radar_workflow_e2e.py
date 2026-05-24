"""
End-to-end contract tests for RadarPublicationWorkflow (Plan 022, Track B).

These complement the existing radar coverage rather than duplicate it:

  * test_radar_schema.py hand-rolls the storage steps ("simulate what the
    workflow does") instead of calling the workflow.
  * test_radar_categorizer.py::TestDetectMovements drives ``_detect_movements``
    in isolation with a mocked session.

Neither actually runs ``RadarPublicationWorkflow.run()``. This module does:
it seeds repository_dependencies + packages in a live database, calls run(),
and asserts the persisted radar_publications / radar_blips / radar_blip_history
rows — exercising ``_load_package_metrics`` and ``_store_publication``, which
are otherwise untouched by tests.

Requires a live PostgreSQL test database (see tests/contract/conftest.py).
"""

from datetime import datetime, timedelta, UTC

import pytest
from sqlalchemy import func

from src.database.models.dependency import RepositoryDependency
from src.database.models.package import Package
from src.database.models.radar import (
    RadarBlip as RadarBlipModel,
    RadarBlipHistory,
    RadarPublication,
)
from src.database.models.repository import Repository
from src.workflows.radar_publication import RadarPublicationWorkflow


# ----------------------------------------------------------------------
# Seeding helpers
# ----------------------------------------------------------------------

def _make_repo(session, repo_id):
    session.add(
        Repository(
            repo_id=repo_id,
            name=repo_id,
            url=f"https://example.test/{repo_id}",
        )
    )


def _seed_usage(
    session,
    package_name,
    ecosystem,
    *,
    repo_count,
    days_old,
    vulnerable_repos=0,
    start_index=0,
):
    """Attach *package_name* to *repo_count* distinct repositories.

    ``first_seen_at`` is set *days_old* in the past (drives time_in_use_days);
    the first *vulnerable_repos* rows carry has_known_vulnerabilities=True
    (drives exposed_cves). ``start_index`` lets a later call add more repos to
    an existing package without colliding on the repo primary key.
    """
    now = datetime.now(UTC)
    first_seen = now - timedelta(days=days_old)
    for i in range(start_index, start_index + repo_count):
        repo_id = f"{package_name}-repo-{i}"
        _make_repo(session, repo_id)
        session.add(
            RepositoryDependency(
                repo_id=repo_id,
                package_name=package_name,
                ecosystem=ecosystem,
                version="1.0.0",
                first_seen_at=first_seen,
                last_seen_at=now,
                has_known_vulnerabilities=(i - start_index) < vulnerable_repos,
            )
        )
    session.flush()


def _make_package(session, package_name, ecosystem, *, is_eol=False, eol_date=None,
                  latest_version=None):
    session.add(
        Package(
            package_name=package_name,
            ecosystem=ecosystem,
            is_eol=is_eol,
            eol_date=eol_date,
            latest_version=latest_version,
        )
    )
    session.flush()


def _blips_by_name(session, publication_id):
    rows = (
        session.query(RadarBlipModel)
        .filter(RadarBlipModel.publication_id == publication_id)
        .all()
    )
    return {b.package_name: b for b in rows}


@pytest.mark.integration
class TestRadarWorkflowE2E:

    def test_run_creates_publication_blips_and_first_history(self, db_session):
        """First publication: blips categorized into rings, persisted, and a
        history row written for every blip (prior_ring=None on a cold start)."""
        # assess: 3 repos, 200 days, no CVE  -> Assess
        _seed_usage(db_session, "assess-lib", "npm", repo_count=3, days_old=200)
        # trial: 6 repos, 120 days, no CVE   -> Trial
        _seed_usage(db_session, "trial-lib", "pypi", repo_count=6, days_old=120)
        # hold (EOL): EOL package overrides adoption -> Hold
        _seed_usage(db_session, "eol-lib", "maven", repo_count=3, days_old=300)
        _make_package(db_session, "eol-lib", "maven", is_eol=True)
        # hold (CVE): exposed CVEs override adoption -> Hold
        _seed_usage(db_session, "cve-lib", "npm", repo_count=4, days_old=200,
                    vulnerable_repos=2)
        # hold (single use): 1 repo -> Hold; docker ecosystem -> Infrastructure
        _seed_usage(db_session, "single-lib", "docker", repo_count=1, days_old=30)
        # excluded by "internal-*" glob -> no blip
        _seed_usage(db_session, "internal-secret", "npm", repo_count=3, days_old=200)

        workflow = RadarPublicationWorkflow(session=db_session)
        pub = workflow.run(
            description="first radar",
            published_by="e2e-test",
            publication_version="e2e-v1",
        )

        # Publication row created and flagged latest
        assert pub.id is not None
        assert pub.is_latest is True
        assert pub.published_by == "e2e-test"
        assert pub.publication_version == "e2e-v1"

        blips = _blips_by_name(db_session, pub.id)
        # 6 packages seeded, 1 excluded -> 5 blips
        assert set(blips) == {"assess-lib", "trial-lib", "eol-lib", "cve-lib", "single-lib"}
        assert "internal-secret" not in blips

        # Rings derived from the real categorizer over real metrics
        assert blips["assess-lib"].ring == "Assess"
        assert blips["trial-lib"].ring == "Trial"
        assert blips["eol-lib"].ring == "Hold"
        assert blips["eol-lib"].is_eol is True
        assert blips["cve-lib"].ring == "Hold"
        assert blips["cve-lib"].exposed_to_cves == 2
        assert blips["single-lib"].ring == "Hold"

        # Quadrant: language ecosystems -> Languages & Frameworks; docker -> Infrastructure
        assert blips["assess-lib"].quadrant == "Languages & Frameworks"
        assert blips["single-lib"].quadrant == "Infrastructure"

        # repo_count aggregated from repository_dependencies
        assert blips["trial-lib"].repo_count == 6
        assert blips["assess-lib"].repo_count == 3

        # Cold start: nothing to compare against, so no blip is "new" or "moved"
        assert all(not b.is_new for b in blips.values())
        assert all(not b.is_moved for b in blips.values())

        # History: one row per blip, all transitioning from no prior ring
        history = (
            db_session.query(RadarBlipHistory)
            .filter(RadarBlipHistory.publication_date == pub.publication_date.date())
            .all()
        )
        hist_names = {h.package_name for h in history}
        assert hist_names == set(blips)
        assert all(h.prior_ring is None for h in history)

    def test_run_detects_movement_new_and_removed(self, db_session):
        """Second publication: a package moving rings, a brand-new package, and
        a disappeared package are each reflected in flags + history, and only one
        publication stays flagged latest."""
        # --- Publication 1 ---
        _seed_usage(db_session, "mover-lib", "npm", repo_count=3, days_old=200)   # Assess
        _seed_usage(db_session, "stayer-lib", "pypi", repo_count=6, days_old=120)  # Trial
        _seed_usage(db_session, "goner-lib", "npm", repo_count=2, days_old=100)    # Assess

        workflow = RadarPublicationWorkflow(session=db_session)
        pub1 = workflow.run(published_by="e2e-test", publication_version="e2e-v1")

        pub1_blips = _blips_by_name(db_session, pub1.id)
        assert pub1_blips["mover-lib"].ring == "Assess"
        assert pub1_blips["stayer-lib"].ring == "Trial"

        # --- Mutate state ---
        # mover-lib: 3 -> 6 repos (same age) so it crosses Assess -> Trial
        _seed_usage(db_session, "mover-lib", "npm", repo_count=3, days_old=200,
                    start_index=3)
        # newcomer-lib: appears for the first time -> is_new
        _seed_usage(db_session, "newcomer-lib", "npm", repo_count=2, days_old=50)
        # goner-lib: remove all usage so it drops out of the snapshot
        db_session.query(RepositoryDependency).filter_by(package_name="goner-lib").delete()
        db_session.flush()

        # History rows are dated by calendar day, and both runs happen today, so
        # isolate this cycle's history by id rather than publication_date.
        max_hist_id_before = db_session.query(func.max(RadarBlipHistory.id)).scalar() or 0

        # --- Publication 2 ---
        pub2 = workflow.run(published_by="e2e-test", publication_version="e2e-v2")
        assert pub2.id != pub1.id

        # Exactly one latest publication, and it is pub2
        latest = (
            db_session.query(RadarPublication)
            .filter(RadarPublication.is_latest == True)  # noqa: E712
            .all()
        )
        assert len(latest) == 1
        assert latest[0].id == pub2.id
        assert db_session.get(RadarPublication, pub1.id).is_latest is False

        pub2_blips = _blips_by_name(db_session, pub2.id)
        # goner-lib has no usage and must not appear as a blip
        assert set(pub2_blips) == {"mover-lib", "stayer-lib", "newcomer-lib"}

        # Movement
        assert pub2_blips["mover-lib"].ring == "Trial"
        assert pub2_blips["mover-lib"].is_moved is True
        assert pub2_blips["mover-lib"].repo_count == 6
        # Unchanged package
        assert pub2_blips["stayer-lib"].is_moved is False
        assert pub2_blips["stayer-lib"].is_new is False
        # New package
        assert pub2_blips["newcomer-lib"].is_new is True

        pub2_history = {
            h.package_name: h
            for h in db_session.query(RadarBlipHistory)
            .filter(RadarBlipHistory.id > max_hist_id_before)
            .all()
        }
        # mover-lib: Assess -> Trial, repo delta +3
        assert pub2_history["mover-lib"].prior_ring == "Assess"
        assert pub2_history["mover-lib"].current_ring == "Trial"
        assert pub2_history["mover-lib"].repo_count_delta == 3
        # newcomer-lib: no prior ring
        assert pub2_history["newcomer-lib"].prior_ring is None
        # goner-lib: removed from the radar
        assert pub2_history["goner-lib"].current_ring == "Removed"
        assert pub2_history["goner-lib"].repo_count_delta == -2
        # stayer-lib unchanged -> no history row this cycle
        assert "stayer-lib" not in pub2_history

    def test_run_excludes_configured_packages(self, db_session):
        """Packages matching an exclusion glob never become blips."""
        _seed_usage(db_session, "internal-tooling", "npm", repo_count=4, days_old=200)
        _seed_usage(db_session, "test-package-fixture", "pypi", repo_count=3, days_old=200)
        _seed_usage(db_session, "real-lib", "npm", repo_count=3, days_old=200)

        pub = RadarPublicationWorkflow(session=db_session).run(published_by="e2e-test")

        blips = _blips_by_name(db_session, pub.id)
        assert set(blips) == {"real-lib"}
