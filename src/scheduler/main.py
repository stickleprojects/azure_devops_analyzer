"""
APScheduler entrypoint that enqueues Celery tasks based on config.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, UTC
from typing import Any, Dict

import yaml
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.blocking import BlockingScheduler

from src.scheduler.celery_app import celery_app

DEFAULT_CONFIG_PATH = "/app/config/scheduler.yaml"

TASKS_BY_PLATFORM = {
    "github": "tasks.run_github_extraction",
    "azure_devops": "tasks.run_azure_devops_extraction",
}

MAINTENANCE_TASKS = {
    "database_cleanup": "tasks.cleanup_database",
    "database_backup": "tasks.backup_database",
}


logger = logging.getLogger(__name__)


def _build_database_url() -> str:
    explicit = os.getenv("SCHEDULER_DATABASE_URL") or os.getenv("DATABASE_URL")
    if explicit:
        return explicit

    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    host = os.getenv("POSTGRES_HOST", "timescaledb")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "repo_analyzer")

    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"


def _enqueue_task(task_name: str, context: str) -> None:
    logger.info("Enqueuing task=%s context=%s", task_name, context)
    celery_app.send_task(task_name)


def _load_config(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        logger.warning("Scheduler config not found at %s; using defaults", path)
        return {}

    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _configure_logging(config: Dict[str, Any]) -> None:
    log_level = (
        config.get("logging", {}).get("level")
        or os.getenv("LOG_LEVEL", "INFO")
    )
    logging.basicConfig(
        level=getattr(logging, str(log_level).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def _schedule_platform_jobs(
    scheduler: BlockingScheduler,
    job_id: str,
    job_config: Dict[str, Any],
    platforms: list[str],
) -> None:
    trigger = job_config.get("trigger", "interval")
    trigger_args = {k: v for k, v in job_config.items() if k not in {"trigger", "platforms"}}

    for platform in platforms:
        task_name = TASKS_BY_PLATFORM.get(platform)
        if not task_name:
            logger.warning("No task mapped for platform=%s; skipping", platform)
            continue

        scheduled_id = f"{job_id}_{platform}"
        scheduler.add_job(
            _enqueue_task,
            trigger=trigger,
            id=scheduled_id,
            replace_existing=True,
            kwargs={
                "task_name": task_name,
                "context": f"{job_id}:{platform}",
            },
            **trigger_args,
        )
        logger.info("Scheduled job=%s trigger=%s", scheduled_id, trigger)


def _schedule_maintenance_jobs(
    scheduler: BlockingScheduler,
    job_id: str,
    job_config: Dict[str, Any],
) -> None:
    task_name = MAINTENANCE_TASKS.get(job_id)
    if not task_name:
        return

    trigger = job_config.get("trigger", "interval")
    trigger_args = {
        k: v
        for k, v in job_config.items()
        if k not in {"trigger", "retention_days"}
    }

    scheduler.add_job(
        _enqueue_task,
        trigger=trigger,
        id=job_id,
        replace_existing=True,
        kwargs={
            "task_name": task_name,
            "context": job_id,
        },
        **trigger_args,
    )
    logger.info("Scheduled job=%s trigger=%s", job_id, trigger)


def _configure_scheduler(config: Dict[str, Any]) -> BlockingScheduler:
    jobstores = {
        "default": SQLAlchemyJobStore(url=_build_database_url())
    }
    executors = {
        "default": ThreadPoolExecutor(10)
    }
    job_defaults = config.get("scheduler", {}).get("job_defaults", {})
    timezone = config.get("scheduler", {}).get("timezone", "UTC")

    scheduler = BlockingScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults,
        timezone=timezone,
    )

    jobs = config.get("jobs", {})
    if not jobs:
        logger.warning("No scheduler jobs configured; scheduler will idle")

    for job_id, job_config in jobs.items():
        if job_id in MAINTENANCE_TASKS:
            _schedule_maintenance_jobs(scheduler, job_id, job_config)
            continue

        platforms = job_config.get("platforms")
        if not platforms:
            platforms = list(TASKS_BY_PLATFORM.keys())
            logger.info(
                "Job=%s has no platforms configured; defaulting to %s",
                job_id,
                ", ".join(platforms),
            )

        _schedule_platform_jobs(scheduler, job_id, job_config, platforms)

    return scheduler


def main() -> None:
    config_path = os.getenv("SCHEDULER_CONFIG_PATH", DEFAULT_CONFIG_PATH)
    config = _load_config(config_path)
    _configure_logging(config)

    logger.info("Scheduler starting at %s", datetime.now(UTC).isoformat())

    scheduler = _configure_scheduler(config)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler shutdown requested")


if __name__ == "__main__":
    main()
