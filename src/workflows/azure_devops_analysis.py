"""
Azure DevOps repository analysis workflow.

Orchestrates the extraction and storage of Azure DevOps repository data
including organizations, projects, repositories, branches, commits, and pull requests.
"""

import logging
import socket
from dataclasses import dataclass
from datetime import datetime, timedelta, UTC
from typing import Optional

from src.database.connection import session_scope
from src.database.models import Organization, Project, Technology
from src.analyzers.technology_enricher import TechnologyEnricher
from src.database.storage import (
    should_scan_repository,
    store_organization,
    store_project,
    store_repository,
    store_branch,
    store_commit,
    store_pull_request,
    store_dependencies,
    store_enriched_dependencies,
    store_detections,
    store_readme,
    update_repository_analyzed_timestamp,
    get_extraction_summary,
    start_extraction_run,
    update_extraction_run_progress,
    complete_extraction_run,
    fail_extraction_run,
    start_repository_extraction,
    skip_repository_extraction,
    complete_repository_extraction,
    fail_repository_extraction
)
from src.analyzers.dependency_analyzer import DependencyAnalyzer
from src.analyzers.technology_detector import TechnologyDetector
from src.analyzers.contributor_analyzer import calculate_and_store_contributor_metrics
from src.extractors.azure_devops.extractor import AzureDevOpsExtractor
from src.workflows.scope_handling import list_repositories_or_skip

logger = logging.getLogger(__name__)


@dataclass
class ExtractionLimits:
    """Configuration for limiting extraction scope."""

    max_branches: int = 10
    max_commits: int = 50
    max_pull_requests: int = 20
    min_scan_interval_hours: int = 6
    extract_dependencies: bool = True


