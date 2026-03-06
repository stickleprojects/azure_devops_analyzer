#!/usr/bin/env python3
"""Enrich a fixture repository seed with commits and pull requests.

Reads enrichment parameters (themes, sizing, PR status distribution) from
config.json by resolving the seed name to its repo_template and pattern.
No Ollama required.

Usage:
    python enrich-repo.py <seed.json> [config.json]

config.json defaults to tests/fixtures/scenarios/config.json relative to the
script's parent directory (i.e. the project root).
"""

import sys
import json
import tempfile
import shutil
import random
from pathlib import Path
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# Config resolution
# ---------------------------------------------------------------------------

DEFAULT_CONFIG = Path(__file__).parent.parent / "tests/fixtures/scenarios/config.json"


def find_template_name(seed_name: str, config: dict) -> str | None:
    """Return the repo_templates key for seed_name by scanning repo_sets."""
    for repo_set in config["repo_sets"]:
        if "names" in repo_set and seed_name in repo_set["names"]:
            return repo_set["template"]
        if "name_template" in repo_set:
            tmpl = repo_set["name_template"]
            for service in repo_set.get("services", []):
                if tmpl.replace("{service}", service) == seed_name:
                    return repo_set["template"]
    return None


def load_enrichment_config(seed_name: str, config: dict) -> dict:
    """Resolve seed name → template → pattern and return a flat enrichment config."""
    template_name = find_template_name(seed_name, config)
    if template_name is None:
        raise ValueError(
            f"Seed '{seed_name}' not found in any repo_sets entry in config.json. "
            "Check that config.json has a matching names or name_template entry."
        )

    if template_name not in config["repo_templates"]:
        raise ValueError(
            f"Template '{template_name}' referenced by repo_sets but not defined "
            "in repo_templates in config.json."
        )
    tmpl = config["repo_templates"][template_name]

    pattern_name = tmpl["pattern"]
    if pattern_name not in config["patterns"]:
        raise ValueError(
            f"Pattern '{pattern_name}' referenced by template '{template_name}' but "
            "not defined in patterns in config.json."
        )
    pat = config["patterns"][pattern_name]

    return {
        "commit_message_themes": tmpl["commit_message_themes"],
        "pr_title_themes": tmpl["pr_title_themes"],
        "commit_min": pat["commits"]["min"],
        "commit_max": pat["commits"]["max"],
        "pr_min": pat["pull_requests"]["min"],
        "pr_max": pat["pull_requests"]["max"],
        "commit_meta": pat["commit_metadata"],
        "pr_meta": pat["pr_metadata"],
        "pr_status": pat["pr_status"],
    }


# ---------------------------------------------------------------------------
# Helper functions (names must match the enrichment prompt spec)
# ---------------------------------------------------------------------------

