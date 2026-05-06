"""
Contract tests for Tech Radar API endpoints (Plan 022).

Tests A1–A6 exercise /api/radar, /api/radar/history, and /api/radar/export.

Uses the app_client fixture (from tests/contract/api/conftest.py) which
patches get_session to use the test database session.
"""

from datetime import datetime, date, timedelta, UTC

import pytest

from src.database.models.radar import (
    RadarBlip as RadarBlipModel,
    RadarBlipHistory,
    RadarPublication,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_publication(session, *, is_latest=True, version="v-test"):
    pub = RadarPublication(
        publication_date=datetime.now(UTC),
        publication_version=version,
        description="Test pub",
        published_by="pytest",
        is_latest=is_latest,
        created_at=datetime.now(UTC),
    )
    session.add(pub)
    session.flush()
    return pub


def _make_blip(session, pub_id, *, package_name, ring="Adopt",
               quadrant="Languages & Frameworks", ecosystem="npm",
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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestRadarEndpoints:

    def test_a1_get_radar_returns_tw_schema(self, app_client, db_session):
        """A1: GET /api/radar → 200, valid TW schema, all quadrants present."""
        pub = _make_publication(db_session)
        _make_blip(db_session, pub.id, package_name="lodash-a1")
        db_session.commit()

        resp = app_client.get("/api/radar")
        assert resp.status_code == 200

        data = resp.get_json()
        assert "documentTitle" in data
        assert "quadrants" in data
        assert "rings" in data
        assert "entries" in data

        quadrant_names = {q["name"] for q in data["quadrants"]}
        assert quadrant_names == {
            "Infrastructure", "Platforms", "Tools", "Languages & Frameworks"
        }

        ring_names = {r["name"] for r in data["rings"]}
        assert ring_names == {"Adopt", "Trial", "Assess", "Hold"}

    def test_a2_radar_entries_have_required_fields(self, app_client, db_session):
        """A2: Radar entries have ring, quadrant, and label fields."""
        pub = _make_publication(db_session, version="v-a2")
        _make_blip(db_session, pub.id, package_name="react-a2", ring="Trial")
        _make_blip(db_session, pub.id, package_name="vue-a2",   ring="Assess")
        db_session.commit()

        resp = app_client.get("/api/radar")
        assert resp.status_code == 200
        data = resp.get_json()

        assert len(data["entries"]) >= 2
        for entry in data["entries"]:
            assert "ring" in entry
            assert "quadrant" in entry
            assert "label" in entry

    def test_a3_radar_history_sorted_by_date(self, app_client, db_session):
        """A3: GET /api/radar/history?package_name=lodash → 200, sorted by date."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        db_session.add(RadarBlipHistory(
            package_name="lodash-a3", ecosystem="npm",
            publication_date=yesterday,
            prior_ring=None, current_ring="Assess",
            created_at=datetime.now(UTC),
        ))
        db_session.add(RadarBlipHistory(
            package_name="lodash-a3", ecosystem="npm",
            publication_date=today,
            prior_ring="Assess", current_ring="Trial",
            created_at=datetime.now(UTC),
        ))
        db_session.commit()

        resp = app_client.get("/api/radar/history?package_name=lodash-a3")
        assert resp.status_code == 200

        timeline = resp.get_json()["timeline"]
        assert len(timeline) == 2
        # Default ordering is descending (newest first)
        assert timeline[0]["current_ring"] == "Trial"
        assert timeline[1]["current_ring"] == "Assess"

    def test_a4_export_csv_correct_headers(self, app_client, db_session):
        """A4: GET /api/radar/export?format=csv → 200, CSV with correct headers."""
        pub = _make_publication(db_session, version="v-a4")
        _make_blip(db_session, pub.id, package_name="express-a4", ring="Adopt")
        db_session.commit()

        resp = app_client.get("/api/radar/export?format=csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.content_type

        csv_text = resp.data.decode("utf-8")
        header_line = csv_text.splitlines()[0]
        assert "package_name" in header_line
        assert "ring" in header_line
        assert "quadrant" in header_line

        # Verify the blip is in the CSV
        assert "express-a4" in csv_text

    def test_a5_export_invalid_date_returns_error(self, app_client, db_session):
        """A5: GET /api/radar/export?date=invalid → 404 or error."""
        db_session.commit()

        resp = app_client.get("/api/radar/export?date=not-a-date")
        assert resp.status_code in (400, 404)

    def test_a6_new_publication_updates_radar(self, app_client, db_session):
        """A6: After publishing new radar, /api/radar returns updated entries."""
        # First publication
        old_pub = _make_publication(db_session, version="v-a6-old", is_latest=True)
        _make_blip(db_session, old_pub.id, package_name="old-lib-a6", ring="Hold")
        db_session.commit()

        resp_old = app_client.get("/api/radar")
        assert resp_old.status_code == 200
        entries_old = resp_old.get_json()["entries"]
        old_names = {e["label"] for e in entries_old}
        assert "old-lib-a6" in old_names

        # Publish a new (latest) radar
        (
            db_session.query(RadarPublication)
            .filter(RadarPublication.is_latest == True)  # noqa: E712
            .update({"is_latest": False})
        )
        new_pub = _make_publication(db_session, version="v-a6-new", is_latest=True)
        _make_blip(db_session, new_pub.id, package_name="new-lib-a6", ring="Adopt")
        db_session.commit()

        resp_new = app_client.get("/api/radar")
        assert resp_new.status_code == 200
        entries_new = resp_new.get_json()["entries"]
        new_names = {e["label"] for e in entries_new}
        assert "new-lib-a6" in new_names
        assert "old-lib-a6" not in new_names

    def test_a7_radar_empty_when_no_publication(self, app_client, db_session):
        """No publication → /api/radar returns 200 with empty entries."""
        # Ensure no is_latest publication exists
        (
            db_session.query(RadarPublication)
            .filter(RadarPublication.is_latest == True)  # noqa: E712
            .update({"is_latest": False})
        )
        db_session.commit()

        resp = app_client.get("/api/radar")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["entries"] == []

    def test_a8_history_all_packages_when_no_filter(self, app_client, db_session):
        """GET /api/radar/history with no filter returns all history rows."""
        for pkg in ("pkg-x", "pkg-y"):
            db_session.add(RadarBlipHistory(
                package_name=pkg, ecosystem="npm",
                publication_date=date.today(),
                prior_ring=None, current_ring="Assess",
                created_at=datetime.now(UTC),
            ))
        db_session.commit()

        resp = app_client.get("/api/radar/history")
        assert resp.status_code == 200
        timeline = resp.get_json()["timeline"]
        names = {row["package_name"] for row in timeline}
        assert "pkg-x" in names
        assert "pkg-y" in names
