"""Workflow-level tests for GitHubAnalysisWorkflow.

Mirror of ``test_azure_devops_workflow.py`` so the two platforms have parity
in test coverage of the workflow→extractor contract. See the module docstring
of the Azure version for the rationale (parameter-passing regressions slipping
past existing tests because nothing drove ``run()`` end-to-end with a
signature-bound mock).

GitHub's extraction hierarchy is org → repos (no project layer), so the
"skip the scope on permission error" behaviour applies at the org boundary.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from unittest.mock import DEFAULT, MagicMock, create_autospec, patch

import pytest

from src.extractors.base import OrganizationData, Platform
from src.extractors.github.extractor import GitHubExtractor
from src.workflows.github_analysis import GitHubAnalysisWorkflow


@contextmanager
def _fake_session_scope():
    yield MagicMock()


class _GitHubLikeError(Exception):
    """Stand-in for ``github.GithubException`` — carries ``.status``."""

    def __init__(self, status: int):
        super().__init__(f"HTTP {status}")
        self.status = status


def _org(name: str = "acme") -> OrganizationData:
    return OrganizationData(
        name=name,
        url=f"https://github.com/{name}",
        platform=Platform.GITHUB,
    )


@pytest.fixture
def patched_workflow_module():
    """Patch out DB & health-check side effects in the GitHub workflow module."""
    summary = {
        "organizations": 1,
        "projects": 1,
        "repositories": 0,
        "branches": 0,
        "commits": 0,
        "pull_requests": 0,
        "contributors": 0,
        "dependencies": 0,
    }
    with patch.multiple(
        "src.workflows.github_analysis",
        session_scope=_fake_session_scope,
        store_organization=DEFAULT,
        store_project=DEFAULT,
        start_extraction_run=DEFAULT,
        update_extraction_run_progress=DEFAULT,
        complete_extraction_run=DEFAULT,
        fail_extraction_run=DEFAULT,
        get_extraction_summary=DEFAULT,
    ) as mocks, patch(
        "src.utils.extraction_health.compute_extraction_health",
        return_value=MagicMock(is_healthy=True),
    ), patch(
        "src.utils.metrics.emit_health_report"
    ):
        mocks["store_organization"].return_value = MagicMock(organization_id=1)
        mocks["store_project"].return_value = MagicMock(project_id=1)
        mocks["start_extraction_run"].return_value = "run-id-xyz"
        mocks["get_extraction_summary"].return_value = summary
        yield mocks


@pytest.fixture
def autospec_extractor():
    """A GitHubExtractor mock that enforces the real method signatures.

    Calls with a typo'd kwarg (e.g. ``organisation=`` instead of ``organization=``)
    raise ``TypeError`` here rather than passing silently as bare ``Mock()`` would.
    """
    return create_autospec(GitHubExtractor, instance=True)


class TestExtractorCallShape:
    """Lock in the exact extractor call sequence and argument shape for GitHub."""

    def test_get_organizations_called_with_no_args(
        self, patched_workflow_module, autospec_extractor
    ):
        autospec_extractor.get_organizations.return_value = [_org()]
        autospec_extractor.get_repositories.return_value = []

        GitHubAnalysisWorkflow(extractor=autospec_extractor).run()

        autospec_extractor.get_organizations.assert_called_once_with()

    def test_get_repositories_called_with_org_name_positional(
        self, patched_workflow_module, autospec_extractor
    ):
        """GitHub has no project layer; the helper must call
        ``get_repositories(org)`` with no ``project=`` kwarg."""
        autospec_extractor.get_organizations.return_value = [_org("acme")]
        autospec_extractor.get_repositories.return_value = []

        GitHubAnalysisWorkflow(extractor=autospec_extractor).run()

        autospec_extractor.get_repositories.assert_called_once_with("acme")

    def test_iterates_all_orgs_in_order(
        self, patched_workflow_module, autospec_extractor
    ):
        autospec_extractor.get_organizations.return_value = [
            _org("org-a"),
            _org("org-b"),
            _org("org-c"),
        ]
        autospec_extractor.get_repositories.return_value = []

        GitHubAnalysisWorkflow(extractor=autospec_extractor).run()

        called_orgs = [
            call.args[0]
            for call in autospec_extractor.get_repositories.call_args_list
        ]
        assert called_orgs == ["org-a", "org-b", "org-c"]


class TestSkipsInaccessibleOrg:
    """A 403 on one org must not abort the rest of the run."""

    def test_403_on_middle_org_continues_to_next(
        self, patched_workflow_module, autospec_extractor, caplog
    ):
        autospec_extractor.get_organizations.return_value = [
            _org("Accessible1"),
            _org("Forbidden"),
            _org("Accessible2"),
        ]

        def get_repos_side_effect(organization):
            if organization == "Forbidden":
                raise _GitHubLikeError(403)
            return []

        autospec_extractor.get_repositories.side_effect = get_repos_side_effect

        with caplog.at_level(logging.WARNING):
            GitHubAnalysisWorkflow(extractor=autospec_extractor).run()

        assert autospec_extractor.get_repositories.call_count == 3
        skip_records = [
            rec for rec in caplog.records
            if "Skipping" in rec.message and "Forbidden" in rec.message
        ]
        assert len(skip_records) == 1

    def test_start_extraction_run_not_called_for_skipped_org(
        self, patched_workflow_module, autospec_extractor
    ):
        autospec_extractor.get_organizations.return_value = [
            _org("Forbidden"),
            _org("Ok"),
        ]
        autospec_extractor.get_repositories.side_effect = [
            _GitHubLikeError(403),
            [],
        ]

        GitHubAnalysisWorkflow(extractor=autospec_extractor).run()

        start_run = patched_workflow_module["start_extraction_run"]
        assert start_run.call_count == 1
        assert start_run.call_args.kwargs["organization_name"] == "Ok"

    @pytest.mark.parametrize("status", [401, 403, 404])
    def test_all_permission_statuses_treated_as_skip(
        self, status, patched_workflow_module, autospec_extractor
    ):
        autospec_extractor.get_organizations.return_value = [
            _org("A"),
            _org("B"),
        ]
        autospec_extractor.get_repositories.side_effect = [
            _GitHubLikeError(status),
            [],
        ]

        # Should not raise.
        GitHubAnalysisWorkflow(extractor=autospec_extractor).run()

        assert autospec_extractor.get_repositories.call_count == 2

    def test_500_on_org_aborts_workflow(
        self, patched_workflow_module, autospec_extractor
    ):
        autospec_extractor.get_organizations.return_value = [_org("A"), _org("B")]
        autospec_extractor.get_repositories.side_effect = _GitHubLikeError(500)

        with pytest.raises(_GitHubLikeError):
            GitHubAnalysisWorkflow(extractor=autospec_extractor).run()

        assert autospec_extractor.get_repositories.call_count == 1

    def test_rate_limit_429_aborts_workflow(
        self, patched_workflow_module, autospec_extractor
    ):
        """429 is transient — must propagate so the retry-with-backoff path
        in the extractor (not the workflow skip path) handles it."""
        autospec_extractor.get_organizations.return_value = [_org("A"), _org("B")]
        autospec_extractor.get_repositories.side_effect = _GitHubLikeError(429)

        with pytest.raises(_GitHubLikeError):
            GitHubAnalysisWorkflow(extractor=autospec_extractor).run()
