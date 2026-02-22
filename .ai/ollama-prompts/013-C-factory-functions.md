# Task: Extend tests/fixtures/sample_data.py with two factory functions

Add two new functions at the bottom of `tests/fixtures/sample_data.py`.
Do not modify any existing functions. Do not change any imports unless adding new ones
required by the new functions.

---

## New imports needed (add to top of file if not already present)

```python
from datetime import datetime, UTC
from src.analyzers.technology_detector import TechnologyDetection
from src.extractors.base import FileTreeItem
import json
import pathlib
```

---

## Function 1: sample_technology_detection

```python
def sample_technology_detection(
    programming_languages: list[str] | None = None,
    frameworks: list[str] | None = None,
    databases: list[str] | None = None,
    deployment_platforms: list[str] | None = None,
    build_tools: list[str] | None = None,
    testing_frameworks: list[str] | None = None,
    ci_cd_platforms: list[str] | None = None,
    primary_language: str | None = "Python",
    overall_confidence: float = 0.75,
) -> TechnologyDetection:
    """Factory for TechnologyDetection with sensible defaults."""
```

Implementation rules:
- Default each list argument to `[]` when `None` (use `or []` inside the function body,
  not as a default value, to avoid mutable default argument issues).
- `language_confidence` defaults to `0.75`.
- `framework_confidence` defaults to `0.5`.
- `overall_confidence` is passed through as-is.
- `all_technologies` is the union of all list arguments (deduplicated, sorted).
- `analyzed_at` is `datetime.now(UTC)`.
- `documentation_tools` defaults to `[]`.

---

## Function 2: sample_file_tree

```python
def sample_file_tree(scenario_name: str) -> list[FileTreeItem]:
    """Load a named scenario and return its file tree as FileTreeItem objects."""
```

Implementation rules:
- Resolve path as:
  `pathlib.Path(__file__).parent / "scenarios" / f"{scenario_name}.json"`
- Load JSON, read the `"file_names"` list.
- Return `[FileTreeItem(path=p, is_directory=False, size=100) for p in file_names]`.
- Raise `FileNotFoundError` with a clear message if the scenario file does not exist.

---

## Output

Write the **complete updated content** of `tests/fixtures/sample_data.py`, including
all existing functions unchanged, plus the two new functions and any new imports added
at the top. Do not remove or alter any existing code.
