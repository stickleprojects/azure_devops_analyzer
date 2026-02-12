"""Unit tests for the extractor caching decorator."""

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

import pytest

from src.extractors.cache import (
    _NONE_SENTINEL,
    _file_cache_path,
    _make_cache_key,
    _normalize_arg,
    cached,
)
from src.extractors.base import RepositoryExtractor


# ---------------------------------------------------------------------------
# Concrete stub so we can instantiate the ABC
# ---------------------------------------------------------------------------

class _StubExtractor(RepositoryExtractor):
    """Minimal concrete extractor used only in these tests."""

    @property
    def platform(self):
        return "stub"

    def get_organizations(self):
        return []

    def get_projects(self, organization):
        return []

    def get_repositories(self, organization, project=None):
        return []

    def get_repository(self, repo_id):
        raise NotImplementedError

    def get_branches(self, repo_id):
        return []

    def get_languages(self, repo_id):
        return []

    def get_commits(self, repo_id, branch=None, since=None, until=None, limit=None):
        return []

    def get_pull_requests(self, repo_id, status=None, since=None):
        return []

    def get_file_tree(self, repo_id, branch=None):
        return []

    def get_file_content(self, repo_id, file_path, branch=None):
        return None


# ---------------------------------------------------------------------------
# _normalize_arg
# ---------------------------------------------------------------------------

class TestNormalizeArg:
    def test_none_returns_sentinel(self):
        assert _normalize_arg(None) == _NONE_SENTINEL

    def test_datetime_returns_iso(self):
        dt = datetime(2025, 6, 15, 12, 30, 0, tzinfo=timezone.utc)
        assert _normalize_arg(dt) == dt.isoformat()

    def test_naive_datetime_returns_iso(self):
        dt = datetime(2025, 1, 1, 0, 0, 0)
        assert _normalize_arg(dt) == "2025-01-01T00:00:00"

    def test_string_passthrough(self):
        assert _normalize_arg("hello") == "hello"

    def test_int_becomes_string(self):
        assert _normalize_arg(42) == "42"

    def test_bool_becomes_string(self):
        assert _normalize_arg(True) == "True"


# ---------------------------------------------------------------------------
# _make_cache_key
# ---------------------------------------------------------------------------

class TestMakeCacheKey:
    def test_method_only(self):
        key = _make_cache_key("get_branches", (), {})
        assert key == "get_branches"

    def test_positional_args(self):
        key = _make_cache_key("get_file_content", ("owner/repo", "README.md"), {})
        assert key == "get_file_content|owner/repo|README.md"

    def test_kwargs_sorted(self):
        key = _make_cache_key("get_commits", (), {"branch": "main", "limit": 100})
        assert key == "get_commits|branch=main|limit=100"

    def test_mixed_args_and_kwargs(self):
        key = _make_cache_key("get_file_content", ("owner/repo",), {"branch": "dev"})
        assert key == "get_file_content|owner/repo|branch=dev"

    def test_none_kwarg_uses_sentinel(self):
        key = _make_cache_key("get_file_tree", ("r",), {"branch": None})
        assert _NONE_SENTINEL in key

    def test_datetime_kwarg(self):
        dt = datetime(2025, 3, 1, tzinfo=timezone.utc)
        key = _make_cache_key("get_commits", (), {"since": dt})
        assert "2025-03-01" in key

    def test_different_args_produce_different_keys(self):
        k1 = _make_cache_key("m", ("a",), {})
        k2 = _make_cache_key("m", ("b",), {})
        assert k1 != k2


# ---------------------------------------------------------------------------
# @cached decorator — behaviour
# ---------------------------------------------------------------------------

class TestCachedDecorator:
    """Test the @cached decorator on a real extractor instance."""

    def _make_extractor(self):
        """Create a stub extractor with a cached method backed by a mock."""
        ext = _StubExtractor()
        ext._underlying = MagicMock(return_value=["file1", "file2"])

        # Attach a cached method dynamically
        @cached
        def get_file_tree(self, repo_id, branch=None):
            return self._underlying(repo_id, branch)

        # Bind it as an unbound function so the decorator's `self` works
        import types
        ext.get_file_tree = types.MethodType(get_file_tree, ext)
        return ext

    def test_first_call_is_cache_miss(self):
        ext = self._make_extractor()
        result = ext.get_file_tree("owner/repo")

        assert result == ["file1", "file2"]
        assert ext._cache_misses == 1
        assert ext._cache_hits == 0
        ext._underlying.assert_called_once_with("owner/repo", None)

    def test_second_call_is_cache_hit(self):
        ext = self._make_extractor()
        ext.get_file_tree("owner/repo")
        ext.get_file_tree("owner/repo")

        assert ext._cache_hits == 1
        assert ext._cache_misses == 1
        # Underlying called only once
        ext._underlying.assert_called_once()

    def test_cache_hit_returns_same_object(self):
        ext = self._make_extractor()
        first = ext.get_file_tree("owner/repo")
        second = ext.get_file_tree("owner/repo")
        assert first is second

    def test_different_args_are_separate_entries(self):
        ext = self._make_extractor()
        ext.get_file_tree("repo-a")
        ext.get_file_tree("repo-b")

        assert ext._cache_misses == 2
        assert ext._cache_hits == 0
        assert ext._underlying.call_count == 2

    def test_different_kwargs_are_separate_entries(self):
        ext = self._make_extractor()
        ext.get_file_tree("repo", branch="main")
        ext.get_file_tree("repo", branch="dev")

        assert ext._cache_misses == 2

    def test_explicit_none_kwarg_vs_omitted_are_separate(self):
        """branch=None (explicit) and omitted branch produce different keys.

        The decorator operates on raw *args/**kwargs and cannot see default
        parameter values, so these are treated as distinct calls. In practice
        callers use consistent call patterns, so this does not cause issues.
        """
        ext = self._make_extractor()
        ext.get_file_tree("repo", branch=None)
        ext.get_file_tree("repo")  # branch omitted entirely

        # Two distinct cache entries
        assert ext._cache_misses == 2
        assert ext._cache_hits == 0


