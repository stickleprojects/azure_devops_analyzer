"""
CONTRACT Tests for Dependency Enrichment Integration in Workflows

Tests that the GitHub analysis workflow correctly uses enriched dependencies.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, UTC

from src.workflows.github_analysis import GitHubAnalysisWorkflow
from src.extractors.base import RepositoryData, DependencyData
from src.analyzers.dependency_enricher import EnrichedDependency


class TestGitHubWorkflowDependencyEnrichment:
    """CONTRACT: GitHub workflow must enrich dependencies during extraction."""

    def test_workflow_uses_enriched_dependencies(self):
        """CONTRACT: _process_dependencies uses enriched data when available."""
        workflow = GitHubAnalysisWorkflow()
        
        # Create mock repository data
        repo_data = Mock()
        repo_data.repo_id = "test/repo"
        repo_data.default_branch = "main"
        
        # Create mock extractor
        workflow.extractor = Mock()
        
        # Create mock result with enriched dependencies
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
                latest_version="2.31.0",
                has_vulnerabilities=True,
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
             patch("src.workflows.github_analysis.store_enriched_dependencies") as mock_store_enriched:
            
            # Setup analyzer mock
            mock_analyzer = Mock()
            mock_analyzer.analyze.return_value = mock_result
            mock_analyzer_class.return_value = mock_analyzer
            
            # Setup session mock
            mock_session_instance = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_session_instance
            
            # Call the method
            workflow._process_dependencies(repo_data)
            
            # Verify enriched storage was called
            mock_store_enriched.assert_called_once()
            call_args = mock_store_enriched.call_args
            
            # Verify the call used enriched dependencies
            assert len(call_args[0][2]) == 1  # enriched_dependencies argument
            assert call_args[0][2][0].latest_version == "2.31.0"
            assert call_args[0][2][0].has_vulnerabilities is True

    def test_workflow_falls_back_to_unenriched_if_empty(self):
        """CONTRACT: Falls back to unenriched if enrichment produces no results."""
        workflow = GitHubAnalysisWorkflow()
        
        repo_data = Mock()
        repo_data.repo_id = "test/repo"
        repo_data.default_branch = "main"
        
        workflow.extractor = Mock()
        
        # Result with dependencies but no enriched (enrichment failed)
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
             patch("src.workflows.github_analysis.store_enriched_dependencies") as mock_store_enriched:
            
            mock_analyzer = Mock()
            mock_analyzer.analyze.return_value = mock_result
            mock_analyzer_class.return_value = mock_analyzer
            
            mock_session_instance = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_session_instance
            
            workflow._process_dependencies(repo_data)
            
            # Verify unenriched storage was called (fallback)
            mock_store.assert_called_once()
            # Verify enriched storage was NOT called
            mock_store_enriched.assert_not_called()

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
            
            # Verify DependencyAnalyzer was initialized with enrich=True
            mock_analyzer_class.assert_called_once_with(enrich=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
