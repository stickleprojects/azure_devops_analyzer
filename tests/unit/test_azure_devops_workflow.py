"""Workflow-level tests for AzureDevOpsAnalysisWorkflow.

These tests target the class of bug that motivated this refactor: a
parameter-passing regression between the workflow and the extractor that
slipped past every existing unit test because nothing actually drove
``AzureDevOpsAnalysisWorkflow.run()`` end-to-end.

The defining property of these tests is that the extractor is built with
``create_autospec(AzureDevOpsExtractor, instance=True)``. Autospec binds the
mock to the real class's method signatures, so a workflow call like
``self.extractor.get_repositories(organisation="x")`` (typo in kwarg name)
raises ``TypeError`` at test time instead of silently succeeding.

The database and health-check side effects are patched out — these tests are
about call shape, not persistence behaviour.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import DEFAULT, MagicMock, create_autospec, patch

import pytest

from src.extractors.azure_devops.extractor import AzureDevOpsExtractor
from src.extractors.base import OrganizationData, Platform, ProjectData
from src.workflows.azure_devops_analysis import AzureDevOpsAnalysisWorkflow


@contextmanager
def _fake_session_scope():
    yield MagicMock()


class _AzureLikeError(Exception):
    """Stand-in for AzureDevOpsServiceError — carries ``.status_code``."""

    def __init__(self, status_code: int):
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code


def _org(name: str = "myorg") -> OrganizationData:
    return OrganizationData(
        name=name,
        url=f"https://dev.azure.com/{name}",
        platform=Platform.AZURE_DEVOPS,
    )


def _proj(name: str) -> ProjectData:
    return ProjectData(name=name, description=None, organization_name="myorg")


@pytest.fixture
def patched_workflow_module():
    """Patch out DB & health-check side effects in the workflow module.

    Uses ``DEFAULT`` for everything so ``patch.multiple`` returns the mocks
    in the yielded dict and tests can introspect call counts/args.
    """
    summary = {
        "organizations": 1,
        "projects": 0,
        "repositories": 0,
        "branches": 0,
        "commits": 0,
        "pull_requests": 0,
        "contributors": 0,
        "dependencies": 0,
    }
    with patch.multiple(
        "src.workflows.azure_devops_analysis",
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
    """An AzureDevOpsExtractor mock that enforces the real method signatures.

    Calls with the wrong kwarg name (e.g. ``project_name=`` instead of
    ``project=``) raise ``TypeError`` here.
    """
    return create_autospec(AzureDevOpsExtractor, instance=True)


class TestExtractorCallShape:
    """Lock in the exact extractor call sequence and argument shape.

    These are contract tests: a regression in how the workflow calls the
    extractor surfaces here as a test failure rather than as a 4am
    "extraction failed" page from production.
    """

    def test_get_organizations_called_with_no_args(
        self, patched_workflow_module, autospec_extractor
    ):
        autospec_extractor.get_organizations.return_value = [_org()]
        autospec_extractor.get_projects.return_value = []

        AzureDevOpsAnalysisWorkflow(extractor=autospec_extractor).run()

        autospec_extractor.get_organizations.assert_called_once_with()

    def test_get_projects_called_with_org_name_positional(
        self, patched_workflow_module, autospec_extractor
    ):
        autospec_extractor.get_organizations.return_value = [_org("acme")]
        autospec_extractor.get_projects.return_value = []

        AzureDevOpsAnalysisWorkflow(extractor=autospec_extractor).run()

        autospec_extractor.get_projects.assert_called_once_with("acme")

    def test_get_repositories_called_with_org_positional_and_project_kwarg(
        self, patched_workflow_module, autospec_extractor
    ):
        """The regression guard: the second arg must be ``project=...``,
        not ``project_name=...`` or positional."""
        autospec_extractor.get_organizations.return_value = [_org("acme")]
        autospec_extractor.get_projects.return_value = [_proj("Payments")]
        autospec_extractor.get_repositories.return_value = []

        AzureDevOpsAnalysisWorkflow(extractor=autospec_extractor).run()

        autospec_extractor.get_repositories.assert_called_once_with(
            "acme", project="Payments"
        )

    def test_iterates_all_projects_in_order(
        self, patched_workflow_module, autospec_extractor
    ):
        autospec_extractor.get_organizations.return_value = [_org()]
        autospec_extractor.get_projects.return_value = [
            _proj("P1"),
            _proj("P2"),
            _proj("P3"),
        ]
        autospec_extractor.get_repositories.return_value = []

        AzureDevOpsAnalysisWorkflow(extractor=autospec_extractor).run()

        called_projects = [
            call.kwargs["project"]
            for call in autospec_extractor.get_repositories.call_args_list
        ]
        assert called_projects == ["P1", "P2", "P3"]


class TestSkipsInaccessibleProject:
    """The behaviour change shipped on this branch: a 403 on one project
    must not abort the rest of the run."""

    def test_403_on_middle_project_continues_to_next(
        self, patched_workflow_module, autospec_extractor, caplog
    ):
        autospec_extractor.get_organizations.return_value = [_org()]
        autospec_extractor.get_projects.return_value = [
            _proj("Accessible1"),
            _proj("Forbidden"),
            _proj("Accessible2"),
        ]

        def get_repos_side_effect(organization, project=None):
            if project == "Forbidden":
                raise _AzureLikeError(403)
            return []

        autospec_extractor.get_repositories.side_effect = get_repos_side_effect

        with caplog.at_level(logging.WARNING):
            AzureDevOpsAnalysisWorkflow(extractor=autospec_extractor).run()

        # All three projects attempted — the forbidden one did not abort.
        assert autospec_extractor.get_repositories.call_count == 3
        # Visible skip log fired exactly once, naming the project.
        skip_records = [
            rec for rec in caplog.records
            if "Skipping" in rec.message and "Forbidden" in rec.message
        ]
        assert len(skip_records) == 1

    def test_start_extraction_run_not_called_for_skipped_project(
        self, patched_workflow_module, autospec_extractor
    ):
        """A skipped project must not leave an extraction_run row behind —
        the early return happens before ``start_extraction_run``."""
        autospec_extractor.get_organizations.return_value = [_org()]
        autospec_extractor.get_projects.return_value = [
            _proj("Forbidden"),
            _proj("Ok"),
        ]
        autospec_extractor.get_repositories.side_effect = [
            _AzureLikeError(403),
            [],
        ]

        AzureDevOpsAnalysisWorkflow(extractor=autospec_extractor).run()

        start_run = patched_workflow_module["start_extraction_run"]
        assert start_run.call_count == 1
        # The single call was for the accessible project.
        assert start_run.call_args.kwargs["project_name"] == "Ok"

    @pytest.mark.parametrize("status", [401, 403, 404])
    def test_all_permission_statuses_treated_as_skip(
        self, status, patched_workflow_module, autospec_extractor
    ):
        autospec_extractor.get_organizations.return_value = [_org()]
        autospec_extractor.get_projects.return_value = [_proj("A"), _proj("B")]
        autospec_extractor.get_repositories.side_effect = [
            _AzureLikeError(status),
            [],
        ]

        # Should not raise.
        AzureDevOpsAnalysisWorkflow(extractor=autospec_extractor).run()

        assert autospec_extractor.get_repositories.call_count == 2

    def test_500_on_project_aborts_workflow(
        self, patched_workflow_module, autospec_extractor
    ):
        """Server errors are not 'permission denied' — they must propagate so
        the operator sees something is wrong, not get a silent partial run."""
        autospec_extractor.get_organizations.return_value = [_org()]
        autospec_extractor.get_projects.return_value = [_proj("A"), _proj("B")]
        autospec_extractor.get_repositories.side_effect = _AzureLikeError(500)

        with pytest.raises(_AzureLikeError):
            AzureDevOpsAnalysisWorkflow(extractor=autospec_extractor).run()

        # Aborted after the first project — never reached the second.
        assert autospec_extractor.get_repositories.call_count == 1


class TestTechnologyPersistence:
    """Regression coverage for technology detection persistence on Azure runs."""

    def test_process_technologies_persists_detected_stack(self, autospec_extractor):
        repo_data = MagicMock(repo_id="org/proj/repo", name="repo")
        autospec_extractor.get_file_tree.return_value = [MagicMock(path="requirements.txt")]
        detection = SimpleNamespace(
            all_technologies=["Django"],
            primary_language="Python",
            frameworks=["Django"],
            databases=[],
        )

        with patch(
            "src.workflows.azure_devops_analysis.TechnologyDetector"
        ) as detector_cls, patch(
            "src.workflows.azure_devops_analysis.store_detections"
        ) as store_detections_mock, patch(
            "src.workflows.azure_devops_analysis.session_scope"
        ) as session_scope_mock:
            detector_cls.return_value.detect.return_value = detection
            store_detections_mock.return_value = []
            session_scope_mock.return_value = _fake_session_scope()

            workflow = AzureDevOpsAnalysisWorkflow(extractor=autospec_extractor)
            workflow._process_technologies(repo_data)

        store_detections_mock.assert_called_once()
        assert store_detections_mock.call_args.args[1] == repo_data.repo_id
        assert store_detections_mock.call_args.args[2] is detection

    def test_process_technologies_enriches_stale_eol_rows(self, autospec_extractor):
        repo_data = MagicMock(repo_id="org/proj/repo", name="repo")
        autospec_extractor.get_file_tree.return_value = [MagicMock(path="package.json")]
        detection = SimpleNamespace(
            all_technologies=["React"],
            primary_language="TypeScript",
            frameworks=["React"],
            databases=[],
        )
        stored_entries = [SimpleNamespace(name="React", category="framework")]

        store_session = MagicMock()
        query_session = MagicMock()
        query_session.query.return_value.filter.return_value.all.return_value = []

        @contextmanager
        def _scope_for(session):
            yield session

        with patch(
            "src.workflows.azure_devops_analysis.TechnologyDetector"
        ) as detector_cls, patch(
            "src.workflows.azure_devops_analysis.store_detections",
            return_value=stored_entries,
        ), patch(
            "src.workflows.azure_devops_analysis.TechnologyEnricher"
        ) as enricher_cls, patch(
            "src.workflows.azure_devops_analysis.session_scope",
            side_effect=[_scope_for(store_session), _scope_for(query_session)],
        ):
            detector_cls.return_value.detect.return_value = detection

            workflow = AzureDevOpsAnalysisWorkflow(extractor=autospec_extractor)
            workflow._process_technologies(repo_data)

        enricher_cls.return_value.enrich.assert_called_once_with(
            query_session,
            [("React", "framework")],
        )

    def test_process_technologies_skips_recently_enriched_entries(self, autospec_extractor):
        repo_data = MagicMock(repo_id="org/proj/repo", name="repo")
        autospec_extractor.get_file_tree.return_value = [MagicMock(path="package.json")]
        detection = SimpleNamespace(
            all_technologies=["React"],
            primary_language="TypeScript",
            frameworks=["React"],
            databases=[],
        )
        stored_entries = [SimpleNamespace(name="React", category="framework")]

        store_session = MagicMock()
        query_session = MagicMock()
        query_session.query.return_value.filter.return_value.all.return_value = [
            SimpleNamespace(name="React", category="framework")
        ]

        @contextmanager
        def _scope_for(session):
            yield session

        with patch(
            "src.workflows.azure_devops_analysis.TechnologyDetector"
        ) as detector_cls, patch(
            "src.workflows.azure_devops_analysis.store_detections",
            return_value=stored_entries,
        ), patch(
            "src.workflows.azure_devops_analysis.TechnologyEnricher"
        ) as enricher_cls, patch(
            "src.workflows.azure_devops_analysis.session_scope",
            side_effect=[_scope_for(store_session), _scope_for(query_session)],
        ):
            detector_cls.return_value.detect.return_value = detection

            workflow = AzureDevOpsAnalysisWorkflow(extractor=autospec_extractor)
            workflow._process_technologies(repo_data)

        enricher_cls.return_value.enrich.assert_not_called()
