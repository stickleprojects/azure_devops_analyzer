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
COMMIT_MIN, COMMIT_MAX, COMMIT_MEDIAN = 15, 25, 20
PR_MIN, PR_MAX, PR_MEDIAN = 5, 10, 7
COMMIT_MESSAGE_THEMES = [
    "Add Docker support",
    "Improve Flask API",
    "Add unit tests",
    "Fix requirements issue",
    "Update CI/CD pipeline"
]
PR_TITLE_THEMES = [
    "Add Docker support",
    "Improve Flask API",
    "Add unit tests",
    "Fix requirements issue",
    "Update CI/CD pipeline"
]
COMMIT_METADATA_FILES_CHANGED_MIN, COMMIT_METADATA_FILES_CHANGED_MAX, COMMIT_METADATA_FILES_CHANGED_MEDIAN = 2, 8, 4
COMMIT_METADATA_LINES_ADDED_MIN, COMMIT_METADATA_LINES_ADDED_MAX, COMMIT_METADATA_LINES_ADDED_MEDIAN = 10, 100, 40
COMMIT_METADATA_LINES_REMOVED_MIN, COMMIT_METADATA_LINES_REMOVED_MAX, COMMIT_METADATA_LINES_REMOVED_MEDIAN = 0, 50, 10
PR_METADATA_FILES_CHANGED_MIN, PR_METADATA_FILES_CHANGED_MAX, PR_METADATA_FILES_CHANGED_MEDIAN = 3, 12, 6
PR_METADATA_LINES_ADDED_MIN, PR_METADATA_LINES_ADDED_MAX, PR_METADATA_LINES_ADDED_MEDIAN = 30, 200, 100
PR_METADATA_LINES_REMOVED_MIN, PR_METADATA_LINES_REMOVED_MAX, PR_METADATA_LINES_REMOVED_MEDIAN = 5, 80, 30
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

def enrich_repo(seed_path: Path) -> None:
    """Enrich seed JSON at seed_path with commits and pull requests."""
    with open(seed_path, encoding='utf-8') as f:
        seed_data = json.load(f)

    if len(seed_data.get("commits", [])) >= COMMIT_MIN:
        print(f"[OK] {seed_data['name']}.json (already done, skipping)")
        return

    # Backup original before modifying
    backup_path = seed_path.with_suffix('.json.bak')
    shutil.copy2(seed_path, backup_path)

    # Generate commits
    num_commits = random.randint(COMMIT_MIN, COMMIT_MAX)
    if abs(num_commits - COMMIT_MEDIAN) > 2:
        num_commits = COMMIT_MEDIAN + random.randint(-2, 2)
    start_date = datetime.now(timezone.utc) - timedelta(days=90)
    end_date = datetime.now(timezone.utc) - timedelta(days=1)

    commits = []
    for i in range(num_commits):
        commit_hash = generate_commit_hash()
        author_name = generate_realistic_name()
        author_email = generate_realistic_email(author_name)
        committer_name = generate_realistic_name() if random.random() > 0.5 else author_name
        committer_email = generate_realistic_email(committer_name) if committer_name != author_name else author_email
        message = random.choice(COMMIT_MESSAGE_THEMES)
        commit_date = generate_random_date(start_date, end_date)
        files_changed = random.randint(COMMIT_METADATA_FILES_CHANGED_MIN, COMMIT_METADATA_FILES_CHANGED_MAX)
        lines_added = random.randint(COMMIT_METADATA_LINES_ADDED_MIN, COMMIT_METADATA_LINES_ADDED_MAX)
        lines_removed = random.randint(COMMIT_METADATA_LINES_REMOVED_MIN, COMMIT_METADATA_LINES_REMOVED_MAX)

        commits.append({
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
        })

    # Generate pull requests
    num_prs = random.randint(PR_MIN, PR_MAX)
    if abs(num_prs - PR_MEDIAN) > 2:
        num_prs = PR_MEDIAN + random.randint(-2, 2)

    prs = []
    for i in range(1, num_prs + 1):
        title = random.choice(PR_TITLE_THEMES)
        description = f"Added {title}"
        status = "merged"
        if random.random() < PR_STATUS_OPEN:
            status = "open"
        elif random.random() < PR_STATUS_CLOSED:
            status = "closed"

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
        files_changed = random.randint(PR_METADATA_FILES_CHANGED_MIN, PR_METADATA_FILES_CHANGED_MAX)
        lines_added = random.randint(PR_METADATA_LINES_ADDED_MIN, PR_METADATA_LINES_ADDED_MAX)
        lines_removed = random.randint(PR_METADATA_LINES_REMOVED_MIN, PR_METADATA_LINES_REMOVED_MAX)

        prs.append({
            "pr_number": i,
            "title": title,
            "description": description,
            "status": status,
            "created_at": created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "merged_at": merged_at.strftime("%Y-%m-%dT%H:%M:%SZ") if merged_at else None,
            "closed_at": closed_at.strftime("%Y-%m-%dT%H:%M:%SZ") if closed_at else None,
            "author_name": author_name,
            "author_email": author_email,
            "review_comments": review_comments,
            "commits_count": commits_count,
            "files_changed": files_changed,
            "lines_added": lines_added,
            "lines_removed": lines_removed
        })

    seed_data["commits"] = commits
    seed_data["pull_requests"] = prs

    # Write enriched JSON back to same path
    with tempfile.NamedTemporaryFile(mode='w', dir=seed_path.parent, delete=False, suffix='.json') as temp_file:
        json.dump(seed_data, temp_file, indent=2)
    shutil.move(temp_file.name, seed_path)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 enrich_repo.py <seed_json_path>", file=sys.stderr)
        sys.exit(1)

    seed_path = Path(sys.argv[1])
    if not seed_path.exists() or not seed_path.is_file():
        print(f"Error: File {seed_path} does not exist or is not a regular file.", file=sys.stderr)
        sys.exit(1)

    try:
        enrich_repo(seed_path)
        print(f"[OK] Enriched {seed_path.name}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)