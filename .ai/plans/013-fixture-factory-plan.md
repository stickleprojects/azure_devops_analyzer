# Plan 013: Fixture Factory & Post-Scan Verification

**Status**: ✅ Complete
**Source**: `.ai/investigations/dev-feedback-and-test-coverage.md` (complete)
**Addresses**: Problem 1 (dev feedback loop) + Problem 2 (realistic test coverage gap)
**Generation Pattern**: Ollama-in-Docker (see `.ai/patterns/ollama-fixture-and-code-generation.md`)

**Implementation Summary**: All deliverables are generated using local LLM (Ollama with qwen2.5-coder:14b) following detailed prompts in `.ai/ollama-prompts/013-*.md`. Regenerate anytime with `bash scripts/run-013-ollama.sh`. Generated test scenarios now support branches, commits, and pull requests for workflow testing.

**Key Features Delivered**:

- 10 diverse test scenarios with realistic file structures
- Scenarios include branch, commit, and PR data for workflow testing
- FixtureExtractor class for loading scenarios in tests
- Factory functions in sample_data.py for test data creation
- Post-scan verification script for canary repository validation
- Live repository snapshot capture utility
- Comprehensive documentation across tests/, scripts/, docs/, and main README

---

## Problem Summary

Two related gaps:

1. **No automated post-scan verification** — after a 30-min scan, correctness is checked
   manually with SQL and Grafana. A canary repo verification script would eliminate most
   of this manual work.

2. **No fixture-driven test infrastructure for detector/manifest logic** — tests patch
   `get_file_tree` inline with `mocker.patch.object`. There is no named scenario library,
   no `FixtureExtractor`, and no `TechnologyDetection` factory. Adding new edge-case tests
   requires duplicating mock setup every time.

---

## Implementation Details

### Generation Infrastructure

All code is generated using Ollama (qwen2.5-coder:14b model) running in Docker containers:

**Orchestration**: `bash scripts/run-013-ollama.sh`

- Executes 5 generation steps sequentially (A through E)
- Validates output after each step (syntax check, line count)
- Supports `--step X` for regenerating individual deliverables
- Supports `--model <name>` for testing different LLMs
- Each step runs in isolated python:3.12-slim container

**Generation Script**: `scripts/ollama-generate.py`

- Calls Ollama API at http://localhost:11434
- Enhanced code extraction (selects largest code block, 50+ char minimum)
- Pure stdlib implementation (no external dependencies)
- Writes generated code directly to target files

**Prompts**: `.ai/ollama-prompts/013-*.md`

- 013-A: Generates Python script that creates 10 scenario JSON files
- 013-B: Generates FixtureExtractor class with branch/commit/PR support
- 013-C: Generates factory functions extending sample_data.py
- 013-D: Generates capture_snapshot.py for live repository capture
- 013-E: Generates verify_canary.py for post-scan validation

**Pattern Documentation**: `.ai/patterns/ollama-fixture-and-code-generation.md`

- Reusable template for mechanical code generation
- Validation checklist and best practices
- Model selection guidance
- Example bash orchestration helpers

### Enhanced Schema Support

Test scenarios now include optional workflow data:

```json
{
  "name": "example-scenario",
  "branches": [
    { "name": "main", "sha": "abc123", "is_default": true },
    { "name": "feature/new", "sha": "def456", "is_default": false }
  ],
  "commits": [
    {
      "sha": "abc123",
      "message": "Initial commit",
      "author": "dev@example.com"
    }
  ],
  "pull_requests": [
    {
      "number": 1,
      "title": "Add feature",
      "state": "open",
      "source_branch": "feature/new"
    }
  ]
}
```

This enables testing of branch-aware extraction, commit history analysis, and PR workflow logic.

### File Organization

- **Scenarios**: `tests/fixtures/scenarios/generated/` for AI-generated files
- **Extractor**: `tests/fixtures/fixture_extractor.py` tries `generated/` first, falls back to parent
- **Documentation**: Comprehensive guides added to 5 README files:
  - `tests/README.md` - Usage guide with examples
  - `scripts/README.md` - run-013-ollama.sh reference
  - `README.md` - Quick start for new developers
  - `docs/README.md` - Navigation to AI patterns
  - `.ai/plans/013-fixture-factory-plan.md` - This file

---

## Solution Design

### Shared fixture JSON schema

All scenario files live in `tests/fixtures/scenarios/` and share this schema:

```json
{
  "name": "python-docker",
  "description": "Python service with Docker and GitHub Actions CI",
  "file_names": [
    "requirements.txt",
    "src/main.py",
    "Dockerfile",
    "docker-compose.yml",
    ".github/workflows/ci.yml"
  ],
  "language_data": [{ "language": "Python" }],
  "manifests": [
    {
      "file_path": "requirements.txt",
      "content": "flask==3.0.0\nrequests==2.31.0\ncelery==5.3.4",
      "ecosystem": "pypi"
    }
  ]
}
```

