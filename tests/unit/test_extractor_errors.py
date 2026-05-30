"""Unit tests for src.extractors.errors — cross-platform permission classifier."""

from __future__ import annotations

import pytest

from src.extractors.errors import http_status, is_permission_error


class _GitHubLikeError(Exception):
    """Minimal stand-in for ``github.GithubException`` — carries ``.status``."""

    def __init__(self, status: int):
        super().__init__(f"HTTP {status}")
        self.status = status


class _AzureLikeError(Exception):
    """Minimal stand-in for ``AzureDevOpsServiceError`` — carries ``.status_code``."""

    def __init__(self, status_code: int, inner_status_code: int | None = None):
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code
        if inner_status_code is not None:
            inner = type("Inner", (), {"status_code": inner_status_code})()
            self.inner_exception = inner
        else:
            self.inner_exception = None


class TestHttpStatus:
    """``http_status`` should locate the numeric status across attribute shapes."""

    def test_github_status_attribute(self):
        assert http_status(_GitHubLikeError(403)) == 403

    def test_azure_status_code_attribute(self):
        assert http_status(_AzureLikeError(403)) == 403

    def test_azure_inner_exception_status_code(self):
        """Azure DevOps SDK wraps the real HTTP error in ``inner_exception``."""
        outer = _AzureLikeError(status_code=0, inner_status_code=403)
        # outer.status_code is 0 (falsy but a valid int), still returned first
        assert outer.status_code == 0
        # Force the outer to lack a usable status so we test the inner-fallback path
        del outer.status_code
        assert http_status(outer) == 403

    def test_returns_none_when_no_status(self):
        assert http_status(ValueError("nope")) is None

    def test_non_int_status_ignored(self):
        """A non-int ``status`` (e.g. a string) must not be returned."""
        exc = Exception()
        exc.status = "403"  # type: ignore[attr-defined]
        assert http_status(exc) is None


class TestIsPermissionError:
    """``is_permission_error`` should treat 401/403/404 as 'no access'."""

    @pytest.mark.parametrize("status", [401, 403, 404])
    def test_github_permission_statuses(self, status):
        assert is_permission_error(_GitHubLikeError(status)) is True

    @pytest.mark.parametrize("status", [401, 403, 404])
    def test_azure_permission_statuses(self, status):
        assert is_permission_error(_AzureLikeError(status)) is True

    @pytest.mark.parametrize("status", [200, 400, 429, 500, 502, 503])
    def test_non_permission_statuses(self, status):
        """Other statuses (incl. rate-limit 429 and server errors) are not 'permission'."""
        assert is_permission_error(_GitHubLikeError(status)) is False
        assert is_permission_error(_AzureLikeError(status)) is False

    def test_unrelated_exception_is_not_permission(self):
        assert is_permission_error(ValueError("boom")) is False

    def test_azure_inner_403_via_fallback(self):
        outer = _AzureLikeError(status_code=0, inner_status_code=403)
        del outer.status_code
        assert is_permission_error(outer) is True
