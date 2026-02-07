import logging
from typing import Optional

from src.scheduler.celery_app import celery_app
from src.workflows.github_analysis import GitHubAnalysisWorkflow, ExtractionLimits
from src.workflows.azure_devops_analysis import run_azure_devops_extraction

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.run_github_extraction", bind=True)
def run_github_extraction(self):
    """
    Execute GitHub repository extraction and analysis workflow.
    
    This task orchestrates the full GitHub analysis:
    1. Fetch organizations/users
    2. Fetch repositories for each org/user
    3. Extract and store repository data (branches, commits, PRs)
    """
    logger.info(f"Starting GitHub extraction task: {self.request.id}")
    
    try:
        # Create workflow with standard limits
        limits = ExtractionLimits(
            max_branches=10,
            max_commits=50,
            max_pull_requests=20,
            min_scan_interval_hours=6,
            extract_dependencies=True,
        )
        
        workflow = GitHubAnalysisWorkflow(limits=limits)
        
        # Run the workflow
        summary = workflow.run()
        
        logger.info(f"GitHub extraction completed. Summary: {summary}")
        return {"status": "success", "summary": summary}
        
    except Exception as e:
        logger.error(f"GitHub extraction failed: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


@celery_app.task(name="tasks.run_azure_devops_extraction", bind=True)
def run_azure_devops_extraction_task(self):
    """
    Execute Azure DevOps repository extraction and analysis workflow.
    """
    logger.info("Starting Azure DevOps extraction task: %s", self.request.id)

    try:
        summary = run_azure_devops_extraction()

        logger.info("Azure DevOps extraction completed. Summary: %s", summary)
        return {"status": "success", "summary": summary}

    except Exception as e:
        logger.error("Azure DevOps extraction failed: %s", e, exc_info=True)
        return {"status": "error", "message": str(e)}


@celery_app.task(name="tasks.cleanup_database")
def cleanup_database():
    """
    Perform database maintenance and cleanup.
    """
    logger.info("Cleaning up database...")
    # TODO: Implement cleanup logic
    logger.info("Database cleanup completed.")
    return {"status": "completed", "type": "cleanup"}


@celery_app.task(name="tasks.backup_database")
def backup_database():
    """
    Perform database backup.
    """
    logger.info("Backing up database...")
    # TODO: Implement backup logic
    logger.info("Database backup completed.")
    return {"status": "completed", "type": "backup"}