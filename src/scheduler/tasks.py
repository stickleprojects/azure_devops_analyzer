import logging
import time
from typing import List, Dict, Any
from scheduler.celery_app import celery_app
from tasks.extraction import extract_repository_data
from tasks.analysis import analyze_repository
from tasks.storage import store_results
from tasks.maintenance import cleanup_old_data, backup_database as do_backup

logger = logging.getLogger(__name__)

@celery_app.task(name="tasks.run_full_scan", bind=True)
def run_full_scan(self):
    """
    Execute full repository scan workflow.
    """
    logger.info(f"Starting full scan task: {self.request.id}")
    
    # Placeholder: Fetch list of repositories
    # In a real implementation, this would call a discovery service
    # repositories = get_all_repositories()
    repositories = [] 
    
    job_ids = []
    for repo in repositories:
        task = process_repository.delay(repo['id'])
        job_ids.append(task.id)
        
    logger.info(f"Full scan initiated. Enqueued {len(job_ids)} repository tasks.")
    return {"status": "initiated", "jobs_enqueued": len(job_ids)}

@celery_app.task(name="tasks.process_repository", bind=True)
def process_repository(self, repo_id: str):
    """
    Process a single repository: Extract -> Analyze -> Store
    """
    logger.info(f"Processing repository: {repo_id}")
    try:
        # 1. Extract
        repo_data = extract_repository_data(repo_id)
        # 2. Analyze
        analysis_results = analyze_repository(repo_data)
        # 3. Store
        store_results(repo_id, repo_data, analysis_results)
        return {"status": "success", "repo_id": repo_id}
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