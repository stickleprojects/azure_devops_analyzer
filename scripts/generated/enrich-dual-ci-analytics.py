#!/usr/bin/env python3
"""Enrich fixture repository seed with commits and pull requests."""

import sys, json, tempfile, shutil, random
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Required Helper Functions
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

def main():
    if len(sys.argv) != 2:
        sys.stderr.write("Usage: {} <seed_json_file>\n".format(sys.argv[0]))
        sys.exit(1)

    seed_file = Path(sys.argv[1])
    if not seed_file.exists() or not seed_file.is_file():
        sys.stderr.write(f"Error: File '{seed_file}' does not exist or is not a file.\n")
        sys.exit(1)

    try:
        with open(seed_file, 'r') as f:
            seed_data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        sys.stderr.write(f"Error: Failed to read JSON from '{seed_file}': {e}\n")
        sys.exit(1)

    if not isinstance(seed_data, dict):
        sys.stderr.write("Error: Seed data is not a dictionary.\n")
        sys.exit(1)

    required_keys = {'name', 'file_names'}
    missing_keys = required_keys - seed_data.keys()
    if missing_keys:
        sys.stderr.write(f"Error: Seed data missing required keys: {', '.join(missing_keys)}\n")
        sys.exit(1)

    # Check for existing commits and skip enrichment if already done
    if len(seed_data.get("commits", [])) >= COMMIT_MIN:
        print(f"[OK] {seed_data['name']}.json (already done, skipping)")
        return

    # Backup original file before modifying
    backup_file = seed_file.with_suffix('.json.bak')
    shutil.copy2(seed_file, backup_file)

    # Generate commits
    num_commits = random.randint(COMMIT_MIN, COMMIT_MAX)
    commit_date_start = datetime.now(timezone.utc) - timedelta(days=90)
    commit_date_end = datetime.now(timezone.utc) - timedelta(days=1)
    commits = []

    for i in range(num_commits):
        author_name = generate_realistic_name()
        author_email = generate_realistic_email(author_name)
        committer_name = random.choice([author_name, generate_realistic_name()])
        committer_email = random.choice([author_email, generate_realistic_email(committer_name)])
        message = random.choice(COMMIT_MESSAGE_THEMES)
        commit_date = generate_random_date(commit_date_start, commit_date_end)

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

        commit = {
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
        }
        commits.append(commit)

    # Generate pull requests
    num_prs = random.randint(PR_MIN, PR_MAX)
    prs = []

    for i in range(num_prs):
        title = random.choice(PR_TITLE_THEMES)
        description = f"Added {title}"
        status = random.choices(list(PR_STATUS.keys()), list(PR_STATUS.values()))[0]
        created_at = generate_random_date(commit_date_start, commit_date_end)

        if status == "merged":
            merged_at = generate_random_date(created_at, commit_date_end)
        else:
            merged_at = None

        if status in ["closed", "merged"]:
            closed_at = generate_random_date(created_at, commit_date_end)
        else:
            closed_at = None

        author_name = generate_realistic_name()
        author_email = generate_realistic_email(author_name)

        pr = {
            "pr_number": i + 1,
            "title": title,
            "description": description,
            "status": status,
            "created_at": created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "merged_at": merged_at.strftime("%Y-%m-%dT%H:%M:%SZ") if merged_at else None,
            "closed_at": closed_at.strftime("%Y-%m-%dT%H:%M:%SZ") if closed_at else None,
            "author_name": author_name,
            "author_email": author_email,
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
        prs.append(pr)

    # Enrich seed data with commits and pull requests
    seed_data.update({"commits": commits, "pull_requests": prs})

    # Write enriched JSON back to the same file atomically
    temp_file = tempfile.NamedTemporaryFile(mode='w', dir=seed_file.parent, delete=False, suffix='.json')
    try:
        with temp_file as f:
            json.dump(seed_data, f, indent=2)
        shutil.move(temp_file.name, seed_file)
        print(f"[OK] Enriched {seed_file.name}")
    except Exception as e:
        sys.stderr.write(f"Error: Failed to write enriched JSON to '{seed_file}': {e}\n")
        if temp_file and not temp_file.closed:
            temp_file.close()
            Path(temp_file.name).unlink(missing_ok=True)
        sys.exit(1)

if __name__ == "__main__":
    main()