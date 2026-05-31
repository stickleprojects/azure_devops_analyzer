"""Unit tests for src.workflows.scope_handling — shared per-scope skip helper.

These tests use ``create_autospec`` rather than bare ``Mock()`` so that
misspelled keyword arguments (e.g. ``project=`` vs ``proj=``) or wrong
positional shapes raise ``TypeError`` at call time, not pass silently. This
is a deliberate guard against the class of bug the user hit when running
against real Azure DevOps credentials — a parameter-passing regression that
existing Mock-based tests would not have detected.
"""

from __future__ import annotations

import logging
from unittest.mock import create_autospec

import pytest

from src.extractors.base import RepositoryExtractor
from src.workflows.scope_handling import list_repositories_or_skip


class _GitHubLikeError(Exception):
    def __init__(self, status: int):
        super().__init__(f"HTTP {status}")
        self.status = status


class _AzureLikeError(Exception):
    def __init__(self, status_code: int):
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code


def _make_extractor():
    """Return an extractor mock that enforces the real RepositoryExtractor API.

    ``create_autospec`` makes the mock reject calls whose argument shapes
    don't match ``RepositoryExtractor.get_repositories(self, organization,
    project=None)``. If the production code ever drifts from the abstract
    signature, these tests fail rather than silently pass.
    """
    return create_autospec(RepositoryExtractor, instance=True)


class TestListRepositoriesOrSkip:
    """Returns repos on success; ``None`` on permission errors; re-raises everything else."""

    def test_returns_repos_on_success_with_project(self):
        extractor = _make_extractor()
        extractor.get_repositories.return_value = ["repo-a", "repo-b"]

        result = list_repositories_or_skip(
            extractor, "myorg", project="myproject", scope_label="project myorg/myproject"
        )

        assert result == ["repo-a", "repo-b"]
        extractor.get_repositories.assert_called_once_with("myorg", project="myproject")

    def test_returns_repos_on_success_without_project(self):
        """GitHub-shape call: no project kwarg passed when project=None."""
        extractor = _make_extractor()
        extractor.get_repositories.return_value = ["repo-x"]

        result = list_repositories_or_skip(extractor, "myorg", scope_label="org myorg")

        assert result == ["repo-x"]
        extractor.get_repositories.assert_called_once_with("myorg")

    @pytest.mark.parametrize("status", [401, 403, 404])
    def test_skips_on_github_permission_error(self, status, caplog):
        extractor = _make_extractor()
        extractor.get_repositories.side_effect = _GitHubLikeError(status)

        with caplog.at_level(logging.WARNING):
            result = list_repositories_or_skip(
                extractor, "myorg", scope_label="org myorg"
            )

        assert result is None
        assert any("Skipping org myorg" in rec.message for rec in caplog.records)
        assert any(str(status) in rec.message for rec in caplog.records)

    @pytest.mark.parametrize("status", [401, 403, 404])
    def test_skips_on_azure_permission_error(self, status, caplog):
        extractor = _make_extractor()
        extractor.get_repositories.side_effect = _AzureLikeError(status)

        with caplog.at_level(logging.WARNING):
            result = list_repositories_or_skip(
                extractor, "myorg", project="proj", scope_label="project myorg/proj"
            )

        assert result is None
        assert any("Skipping project myorg/proj" in rec.message for rec in caplog.records)

    def test_reraises_non_permission_exceptions(self):
        """Server errors, rate limits, and unrelated failures must propagate."""
        extractor = _make_extractor()
        extractor.get_repositories.side_effect = _AzureLikeError(500)

        with pytest.raises(_AzureLikeError):
            list_repositories_or_skip(
                extractor, "myorg", project="proj", scope_label="project myorg/proj"
            )

    def test_reraises_rate_limit_429(self):
        """429 is a transient, not a permission issue — must propagate so the
        extractor's retry-with-backoff path stays in charge."""
        extractor = _make_extractor()
        extractor.get_repositories.side_effect = _GitHubLikeError(429)

        with pytest.raises(_GitHubLikeError):
            list_repositories_or_skip(extractor, "myorg", scope_label="org myorg")

    def test_reraises_unrelated_exception(self):
        extractor = _make_extractor()
        extractor.get_repositories.side_effect = ValueError("unexpected")

        with pytest.raises(ValueError):
            list_repositories_or_skip(extractor, "myorg", scope_label="org myorg")


class TestRespectsAbstractSignature:
    """Regression guard against parameter-shape drift.

    If someone changes ``RepositoryExtractor.get_repositories`` to add a
    required argument, or renames ``project=`` to something else, the
    autospec-bound mock will reject the call we make from
    ``list_repositories_or_skip`` and these tests will fail. That's the
    intended behaviour — these are the contract checks.
    """

    def test_helper_call_matches_abstract_signature(self):
        extractor = _make_extractor()
        extractor.get_repositories.return_value = []

        list_repositories_or_skip(extractor, "org", scope_label="org x")
        list_repositories_or_skip(
            extractor, "org", project="p", scope_label="project x/p"
        )

    def test_misspelled_kwarg_would_fail(self):
        """Sanity check: an extractor whose signature does NOT have ``project=``
        would correctly reject our call. (We invoke the spec directly to
        prove the contract is being enforced.)"""
        extractor = _make_extractor()
        # The autospec extractor's get_repositories accepts ``project=``;
        # if we pass an unknown kwarg, it raises TypeError. This is the
        # protection that bare Mock() lacks.
        with pytest.raises(TypeError):
            extractor.get_repositories("org", projct="typo")  # noqa: misspelling on purpose
