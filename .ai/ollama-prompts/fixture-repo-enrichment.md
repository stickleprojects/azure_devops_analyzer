# Prompt: Generate Per-Repo Fixture Enrichment Script

You are a Python code generation expert. Your task is to write a complete, runnable Python script that enriches a fixture repository seed with realistic commits and pull requests.

## Context

The fixture system uses a two-layer generation approach:

1. Layer 1: Generate structural seeds (already done)
2. **Layer 2 (this prompt)**: Add commits and PRs to each seed

You have access to the complete config object which includes:

- The seed JSON file being enriched (file path passed via `sys.argv[1]`)
- The repo configuration: sizing ranges, metadata ranges, themes
- Pattern configuration: commit/PR metadata ranges, status distributions

## Task

Generate a complete Python script: `scripts/generated/enrich-{repo}.py`

**Input**:

- `sys.argv[1]`: path to seed JSON file (e.g., `tests/fixtures/scenarios/generated/python-docker.json`)

**Important**: The repo config and seed JSON are already visible to you in the system context above.
Extract the config entry matching this repo's `name` field and embed the sizing/theme values
as hardcoded Python constants at the top of the generated script. Do NOT read config from
`sys.argv[2]` or any other argument — `sys.argv[1]` is the only argument.

**Logic**:

1. Read seed JSON from `sys.argv[1]`
2. Generate realistic commits and PRs based on config sizing/themes
3. Write enriched JSON back to same path
4. Print `[OK] Enriched {filename}` on success
5. Exit with code 1 on error

**Idempotency**:

- If enrichment runs twice, result must be identical
- If seed already has commits/PRs, skip enrichment (assume already done)
- Backup original before modifying: `{name}.json.bak`

## Commit Generation

### Sizing

- Source config: `config["commits"]` dict with `min`, `max`, `median` values
- Generate quantity: random int in [min, max], aiming for median ± 2
- Example: if median is 20, generate 18–22 commits

### Metadata per Commit

- `commit_hash`: 40-char hex string (fake but valid format)
- `author_name`: realistic name (vary per commit)
- `author_email`: realistic email format
- `committer_name`: same as author or different (vary)
- `committer_email`: same as author or different
- `message`: drawn from config `commit_message_themes` list (random selection, uniform probability)
- `commit_date`: ordered oldest → newest, range 90 days ago to 1 day ago
- `files_changed`: random int in config `commit_metadata["files_changed"]` range
- `lines_added`: random int in config `commit_metadata"]["lines_added"]` range
- `lines_removed`: random int in config `commit_metadata"]["lines_removed"]` range

### Diffstat Ranges (from config)

Source config at: `config["commit_metadata"]` with min/max/median for each metric.
Example:

```json
"commit_metadata": {
  "files_changed": {"min": 2, "max": 8, "median": 4},
  "lines_added": {"min": 10, "max": 100, "median": 40},
  "lines_removed": {"min": 0, "max": 50, "median": 10}
}
```

### Date Distribution

- Oldest commit: ~90 days before today (ISO format: YYYY-MM-DD)
- Newest commit: ~1 day before today
- Distribute evenly across this range (no clustering)
- Format: ISO 8601 datetime (YYYY-MM-DDTHH:MM:SSZ)

## Pull Request Generation

### Sizing

- Source config: `config["pull_requests"]` dict with `min`, `max`, `median` values
- Generate quantity: random int in [min, max], aiming for median ± 2

### Metadata per PR

- `pr_number`: sequential starting from 1
- `title`: drawn from config `pr_title_themes` list (random selection)
- `description`: short placeholder (e.g., "Added {title}")
- `status`: distributed per config `pr_status` percentages (merged/open/closed)
  - Example: `{"merged": 0.70, "open": 0.20, "closed": 0.10}` → 70% PRs get status "merged", etc.
