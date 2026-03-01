#!/usr/bin/env python3
"""Enrich fixture repository seed with commits and pull requests."""

import sys, json, tempfile, shutil, random
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Helper functions
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
PR_TITLE_THEMES = [
    "Add Docker support",
    "Improve Flask API",
    "Add unit tests",
    "Fix requirements issue",
    "Update CI/CD pipeline"
]
PR_STATUS = {"merged": 0.7, "open": 0.2, "closed": 0.1}
FILES_CHANGED_MIN, FILES_CHANGED_MAX, FILES_CHANGED_MEDIAN = 2, 8, 4
LINES_ADDED_MIN, LINES_ADDED_MAX, LINES_ADDED_MEDIAN = 10, 100, 40
LINES_REMOVED_MIN, LINES_REMOVED_MAX, LINES_REMOVED_MEDIAN = 0, 50, 10
PR_FILES_CHANGED_MIN, PR_FILES_CHANGED_MAX, PR_FILES_CHANGED_MEDIAN = 3, 12, 6
PR_LINES_ADDED_MIN, PR_LINES_ADDED_MAX, PR_LINES_ADDED_MEDIAN = 30, 200, 100
PR_LINES_REMOVED_MIN, PR_LINES_REMOVED_MAX, PR_LINES_REMOVED_MEDIAN = 5, 80, 30

def enrich_repo(seed_file):
    try:
        seed_data = json.loads(seed_file.read_text(encoding='utf-8'))
        if "name" not in seed_data or "file_names" not in seed_data:
            print(f"Error: Seed file {seed_file.name} is missing required fields.", file=sys.stderr)
            sys.exit(1)

        if len(seed_data.get("commits", [])) >= COMMIT_MIN:
            print(f"[OK] {seed_data['name']}.json (already done, skipping)")
            return

        # Backup original
        backup_path = seed_file.with_suffix('.json.bak')
        shutil.copy2(seed_file, backup_path)

        # Generate commits
        num_commits = random.randint(COMMIT_MIN, COMMIT_MAX)
        end_date = datetime.now(timezone.utc) - timedelta(days=1)
        start_date = end_date - timedelta(days=90)
        commits = []
        for i in range(num_commits):
            author_name = generate_realistic_name()
            author_email = generate_realistic_email(author_name)
            committer_name = random.choice([author_name, generate_realistic_name()])
            committer_email = random.choice([author_email, generate_realistic_email(committer_name)])
            message = random.choice(COMMIT_MESSAGE_THEMES)
            commit_date = generate_random_date(start_date, end_date)
            files_changed = random.randint(FILES_CHANGED_MIN, FILES_CHANGED_MAX)
            lines_added = random.randint(LINES_ADDED_MIN, LINES_ADDED_MAX)
            lines_removed = random.randint(LINES_REMOVED_MIN, LINES_REMOVED_MAX)

            commits.append({
                "commit_hash": generate_commit_hash(),
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
        prs = []
        for i in range(num_prs):
            title = random.choice(PR_TITLE_THEMES)
            description = f"Added {title}"
            status = random.choices(list(PR_STATUS.keys()), weights=list(PR_STATUS.values()))[0]
            created_at = generate_random_date(start_date, end_date)

            pr_data = {
                "pr_number": i + 1,
                "title": title,
                "description": description,
                "status": status,
                "created_at": created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "author_name": generate_realistic_name(),
                "author_email": generate_realistic_email(generate_realistic_name()),
                "review_comments": random.randint(0, 5),
                "commits_count": random.randint(1, 5),
                "files_changed": random.randint(PR_FILES_CHANGED_MIN, PR_FILES_CHANGED_MAX),
                "lines_added": random.randint(PR_LINES_ADDED_MIN, PR_LINES_ADDED_MAX),
                "lines_removed": random.randint(PR_LINES_REMOVED_MIN, PR_LINES_REMOVED_MAX)
            }

            if status == "merged":
                merged_at = generate_random_date(created_at, end_date)
                pr_data["merged_at"] = merged_at.strftime("%Y-%m-%dT%H:%M:%SZ")

            if status == "closed":
                closed_at = generate_random_date(created_at, end_date)
                pr_data["closed_at"] = closed_at.strftime("%Y-%m-%dT%H:%M:%SZ")

            prs.append(pr_data)

        seed_data["commits"] = commits
        seed_data["pull_requests"] = prs

        # Write back to the original file atomically
        temp_file = tempfile.NamedTemporaryFile(mode='w', dir=seed_file.parent, delete=False, suffix='.json')
        try:
            json.dump(seed_data, temp_file)
            temp_file.close()
            shutil.move(temp_file.name, seed_file)
        except Exception as e:
            print(f"Error writing to {seed_file.name}: {e}", file=sys.stderr)
            sys.exit(1)

        print(f"[OK] Enriched {seed_file.name}")

    except json.JSONDecodeError:
        print(f"Error: Seed file {seed_file.name} is not valid JSON.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python enrich_repo.py <seed_file>", file=sys.stderr)
        sys.exit(1)

    seed_path = Path(sys.argv[1])
    if not seed_path.exists() or not seed_path.is_file():
        print(f"Error: Seed file {seed_path} does not exist.", file=sys.stderr)
        sys.exit(1)

    enrich_repo(seed_path)