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
- Config data (will be provided as `--context` to Ollama, containing repo sizing/themes)

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
- `created_at`: random date in commit date range (or slightly later)
- `merged_at`: present only if status is "merged"; must be >= created_at and within commit range
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
  - Validate schema (must have `name`, `file_names`, `languages`)
  - If config missing fields, use sensible defaults
  - Exit 1 on any error; print error to stderr
- **Idempotency**:
  - If seed already has commits/PRs, skip enrichment
  - Backup original before modifying
  - Atomic writes: use `tempfile.NamedTemporaryFile(dir=seed_file.parent, delete=False)` to create temp file in same directory, then `shutil.move()` to replace original (NOT `os.rename()` or `Path.replace()` which fail across filesystems)
- **Output progress**: Print `[OK] Enriched {filename}` on success
- **No TODOs**: Fully runnable code, no incomplete sections

## Code Quality

- Use `pathlib.Path` and `json` from stdlib
- Use `random` for deterministic seeding (optional: `seed()` call)
- Use `datetime` for date math
- Per-function docstrings
- Proper error messages to stderr
- Clean, readable Python

## Output

Write the complete Python script source code. Start with shebang and imports, end with error handling and success message. Ready to execute:

```python
#!/usr/bin/env python3
"""Enrich fixture repository seed with commits and pull requests."""
...
```

That's it. Write the full script now, no explanations.
