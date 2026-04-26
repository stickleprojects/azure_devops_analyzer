"""
Unit tests for RadarCategorizer (Plan 022).

Covers deterministic scenarios (C1–C6) and property-based monotonicity tests.
"""

import pytest
from datetime import date, timedelta

try:
    from hypothesis import given, settings, strategies as st
    HAS_HYPOTHESIS = True
except ImportError:
    HAS_HYPOTHESIS = False
    # Provide stubs so the file is importable without hypothesis installed
    def given(*args, **kwargs):
        def decorator(fn):
            return pytest.mark.skip(reason="hypothesis not installed")(fn)
        return decorator

    def settings(*args, **kwargs):
        def decorator(fn):
            return fn
        return decorator

    class st:
        """Stub for hypothesis.strategies — only present when hypothesis is not installed.
        Methods return None because they are called at class-definition time
        (as decorator arguments); the outer ``given`` stub skips the test.
        """
        @staticmethod
        def integers(**kwargs):
            return None

from src.analyzers.radar_categorization import RadarCategorizer, Ring, Quadrant


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_metrics(**kwargs) -> dict:
    """Return a minimal metrics dict with optional overrides."""
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


# ---------------------------------------------------------------------------
# Deterministic tests (C1–C6)
# ---------------------------------------------------------------------------

class TestCategorizationDeterministic:

    def test_c1_adopt_ring(self):
        """C1: 30 repos, 200 days old → ring=Adopt."""
        categorizer = RadarCategorizer()
        blip = categorizer.categorize(
            "well-used-lib", "npm",
            _make_metrics(repo_count=30, time_in_use_days=200),
        )
        assert blip.ring == Ring.ADOPT

    def test_c2_assess_ring(self):
        """C2: 3 repos, 60 days old → ring=Assess."""
        categorizer = RadarCategorizer()
        blip = categorizer.categorize(
            "small-lib", "npm",
            _make_metrics(repo_count=3, time_in_use_days=60),
        )
        assert blip.ring == Ring.ASSESS

    def test_c3_eol_package_is_hold(self):
        """C3: 1 repo, EOL → ring=Hold."""
        categorizer = RadarCategorizer()
        blip = categorizer.categorize(
            "old-lib", "pypi",
            _make_metrics(repo_count=1, is_eol=True),
        )
        assert blip.ring == Ring.HOLD

    def test_c4_high_cve_exposure_is_hold(self):
        """C4: high CVE exposure, low adoption → ring=Hold."""
        categorizer = RadarCategorizer()
        blip = categorizer.categorize(
            "vuln-lib", "npm",
            _make_metrics(repo_count=3, time_in_use_days=120, exposed_cves=5),
        )
        assert blip.ring == Ring.HOLD

    def test_c5_language_package_quadrant(self):
        """C5: language category → quadrant='Languages & Frameworks'."""
        categorizer = RadarCategorizer()
        blip = categorizer.categorize(
            "python", "pypi",
            _make_metrics(category="language"),
        )
        assert blip.quadrant == Quadrant.LANGUAGES

    def test_c6_custom_rule_min_adopt_repos(self):
        """C6: custom config with min_adopt_repos=20 is respected."""
        import json, tempfile, pathlib
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
            # 22 repos + 190 days → should be Adopt (≥20 threshold)
            blip_adopt = categorizer.categorize(
                "lib-a", "npm",
                _make_metrics(repo_count=22, time_in_use_days=190),
            )
            assert blip_adopt.ring == Ring.ADOPT

            # 18 repos + 200 days → NOT adopt (below custom threshold of 20)
            blip_not_adopt = categorizer.categorize(
                "lib-b", "npm",
                _make_metrics(repo_count=18, time_in_use_days=200),
            )
            assert blip_not_adopt.ring != Ring.ADOPT
        finally:
            tmp_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Additional targeted unit tests
# ---------------------------------------------------------------------------