def generate_realistic_name() -> str:
    first_names = ["Alice", "Bob", "Charlie", "David", "Eve"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones"]
    return f"{random.choice(first_names)} {random.choice(last_names)}"


def generate_realistic_email(name: str) -> str:
    first, last = name.split()
    domain = random.choice(["example.com", "test.org", "sample.net"])
    return f"{first.lower()}.{last.lower()}@{domain}"


def generate_commit_hash() -> str:
    return "".join(random.choices("0123456789abcdef", k=40))


def generate_random_date(start: datetime, end: datetime) -> datetime:
    """Return a random timezone-aware UTC datetime between start and end."""
    delta_days = int((end - start).total_seconds() / 86400)
    return start + timedelta(days=random.randint(0, max(delta_days, 0)))


# ---------------------------------------------------------------------------
# Enrichment logic
# ---------------------------------------------------------------------------

def enrich_repo(seed_path: Path, cfg: dict) -> None:
    """Enrich seed JSON at seed_path with commits and pull requests."""
    with open(seed_path, encoding="utf-8") as f:
        seed_data = json.load(f)

    commit_min = cfg["commit_min"]
    commit_max = cfg["commit_max"]

    # Edge-case-empty repos: write empty arrays and done
    if commit_max == 0:
        if not seed_data.get("commits") and not seed_data.get("pull_requests"):
            seed_data["commits"] = []
            seed_data["pull_requests"] = []
            _write_atomic(seed_path, seed_data)
            print(f"[OK] {seed_data['name']}.json (edge-case-empty, written empty arrays)")
        else:
            print(f"[OK] {seed_data['name']}.json (already done, skipping)")
        return

    # Idempotency: skip if already enriched
    if len(seed_data.get("commits", [])) >= commit_min:
        print(f"[OK] {seed_data['name']}.json (already done, skipping)")
        return

    # Backup original
    backup_path = seed_path.with_suffix(".json.bak")
    shutil.copy2(seed_path, backup_path)

    end_date = datetime.now(timezone.utc) - timedelta(days=1)
    start_date = end_date - timedelta(days=90)

    # Generate commits (sorted oldest → newest)
    num_commits = random.randint(commit_min, commit_max)
    commit_dates = sorted(
        generate_random_date(start_date, end_date) for _ in range(num_commits)
    )

    commits = []
    cm = cfg["commit_meta"]
    for dt in commit_dates:
        author_name = generate_realistic_name()
        committer_name = random.choice([author_name, generate_realistic_name()])
        commits.append({
            "commit_hash": generate_commit_hash(),
            "author_name": author_name,
            "author_email": generate_realistic_email(author_name),
            "committer_name": committer_name,
            "committer_email": generate_realistic_email(committer_name),
            "message": random.choice(cfg["commit_message_themes"]),
            "commit_date": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "files_changed": random.randint(cm["files_changed"]["min"], cm["files_changed"]["max"]),
            "lines_added": random.randint(cm["lines_added"]["min"], cm["lines_added"]["max"]),
            "lines_removed": random.randint(cm["lines_removed"]["min"], cm["lines_removed"]["max"]),
        })

    # Generate pull requests
    num_prs = random.randint(cfg["pr_min"], cfg["pr_max"])
    status_keys = list(cfg["pr_status"].keys())
    status_weights = [cfg["pr_status"][k] for k in status_keys]
    pm = cfg["pr_meta"]

    prs = []
    for pr_number in range(1, num_prs + 1):
        created_at = generate_random_date(start_date, end_date)
        status = random.choices(status_keys, weights=status_weights, k=1)[0]
        author_name = generate_realistic_name()

        pr_data: dict = {
            "pr_number": pr_number,
            "title": random.choice(cfg["pr_title_themes"]),
            "description": f"Added {random.choice(cfg['pr_title_themes'])}",
            "status": status,
            "created_at": created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "author_name": author_name,
            "author_email": generate_realistic_email(author_name),
            "review_comments": random.randint(0, 5),
            "commits_count": random.randint(1, 5),
            "files_changed": random.randint(pm["files_changed"]["min"], pm["files_changed"]["max"]),
            "lines_added": random.randint(pm["lines_added"]["min"], pm["lines_added"]["max"]),
            "lines_removed": random.randint(pm["lines_removed"]["min"], pm["lines_removed"]["max"]),
        }

        if status == "merged":
            merged_at = generate_random_date(created_at, end_date)
            pr_data["merged_at"] = merged_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        elif status == "closed":
            closed_at = generate_random_date(created_at, end_date)
            pr_data["closed_at"] = closed_at.strftime("%Y-%m-%dT%H:%M:%SZ")

        prs.append(pr_data)

    seed_data["commits"] = commits
    seed_data["pull_requests"] = prs

    _write_atomic(seed_path, seed_data)
    print(f"[OK] Enriched {seed_path.name}")


def _write_atomic(path: Path, data: dict) -> None:
    """Write data as JSON to path atomically via a temp file."""
    with tempfile.NamedTemporaryFile(
        mode="w", dir=path.parent, delete=False, suffix=".json"
    ) as tmp:
        json.dump(data, tmp, indent=2)
        tmp_path = Path(tmp.name)
    shutil.move(str(tmp_path), str(path))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: python enrich-repo.py <seed.json> [config.json]\n")
        sys.exit(1)

    seed_path = Path(sys.argv[1])
    if not seed_path.exists():
        sys.stderr.write(f"Error: seed file not found: {seed_path}\n")
        sys.exit(1)

    config_path = Path(sys.argv[2]) if len(sys.argv) >= 3 else DEFAULT_CONFIG
    if not config_path.exists():
        sys.stderr.write(f"Error: config file not found: {config_path}\n")
        sys.exit(1)

    try:
        with open(seed_path, encoding="utf-8") as f:
            seed_data = json.load(f)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"Error: invalid JSON in seed file {seed_path}: {exc}\n")
        sys.exit(1)

    if "name" not in seed_data or "file_names" not in seed_data:
        sys.stderr.write(
            f"Error: seed file must contain 'name' and 'file_names' fields.\n"
        )
        sys.exit(1)

    try:
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"Error: invalid JSON in config file {config_path}: {exc}\n")
        sys.exit(1)

    try:
        cfg = load_enrichment_config(seed_data["name"], config)
    except ValueError as exc:
        sys.stderr.write(f"Error: {exc}\n")
        sys.exit(1)

    try:
        enrich_repo(seed_path, cfg)
    except Exception as exc:
        sys.stderr.write(f"Error during enrichment: {exc}\n")
        sys.exit(1)
