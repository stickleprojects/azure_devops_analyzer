#!/usr/bin/env python3
"""
Progress Monitoring Script

Usage:
    python scripts/check_progress.py              # Show all progress
    python scripts/check_progress.py --github     # GitHub only
    python scripts/check_progress.py --azure      # Azure DevOps only
    python scripts/check_progress.py --watch      # Auto-refresh every 5 seconds
"""

import argparse
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.connection import session_scope
from src.database.models import Repository, Commit, PullRequest, Branch
from sqlalchemy import func, desc


def get_extraction_progress(session, platform=None):
    """Get extraction progress statistics."""
    
    query = session.query(Repository)
    if platform:
        query = query.filter(Repository.repo_id.like(f"{platform}%"))
    
    total_repos = query.count()
    
    # Repos analyzed in last hour
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    recent = query.filter(
        Repository.last_analyzed_at >= one_hour_ago
    ).count()
    
    # Repos analyzed in last 24 hours
    one_day_ago = datetime.utcnow() - timedelta(days=1)
    today = query.filter(
        Repository.last_analyzed_at >= one_day_ago
    ).count()
    
    # Never analyzed
    never_analyzed = query.filter(
        Repository.last_analyzed_at.is_(None)
    ).count()
    
    # Get most recently analyzed repos
    recent_repos = query.filter(
        Repository.last_analyzed_at.isnot(None)
    ).order_by(
        desc(Repository.last_analyzed_at)
    ).limit(5).all()
    
    return {
        'total_repos': total_repos,
        'recent_1h': recent,
        'recent_24h': today,
        'never_analyzed': never_analyzed,
        'analyzed': total_repos - never_analyzed,
        'recent_repos': recent_repos
    }


def get_data_statistics(session, platform=None):
    """Get data extraction statistics."""
    
    repo_filter = f"{platform}%" if platform else "%"
    
    commits = session.query(func.count(Commit.commit_id)).filter(
        Commit.repo_id.like(repo_filter)
    ).scalar() or 0
    
    prs = session.query(func.count(PullRequest.pr_id)).filter(
        PullRequest.repo_id.like(repo_filter)
    ).scalar() or 0
    
    branches = session.query(func.count(Branch.branch_id)).filter(
        Branch.repo_id.like(repo_filter)
    ).scalar() or 0
    
    return {
        'commits': commits,
        'pull_requests': prs,
        'branches': branches
    }


def print_progress(github_progress, azure_progress, github_stats, azure_stats):
    """Print formatted progress report."""
    
    print("\n" + "=" * 70)
    print(f"{'REPOSITORY EXTRACTION PROGRESS':^70}")
    print(f"{'Updated: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S'):^70}")
    print("=" * 70)
    
    # GitHub Progress
    print(f"\n{'GITHUB':^70}")
    print("-" * 70)
    print(f"  Total Repositories:     {github_progress['total_repos']:>6}")
    print(f"  Analyzed:              {github_progress['analyzed']:>6}")
    print(f"  Never Analyzed:        {github_progress['never_analyzed']:>6}")
    print(f"  Analyzed (Last 1h):    {github_progress['recent_1h']:>6}")
    print(f"  Analyzed (Last 24h):   {github_progress['recent_24h']:>6}")
    print()
    print(f"  Data Extracted:")
    print(f"    Commits:             {github_stats['commits']:>6}")
    print(f"    Pull Requests:       {github_stats['pull_requests']:>6}")
    print(f"    Branches:            {github_stats['branches']:>6}")
    
    if github_progress['recent_repos']:
        print(f"\n  Recently Analyzed:")
        for repo in github_progress['recent_repos']:
            age = "Never" if not repo.last_analyzed_at else \
                  f"{(datetime.utcnow() - repo.last_analyzed_at).total_seconds() / 60:.0f}m ago"
            print(f"    • {repo.name:<40} {age:>10}")
    
    # Azure DevOps Progress
    print(f"\n{'AZURE DEVOPS':^70}")
    print("-" * 70)
    print(f"  Total Repositories:     {azure_progress['total_repos']:>6}")
    print(f"  Analyzed:              {azure_progress['analyzed']:>6}")
    print(f"  Never Analyzed:        {azure_progress['never_analyzed']:>6}")
    print(f"  Analyzed (Last 1h):    {azure_progress['recent_1h']:>6}")
    print(f"  Analyzed (Last 24h):   {azure_progress['recent_24h']:>6}")
    print()
    print(f"  Data Extracted:")
    print(f"    Commits:             {azure_stats['commits']:>6}")
    print(f"    Pull Requests:       {azure_stats['pull_requests']:>6}")
    print(f"    Branches:            {azure_stats['branches']:>6}")
    
    if azure_progress['recent_repos']:
        print(f"\n  Recently Analyzed:")
        for repo in azure_progress['recent_repos']:
            age = "Never" if not repo.last_analyzed_at else \
                  f"{(datetime.utcnow() - repo.last_analyzed_at).total_seconds() / 60:.0f}m ago"
            print(f"    • {repo.name:<40} {age:>10}")
    
    # Overall Summary
    total_repos = github_progress['total_repos'] + azure_progress['total_repos']
    total_analyzed = github_progress['analyzed'] + azure_progress['analyzed']
    
    print(f"\n{'OVERALL SUMMARY':^70}")
    print("-" * 70)
    print(f"  Total Repositories:     {total_repos:>6}")
    print(f"  Total Analyzed:        {total_analyzed:>6}")
    print(f"  Completion:            {total_analyzed/total_repos*100 if total_repos > 0 else 0:>5.1f}%")
    print("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Monitor repository extraction progress")
    parser.add_argument('--github', action='store_true', help='Show GitHub only')
    parser.add_argument('--azure', action='store_true', help='Show Azure DevOps only')
    parser.add_argument('--watch', action='store_true', help='Auto-refresh every 5 seconds')
    parser.add_argument('--interval', type=int, default=5, help='Refresh interval in seconds (default: 5)')
    
    args = parser.parse_args()
    
    try:
        while True:
            try:
                with session_scope() as session:
                # Determine which platforms to show
                show_github = not args.azure  # Show if not Azure-only
                show_azure = not args.github  # Show if not GitHub-only
                
                github_progress = get_extraction_progress(session, 'github' if show_github else None)
                azure_progress = get_extraction_progress(session, 'azure' if show_azure else None)
                github_stats = get_data_statistics(session, 'github' if show_github else None)
                azure_stats = get_data_statistics(session, 'azure' if show_azure else None)
                
                # Clear screen in watch mode
                if args.watch:
                    print("\033[2J\033[H", end="")  # Clear screen and move cursor to top
                
                print_progress(github_progress, azure_progress, github_stats, azure_stats)
            
            if not args.watch:
                break
            
            time.sleep(args.interval)
    
    except Exception as e:
        if "connection" in str(e).lower() or "operational" in str(e).lower():
            print("\n❌ ERROR: Cannot connect to database", file=sys.stderr)
            print("\nMake sure Docker services are running:", file=sys.stderr)
            print("  docker compose up -d\n", file=sys.stderr)
            sys.exit(1)
        raise
    
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")
        sys.exit(0)


if __name__ == "__main__":
    main()
