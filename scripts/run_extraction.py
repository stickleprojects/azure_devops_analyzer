#!/usr/bin/env python3
"""
CLI entry point for running GitHub repository extraction.

This script can be run directly or invoked from the PowerShell wrapper script.

Usage:
    python run_extraction.py
    python run_extraction.py --max-repos 10
    python run_extraction.py --max-commits 100 --max-prs 50
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path when running as script
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.workflows.github_analysis import (
    GitHubAnalysisWorkflow,
    ExtractionLimits,
    print_extraction_summary,
)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the extraction process."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run GitHub repository extraction workflow.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--max-branches",
        type=int,
        default=10,
        help="Maximum branches to fetch per repository",
    )
    parser.add_argument(
        "--max-commits",
        type=int,
        default=50,
        help="Maximum commits to fetch per repository",
    )
    parser.add_argument(
        "--max-prs",
        type=int,
        default=20,
        help="Maximum pull requests to fetch per repository",
    )
    parser.add_argument(
        "--scan-interval",
        type=int,
        default=6,
        help="Minimum hours between rescanning the same repository",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser.parse_args()


def main() -> int:
    """
    Main entry point for the extraction script.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    args = parse_args()
    setup_logging(args.verbose)

    logger = logging.getLogger(__name__)
    logger.info("Initializing GitHub extraction workflow...")

    limits = ExtractionLimits(
        max_branches=args.max_branches,
        max_commits=args.max_commits,
        max_pull_requests=args.max_prs,
        min_scan_interval_hours=args.scan_interval,
    )

    try:
        workflow = GitHubAnalysisWorkflow(limits=limits)
        summary = workflow.run()
        print_extraction_summary(summary)
        return 0

    except KeyboardInterrupt:
        logger.warning("Extraction interrupted by user")
        return 130

    except Exception as e:
        logger.error("Extraction failed: %s", e, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
