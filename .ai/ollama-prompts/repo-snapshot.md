# Task: Create scripts/capture_snapshot.py

Create `scripts/capture_snapshot.py` — a CLI utility that connects to a real repository
extractor and writes a scenario JSON file compatible with `tests/fixtures/scenarios/`.

Manually captured scenarios should be saved outside the generated/ subfolder to distinguish
them from AI-generated fixtures.

## CLI interface

Usage format:
python scripts/capture_snapshot.py <repo_id> --platform <platform> --output <path> [--branch <branch>]

Arguments:
repo_id Repository identifier (e.g. "owner/repo" for GitHub)

Options:
--platform Platform: "github" or "azure_devops" (required)
--output Path to write scenario JSON (required)
--branch Branch to scan (default: default branch)

Example invocation (manual capture, not in generated/):
python scripts/capture_snapshot.py myorg/myrepo --platform github --output tests/fixtures/scenarios/myrepo.json

## Behaviour

1. Parse args with `argparse`.
2. Call `src.extractors.factory.get_extractor(platform)` to get an extractor instance.
3. Call `extractor.get_file_tree(repo_id, branch)` → build `file_names` list from
   `item.path` for every item where `item.is_directory is False`.
4. Call `extractor.get_languages(repo_id)` → build `language_data` list as
   `[{"language": ld.language, "byte_count": ld.byte_count, "percentage": ld.percentage} for ld in ...]`.
5. Call `extractor.extract_manifests(repo_id, branch)` → build `manifests` list as
   `[{"file_path": m.file_path, "content": m.content, "ecosystem": m.ecosystem} for m in ...]`.
6. Assemble the scenario dict with keys: "name" (from output path stem), "description"
   (formatted as "Captured from {platform}:{repo_id}"), "file_names", "language_data", "manifests".
7. Write to `args.output` with `json.dumps(scenario, indent=2)`.
8. Print a summary: number of files, manifests, languages captured.

## Error handling

- If the extractor raises an exception, print the error and exit with code 1.
- Create parent directories of `--output` if they don't exist (`pathlib.Path.mkdir(parents=True, exist_ok=True)`).

## Imports

```python
import argparse
import json
import pathlib
import sys
from src.extractors.factory import get_extractor
```

## Output

Write ONLY the complete, runnable Python source for `scripts/capture_snapshot.py` as a single code block.
Keep it simple — no classes, just a `main()` function and `if __name__ == "__main__"` guard.

Your response must be structured EXACTLY as:

```python
import argparse
import json
import pathlib
import sys
from src.extractors.factory import get_extractor

def main():
    # ... full implementation ...

if __name__ == "__main__":
    main()
```

Do NOT include usage examples, commentary, or multiple code blocks in your response.
