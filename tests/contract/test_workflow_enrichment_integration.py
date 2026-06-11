"""
CONTRACT Tests for Dependency Enrichment Integration in Workflows

Tests that the GitHub and Azure DevOps analysis workflows correctly use
enriched dependencies.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, UTC

from src.workflows.github_analysis import GitHubAnalysisWorkflow
from src.workflows.azure_devops_analysis import AzureDevOpsAnalysisWorkflow
from src.extractors.base import RepositoryData, DependencyData
from src.analyzers.dependency_enricher import EnrichedDependency, PackageMetadata


class TestGitHubWorkflowDependencyEnrichment:
    """CONTRACT: GitHub workflow must enrich dependencies during extraction."""

    def test_workflow_uses_enriched_dependencies(self):
        """CONTRACT: _process_dependencies writes package metadata + repo deps when enriched."""
        workflow = GitHubAnalysisWorkflow()

        repo_data = Mock()
        repo_data.repo_id = "test/repo"
        repo_data.default_branch = "main"

        workflow.extractor = Mock()

        pkg_meta = PackageMetadata(
            package_name="requests",
            ecosystem="pypi",
            latest_version="2.31.0",
            is_eol=False,
            vulnerabilities=[],
        )
        mock_result = Mock()
        mock_result.dependencies = [
            DependencyData("requests", "pypi", "2.28.0", False, "requirements.txt")
        ]
        mock_result.enriched_dependencies = [
            EnrichedDependency(
                package_name="requests",
                ecosystem="pypi",
                version="2.28.0",
                is_dev_dependency=False,
                source_file="requirements.txt",
                version_constraint=None,
                has_known_vulnerabilities=False,
                package_metadata=pkg_meta,
            )
        ]
        mock_result.total_dependencies = 1
        mock_result.dev_dependencies = 0
        mock_result.prod_dependencies = 1
        mock_result.ecosystems = {"pypi"}
        mock_result.analyzed_at = datetime.now(UTC)
        mock_result.enrichment_errors = []
        mock_result.parse_errors = []

        with patch("src.workflows.github_analysis.DependencyAnalyzer") as mock_analyzer_class, \
             patch("src.workflows.github_analysis.session_scope") as mock_session, \
             patch("src.workflows.github_analysis.store_package_metadata") as mock_store_pkg, \
             patch("src.workflows.github_analysis.store_repo_dependencies") as mock_store_repo:

            mock_analyzer = Mock()
            mock_analyzer.analyze.return_value = mock_result
            mock_analyzer_class.return_value = mock_analyzer

            mock_session_instance = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_session_instance

            workflow._process_dependencies(repo_data)

            # Package metadata was stored once
            mock_store_pkg.assert_called_once()
            call_kwargs = mock_store_pkg.call_args
            assert call_kwargs[1]["package_name"] == "requests"
            assert call_kwargs[1]["latest_version"] == "2.31.0"

            # Repo dependencies were stored
            mock_store_repo.assert_called_once()
            repo_dep_args = mock_store_repo.call_args[0]
            assert repo_dep_args[1] == "test/repo"
            assert len(repo_dep_args[2]) == 1

    def test_workflow_falls_back_to_unenriched_if_empty(self):
        """CONTRACT: Falls back to unenriched if enrichment produces no results."""
        workflow = GitHubAnalysisWorkflow()

        repo_data = Mock()
        repo_data.repo_id = "test/repo"
        repo_data.default_branch = "main"

        workflow.extractor = Mock()

        mock_result = Mock()
        mock_result.dependencies = [
            DependencyData("requests", "pypi", "2.28.0", False, "requirements.txt")
        ]
        mock_result.enriched_dependencies = []  # Empty - enrichment failed
        mock_result.total_dependencies = 1
        mock_result.dev_dependencies = 0
        mock_result.prod_dependencies = 1
        mock_result.ecosystems = {"pypi"}
        mock_result.analyzed_at = datetime.now(UTC)
        mock_result.enrichment_errors = ["Enrichment timeout"]
        mock_result.parse_errors = []

        with patch("src.workflows.github_analysis.DependencyAnalyzer") as mock_analyzer_class, \
             patch("src.workflows.github_analysis.session_scope") as mock_session, \
             patch("src.workflows.github_analysis.store_dependencies") as mock_store, \
             patch("src.workflows.github_analysis.store_repo_dependencies") as mock_store_repo:

            mock_analyzer = Mock()
            mock_analyzer.analyze.return_value = mock_result
            mock_analyzer_class.return_value = mock_analyzer

            mock_session_instance = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_session_instance

            workflow._process_dependencies(repo_data)

            # Unenriched fallback was called
            mock_store.assert_called_once()
            # Enriched path was NOT called
            mock_store_repo.assert_not_called()

    def test_workflow_enables_enrichment_flag(self):
        """CONTRACT: DependencyAnalyzer is initialized with enrich=True."""
        workflow = GitHubAnalysisWorkflow()

        repo_data = Mock()
        repo_data.repo_id = "test/repo"
        repo_data.default_branch = "main"

        workflow.extractor = Mock()
        mock_result = Mock()
        mock_result.dependencies = []
        mock_result.enriched_dependencies = []
        mock_result.parse_errors = []

        with patch("src.workflows.github_analysis.DependencyAnalyzer") as mock_analyzer_class, \
             patch("src.workflows.github_analysis.session_scope"):

            mock_analyzer_class.return_value.analyze.return_value = mock_result

            workflow._process_dependencies(repo_data)

            mock_analyzer_class.assert_called_once_with(enrich=True)


class TestAzureDevOpsWorkflowDependencyEnrichment:
    """CONTRACT: Azure workflow must enrich dependencies during extraction."""

    def test_workflow_uses_enriched_dependencies(self):
        """CONTRACT: _process_dependencies writes package metadata + repo deps when enriched."""
        workflow = AzureDevOpsAnalysisWorkflow()

        repo_data = Mock()
        repo_data.repo_id = "test/repo"
        repo_data.default_branch = "main"

        workflow.extractor = Mock()

        pkg_meta = PackageMetadata(
            package_name="requests",
            ecosystem="pypi",
            latest_version="2.31.0",
            is_eol=False,
            vulnerabilities=[],
        )
        mock_result = Mock()
        mock_result.dependencies = [
            DependencyData("requests", "pypi", "2.28.0", False, "requirements.txt")
        ]
        mock_result.enriched_dependencies = [
            EnrichedDependency(
                package_name="requests",
                ecosystem="pypi",
                version="2.28.0",
                is_dev_dependency=False,
                source_file="requirements.txt",
                version_constraint=None,
                has_known_vulnerabilities=False,
                package_metadata=pkg_meta,
            )
        ]
        mock_result.total_dependencies = 1
        mock_result.dev_dependencies = 0
        mock_result.prod_dependencies = 1
        mock_result.ecosystems = {"pypi"}
        mock_result.analyzed_at = datetime.now(UTC)
        mock_result.enrichment_errors = []
        mock_result.parse_errors = []

        with patch("src.workflows.azure_devops_analysis.DependencyAnalyzer") as mock_analyzer_class, \
             patch("src.workflows.azure_devops_analysis.session_scope") as mock_session, \
             patch("src.workflows.azure_devops_analysis.store_package_metadata") as mock_store_pkg, \
             patch("src.workflows.azure_devops_analysis.store_repo_dependencies") as mock_store_repo:

            mock_analyzer = Mock()
            mock_analyzer.analyze.return_value = mock_result
            mock_analyzer_class.return_value = mock_analyzer

            mock_session_instance = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_session_instance

            workflow._process_dependencies(repo_data)

            mock_store_pkg.assert_called_once()
            call_kwargs = mock_store_pkg.call_args
            assert call_kwargs[1]["package_name"] == "requests"
            assert call_kwargs[1]["latest_version"] == "2.31.0"

            mock_store_repo.assert_called_once()
            repo_dep_args = mock_store_repo.call_args[0]
            assert repo_dep_args[1] == "test/repo"
            assert len(repo_dep_args[2]) == 1

    def test_workflow_falls_back_to_unenriched_if_empty(self):
        """CONTRACT: Falls back to unenriched if enrichment produces no results."""
        workflow = AzureDevOpsAnalysisWorkflow()

        repo_data = Mock()
        repo_data.repo_id = "test/repo"
        repo_data.default_branch = "main"

        workflow.extractor = Mock()

        mock_result = Mock()
        mock_result.dependencies = [
            DependencyData("requests", "pypi", "2.28.0", False, "requirements.txt")
        ]
        mock_result.enriched_dependencies = []
        mock_result.total_dependencies = 1
        mock_result.dev_dependencies = 0
        mock_result.prod_dependencies = 1
        mock_result.ecosystems = {"pypi"}
        mock_result.analyzed_at = datetime.now(UTC)
        mock_result.enrichment_errors = ["Enrichment timeout"]
        mock_result.parse_errors = []

        with patch("src.workflows.azure_devops_analysis.DependencyAnalyzer") as mock_analyzer_class, \
             patch("src.workflows.azure_devops_analysis.session_scope") as mock_session, \
             patch("src.workflows.azure_devops_analysis.store_dependencies") as mock_store, \
             patch("src.workflows.azure_devops_analysis.store_repo_dependencies") as mock_store_repo:

            mock_analyzer = Mock()
            mock_analyzer.analyze.return_value = mock_result
            mock_analyzer_class.return_value = mock_analyzer

            mock_session_instance = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_session_instance

            workflow._process_dependencies(repo_data)

            mock_store.assert_called_once()
            mock_store_repo.assert_not_called()

    def test_workflow_enables_enrichment_flag(self):
        """CONTRACT: DependencyAnalyzer is initialized with enrich=True."""
        workflow = AzureDevOpsAnalysisWorkflow()

        repo_data = Mock()
        repo_data.repo_id = "test/repo"
        repo_data.default_branch = "main"

        workflow.extractor = Mock()
        mock_result = Mock()
        mock_result.dependencies = []
        mock_result.enriched_dependencies = []
        mock_result.parse_errors = []

        with patch("src.workflows.azure_devops_analysis.DependencyAnalyzer") as mock_analyzer_class, \
             patch("src.workflows.azure_devops_analysis.session_scope"):

            mock_analyzer_class.return_value.analyze.return_value = mock_result

            workflow._process_dependencies(repo_data)

            mock_analyzer_class.assert_called_once_with(enrich=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