- `created_at`: random date in the same 90-day window used for commits (`datetime.now() - timedelta(days=90)` to `datetime.now() - timedelta(days=1)`). Do NOT read dates from `seed_data["commits"]` — the seed may only have placeholder data.
- `merged_at`: present only if status is "merged"; must be >= created_at and within the same window
- `closed_at`: present only if status is "closed"; must be >= created_at
- `author_name`: realistic (may differ from commit author)
- `author_email`: realistic format
- `review_comments`: random int 0–5
- `commits_count`: random int matching typical PR commit count (1–5)
- `files_changed`: random int in config `pr_metadata["files_changed"]` range
- `lines_added`: random int in config `pr_metadata"]["lines_added"]` range
- `lines_removed`: random int in config `pr_metadata"]["lines_removed"]` range

### PR Status Distribution

Source config at: `config["pr_status"]` with percentages (merged/open/closed).

- Use these percentages to distribute PR statuses
- Example: if 0.70 → merged, generate ~70% of PRs with status "merged"

## Example Config Structure (will be passed in context)

```json
{
  "name": "python-docker",
  "commit_message_themes": [
    "Add Docker support",
    "Improve Flask API",
    "Add unit tests",
    "Fix requirements issue",
    "Update CI/CD pipeline"
  ],
  "pr_title_themes": [
    "Add Docker support",
    "Improve Flask API",
    "Add unit tests",
    "Fix requirements issue",
    "Update CI/CD pipeline"
  ],
  "commits": { "min": 15, "max": 25, "median": 20 },
  "commit_metadata": {
    "files_changed": { "min": 2, "max": 8, "median": 4 },
    "lines_added": { "min": 10, "max": 100, "median": 40 },
    "lines_removed": { "min": 0, "max": 50, "median": 10 }
  },
  "pull_requests": { "min": 5, "max": 10, "median": 7 },
  "pr_metadata": {
    "files_changed": { "min": 3, "max": 12, "median": 6 },
    "lines_added": { "min": 30, "max": 200, "median": 100 },
    "lines_removed": { "min": 5, "max": 80, "median": 30 }
  },
  "pr_status": { "merged": 0.7, "open": 0.2, "closed": 0.1 }
}
```

## Enriched JSON Schema

After enrichment, the seed JSON should have this structure:

```json
{
  "name": "python-docker",
  "description": "...",
  "languages": ["Python"],
  "file_names": [...],
  "manifests": {...},
  "branches": [...],
  "commits": [
    {
      "commit_hash": "abc123...",
      "author_name": "Alice Smith",
      "author_email": "alice@example.com",
      "committer_name": "Alice Smith",
      "committer_email": "alice@example.com",
      "message": "Add Docker support",
      "commit_date": "2025-11-25T10:30:00Z",
      "files_changed": 4,
      "lines_added": 45,
      "lines_removed": 12
    },
    ...
  ],
  "pull_requests": [
    {
      "pr_number": 1,
      "title": "Add Docker support",
      "description": "Added Docker support",
      "status": "merged",
      "created_at": "2025-11-24T08:15:00Z",
      "merged_at": "2025-11-25T14:20:00Z",
      "author_name": "Bob Johnson",
      "author_email": "bob@example.com",
      "review_comments": 2,
      "commits_count": 3,
      "files_changed": 6,
      "lines_added": 120,
      "lines_removed": 45
    },
    ...
  ]
}
```

## Guidelines

- **Realism**: Commit messages and PR titles should match repo tech stack (Python → Flask, pytest; Go → Gin, go.mod; etc.)
- **Chronology**: All PR created_at dates must be valid relative to commit dates; merged_at > created_at
- **Determinism**: Use median ± 2 as target to keep quantities consistent across runs
- **Error handling**:
  - Check seed file exists and is valid JSON
  - Validate schema (must have `name` and `file_names` — do NOT check for `languages`, seeds use `language_data`)
  - If config missing fields, use sensible defaults
  - Exit 1 on any error; print error to stderr
