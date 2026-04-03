"""
Unit tests for _version_is_affected() helper in dependency_enricher.

Tests the version comparison logic that determines whether a repo's pinned
version of a package is below the fixed_in_version of a CVE (i.e. exposed).
"""

import pytest
from src.analyzers.dependency_enricher import _version_is_affected


class TestVersionIsAffected:

    def test_current_below_fixed_is_affected(self):
        """3.10.0 < 4.17.21 → True (repo is exposed)."""
        assert _version_is_affected("3.10.0", "4.17.21") is True

    def test_current_at_fixed_is_not_affected(self):
        """At the fix boundary (current == fixed_in) is considered safe."""
        assert _version_is_affected("4.17.21", "4.17.21") is False

    def test_current_above_fixed_is_not_affected(self):
        """4.18.0 > 4.17.21 → False (repo is patched)."""
        assert _version_is_affected("4.18.0", "4.17.21") is False

    def test_patch_version_below_fixed(self):
        """2.28.0 < 2.29.0 → True."""
        assert _version_is_affected("2.28.0", "2.29.0") is True

    def test_patch_version_equal_to_fixed(self):
        """2.29.0 == 2.29.0 → False."""
        assert _version_is_affected("2.29.0", "2.29.0") is False

    def test_major_version_difference(self):
        """1.x is below 2.0.0 → True."""
        assert _version_is_affected("1.99.99", "2.0.0") is True

    def test_none_current_version(self):
        """None current version → False (fail safe)."""
        assert _version_is_affected(None, "4.17.21") is False

    def test_none_fixed_in_version(self):
        """None fixed_in → False (no known fix, can't determine exposure)."""
        assert _version_is_affected("3.10.0", None) is False

    def test_both_none(self):
        """Both None → False."""
        assert _version_is_affected(None, None) is False

    def test_unparseable_current_version(self):
        """Unparseable current version → False (fail safe)."""
        assert _version_is_affected("not-a-version", "4.17.21") is False

    def test_unparseable_fixed_version(self):
        """Unparseable fixed_in → False (fail safe)."""
        assert _version_is_affected("3.10.0", "not-a-version") is False

    def test_both_unparseable(self):
        """Both unparseable → False."""
        assert _version_is_affected("??", "??") is False

    def test_prerelease_below_fixed(self):
        """Pre-release versions: 1.0.0a1 < 1.0.0 → True (alpha is below release)."""
        assert _version_is_affected("1.0.0a1", "1.0.0") is True

    def test_empty_string_current(self):
        """Empty string current → False (fail safe)."""
        assert _version_is_affected("", "4.17.21") is False

    def test_empty_string_fixed(self):
        """Empty string fixed_in → False (fail safe)."""
        assert _version_is_affected("3.10.0", "") is False
