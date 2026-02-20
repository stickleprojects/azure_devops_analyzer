#!/usr/bin/env python3
"""
Compute and persist service-level metrics.

This script aggregates metrics across all repositories belonging to each service
and stores the results in the service_metrics table. It supports computing metrics
for specific time periods or all services at once.

Usage:
    python compute_service_metrics.py                           # All services, current month
    python compute_service_metrics.py --service 1               # Specific service
    python compute_service_metrics.py --period 2025-01-01       # Specific date range
    python compute_service_metrics.py --service 1 --dry-run     # Preview without persisting
    python compute_service_metrics.py --all --verbose           # Verbose output

Typical Usage:
    # Docker execution
    docker-compose exec analyzer python scripts/compute_service_metrics.py --all
    
    # Or via bash script
    bash ./scripts/compute_service_metrics_docker.sh
"""

import argparse
import logging
import sys
from datetime import datetime, UTC, timedelta
from pathlib import Path

# Add src to path when running as script
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import get_session
from src.database.models.service import Service
from src.database.service_analytics import (
    compute_service_metrics,
    compute_all_services_metrics,
)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the computation process."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Compute and persist service-level metrics.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python compute_service_metrics.py --all
    Compute metrics for all services for the current month
    
  python compute_service_metrics.py --service 5
    Compute metrics for service 5 for the current month
    
  python compute_service_metrics.py --period 2025-01-01 --all
    Compute metrics for all services from Jan 1, 2025 to today
    
  python compute_service_metrics.py --start 2025-01-01 --end 2025-12-31 --all
    Compute metrics for all services for the entire year 2025
    
  python compute_service_metrics.py --all --dry-run
    Preview metrics without saving to database
        """,
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Compute metrics for all services",
    )
    parser.add_argument(
        "--service",
        type=int,
        help="Compute metrics for a specific service ID",
    )
    parser.add_argument(
        "--period",
        type=str,
        default=None,
        help="Period start date (YYYY-MM-DD). Default: first day of current month",
    )
    parser.add_argument(
        "--start",
        type=str,
        help="Period start date (YYYY-MM-DD). Overrides --period",
    )
    parser.add_argument(
        "--end",
        type=str,
        help="Period end date (YYYY-MM-DD). Default: today",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview metrics without persisting to database",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    
    return parser.parse_args()


def parse_date(date_str: str, label: str = "date") -> datetime:
    """Parse a date string in YYYY-MM-DD format."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC)
    except ValueError:
        raise ValueError(f"Invalid {label}: {date_str}. Expected YYYY-MM-DD")


def main() -> int:
    """
    Main entry point for service metrics computation.

    Returns:
        0 on success, 1 on failure
    """
    args = parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    try:
        # Validate arguments
        if not args.all and not args.service:
            logger.error("Must specify either --all or --service <id>")
            return 1
        
        if args.all and args.service:
            logger.error("Cannot specify both --all and --service")
            return 1
        
        # Determine period boundaries
        if args.start:
            period_start = parse_date(args.start, "start date")
        elif args.period:
            period_start = parse_date(args.period, "period start date")
        else:
            # Default to first day of current month
            now = datetime.now(UTC)
            period_start = datetime(now.year, now.month, 1, tzinfo=UTC)
        
        if args.end:
            period_end = parse_date(args.end, "end date")
        else:
            # Default to today (end of day)
            period_end = datetime.now(UTC).replace(hour=23, minute=59, second=59)
        
        # Ensure period_end is after period_start
        if period_end <= period_start:
            logger.error("Period end must be after period start")
            return 1
        
        logger.info(f"Period: {period_start.date()} to {period_end.date()}")
        
        # Get database session
        session = get_session()
        
        try:
            if args.all:
                logger.info("Computing metrics for all services...")
                metrics = compute_all_services_metrics(
                    session,
                    period_start=period_start,
                    period_end=period_end,
                )
                logger.info(f"Computed metrics for {len(metrics)} service(s)")
                
                # Display preview
                for metric in metrics:
                    logger.info(
                        f"  Service {metric.service_id}: "
                        f"{metric.total_repositories} repos, "
                        f"{metric.total_commits} commits, "
                        f"{metric.total_prs_created} PRs"
                    )
                
                if not args.dry_run:
                    session.add_all(metrics)
                    session.commit()
                    logger.info(f"✓ Persisted {len(metrics)} service metric(s) to database")
                else:
                    logger.info("(dry-run mode: metrics not persisted)")
            else:
                # Single service
                service_id = args.service
                logger.info(f"Computing metrics for service {service_id}...")
                
                # Verify service exists
                if not session.get(Service, service_id):
                    logger.error(f"Service {service_id} not found")
                    return 1
                
                metric = compute_service_metrics(
                    session,
                    service_id=service_id,
                    period_start=period_start,
                    period_end=period_end,
                )
                
                # Display preview
                logger.info(
                    f"Service {service_id}: "
                    f"{metric.total_repositories} repos, "
                    f"{metric.active_repositories} active, "
                    f"{metric.total_commits} commits, "
                    f"{metric.total_prs_created} PRs, "
                    f"{metric.unique_contributors} contributors"
                )
                
                if not args.dry_run:
                    session.add(metric)
                    session.commit()
                    logger.info(f"✓ Persisted service metric to database")
                else:
                    logger.info("(dry-run mode: metric not persisted)")
            
            return 0
        finally:
            session.close()
    
    except ValueError as e:
        logger.error(f"Invalid argument: {e}")
        return 1
    except Exception as e:
        logger.exception(f"Failed to compute service metrics: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
