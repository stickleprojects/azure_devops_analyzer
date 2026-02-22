````markdown
# Task: Create scripts/generate-013-fixtures.py

Create `scripts/generate-013-fixtures.py` — a Python script that generates 10 diverse test
scenario JSON files for testing the technology detection system.

## Purpose

Generate realistic test fixture scenarios that cover a variety of technology stacks, CI/CD
platforms, package managers, and edge cases. No LLM needed at runtime — the script contains
hardcoded scenario data and writes JSON files directly.

## Output location

All scenarios must be written to: `tests/fixtures/scenarios/generated/`

## Scenario JSON schema

Each scenario is a dict with these keys:

```json
{
  "name": "python-docker",
  "description": "Brief description of the scenario",
  "file_names": ["requirements.txt", "src/main.py", "Dockerfile"],
  "language_data": [
    { "language": "Python", "byte_count": 12000, "percentage": 85.0 }
  ],
  "manifests": [
    {
      "file_path": "requirements.txt",
      "content": "flask==3.0.0\nrequests==2.31.0\n",
      "ecosystem": "pypi"
    }
  ],
  "branches": [
    { "name": "main", "latest_commit_sha": "abc123def456" },
    { "name": "develop", "latest_commit_sha": "def789ghi012" }
  ],
  "commits": [
    {
      "sha": "abc123def456",
      "message": "Add Docker support",
      "author_email": "developer@example.com",
      "author_name": "Developer",
      "committer_email": "developer@example.com",
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
      "title": "Add Docker support",
      "description": "Adds Dockerfile and docker-compose configuration",
      "source_branch": "feature/docker",
      "target_branch": "main",
      "author_email": "developer@example.com",
      "author_name": "Developer",
      "status": "merged",
      "created_at": "2026-01-12T14:00:00",
      "merged_at": "2026-01-15T10:30:00",
      "files_changed": 3,
      "lines_added": 45,
      "lines_removed": 12
    }
  ]
}
```

**Optional fields**: `branches`, `commits`, and `pull_requests` are optional. Include them for scenarios
that need to test commit/PR analysis, but can be omitted for simple technology detection tests.

## Required scenario diversity

Create exactly 10 scenarios covering:

1. **python-docker** - Python service with Docker and GitHub Actions CI
   - Files: requirements.txt, src/main.py, Dockerfile, docker-compose.yml, .github/workflows/ci.yml
   - Language: Python (85%)
   - Manifest: requirements.txt with flask, requests, celery

2. **react-spa** - React SPA with TypeScript and GitHub Actions
   - Files: package.json, tsconfig.json, src/App.tsx, src/index.tsx, .github/workflows/ci.yml
   - Languages: TypeScript (90%), HTML (7%), CSS (3%)
   - Manifest: package.json with react, react-dom, typescript

3. **java-maven-jenkins** - Java service with Maven and Jenkins CI
   - Files: pom.xml, Jenkinsfile, src/main/java/com/example/App.java
   - Language: Java (95%)
   - Manifest: pom.xml with spring-boot-starter-web

4. **fullstack-monorepo** - Python backend + React frontend in monorepo
   - Files: requirements.txt, frontend/package.json, src/api/main.py, frontend/src/App.tsx
   - Languages: Python (55%), TypeScript (45%)
   - Manifests: Both requirements.txt (fastapi, uvicorn) and package.json (react, axios)

5. **dotnet-legacy** - .NET with both legacy packages.config and modern .csproj, Azure Pipelines
   - Files: MyApp.csproj, packages.config, azure-pipelines.yml, src/Program.cs
   - Language: C# (98%)
   - Manifests: Both .csproj and packages.config (different Newtonsoft.Json versions)

6. **dual-ci** - Repository with both Jenkins and GitHub Actions
   - Files: Jenkinsfile, .github/workflows/ci.yml, requirements.txt, src/app.py
   - Language: Python (100%)
   - Manifest: requirements.txt with flask, pytest

7. **python-dual-deps** - Python with both Pipfile and requirements.txt
   - Files: Pipfile, Pipfile.lock, requirements.txt, app.py
   - Language: Python (100%)
   - Manifests: Both Pipfile and requirements.txt with overlapping deps

8. **go-microservice** - Go microservice with sparse file tree
   - Files: go.mod, go.sum, main.go, Dockerfile
   - Language: Go (100%)
   - Manifest: go.mod with gin-gonic/gin

9. **empty-stub** - Repository with no code (edge case)
   - Files: README.md only
   - Languages: empty list
   - Manifests: empty list

10. **deep-nested-manifests** - Manifests only in subdirectories (edge case)
    - Files: services/api/requirements.txt, services/web/package.json, services/\*/src/...
    - Languages: Python (50%), TypeScript (50%)
    - Manifests: Both nested in services/ subdirectories

**Branch/Commit/PR Guidelines**:

- Scenarios 1, 2, 3, 4, 5, 8, 10: Include branches, commits, and pull requests
- Scenarios 6, 7, 9: Omit branches/commits/PRs (minimal edge cases)
- Always include at least "main" branch when branches are present
- Commit dates should be sequential (oldest to newest)
- PR dates should align with commit dates (created before merged)
- Use ISO 8601 format without timezone: "2026-01-15T10:30:00"
- PR statuses: "merged", "open", or "closed"

## Implementation requirements

- Use `pathlib.Path` for all file operations
- Define scenarios as a list of dicts in a `SCENARIOS` constant
- In `main()`: create output directory, iterate scenarios, write JSON files
- Print progress: `[OK] <relative-path>` for each file, then summary line
- Add `if __name__ == "__main__"` guard
- Use `json.dumps(scenario, indent=2) + "\n"` for formatting

## Manifest content guidelines

Keep manifest content realistic but minimal:

- Python requirements.txt: 2-4 packages with versions
- package.json: Valid JSON with name, dependencies object
- Maven pom.xml: Valid XML with groupId, artifactId, version, dependencies
- .csproj: Valid XML with TargetFramework, PackageReference items
- go.mod: Valid go.mod syntax with module path and require block

## Imports

Required imports:
import json
import pathlib

## Output

Write ONLY the complete, runnable Python source for `scripts/generate-013-fixtures.py` as a single code block.

Your response must be structured EXACTLY as:

```python
#!/usr/bin/env python3
"""Generate test fixture JSON files for plan 013.

No LLM needed — all scenario data is deterministic from the plan spec.

AI-generated fixtures are placed in tests/fixtures/scenarios/generated/ to distinguish
them from manually created scenarios.

Usage:
    python scripts/generate-013-fixtures.py
"""

import json
import pathlib

SCENARIOS_DIR = pathlib.Path(__file__).parent.parent / "tests" / "fixtures" / "scenarios" / "generated"

SCENARIOS = [
    # ... 10 scenario dicts here ...
]

def main() -> None:
    # ... implementation ...

if __name__ == "__main__":
    main()
```

Do NOT include usage examples, commentary, or multiple code blocks in your response.
````