class TestCategorizationAdditional:

    def test_trial_ring(self):
        """10 repos, 120 days → Trial."""
        categorizer = RadarCategorizer()
        blip = categorizer.categorize(
            "mid-lib", "npm",
            _make_metrics(repo_count=10, time_in_use_days=120),
        )
        assert blip.ring == Ring.TRIAL

    def test_hold_single_repo(self):
        """1 repo, no EOL, no CVE, short time → Hold."""
        categorizer = RadarCategorizer()
        blip = categorizer.categorize(
            "new-lib", "npm",
            _make_metrics(repo_count=1, time_in_use_days=5),
        )
        assert blip.ring == Ring.HOLD

    def test_eol_overrides_high_adoption(self):
        """EOL flag overrides good adoption metrics → Hold."""
        categorizer = RadarCategorizer()
        blip = categorizer.categorize(
            "dead-lib", "npm",
            _make_metrics(repo_count=50, time_in_use_days=1000, is_eol=True),
        )
        assert blip.ring == Ring.HOLD

    def test_cve_overrides_high_adoption(self):
        """CVE exposure overrides good adoption metrics → Hold."""
        categorizer = RadarCategorizer()
        blip = categorizer.categorize(
            "vulnerable-lib", "npm",
            _make_metrics(repo_count=50, time_in_use_days=1000, exposed_cves=3),
        )
        assert blip.ring == Ring.HOLD

    def test_framework_quadrant(self):
        """Framework category → Languages & Frameworks."""
        categorizer = RadarCategorizer()
        blip = categorizer.categorize(
            "django", "pypi",
            _make_metrics(category="framework"),
        )
        assert blip.quadrant == Quadrant.LANGUAGES

    def test_database_quadrant(self):
        """Database category → Platforms."""
        categorizer = RadarCategorizer()
        blip = categorizer.categorize(
            "psycopg2", "pypi",
            _make_metrics(category="database"),
        )
        assert blip.quadrant == Quadrant.PLATFORMS

    def test_docker_quadrant(self):
        """Docker category → Infrastructure."""
        categorizer = RadarCategorizer()
        blip = categorizer.categorize(
            "docker-compose", "docker",
            _make_metrics(category="docker"),
        )
        assert blip.quadrant == Quadrant.INFRASTRUCTURE

    def test_is_new_when_no_prior(self):
        """No prior_ring → is_new=True, is_moved=False."""
        categorizer = RadarCategorizer()
        blip = categorizer.categorize("lib", "npm", _make_metrics(repo_count=30, time_in_use_days=200))
        assert blip.is_new is True
        assert blip.is_moved is False

    def test_is_moved_when_ring_changed(self):
        """Different prior_ring → is_moved=True."""
        categorizer = RadarCategorizer()
        blip = categorizer.categorize(
            "lib", "npm",
            _make_metrics(repo_count=30, time_in_use_days=200),
            prior_ring="Trial",
        )
        assert blip.is_new is False
        assert blip.is_moved is True

    def test_not_moved_when_ring_same(self):
        """Same prior_ring → is_moved=False."""
        categorizer = RadarCategorizer()
        blip = categorizer.categorize(
            "lib", "npm",
            _make_metrics(repo_count=30, time_in_use_days=200),
            prior_ring="Adopt",
        )
        assert blip.is_moved is False

    def test_exclusion_glob(self):
        """test-package-* should be excluded."""
        categorizer = RadarCategorizer()
        assert categorizer.is_excluded("test-package-foo") is True
        assert categorizer.is_excluded("normal-lib") is False

    def test_eol_never_adopt(self):
        """EOL packages are never in Adopt ring."""
        categorizer = RadarCategorizer()
        blip = categorizer.categorize(
            "dead-pkg", "npm",
            _make_metrics(repo_count=100, time_in_use_days=1000, is_eol=True),
        )
        assert blip.ring != Ring.ADOPT

    def test_high_cve_exposure_not_adopt(self):
        """Packages with active CVE exposure are not in Adopt ring."""
        categorizer = RadarCategorizer()
        blip = categorizer.categorize(
            "vuln-pkg", "npm",
            _make_metrics(repo_count=100, time_in_use_days=1000, exposed_cves=1),
        )
        assert blip.ring != Ring.ADOPT


# ---------------------------------------------------------------------------
# Property-based tests
# ---------------------------------------------------------------------------

class TestCategorizationPropertyBased:

    @given(
        repo_count=st.integers(min_value=0, max_value=100),
        time_in_use_days=st.integers(min_value=0, max_value=1000),
    )
    @settings(max_examples=200)
    def test_categorization_returns_valid_ring(self, repo_count, time_in_use_days):
        """Categorizer always returns a valid Ring value."""
        categorizer = RadarCategorizer()
        blip = categorizer.categorize(
            "some-lib", "npm",
            _make_metrics(repo_count=repo_count, time_in_use_days=time_in_use_days),
        )
        assert blip.ring in Ring

    @given(
        repo_count=st.integers(min_value=0, max_value=100),
        time_in_use_days=st.integers(min_value=0, max_value=1000),
    )
    @settings(max_examples=200)
    def test_categorization_eol_never_adopt_property(self, repo_count, time_in_use_days):
        """EOL packages are always Hold, regardless of other metrics."""
        categorizer = RadarCategorizer()
        blip = categorizer.categorize(
            "old-pkg", "npm",
            _make_metrics(
                repo_count=repo_count,
                time_in_use_days=time_in_use_days,
                is_eol=True,
            ),
        )
        assert blip.ring == Ring.HOLD

    @given(
        repo_count=st.integers(min_value=1, max_value=100),
        time_in_use_days=st.integers(min_value=0, max_value=1000),
        exposed_cves=st.integers(min_value=1, max_value=50),
    )
    @settings(max_examples=200)
    def test_cve_exposure_never_adopt_property(self, repo_count, time_in_use_days, exposed_cves):
        """CVE-exposed packages are always Hold, regardless of other metrics."""
        categorizer = RadarCategorizer()
        blip = categorizer.categorize(
            "vuln-pkg", "npm",
            _make_metrics(
                repo_count=repo_count,
                time_in_use_days=time_in_use_days,
                exposed_cves=exposed_cves,
            ),
        )
        assert blip.ring == Ring.HOLD

    @given(
        repo_count_low=st.integers(min_value=0, max_value=24),
        repo_count_high=st.integers(min_value=25, max_value=100),
    )
    @settings(max_examples=100)
    def test_more_repos_not_lower_ring(self, repo_count_low, repo_count_high):
        """A package with more repos should not have a lower ring than one with fewer
        (holding time_in_use_days equal and both at the same level, no health issues)."""
        categorizer = RadarCategorizer()
        days = 500  # high enough to not block Adopt on time

        ring_order = {Ring.ADOPT: 0, Ring.TRIAL: 1, Ring.ASSESS: 2, Ring.HOLD: 3}

        blip_low = categorizer.categorize(
            "lib", "npm",
            _make_metrics(repo_count=repo_count_low, time_in_use_days=days),
        )
        blip_high = categorizer.categorize(
            "lib", "npm",
            _make_metrics(repo_count=repo_count_high, time_in_use_days=days),
        )

        assert ring_order[blip_high.ring] <= ring_order[blip_low.ring], (
            f"Higher repo_count ({repo_count_high}) should give same or better ring "
            f"than lower ({repo_count_low}); got {blip_high.ring} vs {blip_low.ring}"
        )
