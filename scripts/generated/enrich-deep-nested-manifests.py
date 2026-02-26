#!/usr/bin/env python3
"""Enrich fixture repository seed with commits and pull requests."""

import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

def generate_random_commit_hash() -> str:
    """Generate a random 40-character hex string."""
    return ''.join(random.choices('0123456789abcdef', k=40))

def generate_realistic_name() -> str:
    """Generate a realistic name."""
    first_names = ["Alice", "Bob", "Charlie", "David", "Eve"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones"]
    return f"{random.choice(first_names)} {random.choice(last_names)}"

def generate_realistic_email(name: str) -> str:
    """Generate a realistic email from a name."""
    username_parts = name.split()
    username = ''.join(part.lower() for part in username_parts)
    domain_parts = ["example", "test", "dev"]
    domain = random.choice(domain_parts) + ".com"
    return f"{username}@{domain}"

def generate_commit_date(start: datetime, end: datetime) -> str:
    """Generate a random commit date within a range."""
    delta = end - start
    random_seconds = random.randint(0, int(delta.total_seconds()))
    return (start + timedelta(seconds=random_seconds)).isoformat()

def generate_pr_status(pr_status: Dict[str, float]) -> str:
    """Generate a PR status based on given probabilities."""
    status_values = list(pr_status.keys())
    status_probabilities = list(pr_status.values())
    return random.choices(status_values, weights=status_probabilities)[0]

def enrich_seed(seed_path: Path, config: Dict[str, Any]) -> None:
    """Enrich the seed JSON with commits and pull requests."""
    if not seed_path.exists():
        print(f"Error: Seed file {seed_path} does not exist.", file=sys.stderr)
        sys.exit(1)

    try:
        with open(seed_path, 'r') as f:
            seed_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to decode JSON from {seed_path}: {e}", file=sys.stderr)
        sys.exit(1)

    if "name" not in seed_data or "file_names" not in seed_data or "languages" not in seed_data:
        print("Error: Seed data must contain 'name', 'file_names', and 'languages'.", file=sys.stderr)
        sys.exit(1)

    # Skip enrichment if already done
    if "commits" in seed_data and "pull_requests" in seed_data:
        print(f"[OK] Enriched {seed_path.name}")
        return

    # Backup original file
    backup_path = seed_path.with_suffix(seed_path.suffix + '.bak')
    seed_path.rename(backup_path)

    start_date = datetime.now(timezone.utc) - timedelta(days=90)
    end_date = datetime.now(timezone.utc) - timedelta(days=1)

    commits_count = random.randint(config["commits"]["min"], config["commits"]["max"])
    prs_count = random.randint(config["pull_requests"]["min"], config["pull_requests"]["max"])

    commits = []
    for i in range(1, commits_count + 1):
        commit_date = generate_commit_date(start_date, end_date)
        commit_message = random.choice(config["commit_message_themes"])
        files_changed = random.randint(
            config["commit_metadata"]["files_changed"]["min"],
            config["commit_metadata"]["files_changed"]["max"]
        )
        lines_added = random.randint(
            config["commit_metadata"]["lines_added"]["min"],
            config["commit_metadata"]["lines_added"]["max"]
        )
        lines_removed = random.randint(
            config["commit_metadata"]["lines_removed"]["min"],
            config["commit_metadata"]["lines_removed"]["max"]
        )

        commit_hash = generate_random_commit_hash()
        author_name = generate_realistic_name()
        author_email = generate_realistic_email(author_name)
        committer_name = random.choice([author_name, generate_realistic_name()])
        committer_email = random.choice([author_email, generate_realistic_email(committer_name)])

        commits.append({
            "commit_hash": commit_hash,
            "author_name": author_name,
            "author_email": author_email,
            "committer_name": committer_name,
            "committer_email": committer_email,
            "message": commit_message,
            "commit_date": commit_date,
            "files_changed": files_changed,
            "lines_added": lines_added,
            "lines_removed": lines_removed
        })

    pull_requests = []
    pr_number = 1
    for i in range(1, prs_count + 1):
        created_at = generate_commit_date(start_date, end_date)
        status = generate_pr_status(config["pr_status"])
        title = random.choice(config["pr_title_themes"])
        description = f"Added {title}"
        review_comments = random.randint(0, 5)
        commits_count_pr = random.randint(1, 5)
        files_changed = random.randint(
            config["pr_metadata"]["files_changed"]["min"],
            config["pr_metadata"]["files_changed"]["max"]
        )
        lines_added = random.randint(
            config["pr_metadata"]["lines_added"]["min"],
            config["pr_metadata"]["lines_added"]["max"]
        )
        lines_removed = random.randint(
            config["pr_metadata"]["lines_removed"]["min"],
            config["pr_metadata"]["lines_removed"]["max"]
        )

        author_name = generate_realistic_name()
        author_email = generate_realistic_email(author_name)

        pr_data = {
            "pr_number": pr_number,
            "title": title,
            "description": description,
            "status": status,
            "created_at": created_at,
            "author_name": author_name,
            "author_email": author_email,
            "review_comments": review_comments,
            "commits_count": commits_count_pr,
            "files_changed": files_changed,
            "lines_added": lines_added,
            "lines_removed": lines_removed
        }

        if status == "merged":
            merged_at = generate_commit_date(datetime.fromisoformat(created_at), end_date)
            pr_data["merged_at"] = merged_at

        if status in ["closed", "merged"]:
            closed_at = generate_commit_date(datetime.fromisoformat(created_at), end_date)
            pr_data["closed_at"] = closed_at

        pull_requests.append(pr_data)
        pr_number += 1

    seed_data["commits"] = commits
    seed_data["pull_requests"] = pull_requests

    with open(seed_path, 'w') as f:
        json.dump(seed_data, f, indent=2)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python enrich-repo.py <seed-path> <config-json>", file=sys.stderr)
        sys.exit(1)

    seed_path = Path(sys.argv[1])
    config_json = sys.argv[2]

    try:
        config = json.loads(config_json)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to decode JSON from config: {e}", file=sys.stderr)
        sys.exit(1)

    enrich_seed(seed_path, config)
    print(f"[OK] Enriched {seed_path.name}")