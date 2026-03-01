#!/usr/bin/env python3
"""Enrich fixture repository seed with commits and pull requests."""

import sys
import json
import tempfile
import shutil
import random
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Required helper functions
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
PR_TITLE_THEMES = COMMIT_MESSAGE_THEMES
PR_STATUS = {"merged": 0.7, "open": 0.2, "closed": 0.1}
COMMIT_FILES_CHANGED_MIN, COMMIT_FILES_CHANGED_MAX, COMMIT_FILES_CHANGED_MEDIAN = 2, 8, 4
COMMIT_LINES_ADDED_MIN, COMMIT_LINES_ADDED_MAX, COMMIT_LINES_ADDED_MEDIAN = 10, 100, 40
COMMIT_LINES_REMOVED_MIN, COMMIT_LINES_REMOVED_MAX, COMMIT_LINES_REMOVED_MEDIAN = 0, 50, 10
PR_FILES_CHANGED_MIN, PR_FILES_CHANGED_MAX, PR_FILES_CHANGED_MEDIAN = 3, 12, 6
PR_LINES_ADDED_MIN, PR_LINES_ADDED_MAX, PR_LINES_ADDED_MEDIAN = 30, 200, 100
PR_LINES_REMOVED_MIN, PR_LINES_REMOVED_MAX, PR_LINES_REMOVED_MEDIAN = 5, 80, 30

def generate_commits(seed_data):
    commits = []
    num_commits = random.randint(COMMIT_MIN, COMMIT_MAX)
    start_date = datetime.now(timezone.utc) - timedelta(days=90)
    end_date = datetime.now(timezone.utc) - timedelta(days=1)

    for _ in range(num_commits):
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

        commits.append({
            "commit_hash": commit_hash,
            "author_name": author_name,
            "author_email": author_email,
            "committer_name": committer_name,
            "committer_email": committer_email,
            "message": message,
            "commit_date": commit_date.isoformat(),
            "files_changed": files_changed,
            "lines_added": lines_added,
            "lines_removed": lines_removed
        })

    return commits

def generate_pull_requests(seed_data):
    prs = []
    num_prs = random.randint(PR_MIN, PR_MAX)
    start_date = datetime.now(timezone.utc) - timedelta(days=90)
    end_date = datetime.now(timezone.utc) - timedelta(days=1)

    for i in range(1, num_prs + 1):
        pr_status = random.choices(["merged", "open", "closed"], [PR_STATUS["merged"], PR_STATUS["open"], PR_STATUS["closed"]])[0]
        title = random.choice(PR_TITLE_THEMES)
        description = f"Added {title}"
        created_at = generate_random_date(start_date, end_date)

        pr_data = {
            "pr_number": i,
            "title": title,
            "description": description,
            "status": pr_status,
            "created_at": created_at.isoformat(),
            "author_name": generate_realistic_name(),
            "author_email": generate_realistic_email(pr_data["author_name"]),
            "review_comments": random.randint(0, 5),
            "commits_count": random.randint(1, 5),
            "files_changed": random.randint(PR_FILES_CHANGED_MIN, PR_FILES_CHANGED_MAX),
            "lines_added": random.randint(PR_LINES_ADDED_MIN, PR_LINES_ADDED_MAX),
            "lines_removed": random.randint(PR_LINES_REMOVED_MIN, PR_LINES_REMOVED_MAX)
        }

        if pr_status == "merged":
            merged_at = generate_random_date(created_at, end_date)
            pr_data["merged_at"] = merged_at.isoformat()

        if pr_status == "closed":
            closed_at = generate_random_date(created_at, end_date)
            pr_data["closed_at"] = closed_at.isoformat()

        prs.append(pr_data)

    return prs

def main():
    seed_file_path = sys.argv[1]
    seed_file = Path(seed_file_path)

    if not seed_file.exists() or not seed_file.is_file():
        print(f"Error: Seed file '{seed_file_path}' does not exist or is not a valid file.", file=sys.stderr)
        return 1

    try:
        with open(seed_file, 'r') as f:
            seed_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to decode JSON from seed file '{seed_file_path}'. {e}", file=sys.stderr)
        return 1

    if "name" not in seed_data or "file_names" not in seed_data:
        print(f"Error: Seed file '{seed_file_path}' is missing required fields 'name' and/or 'file_names'.", file=sys.stderr)
        return 1

    if len(seed_data.get("commits", [])) >= COMMIT_MIN:
        print(f"[OK] {seed_data['name']}.json (already done, skipping)")
        return 0

    # Backup original before modifying
    backup_path = seed_file.with_suffix('.json.bak')
    shutil.copy2(seed_file, backup_path)

    # Generate commits and PRs
    seed_data["commits"] = generate_commits(seed_data)
    seed_data["pull_requests"] = generate_pull_requests(seed_data)

    # Write enriched JSON back to same path
    with tempfile.NamedTemporaryFile(mode='w', dir=seed_file.parent, delete=False, suffix='.json') as temp_file:
        json.dump(seed_data, temp_file, indent=2)

    shutil.move(temp_file.name, seed_file_path)

    print(f"[OK] Enriched {seed_file.name}")
    return 0

if __name__ == "__main__":
    sys.exit(main())