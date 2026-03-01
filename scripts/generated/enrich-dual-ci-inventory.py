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
COMMIT_METADATA = {
    "files_changed": {"min": 2, "max": 8, "median": 4},
    "lines_added": {"min": 10, "max": 100, "median": 40},
    "lines_removed": {"min": 0, "max": 50, "median": 10}
}
PR_METADATA = {
    "files_changed": {"min": 3, "max": 12, "median": 6},
    "lines_added": {"min": 30, "max": 200, "median": 100},
    "lines_removed": {"min": 5, "max": 80, "median": 30}
}
PR_STATUS = {
    "merged": 0.7,
    "open": 0.2,
    "closed": 0.1
}

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

    # Backup original
    backup_path = seed_path.with_suffix('.json.bak')
    shutil.copy2(seed_path, backup_path)

    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=90)
    end_date = now - timedelta(days=1)

    def generate_commit():
        commit_hash = generate_commit_hash()
        author_name = generate_realistic_name()
        committer_name = generate_realistic_name() if random.random() < 0.5 else author_name
        message = random.choice(COMMIT_MESSAGE_THEMES)
        commit_date = generate_random_date(start_date, end_date)
        files_changed = random.randint(
            COMMIT_METADATA["files_changed"]["min"],
            COMMIT_METADATA["files_changed"]["max"]
        )
        lines_added = random.randint(
            COMMIT_METADATA["lines_added"]["min"],
            COMMIT_METADATA["lines_added"]["max"]
        )
        lines_removed = random.randint(
            COMMIT_METADATA["lines_removed"]["min"],
            COMMIT_METADATA["lines_removed"]["max"]
        )
        return {
            "commit_hash": commit_hash,
            "author_name": author_name,
            "author_email": generate_realistic_email(author_name),
            "committer_name": committer_name,
            "committer_email": generate_realistic_email(committer_name),
            "message": message,
            "commit_date": commit_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "files_changed": files_changed,
            "lines_added": lines_added,
            "lines_removed": lines_removed
        }

    def generate_pr():
        pr_number = len(seed_data.get("pull_requests", [])) + 1
        title = random.choice(PR_TITLE_THEMES)
        status = random.choices(
            ["merged", "open", "closed"],
            [PR_STATUS["merged"], PR_STATUS["open"], PR_STATUS["closed"]]
        )[0]
        created_at = generate_random_date(start_date, end_date)
        pr_data = {
            "pr_number": pr_number,
            "title": title,
            "description": f"Added {title}",
            "status": status,
            "created_at": created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "author_name": generate_realistic_name(),
            "author_email": generate_realistic_email(generate_realistic_name()),
            "review_comments": random.randint(0, 5),
            "commits_count": random.randint(1, 5),
            "files_changed": random.randint(
                PR_METADATA["files_changed"]["min"],
                PR_METADATA["files_changed"]["max"]
            ),
            "lines_added": random.randint(
                PR_METADATA["lines_added"]["min"],
                PR_METADATA["lines_added"]["max"]
            ),
            "lines_removed": random.randint(
                PR_METADATA["lines_removed"]["min"],
                PR_METADATA["lines_removed"]["max"]
            )
        }
        if status == "merged":
            pr_data["merged_at"] = generate_random_date(created_at, now).strftime("%Y-%m-%dT%H:%M:%SZ")
        elif status == "closed":
            pr_data["closed_at"] = generate_random_date(created_at, now).strftime("%Y-%m-%dT%H:%M:%SZ")
        return pr_data

    # Generate commits
    num_commits = random.randint(COMMIT_MIN, COMMIT_MAX)
    commits = [generate_commit() for _ in range(num_commits)]
    seed_data["commits"] = sorted(commits, key=lambda x: x["commit_date"])

    # Generate pull requests
    num_prs = random.randint(PR_MIN, PR_MAX)
    prs = [generate_pr() for _ in range(num_prs)]
    seed_data["pull_requests"] = sorted(prs, key=lambda x: x["created_at"])

    # Write enriched JSON back to the same path
    with tempfile.NamedTemporaryFile(mode='w', dir=seed_path.parent, delete=False, suffix='.json') as temp_file:
        json.dump(seed_data, temp_file, indent=2)

    shutil.move(temp_file.name, seed_path)
    print(f"[OK] Enriched {seed_path.name}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.stderr.write("Usage: python3 enrich_repo.py <seed_json_path>\n")
        sys.exit(1)

    seed_path = Path(sys.argv[1])

    if not seed_path.exists() or not seed_path.is_file():
        sys.stderr.write(f"Error: {seed_path} does not exist or is not a file.\n")
        sys.exit(1)

    try:
        enrich_repo(seed_path)
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)