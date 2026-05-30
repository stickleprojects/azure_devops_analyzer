#!/usr/bin/env python3
"""
CLI entry point for running repository extraction workflows.

Usage:
python run_extraction.py
python run_extraction.py --source github
python run_extraction.py --source azure-devops
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path when running as script
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.workflows.github_analysis import (
    GitHubAnalysisWorkflow,
    ExtractionLimits as GitHubExtractionLimits,
    print_extraction_summary as print_github_summary,
)

from src.workflows.azure_devops_analysis import (
    AzureDevOpsAnalysisWorkflow,
    ExtractionLimits as AzureExtractionLimits,
    print_extraction_summary as print_azure_summary,
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
        description="Run repository extraction workflow.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # ✅ NEW: source selector
    parser.add_argument(
        "--source",
        choices=["github", "azure-devops"],
        default="azure-devops",
        help="Select which workflow to run",
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
    """Main entry point for the extraction script."""
    args = parse_args()
    setup_logging(args.verbose)

    logging.info(f"Starting extraction for source: {args.source}")

    

    try:
        if args.source == "github":
            # ✅ Build limits (shared structure)
            limits = GitHubExtractionLimits(
                max_branches=args.max_branches,
                max_commits=args.max_commits,
                max_pull_requests=args.max_prs,
                min_scan_interval_hours=args.scan_interval,
            )
            workflow = GitHubAnalysisWorkflow(limits=limits)
            result = workflow.run()
            print_github_summary(result)

        elif args.source == "azure-devops":
            # Reuse limits structure (same fields expected)
            azure_limits = AzureExtractionLimits(
                max_branches=args.max_branches,
                max_commits=args.max_commits,
                max_pull_requests=args.max_prs,
                min_scan_interval_hours=args.scan_interval,
            )

            workflow = AzureDevOpsAnalysisWorkflow(limits= azure_limits)
            result = workflow.run()
            print_azure_summary(result)

        logging.info("Extraction completed successfully")
        return 0

    except Exception as e:
        logging.exception(f"Extraction failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())