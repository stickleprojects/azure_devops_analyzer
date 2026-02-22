# Plan 013: Fixture Factory & Post-Scan Verification

**Status**: Planned
**Source**: `.ai/investigations/dev-feedback-and-test-coverage.md` (complete)
**Addresses**: Problem 1 (dev feedback loop) + Problem 2 (realistic test coverage gap)

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
  "language_data": [
    {"language": "Python"}
  ],
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

| File | Pattern | Key signals |
|------|---------|-------------|
| `python-docker.json` | Python service + Docker + GH Actions | `requirements.txt`, `Dockerfile`, `.github/workflows/ci.yml` |
| `react-spa.json` | React SPA, TypeScript, GitHub Actions | `package.json`, `tsconfig.json`, `.github/workflows/` |
| `java-maven-jenkins.json` | Java, Maven, Jenkins | `pom.xml`, `Jenkinsfile` |
| `fullstack-monorepo.json` | Python backend + React frontend | `requirements.txt`, `frontend/package.json` |
| `dotnet-legacy.json` | .NET migration with old + new deps | `MyApp.csproj`, `packages.config`, `azure-pipelines.yml` |
| `dual-ci.json` | Jenkins + GitHub Actions both present | `Jenkinsfile`, `.github/workflows/ci.yml` |
| `python-dual-deps.json` | Pipfile + requirements.txt coexist | `Pipfile`, `Pipfile.lock`, `requirements.txt` |
| `go-microservice.json` | Go, Docker only; sparse tree | `go.mod`, `go.sum`, `Dockerfile` |
| `empty-stub.json` | No code; README only | `README.md` |
| `deep-nested-manifests.json` | Manifests only in subdirs | `services/api/requirements.txt`, `services/web/package.json` |

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

| File | Action |
|------|--------|
| `tests/fixtures/scenarios/python-docker.json` | New |
| `tests/fixtures/scenarios/react-spa.json` | New |
| `tests/fixtures/scenarios/java-maven-jenkins.json` | New |
| `tests/fixtures/scenarios/fullstack-monorepo.json` | New |
| `tests/fixtures/scenarios/dotnet-legacy.json` | New |
| `tests/fixtures/scenarios/dual-ci.json` | New |
| `tests/fixtures/scenarios/python-dual-deps.json` | New |
| `tests/fixtures/scenarios/go-microservice.json` | New |
| `tests/fixtures/scenarios/empty-stub.json` | New |
| `tests/fixtures/scenarios/deep-nested-manifests.json` | New |
| `tests/fixtures/fixture_extractor.py` | New |
| `tests/fixtures/sample_data.py` | Extend (2 factory functions) |
| `scripts/capture_snapshot.py` | New |
| `scripts/verify_canary.py` | New |

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
