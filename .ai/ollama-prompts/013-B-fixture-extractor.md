# Task: Create tests/fixtures/fixture_extractor.py

Create the file `tests/fixtures/fixture_extractor.py` from scratch.

## Purpose

A fake `RepositoryExtractor` subclass used in unit tests. It is backed by scenario JSON
files in `tests/fixtures/scenarios/<name>.json` instead of a live platform API.

## Scenario JSON schema

```json
{
  "name": "python-docker",
  "description": "Python service with Docker",
  "file_names": ["requirements.txt", "src/main.py", "Dockerfile"],
  "language_data": [
    {"language": "Python", "byte_count": 12000, "percentage": 85.0}
  ],
  "manifests": [
    {"file_path": "requirements.txt", "content": "flask==3.0.0\n", "ecosystem": "pypi"}
  ]
}
```

## Class specification

```python
class FixtureExtractor(RepositoryExtractor):
    def __init__(self, scenario: str | dict): ...
    @property
    def platform(self) -> Platform: ...
    def get_file_tree(self, repo_id, branch=None) -> list[FileTreeItem]: ...
    def get_file_content(self, repo_id, file_path, branch=None) -> str | None: ...
    def get_languages(self, repo_id) -> list[LanguageData]: ...
    # All other abstract methods:
    def get_organizations(self): ...
    def get_projects(self, org): ...
    def get_repositories(self, org, project=None): ...
    def get_repository(self, repo_id): ...
    def get_branches(self, repo_id): ...
    def get_commits(self, repo_id, **kwargs): ...
    def get_pull_requests(self, repo_id, **kwargs): ...
```

## Detailed behaviour

- `__init__`:
  - If `scenario` is a `str`, load from `tests/fixtures/scenarios/<scenario>.json`.
    Resolve the path relative to `pathlib.Path(__file__).parent / "scenarios"`.
  - If `scenario` is a `dict`, store it directly as `self._scenario`.

- `platform`: always return `Platform.GITHUB`.

- `get_file_tree`: return `[FileTreeItem(path=p, is_directory=False, size=100) for p in self._scenario["file_names"]]`.

- `get_file_content`: look up `file_path` in `self._scenario["manifests"]` by the
  `file_path` key. Return the `content` string if found, else return `None`.

- `get_languages`: return `[LanguageData(language=d["language"], byte_count=d["byte_count"], percentage=d.get("percentage")) for d in self._scenario["language_data"]]`.

- `extract_manifests`: **do NOT override** — the base class `RepositoryExtractor.extract_manifests`
  is a concrete method that calls `get_file_tree` and `get_file_content`. Our implementations
  of those two methods are sufficient for it to work correctly.

- `get_organizations`, `get_projects`, `get_repositories`, `get_branches`, `get_commits`,
  `get_pull_requests`: return `[]`.

- `get_repository`: raise `NotImplementedError("FixtureExtractor does not support get_repository")`.

## Imports

```python
import json
import pathlib
from src.extractors.base import (
    FileTreeItem,
    LanguageData,
    ManifestFileData,
    Platform,
    RepositoryExtractor,
)
```

(`ManifestFileData` is imported for completeness even though `extract_manifests` is inherited.)

## Output

Write the complete, runnable Python source for `tests/fixtures/fixture_extractor.py`.
Do not add docstrings beyond a one-line class docstring. Do not add type hints beyond
what is shown in the spec above.
