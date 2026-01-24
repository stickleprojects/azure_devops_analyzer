"""
Integration Test: Contributor Metrics Calculation

Tests verify that contributor metrics are calculated and stored correctly
after running the extraction workflow.
"""

import pytest
from datetime import datetime, UTC
from sqlalchemy.orm import Session

from src.workflows.github_analysis import GitHubAnalysisWorkflow, ExtractionLimits
from src.workflows.azure_devops_analysis import AzureDevOpsAnalysisWorkflow
from src.database.models import (
    Repository,
    Contributor,
    ContributorMetric,
    Commit,
)


class TestGitHubContributorMetrics:
    """Test contributor metrics calculation for GitHub repositories."""

    @pytest.mark.integration
    @pytest.mark.live_api
    def test_contributor_metrics_calculated_after_extraction(
        self,
        github_config,
        test_session: Session,
    ):
        """
        CONTRACT: After extraction, contributor metrics should be calculated
        for all contributors in the current month.
        
        Verify:
        - Contributors are created from commits
        - Contributor metrics records exist
        - Metrics have correct period boundaries (current month)
        - Metrics contain expected data (commits, lines, etc.)
        """
        # Setup: Configure workflow with limits
        from src.extractors.github.extractor import GitHubExtractor
        
        extractor = GitHubExtractor(config=github_config)
        limits = ExtractionLimits(
            max_branches=2,
            max_commits=10,
            max_pull_requests=5,
            extract_dependencies=False,  # Skip to speed up test
        )
        workflow = GitHubAnalysisWorkflow(extractor=extractor, limits=limits)
        
        # Act: Run extraction (which now includes contributor metrics)
        summary = workflow.run()
        
        # Assert: Verify summary shows contributors
        assert summary['contributors'] > 0, "Should have extracted at least one contributor"
        
        # Query database for contributor metrics
        metrics = test_session.query(ContributorMetric).all()
        
        # Should have at least one metric record
        assert len(metrics) > 0, "Should have calculated contributor metrics"
        
        # Verify metrics structure
        metric = metrics[0]
        
        # Check period boundaries (should be current month)
        now = datetime.now(UTC)
        expected_start = datetime(now.year, now.month, 1, tzinfo=UTC)
        
        assert metric.period_start == expected_start, (
            f"Period should start at beginning of current month "
            f"(expected {expected_start}, got {metric.period_start})"
        )
        
        # Check that metrics fields are populated
        assert metric.repo_id is not None, "Metric should have repo_id"
        assert metric.contributor_id is not None, "Metric should have contributor_id"
        
        # Check commit count is positive (if there were commits in current month)
        # Note: May be 0 if no commits in current month
        assert metric.commit_count >= 0, "Commit count should be non-negative"
        
        # Verify contributor exists
        contributor = (
            test_session.query(Contributor)
            .filter_by(contributor_id=metric.contributor_id)
            .first()
        )
        assert contributor is not None, "Contributor should exist in database"
        
        # Verify repository exists
        repo = (
            test_session.query(Repository)
            .filter_by(repo_id=metric.repo_id)
            .first()
        )
        assert repo is not None, "Repository should exist in database"
        
        print(f"\n✓ Contributor metrics calculated:")
        print(f"  - {len(metrics)} metric records")
        print(f"  - Period: {metric.period_start.strftime('%Y-%m-%d')} to {metric.period_end.strftime('%Y-%m-%d')}")
        print(f"  - Sample: {contributor.name or contributor.email} - {metric.commit_count} commits")


class TestAzureDevOpsContributorMetrics:
    """Test contributor metrics calculation for Azure DevOps repositories."""

    @pytest.mark.integration
    @pytest.mark.live_api
    @pytest.mark.skipif(
        "not config.getoption('--azure-devops')",
        reason="Azure DevOps tests require --azure-devops flag",
    )
    def test_contributor_metrics_calculated_after_extraction(
        self,
        azure_devops_config,
        test_session: Session,
    ):
        """
        CONTRACT: After Azure DevOps extraction, contributor metrics should be
        calculated for all contributors in the current month.
        """
        # Setup
        from src.extractors.azure_devops.extractor import AzureDevOpsExtractor
        
        extractor = AzureDevOpsExtractor(config=azure_devops_config)
        limits = ExtractionLimits(
            max_branches=2,
            max_commits=10,
            max_pull_requests=5,
            extract_dependencies=False,
        )
        workflow = AzureDevOpsAnalysisWorkflow(extractor=extractor, limits=limits)
        
        # Act
        summary = workflow.run()
        
        # Assert
        assert summary['contributors'] > 0, "Should have extracted contributors"
        
        metrics = test_session.query(ContributorMetric).all()
        assert len(metrics) > 0, "Should have calculated contributor metrics"
        
        print(f"\n✓ Azure DevOps contributor metrics calculated:")
        print(f"  - {len(metrics)} metric records")
