#!/usr/bin/env python3
"""
Submit GitHub extraction task to Celery queue for distributed processing.

This script sends an extraction task to Celery workers and monitors its progress.
It allows extraction to be processed by background workers and monitored in Flower.

Usage:
    python submit_extraction_task.py
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
        description="Submit GitHub extraction task to Celery.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
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


def submit_extraction_task() -> str:
    """
    Submit extraction task to Celery.

    Returns:
        Task ID string.
    """
    logging.info("Submitting GitHub extraction task to Celery...")
    
    # Send task to workers (use delay() for async execution)
    task = run_github_extraction.delay()
    
    logging.info(f"Task submitted with ID: {task.id}")
    return task.id


def monitor_task(task_id: str, timeout: int = 3600) -> bool:
    """
    Monitor task progress and wait for completion.

    Args:
        task_id: ID of the task to monitor
        timeout: Maximum time to wait in seconds

    Returns:
        True if task succeeded, False otherwise
    """
    logging.info(f"Monitoring task {task_id} (timeout: {timeout}s)...")
    
    task = celery_app.AsyncResult(task_id)
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if task.ready():
            if task.successful():
                logging.info(f"Task completed successfully!")
                logging.info(f"Result: {task.result}")
                return True
            else:
                logging.error(f"Task failed!")
                logging.error(f"Error: {task.result}")
                return False
        
        # Show current status
        logging.debug(f"Task state: {task.state}")
        time.sleep(2)
    
    logging.error(f"Task did not complete within {timeout} seconds")
    return False


def main() -> int:
    """Main entry point."""
    args = parse_args()
    setup_logging(args.verbose)
    
    try:
        # Submit the task
        task_id = submit_extraction_task()
        
        # Optionally wait for completion
        if args.wait:
            success = monitor_task(task_id, args.timeout)
            return 0 if success else 1
        else:
            logging.info("Task submitted. Monitor progress in Flower at http://localhost:5555")
            return 0
    
    except Exception as e:
        logging.error(f"Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