- `file_names` drives `TechnologyDetector.detect()` and `FixtureExtractor.get_file_tree()`
- `language_data` drives the `language_data` argument to `detect()`
- `manifests` drives `FixtureExtractor.extract_manifests()`

---

## Deliverables

### A. `tests/fixtures/scenarios/` — 10 scenario JSON files

| File                         | Pattern                               | Key signals                                                  |
| ---------------------------- | ------------------------------------- | ------------------------------------------------------------ |
| `python-docker.json`         | Python service + Docker + GH Actions  | `requirements.txt`, `Dockerfile`, `.github/workflows/ci.yml` |
| `react-spa.json`             | React SPA, TypeScript, GitHub Actions | `package.json`, `tsconfig.json`, `.github/workflows/`        |
| `java-maven-jenkins.json`    | Java, Maven, Jenkins                  | `pom.xml`, `Jenkinsfile`                                     |
| `fullstack-monorepo.json`    | Python backend + React frontend       | `requirements.txt`, `frontend/package.json`                  |
| `dotnet-legacy.json`         | .NET migration with old + new deps    | `MyApp.csproj`, `packages.config`, `azure-pipelines.yml`     |
| `dual-ci.json`               | Jenkins + GitHub Actions both present | `Jenkinsfile`, `.github/workflows/ci.yml`                    |
| `python-dual-deps.json`      | Pipfile + requirements.txt coexist    | `Pipfile`, `Pipfile.lock`, `requirements.txt`                |
| `go-microservice.json`       | Go, Docker only; sparse tree          | `go.mod`, `go.sum`, `Dockerfile`                             |
| `empty-stub.json`            | No code; README only                  | `README.md`                                                  |
| `deep-nested-manifests.json` | Manifests only in subdirs             | `services/api/requirements.txt`, `services/web/package.json` |

### B. `tests/fixtures/fixture_extractor.py` — fake `RepositoryExtractor`

```python
class FixtureExtractor(RepositoryExtractor):
    """Fake extractor backed by a scenario JSON file. Use in unit tests."""

    def __init__(self, scenario: str | dict):
        # str → load from tests/fixtures/scenarios/<scenario>.json
        # dict → use directly
        ...

    @property
    def platform(self) -> Platform: ...

    def get_file_tree(self, repo_id: str, branch: str | None = None) -> list[FileTreeItem]:
        # Returns FileTreeItem(path=p, is_directory=False, size=100) for each file_names entry

    def get_file_content(self, repo_id: str, file_path: str, branch: str | None = None) -> str | None:
        # Returns manifest content if path matches, else None

    def extract_manifests(self, repo_id: str, branch: str | None = None) -> list[ManifestFileData]:
        # Returns ManifestFileData objects from scenario["manifests"]

    def get_languages(self, repo_id: str) -> list[LanguageData]:
        # Returns LanguageData objects from scenario["language_data"]

    # All other abstract methods return [] or raise NotImplementedError with a clear message

    def get_organizations(self): return []
    def get_projects(self, org): return []
    def get_repositories(self, org, project=None): return []
    def get_repository(self, repo_id): raise NotImplementedError(...)
    def get_branches(self, repo_id): return []
    def get_commits(self, repo_id, **kwargs): return []
    def get_pull_requests(self, repo_id, **kwargs): return []
    def get_readme_files(self, repo_id, branch=None): return []
    def get_repository_metadata(self, repo_id, branch=None): return None
```

### C. Extend `tests/fixtures/sample_data.py` — 2 new factory functions

```python
def sample_technology_detection(
    programming_languages: list[str] = None,
    frameworks: list[str] = None,
    databases: list[str] = None,
    deployment_platforms: list[str] = None,
    build_tools: list[str] = None,
    testing_frameworks: list[str] = None,
    ci_cd_platforms: list[str] = None,
    primary_language: str | None = "Python",
    overall_confidence: float = 0.75,
) -> TechnologyDetection:
    """Factory for TechnologyDetection with sensible defaults."""
    ...

def sample_file_tree(scenario_name: str) -> list[FileTreeItem]:
    """Load a named scenario and return its file tree as FileTreeItem objects."""
    ...
```

### D. `scripts/capture_snapshot.py` — one-time capture utility

```
Usage: python scripts/capture_snapshot.py <repo_id> \
           --platform github|azure \
           --output tests/fixtures/scenarios/<name>.json

Options:
  --platform   Platform to connect to (reads env vars for credentials)
  --output     Path to write the scenario JSON file
  --branch     Branch to scan (default: default branch)
```

- Calls real extractor's `get_file_tree()`, `extract_manifests()`, `get_languages()`
- Serialises to the shared JSON schema
- Writes output file; user reviews and commits

### E. `scripts/verify_canary.py` — post-scan verification