# ---------------------------------------------------------------------------
# clear_cache / cache_stats on RepositoryExtractor
# ---------------------------------------------------------------------------

class TestCacheManagement:

    def test_initial_state(self):
        ext = _StubExtractor()
        assert ext.cache_stats == {"hits": 0, "misses": 0, "size": 0, "methods": {}}

    def test_cache_stats_after_usage(self):
        ext = _StubExtractor()
        ext._cache["some_key"] = "value"
        ext._cache_hits = 3
        ext._cache_misses = 5
        ext._cache_method_stats["get_file_tree"] = {"hits": 2, "misses": 1}
        stats = ext.cache_stats
        assert stats == {
            "hits": 3,
            "misses": 5,
            "size": 1,
            "methods": {"get_file_tree": {"hits": 2, "misses": 1}},
        }

    def test_clear_cache_resets_everything(self):
        ext = _StubExtractor()
        ext._cache["k1"] = "v1"
        ext._cache["k2"] = "v2"
        ext._cache_hits = 10
        ext._cache_misses = 7
        ext._cache_method_stats["get_file_tree"] = {"hits": 5, "misses": 3}

        ext.clear_cache()

        assert ext._cache == {}
        assert ext._cache_hits == 0
        assert ext._cache_misses == 0
        assert ext._cache_method_stats == {}
        assert ext.cache_stats == {"hits": 0, "misses": 0, "size": 0, "methods": {}}

    def test_method_stats_tracked_by_decorator(self):
        """Per-method hit/miss counters are populated by the @cached decorator."""
        ext = _StubExtractor()
        ext._underlying_tree = MagicMock(return_value=["f1"])
        ext._underlying_content = MagicMock(return_value="data")

        import types

        @cached
        def get_file_tree(self, repo_id, branch=None):
            return self._underlying_tree(repo_id, branch)

        @cached
        def get_file_content(self, repo_id, file_path, branch=None):
            return self._underlying_content(repo_id, file_path, branch)

        ext.get_file_tree = types.MethodType(get_file_tree, ext)
        ext.get_file_content = types.MethodType(get_file_content, ext)

        # 1 miss + 2 hits on get_file_tree
        ext.get_file_tree("repo")
        ext.get_file_tree("repo")
        ext.get_file_tree("repo")
        # 2 misses on get_file_content (different file paths)
        ext.get_file_content("repo", "README.md")
        ext.get_file_content("repo", "setup.py")

        stats = ext.cache_stats
        assert stats["methods"]["get_file_tree"] == {"hits": 2, "misses": 1}
        assert stats["methods"]["get_file_content"] == {"hits": 0, "misses": 2}
        assert stats["hits"] == 2
        assert stats["misses"] == 3

    def test_clear_cache_allows_fresh_calls(self):
        """After clear_cache, a previously-cached key triggers a new miss."""
        ext = _StubExtractor()
        ext._cache["get_file_tree|repo"] = ["old"]
        ext._cache_hits = 1

        ext.clear_cache()

        # Simulate a miss after clear
        assert "get_file_tree|repo" not in ext._cache


# ---------------------------------------------------------------------------
# File cache behavior
# ---------------------------------------------------------------------------


class TestFileCache:
    def _make_extractor(self):
        ext = _StubExtractor()
        ext._underlying = MagicMock(return_value=["file1", "file2"])

        @cached
        def get_file_tree(self, repo_id, branch=None):
            return self._underlying(repo_id, branch)

        import types

        ext.get_file_tree = types.MethodType(get_file_tree, ext)
        return ext

    def test_file_cache_hit_across_instances(self, tmp_path, monkeypatch):
        monkeypatch.setenv("EXTRACTOR_FILE_CACHE_ENABLED", "true")
        monkeypatch.setenv("EXTRACTOR_FILE_CACHE_PATH", str(tmp_path))

        ext1 = self._make_extractor()
        ext1.get_file_tree("owner/repo")

        ext2 = self._make_extractor()
        result = ext2.get_file_tree("owner/repo")

        assert result == ["file1", "file2"]
        assert ext2._cache_hits == 1
        assert ext2._cache_misses == 0
        ext2._underlying.assert_not_called()

    def test_file_cache_disabled_does_not_write(self, tmp_path, monkeypatch):
        monkeypatch.setenv("EXTRACTOR_FILE_CACHE_ENABLED", "false")
        monkeypatch.setenv("EXTRACTOR_FILE_CACHE_PATH", str(tmp_path))

        ext = self._make_extractor()
        ext.get_file_tree("owner/repo")

        assert list(tmp_path.rglob("*.json")) == []

    def test_corrupt_file_cache_treated_as_miss(self, tmp_path, monkeypatch):
        monkeypatch.setenv("EXTRACTOR_FILE_CACHE_ENABLED", "true")
        monkeypatch.setenv("EXTRACTOR_FILE_CACHE_PATH", str(tmp_path))

        ext = self._make_extractor()
        key = _make_cache_key("get_file_tree", ("owner/repo",), {})
        cache_path = _file_cache_path("get_file_tree", key)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text("not-json", encoding="utf-8")

        result = ext.get_file_tree("owner/repo")

        assert result == ["file1", "file2"]
        assert ext._cache_misses == 1
        ext._underlying.assert_called_once_with("owner/repo", None)
