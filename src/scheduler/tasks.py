import logging
import time
from typing import List, Dict, Any, Optional
from scheduler.celery_app import celery_app
from tasks.extraction import extract_repository_data
from tasks.analysis import analyze_repository
from tasks.storage import store_results
from tasks.maintenance import cleanup_old_data, backup_database as do_backup
from src.extractors import Platform, get_extractor

logger = logging.getLogger(__name__)

@celery_app.task(name="tasks.run_full_scan", bind=True)
def run_full_scan(self, platform: str = "azure_devops", organization: Optional[str] = None):
    """
    Execute full repository scan workflow for a specific platform.

    Args:
        platform: Platform to scan ("azure_devops" or "github")
        organization: Optional organization/user to scan (uses env default if not specified)
    """
    logger.info(f"Starting full scan task: {self.request.id} for platform: {platform}")

    try:
        extractor = get_extractor(platform)
    except ValueError as e:
        logger.error(f"Invalid platform: {platform}")
        return {"status": "error", "message": str(e)}

    # Get organizations to scan
    if organization:
        orgs = [organization]
    else:
        orgs = [org.name for org in extractor.get_organizations()]

    job_ids = []
    for org in orgs:
        repositories = extractor.get_repositories(org)
        for repo in repositories:
            task = process_repository.delay(repo.repo_id, platform)
            job_ids.append(task.id)

    logger.info(f"Full scan initiated. Enqueued {len(job_ids)} repository tasks.")
    return {"status": "initiated", "platform": platform, "jobs_enqueued": len(job_ids)}

@celery_app.task(name="tasks.process_repository", bind=True)
def process_repository(self, repo_id: str, platform: str = "azure_devops"):
    """
    Process a single repository: Extract -> Analyze -> Store

    Args:
        repo_id: Repository identifier (platform-specific)
        platform: Platform the repository belongs to ("azure_devops" or "github")
    """
    logger.info(f"Processing repository: {repo_id} (platform: {platform})")
    try:
        # Get platform-specific extractor
        extractor = get_extractor(platform)

        # 1. Extract using platform-specific extractor
        repo_data = extractor.extract_full_repository(
            repo_id,
            include_commits=True,
            include_prs=True,
            include_file_tree=True,
            commit_limit=1000,
            commit_since_days=90,
        )

        # 2. Analyze (platform-agnostic)
        analysis_results = analyze_repository(repo_data)

        # 3. Store (platform-agnostic)
        store_results(repo_id, repo_data, analysis_results)

        return {"status": "success", "repo_id": repo_id, "platform": platform}
    except Exception as e:
        logger.error(f"Failed to process repository {repo_id}: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)

@celery_app.task(name="tasks.run_incremental_update", bind=True)
def run_incremental_update(self):
    """
    Execute incremental update workflow.
    """
    logger.info(f"Starting incremental update task: {self.request.id}")
    # Placeholder for incremental logic
    time.sleep(2)
    logger.info("Incremental update completed.")
    return {"status": "completed", "type": "incremental"}

@celery_app.task(name="tasks.cleanup_database")
def cleanup_database():
    """
    Perform database maintenance and cleanup.
    """
    logger.info("Cleaning up database...")
    cleanup_old_data()

@celery_app.task(name="tasks.backup_database")
def backup_database():
    """
    Perform database backup.
    """
    logger.info("Backing up database...")
    do_backup()