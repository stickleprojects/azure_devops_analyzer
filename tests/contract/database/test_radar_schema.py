"""
Contract tests for radar schema storage (Plan 022).

Tests S1–S5 verify that radar_publications, radar_blips, and
radar_blip_history rows are persisted and queried correctly.

Requires a live PostgreSQL test database (see tests/contract/conftest.py).
"""

from datetime import datetime, date, timedelta, UTC

import pytest

from src.database.models.radar import (
    RadarBlip as RadarBlipModel,
    RadarBlipHistory,
    RadarPublication,
)


def _make_publication(session, *, is_latest=True, version="v1.0"):
    pub = RadarPublication(
        publication_date=datetime.now(UTC),
        publication_version=version,
        description="Test publication",
        published_by="test",
        is_latest=is_latest,
        created_at=datetime.now(UTC),
    )
    session.add(pub)
    session.flush()
    return pub


def _make_blip(session, pub_id, *, package_name="lodash", ecosystem="npm",
               ring="Adopt", quadrant="Languages & Frameworks",
               is_new=False, is_moved=False, repo_count=10):
    blip = RadarBlipModel(
        publication_id=pub_id,
        package_name=package_name,
        ecosystem=ecosystem,
        ring=ring,
        quadrant=quadrant,
        label=package_name,
        description=f"Used in {repo_count} repos.",
        is_new=is_new,
        is_moved=is_moved,
        repo_count=repo_count,
        exposed_to_cves=0,
        is_eol=False,
        created_at=datetime.now(UTC),
    )
    session.add(blip)
    session.flush()
    return blip


@pytest.mark.integration
class TestRadarSchema:

    def test_s1_insert_publication_with_blips(self, db_session):
        """S1: Insert publication with 3 blips — all rows stored correctly."""
        pub = _make_publication(db_session, version="v1.0")

        blip1 = _make_blip(db_session, pub.id, package_name="lodash",   ring="Adopt")
        blip2 = _make_blip(db_session, pub.id, package_name="react",    ring="Trial")
        blip3 = _make_blip(db_session, pub.id, package_name="leftpad",  ring="Hold")
        db_session.commit()

        stored = (
            db_session.query(RadarBlipModel)
            .filter(RadarBlipModel.publication_id == pub.id)
            .all()
        )
        assert len(stored) == 3
        names = {b.package_name for b in stored}
        assert names == {"lodash", "react", "leftpad"}

    def test_s2_blip_moved_from_trial_to_adopt(self, db_session):
        """S2: Blip moved from Trial → Adopt — is_moved=True, history row created."""
        pub = _make_publication(db_session, version="v2.0")
        blip = _make_blip(
            db_session, pub.id,
            package_name="express-s2",
            ring="Adopt",
            is_moved=True,
        )

        history = RadarBlipHistory(
            package_name="express-s2",
            ecosystem="npm",
            publication_date=date.today(),
            prior_ring="Trial",
            current_ring="Adopt",
            repo_count_delta=5,
            vulnerability_change="unchanged",
            created_at=datetime.now(UTC),
        )
        db_session.add(history)
        db_session.commit()

        stored_blip = (
            db_session.query(RadarBlipModel)
            .filter_by(package_name="express-s2", publication_id=pub.id)
            .one()
        )
        assert stored_blip.is_moved is True
        assert stored_blip.ring == "Adopt"

        stored_history = (
            db_session.query(RadarBlipHistory)
            .filter_by(package_name="express-s2", prior_ring="Trial")
            .first()
        )
        assert stored_history is not None
        assert stored_history.current_ring == "Adopt"

    def test_s3_new_package_is_new_flag(self, db_session):
        """S3: New package added to radar — is_new=True."""
        pub = _make_publication(db_session, version="v3.0")
        blip = _make_blip(
            db_session, pub.id,
            package_name="brand-new-pkg-s3",
            ring="Assess",
            is_new=True,
        )
        db_session.commit()

        stored = (
            db_session.query(RadarBlipModel)
            .filter_by(package_name="brand-new-pkg-s3")
            .first()
        )
        assert stored is not None
        assert stored.is_new is True

    def test_s4_only_one_is_latest(self, db_session):
        """S4: Mark new publication as latest — only one is_latest=True at a time."""
        # Create an older publication and mark it as latest
        old_pub = _make_publication(db_session, version="v4-old", is_latest=True)
        db_session.commit()

        # Simulate what the workflow does: clear is_latest, add new latest
        (
            db_session.query(RadarPublication)
            .filter(RadarPublication.is_latest == True)  # noqa: E712
            .update({"is_latest": False})
        )
        new_pub = _make_publication(db_session, version="v4-new", is_latest=True)
        db_session.commit()

        latest_count = (
            db_session.query(RadarPublication)
            .filter(RadarPublication.is_latest == True)  # noqa: E712
            .count()
        )
        assert latest_count == 1

        latest = (
            db_session.query(RadarPublication)
            .filter(RadarPublication.is_latest == True)  # noqa: E712
            .one()
        )
        assert latest.publication_version == "v4-new"

    def test_s5_blip_history_movement_timeline(self, db_session):
        """S5: Query radar_blip_history for one package — correct movement timeline."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        h1 = RadarBlipHistory(
            package_name="timeline-pkg-s5",
            ecosystem="pypi",
            publication_date=yesterday,
            prior_ring=None,
            current_ring="Assess",
            created_at=datetime.now(UTC),
        )
        h2 = RadarBlipHistory(
            package_name="timeline-pkg-s5",
            ecosystem="pypi",
            publication_date=today,
            prior_ring="Assess",
            current_ring="Trial",
            created_at=datetime.now(UTC),
        )
        db_session.add_all([h1, h2])
        db_session.commit()

        history = (
            db_session.query(RadarBlipHistory)
            .filter_by(package_name="timeline-pkg-s5", ecosystem="pypi")
            .order_by(RadarBlipHistory.publication_date.asc())
            .all()
        )
        assert len(history) == 2
        assert history[0].prior_ring is None
        assert history[0].current_ring == "Assess"
        assert history[1].prior_ring == "Assess"
        assert history[1].current_ring == "Trial"
