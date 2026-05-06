import logging
from datetime import datetime, UTC
from typing import Optional

from src.scheduler.celery_app import celery_app
from src.workflows.github_analysis import GitHubAnalysisWorkflow, ExtractionLimits
from src.workflows.azure_devops_analysis import run_azure_devops_extraction
from src.database import get_session
from src.database.connection import session_scope
from src.database.models.service import Service
from src.database.service_analytics import (
    compute_service_metrics,
    compute_all_services_metrics,
)
from src.database.storage import start_extraction_run, fail_extraction_run

logger = logging.getLogger(__name__)


def _record_task_failure(platform: str, task_error: Exception) -> None:
    """Persist a failed extraction run when a task aborts before workflow run tracking starts."""
    try:
        with session_scope() as session:
            run_id = start_extraction_run(
                session,
                platform=platform,
                organization_name="task-level",
                total_repositories=0,
            )
            fail_extraction_run(session, run_id, str(task_error))
    except Exception as persistence_error:
        logger.warning(
            "Failed to persist task-level extraction failure for platform %s: %s",
            platform,
            persistence_error,
            exc_info=True,
        )


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
        _record_task_failure("github", e)
        return {"status": "error", "message": str(e)}


@celery_app.task(name="tasks.run_azure_devops_extraction_task", bind=True)
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
        _record_task_failure("azure_devops", e)
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


@celery_app.task(name="tasks.compute_service_metrics", bind=True)
def compute_service_metrics_task(
    self,
    service_id: Optional[int] = None,
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
):
    """
    Compute and persist service-level metrics.
    
    Args:
        service_id: Specific service ID to compute metrics for (None = all services)
        period_start: Start date in ISO format (YYYY-MM-DD). Default: first day of current month
        period_end: End date in ISO format (YYYY-MM-DD). Default: today
        
    Returns:
        Dictionary with status and computed metrics summary
    """
    logger.info(
        f"Starting service metrics computation task: {self.request.id} "
        f"(service_id={service_id}, period_start={period_start}, period_end={period_end})"
    )
    
    try:
        # Parse dates
        if period_start:
            start_dt = datetime.fromisoformat(period_start).replace(tzinfo=UTC)
        else:
            # Default to first day of current month
            now = datetime.now(UTC)
            start_dt = datetime(now.year, now.month, 1, tzinfo=UTC)
        
        if period_end:
            end_dt = datetime.fromisoformat(period_end).replace(tzinfo=UTC)
        else:
            # Default to today (end of day)
            end_dt = datetime.now(UTC).replace(hour=23, minute=59, second=59)
        
        # Validate period
        if end_dt <= start_dt:
            error_msg = "Period end must be after period start"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}
        
        logger.info(f"Computing metrics for period: {start_dt.date()} to {end_dt.date()}")
        
        # Get database session
        session = get_session()
        
        try:
            if service_id is None:
                # Compute for all services
                logger.info("Computing metrics for all services...")
                metrics = compute_all_services_metrics(
                    session,
                    period_start=start_dt,
                    period_end=end_dt,
                )
                
                logger.info(f"Computed metrics for {len(metrics)} service(s)")
                
                # Persist to database
                session.add_all(metrics)
                session.commit()
                
                # Build summary
                summary = {
                    "services_processed": len(metrics),
                    "total_repositories": sum(m.total_repositories for m in metrics),
                    "total_commits": sum(m.total_commits for m in metrics),
                    "total_prs": sum(m.total_prs_created for m in metrics),
                }
                
                logger.info(f"✓ Persisted {len(metrics)} service metric(s) to database")
                return {"status": "success", "summary": summary}
            else:
                # Compute for single service
                logger.info(f"Computing metrics for service {service_id}...")
                
                # Verify service exists
                service = session.get(Service, service_id)
                if not service:
                    error_msg = f"Service {service_id} not found"
                    logger.error(error_msg)
                    return {"status": "error", "message": error_msg}
                
                metric = compute_service_metrics(
                    session,
                    service_id=service_id,
                    period_start=start_dt,
                    period_end=end_dt,
                )
                
                # Persist to database
                session.add(metric)
                session.commit()
                
                # Build summary
                summary = {
                    "service_id": service_id,
                    "service_name": service.name,
                    "total_repositories": metric.total_repositories,
                    "active_repositories": metric.active_repositories,
                    "total_commits": metric.total_commits,
                    "total_prs_created": metric.total_prs_created,
                    "unique_contributors": metric.unique_contributors,
                }
                
                logger.info(f"✓ Persisted service metric to database")
                return {"status": "success", "summary": summary}
        finally:
            session.close()
    
    except ValueError as e:
        error_msg = f"Invalid argument: {e}"
        logger.error(error_msg)
        return {"status": "error", "message": error_msg}
    except Exception as e:
        error_msg = f"Failed to compute service metrics: {e}"
        logger.exception(error_msg)
        return {"status": "error", "message": str(e)}