class AzureDevOpsAnalysisWorkflow:
    """
    Workflow for extracting and storing Azure DevOps repository data.

    This class orchestrates the full extraction process:
    1. Fetch organization
    2. Fetch projects for the organization
    3. Create organization and project records
    4. Fetch repositories for each project
    5. For each repository:
       - Store repository metadata
       - Fetch and store branches
       - Fetch and store language statistics
       - Fetch and store commits
       - Fetch and store pull requests with reviews and comments
    """

    def __init__(
        self,
        extractor: Optional[AzureDevOpsExtractor] = None,
        limits: Optional[ExtractionLimits] = None,
    ):
        """
        Initialize the workflow.

        Args:
            extractor: AzureDevOpsExtractor instance (created if not provided).
            limits: Extraction limits configuration.
        """
        self.extractor = extractor or AzureDevOpsExtractor()
        self.limits = limits or ExtractionLimits()

    def run(self) -> dict:
        """
        Execute the full Azure DevOps analysis workflow.

        Returns:
            Summary dictionary with extraction counts.
        """
        logger.info("Starting Azure DevOps analysis workflow")

        orgs = self._fetch_organizations()

        for org_data in orgs:
            self._process_organization(org_data)

        logger.info("Extraction complete")
        return self._get_summary()

    def _fetch_organizations(self):
        """Fetch organizations from Azure DevOps."""
        logger.info("Fetching organizations...")
        orgs = self.extractor.get_organizations()
        logger.info("Found %d organizations", len(orgs))
        return orgs

    def _process_organization(self, org_data):
        """Process a single organization and its projects."""
        logger.info("Processing: %s", org_data.name)

        with session_scope() as session:
            org = store_organization(session, org_data)
            created = org.organization_id is not None
            if created:
                logger.info("  Created organization: %s", org_data.name)
            else:
                logger.info("  Organization exists: %s", org_data.name)

        self._process_projects(org_data)

    def _process_projects(self, org_data):
        """Fetch and process all projects for an organization."""
        logger.info("  Fetching projects for %s...", org_data.name)
        projects = self.extractor.get_projects(org_data.name)
        logger.info("  Found %d projects", len(projects))

        for project_data in projects:
            self._process_project(org_data, project_data)

    def _process_project(self, org_data, project_data):
        """Process a single project and its repositories."""
        logger.info("    Processing project: %s", project_data.name)

        with session_scope() as session:
            org = (
                session.query(Organization)
                .filter(
                    Organization.name == org_data.name,
                    Organization.platform == org_data.platform.value,
                )
                .first()
            )

            store_project(session, org, project_data.name, project_data.description)
            logger.info("      Stored project: %s", project_data.name)

        self._process_repositories(org_data, project_data.name)

    def _process_repositories(self, org_data, project_name):
        """Fetch and process all repositories for a project.

        If the caller lacks permission to list repositories for this
        project, the project is skipped (a warning is logged) and the
        workflow continues with the next project. See
        ``src.workflows.scope_handling.list_repositories_or_skip``.
        """
        logger.info("      Fetching repositories for %s...", project_name)
        repos = list_repositories_or_skip(
            self.extractor,
            org_data.name,
            project=project_name,
            scope_label=f"project {org_data.name}/{project_name}",
        )
        if repos is None:
            return
        logger.info("      Found %d repositories", len(repos))

        with session_scope() as session:
            run_id = start_extraction_run(
                session,
                platform=org_data.platform.value,
                organization_name=org_data.name,
                project_name=project_name,
                total_repositories=len(repos),
            )

        try:
            for index, repo_data in enumerate(repos, start=1):
                with session_scope() as session:
                    update_extraction_run_progress(
                        session,
                        run_id,
                        processed_repositories=index - 1,
                        current_repository_id=repo_data.repo_id,
                    )

                self._process_repository(org_data, repo_data, run_id)

                with session_scope() as session:
                    update_extraction_run_progress(
                        session,
                        run_id,
                        processed_repositories=index,
                        current_repository_id=None,
                    )
        except Exception as e:
            with session_scope() as session:
                fail_extraction_run(session, run_id, str(e))
            raise
        else:
            with session_scope() as session:
                complete_extraction_run(session, run_id)

            # Run health check at the tail of a successful extraction batch.
            # Wrapped in try/except so a bug in health-checking can never
            # crash the extraction workflow (Plan 020 Compatibility Note).
            try:
                from src.utils.extraction_health import compute_extraction_health
                from src.utils.metrics import emit_health_report

                with session_scope() as session:
                    report = compute_extraction_health(
                        session, platform=org_data.platform.value
                    )
                emit_health_report(report)
                if not report.is_healthy:
                    logger.warning(
                        "Extraction health violations detected after %s extraction",
                        org_data.platform.value,
                    )
            except Exception as health_exc:
                logger.warning(
                    "Extraction health check failed (non-fatal): %s", health_exc
                )

    def _process_repository(self, org_data, repo_data, run_id):
        """Process a single repository."""
        logger.info("        Processing repo: %s", repo_data.name)

        # Check if repo was recently scanned
        with session_scope() as session:
            if not should_scan_repository(
                session,
                repo_data.repo_id,
                self.limits.min_scan_interval_hours,
            ):
                skip_reason = (
                    "scanned within last %d hours"
                    % self.limits.min_scan_interval_hours
                )
                skip_repository_extraction(
                    session,
                    run_id,
                    repo_data.repo_id,
                    org_data.platform.value,
                    skip_reason,
                )
                logger.info(
                    "          Skipping %s - scanned within last %d hours",
                    repo_data.name,
                    self.limits.min_scan_interval_hours,
                )
                return

        # Get repository metadata (team_name, service_name)
        try:
            metadata = self.extractor.get_repository_metadata(repo_data.repo_id)
            if metadata:
                repo_data.team_name = metadata.team_name
                repo_data.service_name = metadata.service_name
                logger.info(
                    "          Found metadata: team=%s, service=%s",
                    repo_data.team_name,
                    repo_data.service_name,
                )
        except Exception as e:
            logger.warning("          Failed to fetch repository metadata: %s", e)

        metric_id = None
        try:
            # Store repository before extraction metrics (FK dependency)
            with session_scope() as session:
                project = (
                    session.query(Project)
                    .join(Organization)
                    .filter(
                        Organization.name == org_data.name,
                        Organization.platform == org_data.platform.value,
                        Project.name == repo_data.project_name,
                    )
                    .first()
                )

                store_repository(session, project, repo_data)
                logger.info("          Stored repository: %s", repo_data.name)

            with session_scope() as session:
                metric_id = start_repository_extraction(
                    session,
                    run_id,
                    repo_data.repo_id,
                    org_data.platform.value,
                    worker_hostname=socket.gethostname(),
                )

            # Process repository contents
            branches_count = self._process_branches(repo_data)
            self._process_languages(repo_data)
            self._process_technologies(repo_data)
            self._process_readme_files(repo_data)
            commits_count = self._process_commits(repo_data)
            prs_count = self._process_pull_requests(repo_data)

            # Extract dependencies
            if self.limits.extract_dependencies:
                self._process_dependencies(repo_data)

        # PAUSED: Contributor metrics calculation disabled temporarily
        # Reason: Performance concerns - complex multi-query aggregation is slow
        # Status: Implementation complete (FR-6.1-6.4) but not active
        # See: CONTRIBUTOR_METRICS_GUIDE.md for architecture
        # TODO: Optimize and re-enable in future sprint
        # self._process_contributor_metrics(repo_data)

            # Update timestamp
            with session_scope() as session:
                update_repository_analyzed_timestamp(session, repo_data.repo_id)
                logger.info("          Updated last_analyzed_at for %s", repo_data.name)

            stats = self.extractor.cache_stats
            with session_scope() as session:
                complete_repository_extraction(
                    session,
                    metric_id,
                    commits_extracted=commits_count,
                    pull_requests_extracted=prs_count,
                    branches_extracted=branches_count,
                    cache_hits=stats["hits"],
                    cache_misses=stats["misses"],
                )

            logger.info("          Cache stats for %s: %s", repo_data.repo_id, stats)
            self.extractor.clear_cache()
        except Exception as e:
            if metric_id is not None:
                with session_scope() as session:
                    fail_repository_extraction(session, metric_id, str(e))
            logger.warning("          Repository processing failed: %s", e)
            self.extractor.clear_cache()
            return

    def _process_branches(self, repo_data) -> int:
        """Fetch and store branches for a repository."""
        try:
            branches = self.extractor.get_branches(repo_data.repo_id)
            logger.info("          Found %d branches", len(branches))

            with session_scope() as session:
                for branch_data in branches[: self.limits.max_branches]:
                    store_branch(session, repo_data.repo_id, branch_data)

            return min(len(branches), self.limits.max_branches)

        except Exception as e:
            logger.warning("          Failed to fetch branches: %s", e)

        return 0

    def _process_languages(self, repo_data):
        """Fetch and store language statistics for a repository."""
        try:
            languages = self.extractor.get_languages(repo_data.repo_id)
            logger.info("          Found %d languages", len(languages))

            if languages:
                with session_scope() as session:
                    from src.database.storage import store_languages
                    store_languages(session, repo_data.repo_id, languages)
                    
                    # Log top 3 languages
                    top_langs = ", ".join(
                        f"{lang.language} ({lang.percentage:.1f}%)"
                        for lang in languages[:3]
                    )
                    logger.info("          Top languages: %s", top_langs)

        except Exception as e:
            logger.warning("          Failed to fetch languages: %s", e)

    def _process_technologies(self, repo_data):
        """Detect and persist technology stack for a repository."""
        try:
            # Get file tree to detect technologies
            file_tree = self.extractor.get_file_tree(repo_data.repo_id)
            if not file_tree:
                logger.info("          No file tree available for technology detection")
                return
            
            # Extract file names from tree
            file_names = [f.path for f in file_tree]
            
            # Detect technologies
            detector = TechnologyDetector()
            tech_detection = detector.detect(file_names)
            
            if tech_detection.all_technologies:
                logger.info("          Detected %d technologies", len(tech_detection.all_technologies))
                logger.info("          Primary language: %s", tech_detection.primary_language)
                
                if tech_detection.frameworks:
                    logger.info("          Frameworks: %s", ", ".join(tech_detection.frameworks[:3]))
                
                if tech_detection.databases:
                    logger.info("          Databases: %s", ", ".join(tech_detection.databases[:2]))

            # Persist detections
            with session_scope() as session:
                stored_entries = store_detections(session, repo_data.repo_id, tech_detection)

            # EOL enrichment (weekly staleness check) — fetch all matching rows in one query
            cutoff = datetime.now(UTC) - timedelta(days=7)
            enricher = TechnologyEnricher()
            with session_scope() as session:
                pairs = [(e.name, e.category) for e in stored_entries]
                if pairs:
                    recently_enriched = {
                        (t.name, t.category)
                        for t in session.query(Technology.name, Technology.category)
                        .filter(
                            Technology.eol_enriched_at > cutoff,
                            Technology.name.in_([p[0] for p in pairs]),
                        )
                        .all()
                    }
                    stale = [p for p in pairs if p not in recently_enriched]
                    if stale:
                        enricher.enrich(session, stale)

        except Exception as e:
            logger.warning("          Failed to detect/persist technologies: %s", e)

    def _process_readme_files(self, repo_data):
        """Fetch and store README files for a repository."""
        try:
            readme_files = self.extractor.get_readme_files(repo_data.repo_id)
            logger.info("          Found %d README files", len(readme_files))

            with session_scope() as session:
                for readme_data in readme_files:
                    store_readme(session, repo_data.repo_id, readme_data)

        except Exception as e:
            logger.warning("          Failed to fetch README files: %s", e)

    def _process_commits(self, repo_data) -> int:
        """Fetch and store commits for a repository."""
        try:
            commits = self.extractor.get_commits(
                repo_data.repo_id,
                limit=self.limits.max_commits,
            )
            logger.info("          Found %d recent commits", len(commits))

            with session_scope() as session:
                stored_count = 0
                for commit_data in commits:
                    result = store_commit(
                        session,
                        repo_data.repo_id,
                        repo_data.default_branch,
                        commit_data,
                    )
                    if result:
                        stored_count += 1

                if stored_count > 0:
                    logger.info("          Stored %d new commits", stored_count)

            return stored_count

        except Exception as e:
            logger.warning("          Failed to fetch commits: %s", e)

        return 0

    def _process_pull_requests(self, repo_data) -> int:
        """Fetch and store pull requests for a repository."""
        try:
            prs = self.extractor.get_pull_requests(repo_data.repo_id)
            prs = prs[: self.limits.max_pull_requests]
            logger.info("          Found %d pull requests", len(prs))

            with session_scope() as session:
                stored_count = 0
                for pr_data in prs:
                    result = store_pull_request(session, repo_data.repo_id, pr_data)
                    if result:
                        stored_count += 1

                if stored_count > 0:
                    logger.info("          Stored %d new pull requests", stored_count)

            return stored_count

        except Exception as e:
            logger.warning("          Failed to fetch PRs: %s", e)

        return 0

    def _process_dependencies(self, repo_data):
        """Extract and store dependencies for a repository."""
        try:
            analyzer = DependencyAnalyzer(enrich=True)
            result = analyzer.analyze(
                self.extractor,
                repo_data.repo_id,
                branch=repo_data.default_branch,
            )

            if result.dependencies:
                logger.info(
                    "          Found %d dependencies from %d ecosystems",
                    result.total_dependencies,
                    len(result.ecosystems),
                )

                with session_scope() as session:
                    # Use enriched dependencies if available, otherwise fall back to unenriched
                    if result.enriched_dependencies:
                        logger.info(
                            "          Enriching %d dependencies (latest versions, EOL, vulnerabilities)",
                            len(result.enriched_dependencies),
                        )
                        store_enriched_dependencies(
                            session,
                            repo_data.repo_id,
                            result.enriched_dependencies,
                            branch_name=repo_data.default_branch,
                        )
                    else:
                        # Fallback to unenriched if enrichment failed
                        store_dependencies(
                            session,
                            repo_data.repo_id,
                            result.dependencies,
                            branch_name=repo_data.default_branch,
                        )
                    
                    logger.info(
                        "          Stored %d dependencies (%d dev, %d prod)",
                        result.total_dependencies,
                        result.dev_dependencies,
                        result.prod_dependencies,
                    )
                    
                    if result.enrichment_errors:
                        logger.warning(
                            "          Enrichment warnings: %s",
                            "; ".join(result.enrichment_errors),
                        )
            else:
                logger.info("          No dependencies found")

            if result.parse_errors:
                for error in result.parse_errors[:3]:
                    logger.warning("          Parse error: %s", error)

        except Exception as e:
            logger.warning("          Failed to extract dependencies: %s", e)

    def _process_contributor_metrics(self, repo_data):
        """Calculate and store contributor metrics for the repository."""
        try:
            from datetime import datetime, UTC
            
            logger.info("          Calculating contributor metrics...")
            
            # Calculate metrics for the current month
            now = datetime.now(UTC)
            period_start = datetime(now.year, now.month, 1, tzinfo=UTC)
            
            # Calculate end of current month
            if now.month == 12:
                period_end = datetime(now.year + 1, 1, 1, tzinfo=UTC)
            else:
                period_end = datetime(now.year, now.month + 1, 1, tzinfo=UTC)
            
            with session_scope() as session:
                # First, quickly check if there are any commits in this period
                from src.database.models import Commit
                has_commits = (
                    session.query(Commit)
                    .filter(
                        Commit.repo_id == repo_data.repo_id,
                        Commit.commit_date >= period_start,
                        Commit.commit_date < period_end,
                    )
                    .limit(1)
                    .first()
                )
                
                if not has_commits:
                    logger.info("          No commits in current period - skipping metrics calculation")
                    return
                
                metrics = calculate_and_store_contributor_metrics(
                    session,
                    repo_data.repo_id,
                    period_start,
                    period_end,
                )
                
                if metrics:
                    logger.info(
                        "          Calculated contributor metrics for %d contributors (period: %s to %s)",
                        len(metrics),
                        period_start.strftime("%Y-%m-%d"),
                        period_end.strftime("%Y-%m-%d"),
                    )
                else:
                    logger.info("          No contributor activity in current period")
                    
        except Exception as e:
            logger.warning("          Failed to calculate contributor metrics: %s", e)

    def _get_summary(self) -> dict:
        """Get extraction summary counts."""
        with session_scope() as session:
            return get_extraction_summary(session)


def run_azure_devops_extraction() -> dict:
    """
    Convenience function to run Azure DevOps extraction workflow.

    Returns:
        Summary dictionary with extraction counts.
    """
    workflow = AzureDevOpsAnalysisWorkflow()
    return workflow.run()


def print_extraction_summary(summary: dict) -> None:
    """
    Print extraction summary to console.

    Args:
        summary: Dictionary with entity counts.
    """
    print("\n" + "=" * 50)
    print("EXTRACTION SUMMARY")
    print("=" * 50)
    print(f"Organizations:  {summary['organizations']}")
    print(f"Projects:       {summary['projects']}")
    print(f"Repositories:   {summary['repositories']}")
    print(f"Branches:       {summary['branches']}")
    print(f"Commits:        {summary['commits']}")
    print(f"Pull Requests:  {summary['pull_requests']}")
    print(f"Contributors:   {summary['contributors']}")
    print(f"Dependencies:   {summary.get('dependencies', 0)}")
    print("=" * 50)
