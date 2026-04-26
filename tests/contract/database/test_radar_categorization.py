"""
Contract tests for radar categorization against the database (Plan 022).

Tests C1–C6 exercise RadarCategorizer scenarios; these are integration-level
tests to confirm the categorizer works with real package data structures
(though no DB queries happen — the categorizer is pure Python).

These sit in tests/contract/database/ to keep related radar tests together
and to benefit from the db_session fixture for future workflow integration.
"""

import json
import pathlib
import tempfile
from datetime import date

import pytest

from src.analyzers.radar_categorization import RadarCategorizer, Ring, Quadrant


def _make_metrics(**kwargs) -> dict:
    base = {
        "repo_count": 1,
        "time_in_use_days": 10,
        "exposed_cves": 0,
        "is_eol": False,
        "eol_date": None,
        "category": "",
        "adopted_date": None,
        "latest_version": None,
    }
    base.update(kwargs)
    return base


@pytest.mark.integration
class TestRadarCategorizationContract:

    def test_c1_adopt_ring_large_adoption(self, db_session):
        """C1: 30 repos, 200 days → Adopt."""
        categorizer = RadarCategorizer()
        blip = categorizer.categorize(
            "lodash", "npm",
            _make_metrics(repo_count=30, time_in_use_days=200),
        )
        assert blip.ring == Ring.ADOPT

    def test_c2_assess_ring_low_adoption(self, db_session):
        """C2: 3 repos, 60 days → Assess."""
        categorizer = RadarCategorizer()
        blip = categorizer.categorize(
            "small-pkg", "npm",
            _make_metrics(repo_count=3, time_in_use_days=60),
        )
        assert blip.ring == Ring.ASSESS

    def test_c3_eol_single_repo_is_hold(self, db_session):
        """C3: 1 repo, EOL=True → Hold."""
        categorizer = RadarCategorizer()
        blip = categorizer.categorize(
            "deprecated-pkg", "pypi",
            _make_metrics(repo_count=1, is_eol=True, eol_date=date(2020, 1, 1)),
        )
        assert blip.ring == Ring.HOLD
        assert blip.is_eol is True

    def test_c4_high_cve_low_adoption_is_hold(self, db_session):
        """C4: High CVE exposure, low adoption → Hold."""
        categorizer = RadarCategorizer()
        blip = categorizer.categorize(
            "vuln-pkg", "npm",
            _make_metrics(repo_count=3, time_in_use_days=90, exposed_cves=5),
        )
        assert blip.ring == Ring.HOLD

    def test_c5_language_package_quadrant(self, db_session):
        """C5: Language category → Languages & Frameworks quadrant."""
        categorizer = RadarCategorizer()
        blip = categorizer.categorize(
            "typescript", "npm",
            _make_metrics(category="language"),
        )
        assert blip.quadrant == Quadrant.LANGUAGES

    def test_c6_custom_rule_respected(self, db_session):
        """C6: Custom min_adopt_repos=20 rule is applied correctly."""
        config = {
            "ring_rules": {
                "adopt": {"min_repo_count": 20, "min_time_in_use_days": 180},
                "trial": {"min_repo_count": 5, "min_time_in_use_days": 90},
                "assess": {"min_repo_count": 2},
                "hold": {},
            },
            "quadrant_mapping": {},
            "exclusions": [],
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp:
            json.dump(config, tmp)
            tmp_path = pathlib.Path(tmp.name)

        try:
            categorizer = RadarCategorizer(config_path=tmp_path)

            # 22 repos + 200 days → Adopt (threshold = 20)
            blip_adopt = categorizer.categorize(
                "lib-above", "npm",
                _make_metrics(repo_count=22, time_in_use_days=200),
            )
            assert blip_adopt.ring == Ring.ADOPT

            # 18 repos + 200 days → NOT Adopt (below custom threshold of 20)
            blip_below = categorizer.categorize(
                "lib-below", "npm",
                _make_metrics(repo_count=18, time_in_use_days=200),
            )
            assert blip_below.ring != Ring.ADOPT
        finally:
            tmp_path.unlink(missing_ok=True)
