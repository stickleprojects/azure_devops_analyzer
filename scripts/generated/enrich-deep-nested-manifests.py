#!/usr/bin/env python3
"""Enrich fixture repository seed with commits and pull requests."""

import sys
import json
import tempfile
import shutil
import random
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Config for this repo (embedded at generation time)
COMMIT_MIN, COMMIT_MAX, COMMIT_MEDIAN = 12, 20, 16
PR_MIN, PR_MAX, PR_MEDIAN = 8, 15, 11
COMMIT_MESSAGE_THEMES = [
    "Backend API implementation",
    "Frontend component",
    "monorepo structure",
    "shared utilities",
    "cross-service communication"
]
PR_TITLE_THEMES = [
    "Add backend service",
    "Add React component",
    "Improve shared library",
    "Cross-service integration",
    "Enhance deployment pipeline"
]
COMMIT_FILES_CHANGED_MIN, COMMIT_FILES_CHANGED_MAX, COMMIT_FILES_CHANGED_MEDIAN = 4, 15, 8
COMMIT_LINES_ADDED_MIN, COMMIT_LINES_ADDED_MAX, COMMIT_LINES_ADDED_MEDIAN = 50, 500, 150
COMMIT_LINES_REMOVED_MIN, COMMIT_LINES_REMOVED_MAX, COMMIT_LINES_REMOVED_MEDIAN = 20, 200, 50
PR_FILES_CHANGED_MIN, PR_FILES_CHANGED_MAX, PR_FILES_CHANGED_MEDIAN = 6, 20, 12
PR_LINES_ADDED_MIN, PR_LINES_ADDED_MAX, PR_LINES_ADDED_MEDIAN = 100, 800, 300
PR_LINES_REMOVED_MIN, PR_LINES_REMOVED_MAX, PR_LINES_REMOVED_MEDIAN = 50, 300, 100
PR_STATUS_MERGED, PR_STATUS_OPEN, PR_STATUS_CLOSED = 0.7, 0.2, 0.1

def generate_realistic_name():
    first_names = ["Alice", "Bob", "Charlie", "David", "Eve"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones"]
    return f"{random.choice(first_names)} {random.choice(last_names)}"

def generate_realistic_email(name):
    first, last = name.split()
    domain = random.choice(["example.com", "test.org", "sample.net"])
    return f"{first.lower()}.{last.lower()}@{domain}"

def generate_commit_hash():
    return ''.join(random.choices('0123456789abcdef', k=40))

def generate_random_date(start, end):
    """Return a random timezone-aware UTC datetime between start and end."""
    delta_days = int((end - start).total_seconds() / 86400)
    return start + timedelta(days=random.randint(0, max(delta_days, 0)))

def generate_commits(seed_data):
    num_commits = random.randint(COMMIT_MIN, COMMIT_MAX)
    commits = []
    
    end_date = datetime.now(timezone.utc) - timedelta(days=1)
    start_date = end_date - timedelta(days=90)

    for i in range(num_commits):
        commit_hash = generate_commit_hash()
        author_name = generate_realistic_name()
        author_email = generate_realistic_email(author_name)
        committer_name = random.choice([author_name, generate_realistic_name()])
        committer_email = random.choice([author_email, generate_realistic_email(committer_name)])
        message = random.choice(COMMIT_MESSAGE_THEMES)
        commit_date = generate_random_date(start_date, end_date)
        
        files_changed = random.randint(COMMIT_FILES_CHANGED_MIN, COMMIT_FILES_CHANGED_MAX)
        lines_added = random.randint(COMMIT_LINES_ADDED_MIN, COMMIT_LINES_ADDED_MAX)
        lines_removed = random.randint(COMMIT_LINES_REMOVED_MIN, COMMIT_LINES_REMOVED_MAX)

        commit_data = {
            "commit_hash": commit_hash,
            "author_name": author_name,
            "author_email": author_email,
            "committer_name": committer_name,
            "committer_email": committer_email,
            "message": message,
            "commit_date": commit_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "files_changed": files_changed,
            "lines_added": lines_added,
            "lines_removed": lines_removed
        }
        
        commits.append(commit_data)
    
    return sorted(commits, key=lambda x: x['commit_date'])

def generate_pull_requests(seed_data):
    num_prs = random.randint(PR_MIN, PR_MAX)
    prs = []
    
    end_date = datetime.now(timezone.utc) - timedelta(days=1)
    start_date = end_date - timedelta(days=90)

    for i in range(1, num_prs + 1):
        title = random.choice(PR_TITLE_THEMES)
        description = f"Added {title}"
        
        status_choices = ["merged", "open", "closed"]
        status_probs = [PR_STATUS_MERGED, PR_STATUS_OPEN, PR_STATUS_CLOSED]
        status = random.choices(status_choices, weights=status_probs)[0]

        created_at = generate_random_date(start_date, end_date)
        merged_at = None
        closed_at = None

        if status == "merged":
            merged_at = generate_random_date(created_at, end_date)
        elif status == "closed":
            closed_at = generate_random_date(created_at, end_date)

        author_name = generate_realistic_name()
        author_email = generate_realistic_email(author_name)
        
        review_comments = random.randint(0, 5)
        commits_count = random.randint(1, 5)
        
        files_changed = random.randint(PR_FILES_CHANGED_MIN, PR_FILES_CHANGED_MAX)
        lines_added = random.randint(PR_LINES_ADDED_MIN, PR_LINES_ADDED_MAX)
        lines_removed = random.randint(PR_LINES_REMOVED_MIN, PR_LINES_REMOVED_MAX)

        pr_data = {
            "pr_number": i,
            "title": title,
            "description": description,
            "status": status,
            "created_at": created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "author_name": author_name,
            "author_email": author_email,
            "review_comments": review_comments,
            "commits_count": commits_count,
            "files_changed": files_changed,
            "lines_added": lines_added,
            "lines_removed": lines_removed
        }
        
        if merged_at:
            pr_data["merged_at"] = merged_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        if closed_at:
            pr_data["closed_at"] = closed_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        prs.append(pr_data)
    
    return sorted(prs, key=lambda x: x['created_at'])

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 enrich.py <seed_file_path>", file=sys.stderr)
        sys.exit(1)

    seed_file = Path(sys.argv[1])
    if not seed_file.exists() or not seed_file.is_file():
        print(f"Error: File '{seed_file}' does not exist.", file=sys.stderr)
        sys.exit(1)

    try:
        with open(seed_file, 'r') as f:
            seed_data = json.load(f)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error: Invalid JSON in file '{seed_file}'.", file=sys.stderr)
        sys.exit(1)

    if "name" not in seed_data or "file_names" not in seed_data:
        print("Error: Seed file must contain 'name' and 'file_names' fields.", file=sys.stderr)
        sys.exit(1)

    if len(seed_data.get("commits", [])) >= COMMIT_MIN:
        print(f"[OK] {seed_data['name']}.json (already done, skipping)")
        return

    # Backup original seed file
    backup_file = f"{seed_file}.bak"
    shutil.copy2(seed_file, backup_file)

    # Generate commits and PRs
    seed_data["commits"] = generate_commits(seed_data)
    seed_data["pull_requests"] = generate_pull_requests(seed_data)

    # Write enriched data back to the original file atomically
    with tempfile.NamedTemporaryFile(mode='w', dir=seed_file.parent, delete=False, suffix='.json') as temp:
        json.dump(seed_data, temp, indent=2)
    
    shutil.move(temp.name, seed_file)

    print(f"[OK] Enriched {seed_file}")

if __name__ == "__main__":
    main()