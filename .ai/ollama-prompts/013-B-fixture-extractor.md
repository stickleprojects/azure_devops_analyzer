# Task: Create tests/fixtures/fixture_extractor.py

Create the file `tests/fixtures/fixture_extractor.py` from scratch.

## Purpose

A fake `RepositoryExtractor` subclass used in unit tests. It is backed by scenario JSON
files in `tests/fixtures/scenarios/<name>.json` or `tests/fixtures/scenarios/generated/<name>.json`
instead of a live platform API.

## Scenario JSON schema

```json
{
  "name": "python-docker",
  "description": "Python service with Docker",
  "file_names": ["requirements.txt", "src/main.py", "Dockerfile"],
  "language_data": [
    { "language": "Python", "byte_count": 12000, "percentage": 85.0 }
  ],
  "manifests": [
    {
      "file_path": "requirements.txt",
      "content": "flask==3.0.0\n",
      "ecosystem": "pypi"
    }
  ],
  "branches": [{ "name": "main", "latest_commit_sha": "abc123" }],
  "commits": [
    {
      "sha": "abc123",
      "message": "Initial commit",
      "author_email": "dev@example.com",
      "author_name": "Developer",
      "committer_email": "dev@example.com",
      "committer_name": "Developer",
      "commit_date": "2026-01-15T10:30:00",
      "files_changed": 3,
      "lines_added": 45,
      "lines_removed": 12
    }
  ],
  "pull_requests": [
    {
      "pr_number": 1,
      "platform_pr_id": "pr-1",
      "title": "Add feature",
      "description": "Description",
      "source_branch": "feature/x",
      "target_branch": "main",
      "author_email": "dev@example.com",
      "author_name": "Developer",
      "status": "merged",
      "created_at": "2026-01-10T09:00:00",
      "merged_at": "2026-01-15T10:30:00",
      "files_changed": 3,
      "lines_added": 45,
      "lines_removed": 12
    }
  ]
}
```

Optional fields: `branches`, `commits`, and `pull_requests` may be absent.

## Class specification

Implement this interface:
class FixtureExtractor(RepositoryExtractor):
def **init**(self, scenario: str | dict)
@property platform(self) -> Platform
def get_file_tree(self, repo_id, branch=None) -> list[FileTreeItem]
def get_file_content(self, repo_id, file_path, branch=None) -> str | None
def get_languages(self, repo_id) -> list[LanguageData]
def get_branches(self, repo_id) -> list[BranchData]
def get_commits(self, repo_id, **kwargs) -> list[CommitData]
def get_pull_requests(self, repo_id, **kwargs) -> list[PullRequestData]
def get_organizations(self)
def get_projects(self, org)
def get_repositories(self, org, project=None)
def get_repository(self, repo_id)

## Detailed behaviour

- `__init__`:
  - If `scenario` is a `str`, load from scenario file. Try these paths in order:
    1. `pathlib.Path(__file__).parent / "scenarios" / "generated" / f"{scenario}.json"`
    2. `pathlib.Path(__file__).parent / "scenarios" / f"{scenario}.json"`
       Use the first path that exists. Raise FileNotFoundError if neither exists.
  - If `scenario` is a `dict`, store it directly as `self._scenario`.

- `platform`: always return `Platform.GITHUB`.

- `get_file_tree`: return `[FileTreeItem(path=p, is_directory=False, size=100) for p in self._scenario["file_names"]]`.

- `get_file_content`: look up `file_path` in `self._scenario["manifests"]` by the
  `file_path` key. Return the `content` string if found, else return `None`.

- `get_languages`: return `[LanguageData(language=d["language"], byte_count=d["byte_count"], percentage=d.get("percentage")) for d in self._scenario["language_data"]]`.

- `extract_manifests`: **do NOT override** — the base class `RepositoryExtractor.extract_manifests`
  is a concrete method that calls `get_file_tree` and `get_file_content`. Our implementations
  of those two methods are sufficient for it to work correctly.

- `get_branches`: return `[BranchData(name=b["name"], latest_commit_sha=b["latest_commit_sha"]) for b in self._scenario.get("branches", [])]`.

- `get_commits`: return `[CommitData(sha=c["sha"], message=c["message"], author_email=c["author_email"], author_name=c.get("author_name"), committer_email=c["committer_email"], committer_name=c.get("committer_name"), commit_date=datetime.fromisoformat(c["commit_date"]), files_changed=c.get("files_changed"), lines_added=c.get("lines_added"), lines_removed=c.get("lines_removed")) for c in self._scenario.get("commits", [])]`.

- `get_pull_requests`: return `[PullRequestData(pr_number=pr["pr_number"], platform_pr_id=pr["platform_pr_id"], title=pr["title"], description=pr.get("description"), source_branch=pr["source_branch"], target_branch=pr["target_branch"], author_email=pr["author_email"], author_name=pr.get("author_name"), status=pr["status"], created_at=datetime.fromisoformat(pr["created_at"]), merged_at=datetime.fromisoformat(pr["merged_at"]) if pr.get("merged_at") else None, closed_at=datetime.fromisoformat(pr["closed_at"]) if pr.get("closed_at") else None, files_changed=pr.get("files_changed", 0), lines_added=pr.get("lines_added", 0), lines_removed=pr.get("lines_removed", 0)) for pr in self._scenario.get("pull_requests", [])]`.

- `get_organizations`, `get_projects`, `get_repositories`: return `[]`.

- `get_repository`: raise `NotImplementedError("FixtureExtractor does not support get_repository")`.

## Imports

Required imports:
import json
import pathlib
from datetime import datetime
from src.extractors.base import BranchData, CommitData, FileTreeItem, LanguageData, ManifestFileData, Platform, PullRequestData, RepositoryExtractor

(ManifestFileData is imported for completeness even though extract_manifests is inherited.)

## Output

Write ONLY the complete, runnable Python source for `tests/fixtures/fixture_extractor.py` as a single code block.
Do not add docstrings beyond a one-line class docstring. Do not add type hints beyond what is shown in the spec above.

Your response must be structured EXACTLY as:

```python
import json
import pathlib
from datetime import datetime
from src.extractors.base import (
    BranchData,
    CommitData,
    FileTreeItem,
    LanguageData,
    ManifestFileData,
    Platform,
    PullRequestData,
    RepositoryExtractor,
)

class FixtureExtractor(RepositoryExtractor):
    """A fake RepositoryExtractor for testing backed by scenario JSON files."""
    # ... full implementation ...
```

Do NOT include usage examples, commentary, or multiple code blocks in your response.