- **Datetime safety**: Always use timezone-aware UTC datetimes. Use `datetime.datetime.now(datetime.timezone.utc)` instead of `datetime.datetime.now()`. Use `generate_random_date(start, end)` (defined in Required Helpers above) for all random date selection — never inline the arithmetic. Keep datetime objects in memory and only convert to ISO string at the final step via `dt.strftime("%Y-%m-%dT%H:%M:%SZ")`. Never re-parse a `"...Z"` ISO string with `fromisoformat()` and then pass it to arithmetic functions alongside an offset-naive datetime — mixing aware and naive datetimes raises `TypeError`.
- **Idempotency**:
  - Check: `if len(seed_data.get("commits", [])) >= COMMIT_MIN:` — if already enriched, print `[OK] {seed_data['name']}.json (already done, skipping)` and return. Do NOT check merely whether the `commits` key exists, as seeds may already contain 1 placeholder commit from Layer 1 generation. Use `seed_data['name']` (not `seed_file.name`) in this message, since helper functions do not have `seed_file` in scope.
  - Backup original before modifying
  - Atomic writes: use `tempfile.NamedTemporaryFile(mode='w', dir=seed_file.parent, delete=False, suffix='.json')` to create temp file in same directory, then `shutil.move()` to replace original (NOT `os.rename()` or `Path.replace()` which fail across filesystems). The `mode='w'` is required so `json.dump()` can write strings.
- **Output progress**: Print `[OK] Enriched {filename}` on success
- **No TODOs**: Fully runnable code, no incomplete sections

## Required Helper Functions

Copy these implementations verbatim into your script — do not rename or restructure them:

```python
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
    # ... enrichment logic here ...
```

Call sites must use these exact names: `generate_realistic_name()`, `generate_realistic_email(name)`, `generate_commit_hash()`, `generate_random_date(start, end)`, `enrich_repo(seed_path)`.

The `enrich_repo` function **must** accept a `Path` object named `seed_path` and open the file with `open()` as shown above. Do NOT name the parameter `seed_file` and do NOT call `json.load(seed_path)` directly on the Path — `json.load` requires an open file handle, not a Path.

## Code Quality

- Use these exact imports at the top of the script:
  ```python
  import sys, json, tempfile, shutil, random
  from pathlib import Path
  from datetime import datetime, timedelta, timezone
  ```
  Always use `from datetime import datetime, timedelta, timezone` — never `import datetime` (module-style). Then call `datetime.now(timezone.utc)`, `timedelta(days=90)`, etc.
- Use `random` for deterministic seeding (optional: `seed()` call)
- Per-function docstrings
- Proper error messages to stderr
- Clean, readable Python
- Always assign variables before using them in dict literals — do NOT reference a variable inside a dict literal before it has been assigned on a prior line. E.g., assign `author_name = generate_realistic_name()` on its own line, then use `"author_name": author_name` in the dict. Also do NOT self-reference the dict being constructed — e.g., `"author_email": generate_realistic_email(pr_metadata["author_name"])` inside the `pr_metadata = {...}` literal is illegal because `pr_metadata` does not exist until the entire dict is evaluated. Assign intermediate values to named variables first:
  ```python
  pr_author_name = generate_realistic_name()
  pr_data = {
      "author_name": pr_author_name,
      "author_email": generate_realistic_email(pr_author_name),
      ...
  }
  ```
- Embed config as hardcoded constants near the top of the script, e.g.:
  ```python
  # Config for this repo (embedded at generation time)
  COMMIT_MIN, COMMIT_MAX, COMMIT_MEDIAN = 15, 25, 20
  PR_MIN, PR_MAX, PR_MEDIAN = 5, 10, 7
  COMMIT_MESSAGE_THEMES = ["Add Docker support", ...]
  PR_TITLE_THEMES = ["Add Docker support", ...]
  PR_STATUS = {"merged": 0.7, "open": 0.2, "closed": 0.1}
  ```

## Output

Write the complete Python script source code. Start with shebang and imports, end with error handling and success message. Ready to execute:

```python
#!/usr/bin/env python3
"""Enrich fixture repository seed with commits and pull requests."""
...
```

That's it. Write the full script now, no explanations.
