#!/usr/bin/env python3
"""Enrich fixture repository seed with commits and pull requests."""

import sys, json, tempfile, shutil, random
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

def enrich_repo(seed_path: Path) -> None:
    """Enrich seed JSON at seed_path with commits and pull requests."""
    with open(seed_path, encoding='utf-8') as f:
        seed_data = json.load(f)

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
    COMMIT_METADATA_FILES_CHANGED_MIN, COMMIT_METADATA_FILES_CHANGED_MAX, COMMIT_METADATA_FILES_CHANGED_MEDIAN = 2, 8, 4
    COMMIT_METADATA_LINES_ADDED_MIN, COMMIT_METADATA_LINES_ADDED_MAX, COMMIT_METADATA_LINES_ADDED_MEDIAN = 10, 100, 40
    COMMIT_METADATA_LINES_REMOVED_MIN, COMMIT_METADATA_LINES_REMOVED_MAX, COMMIT_METADATA_LINES_REMOVED_MEDIAN = 0, 50, 10
    PR_METADATA_FILES_CHANGED_MIN, PR_METADATA_FILES_CHANGED_MAX, PR_METADATA_FILES_CHANGED_MEDIAN = 3, 12, 6
    PR_METADATA_LINES_ADDED_MIN, PR_METADATA_LINES_ADDED_MAX, PR_METADATA_LINES_ADDED_MEDIAN = 30, 200, 100
    PR_METADATA_LINES_REMOVED_MIN, PR_METADATA_LINES_REMOVED_MAX, PR_METADATA_LINES_REMOVED_MEDIAN = 5, 80, 30

    # Check if already enriched
    if len(seed_data.get("commits", [])) >= COMMIT_MIN:
        print(f"[OK] {seed_data['name']}.json (already done, skipping)")
        return

    # Backup original file
    backup_path = seed_path.with_suffix('.json.bak')
    shutil.copy2(seed_path, backup_path)

    # Generate commits
    num_commits = random.randint(COMMIT_MIN, COMMIT_MAX)
    commits_start_date = datetime.now(timezone.utc) - timedelta(days=90)
    commits_end_date = datetime.now(timezone.utc) - timedelta(days=1)
    commits_dates = [generate_random_date(commits_start_date, commits_end_date) for _ in range(num_commits)]
    commits_dates.sort()

    commits = []
    for commit_date in commits_dates:
        author_name = generate_realistic_name()
        author_email = generate_realistic_email(author_name)
        committer_name = random.choice([author_name, generate_realistic_name()])
        committer_email = random.choice([author_email, generate_realistic_email(committer_name)])
        message = random.choice(COMMIT_MESSAGE_THEMES)
        files_changed = random.randint(COMMIT_METADATA_FILES_CHANGED_MIN, COMMIT_METADATA_FILES_CHANGED_MAX)
        lines_added = random.randint(COMMIT_METADATA_LINES_ADDED_MIN, COMMIT_METADATA_LINES_ADDED_MAX)
        lines_removed = random.randint(COMMIT_METADATA_LINES_REMOVED_MIN, COMMIT_METADATA_LINES_REMOVED_MAX)

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
    pr_start_date = datetime.now(timezone.utc) - timedelta(days=90)
    pr_end_date = datetime.now(timezone.utc) - timedelta(days=1)

    prs = []
    for pr_number in range(1, num_prs + 1):
        title = random.choice(PR_TITLE_THEMES)
        description = f"Added {title}"
        status = random.choices(["merged", "open", "closed"], weights=[PR_STATUS["merged"], PR_STATUS["open"], PR_STATUS["closed"]], k=1)[0]
        created_at = generate_random_date(pr_start_date, pr_end_date)

        if status == "merged":
            merged_at = generate_random_date(created_at, pr_end_date)
            closed_at = None
        elif status == "closed":
            closed_at = generate_random_date(created_at, pr_end_date)
            merged_at = None
        else:
            merged_at = None
            closed_at = None

        author_name = generate_realistic_name()
        author_email = generate_realistic_email(author_name)
        review_comments = random.randint(0, 5)
        commits_count = random.randint(1, 5)
        files_changed = random.randint(PR_METADATA_FILES_CHANGED_MIN, PR_METADATA_FILES_CHANGED_MAX)
        lines_added = random.randint(PR_METADATA_LINES_ADDED_MIN, PR_METADATA_LINES_ADDED_MAX)
        lines_removed = random.randint(PR_METADATA_LINES_REMOVED_MIN, PR_METADATA_LINES_REMOVED_MAX)

        pr = {
            "pr_number": pr_number,
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
        }
        prs.append(pr)

    # Update seed data with generated commits and pull requests
    seed_data["commits"] = commits
    seed_data["pull_requests"] = prs

    # Write back to the same file atomically
    temp_file = tempfile.NamedTemporaryFile(mode='w', dir=seed_path.parent, delete=False, suffix='.json')
    try:
        json.dump(seed_data, temp_file, indent=2)
        temp_file.close()
        shutil.move(temp_file.name, seed_path)
        print(f"[OK] Enriched {seed_path.name}")
    except Exception as e:
        sys.stderr.write(f"Error writing enriched data: {e}\n")
        exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.stderr.write("Usage: python3 enrich_repo.py <seed_file_path>\n")
        exit(1)
    
    seed_path = Path(sys.argv[1])
    
    if not seed_path.exists() or not seed_path.is_file():
        sys.stderr.write(f"Error: File {seed_path} does not exist.\n")
        exit(1)
    
    try:
        enrich_repo(seed_path)
    except Exception as e:
        sys.stderr.write(f"Error enriching repository: {e}\n")
        exit(1)