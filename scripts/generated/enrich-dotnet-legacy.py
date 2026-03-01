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
    "files_changed": { "min": 2, "max": 8, "median": 4 },
    "lines_added": { "min": 10, "max": 100, "median": 40 },
    "lines_removed": { "min": 0, "max": 50, "median": 10 }
}
PR_METADATA = {
    "files_changed": { "min": 3, "max": 12, "median": 6 },
    "lines_added": { "min": 30, "max": 200, "median": 100 },
    "lines_removed": { "min": 5, "max": 80, "median": 30 }
}

def generate_commits(seed_data):
    start_date = datetime.now(timezone.utc) - timedelta(days=90)
    end_date = datetime.now(timezone.utc) - timedelta(days=1)
    
    num_commits = random.randint(COMMIT_MIN, COMMIT_MAX)
    commits = []
    for _ in range(num_commits):
        commit_hash = generate_commit_hash()
        author_name = generate_realistic_name()
        author_email = generate_realistic_email(author_name)
        committer_choice = random.choice([True, False])
        if committer_choice:
            committer_name = author_name
            committer_email = author_email
        else:
            committer_name = generate_realistic_name()
            committer_email = generate_realistic_email(committer_name)
        
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
    
    return commits

def generate_pull_requests(seed_data):
    start_date = datetime.now(timezone.utc) - timedelta(days=90)
    end_date = datetime.now(timezone.utc) - timedelta(days=1)
    
    num_prs = random.randint(PR_MIN, PR_MAX)
    prs = []
    for i in range(1, num_prs + 1):
        title = random.choice(PR_TITLE_THEMES)
        description = f"Added {title}"
        status_probs = list(PR_STATUS.values())
        status_choices = list(PR_STATUS.keys())
        status = random.choices(status_choices, status_probs)[0]
        
        created_at = generate_random_date(start_date, end_date)
        merged_at = None
        closed_at = None
        if status == "merged":
            merged_at = generated_random_date(created_at, end_date)
        elif status == "closed":
            closed_at = generate_random_date(created_at, end_date)
        
        author_name = generate_realistic_name()
        author_email = generate_realistic_email(author_name)
        
        review_comments = random.randint(0, 5)
        commits_count = random.randint(1, 5)
        files_changed = random.randint(
            PR_METADATA["files_changed"]["min"],
            PR_METADATA["files_changed"]["max"]
        )
        lines_added = random.randint(
            PR_METADATA["lines_added"]["min"],
            PR_METADATA["lines_added"]["max"]
        )
        lines_removed = random.randint(
            PR_METADATA["lines_removed"]["min"],
            PR_METADATA["lines_removed"]["max"]
        )
        
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
    
    return prs

def enrich_seed(seed_file_path):
    seed_file = Path(seed_file_path)
    
    if not seed_file.exists():
        sys.stderr.write(f"Error: Seed file {seed_file_path} does not exist.\n")
        sys.exit(1)
    
    try:
        with open(seed_file, 'r') as f:
            seed_data = json.load(f)
    except json.JSONDecodeError:
        sys.stderr.write("Error: Seed file is not valid JSON.\n")
        sys.exit(1)
    
    if "name" not in seed_data or "file_names" not in seed_data:
        sys.stderr.write("Error: Seed file must contain 'name' and 'file_names' fields.\n")
        sys.exit(1)
    
    if len(seed_data.get("commits", [])) >= COMMIT_MIN:
        print(f"[OK] {seed_data['name']}.json (already done, skipping)")
        return
    
    # Backup original seed file
    backup_file = f"{seed_file_path}.bak"
    shutil.copy2(seed_file_path, backup_file)
    
    # Generate commits and PRs
    commits = generate_commits(seed_data)
    prs = generate_pull_requests(seed_data)
    
    # Update seed data with new commits and PRs
    seed_data["commits"] = commits
    seed_data["pull_requests"] = prs
    
    # Write enriched JSON back to the same path
    temp_file = tempfile.NamedTemporaryFile(mode='w', dir=seed_file.parent, delete=False, suffix='.json')
    with open(temp_file.name, 'w') as f:
        json.dump(seed_data, f, indent=2)
    
    # Replace original file atomically
    shutil.move(temp_file.name, seed_file_path)
    
    print(f"[OK] Enriched {seed_file.name}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.stderr.write("Usage: python3 enrich-repo.py <path_to_seed_json>\n")
        sys.exit(1)
    
    seed_file_path = sys.argv[1]
    try:
        enrich_seed(seed_file_path)
    except Exception as e:
        sys.stderr.write(f"An error occurred: {e}\n")
        sys.exit(1)