```
Usage: python scripts/verify_canary.py --repo-id <repo_id>

Runs the canary inner join query:
  SELECT r.id
  FROM repositories r
  INNER JOIN commits c       ON r.id = c.repository_id
  INNER JOIN pull_requests p ON r.id = p.repository_id
  INNER JOIN dependencies d  ON r.id = d.repository_id
  INNER JOIN languages l     ON r.id = l.repository_id
  WHERE r.name = '<repo_id>'

Output:
  [PASS] commits      — 142 rows
  [PASS] pull_requests — 37 rows
  [PASS] dependencies  — 89 rows
  [PASS] languages     — 3 rows
  [PASS] canary join   — row present
  Overall: PASS
```

- Reads `DATABASE_URL` from environment (same as app)
- Exits 0 on PASS, 1 on FAIL
- Not wired into CI; run manually after a full scan

---

## Files Changed

| File                                                  | Action                       |
| ----------------------------------------------------- | ---------------------------- |
| `tests/fixtures/scenarios/python-docker.json`         | New                          |
| `tests/fixtures/scenarios/react-spa.json`             | New                          |
| `tests/fixtures/scenarios/java-maven-jenkins.json`    | New                          |
| `tests/fixtures/scenarios/fullstack-monorepo.json`    | New                          |
| `tests/fixtures/scenarios/dotnet-legacy.json`         | New                          |
| `tests/fixtures/scenarios/dual-ci.json`               | New                          |
| `tests/fixtures/scenarios/python-dual-deps.json`      | New                          |
| `tests/fixtures/scenarios/go-microservice.json`       | New                          |
| `tests/fixtures/scenarios/empty-stub.json`            | New                          |
| `tests/fixtures/scenarios/deep-nested-manifests.json` | New                          |
| `tests/fixtures/fixture_extractor.py`                 | New                          |
| `tests/fixtures/sample_data.py`                       | Extend (2 factory functions) |
| `scripts/capture_snapshot.py`                         | New                          |
| `scripts/verify_canary.py`                            | New                          |

---

## Not in Scope

- Plan 011 (technology detection persistence to DB) — depends on this but is separate work
- Plan 012 (package normalisation) — separate work
- CI integration of `verify_canary.py` — manual-only for now
- Grafana dashboard SQL fixture testing — deferred
- Randomised / generative fixture data — deferred (named scenarios cover immediate needs)

---

## Verification

1. `pytest tests/unit/ -v` — all existing tests pass (no regressions)
2. New test using `FixtureExtractor("python-docker")`:
   - `detector.detect(extractor.get_file_names())` → `primary_language == "Python"`, `"Docker" in deployment_platforms`
3. New test using `FixtureExtractor("empty-stub")`:
   - `detector.detect(...)` → `programming_languages == []`, no errors raised
4. New test using `FixtureExtractor("fullstack-monorepo")`:
   - `extract_manifests()` → 2 manifests returned (`requirements.txt` + `package.json`)
5. `python scripts/verify_canary.py --help` — CLI loads without error
6. Pre-commit checks pass on all new files

---

## Completion Summary

### ✅ Delivered

**Generation Infrastructure**:

- Complete Ollama-based code generation pattern
- 5 detailed prompts for all deliverables
- Orchestration script with validation
- Enhanced code extraction algorithm
- Comprehensive pattern documentation

**Test Infrastructure**:

- 10 diverse test scenario JSON files with realistic structures
- FixtureExtractor class supporting all extractor operations
- Factory functions for test data creation
- Support for branches, commits, and pull requests in scenarios
- Clear separation: `generated/` for AI-generated, parent for manual scenarios

**Utilities**:

- Post-scan verification script for canary repository validation
- Live repository snapshot capture tool
- Both integrated with existing extractor factory

**Documentation**:

- 5 README files updated with comprehensive guides
- Quick start examples for new developers
- Navigation paths from discovery to implementation
- Pattern reference for reuse in other projects

### ��� Regeneration

Files can be regenerated anytime with improvements or model updates:

```bash
# Regenerate all files
bash scripts/run-013-ollama.sh

# Regenerate specific step
bash scripts/run-013-ollama.sh --step B

# Try different model
bash scripts/run-013-ollama.sh --model codellama:13b
```

Generated files are deterministic but can be customized by editing prompts in `.ai/ollama-prompts/013-*.md`.

### ��� Usage in Tests

```python
from tests.fixtures.fixture_extractor import FixtureExtractor
from src.analyzers.technology_detector import TechnologyDetector

# Load scenario
extractor = FixtureExtractor("python-docker")

# Use in detection
detector = TechnologyDetector()
result = detector.detect(
    file_tree=extractor.get_file_tree("test-repo"),
    language_data=extractor.get_languages("test-repo")
)

# Verify results
assert result.primary_language == "Python"
assert "Docker" in result.deployment_platforms
```

### ��� Related Plans

- **Plan 011** (Technology Detection Persistence) - Uses scenarios for integration tests
- **Plan 012** (Package Normalization) - May use scenarios for manifest testing
- **Future**: Grafana dashboard SQL fixture testing

**Status**: Ready for use. Plan complete. ✅
