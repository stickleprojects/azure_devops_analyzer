#!/usr/bin/env python3
"""
Submit extraction tasks to Celery queue for distributed processing.

This script sends extraction tasks to Celery workers and monitors their progress.
It allows extraction to be processed by background workers and monitored in Flower.

Usage:
    python submit_extraction_task.py                    # Submit both platforms
    python submit_extraction_task.py --platform github  # GitHub only
    python submit_extraction_task.py --platform azure   # Azure DevOps only
    python submit_extraction_task.py --wait --timeout 3600
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# Add src to path when running as script
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scheduler.celery_app import celery_app
from src.scheduler.tasks import run_github_extraction
from src.scheduler.tasks import run_azure_devops_extraction_task


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the task submission."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Submit extraction tasks to Celery.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--platform",
        choices=["github", "azure", "both"],
        default="both",
        help="Platform to extract from",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for task completion before exiting",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=3600,
        help="Timeout in seconds when waiting for task completion",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser.parse_args()


def submit_extraction_tasks(platform: str) -> list[tuple[str, str]]:
    """
    Submit extraction tasks to Celery.

    Args:
        platform: One of "github", "azure", or "both".

    Returns:
        List of (platform_name, task_id) tuples.
    """
    tasks = []

    if platform in ("github", "both"):
        logging.info("Submitting GitHub extraction task to Celery...")
        task = run_github_extraction.delay()
        logging.info(f"GitHub task submitted with ID: {task.id}")
        tasks.append(("github", task.id))

    if platform in ("azure", "both"):
        logging.info("Submitting Azure DevOps extraction task to Celery...")
        task = run_azure_devops_extraction_task.delay()
        logging.info(f"Azure DevOps task submitted with ID: {task.id}")
        tasks.append(("azure", task.id))

    return tasks


def monitor_tasks(tasks: list[tuple[str, str]], timeout: int = 3600) -> bool:
    """
    Monitor task progress and wait for completion.

    Args:
        tasks: List of (platform_name, task_id) tuples to monitor.
        timeout: Maximum time to wait in seconds.

    Returns:
        True if all tasks succeeded, False otherwise.
    """
    logging.info(f"Monitoring {len(tasks)} task(s) (timeout: {timeout}s)...")

    pending = {task_id: name for name, task_id in tasks}
    results = {}
    start_time = time.time()

    while pending and time.time() - start_time < timeout:
        for task_id, name in list(pending.items()):
            result = celery_app.AsyncResult(task_id)
            if result.ready():
                if result.successful():
                    logging.info(f"{name} task completed successfully!")
                    logging.info(f"{name} result: {result.result}")
                    results[task_id] = True
                else:
                    logging.error(f"{name} task failed!")
                    logging.error(f"{name} error: {result.result}")
                    results[task_id] = False
                del pending[task_id]
            else:
                logging.debug(f"{name} task state: {result.state}")

        if pending:
            time.sleep(2)

    if pending:
        for task_id, name in pending.items():
            logging.error(f"{name} task did not complete within {timeout} seconds")
            results[task_id] = False

    return all(results.values())


def main() -> int:
    """Main entry point."""
    args = parse_args()
    setup_logging(args.verbose)

    try:
        tasks = submit_extraction_tasks(args.platform)

        if args.wait:
            success = monitor_tasks(tasks, args.timeout)
            return 0 if success else 1
        else:
            logging.info("Task(s) submitted. Monitor progress in Flower at http://localhost:5555")
            return 0

    except Exception as e:
        logging.error(f"Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
