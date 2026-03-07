# Plan 015: Wire Generated Fixtures into Integration Tests

## Status: COMPLETE

## Context

27 enriched JSON scenario fixtures live in `tests/fixtures/scenarios/generated/`. Their purpose is to simulate real repositories across diverse tech stacks (Go, Java, polyglot, legacy, etc.) that we can't access via live API. `FixtureExtractor` exists as a drop-in `RepositoryExtractor` backed by these files — but it has never been used in tests.

The goal: add **fixture-backed integration tests** that exercise the full extraction -> storage pipeline using `FixtureExtractor` as the data source, against the real test database, with no live API credentials required. Existing unit tests and live-API integration tests are untouched.

## Completion Notes (2026-03-06)

This plan is implemented.

- `tests/fixtures/fixture_extractor.py` was updated to support generated fixture schema:
  - `get_file_content()` supports flat manifest dicts with legacy list fallback
  - `get_commits()` accepts `sha` or `commit_hash`
  - `get_branches()` handles string branch lists and object branch entries
  - `get_languages()` handles string language lists and object-style language data
- `tests/contract/integration/test_fixture_scenarios.py` was added and exercises fixture-backed persistence for commits, pull requests, and languages across six scenarios.
- Additional file-content assertions were added in the same test module to explicitly verify manifest lookup behavior.
- Validation run: `bash scripts/run-tests-docker.sh` completed successfully (exit code 0).

## Blocker: Schema Mismatches in FixtureExtractor

`FixtureExtractor` was written expecting a different JSON shape than what the Ollama enrichment produced. Must be fixed before anything else.

| Method             | Extractor reads                                   | Generated JSON has                            |
| ------------------ | ------------------------------------------------- | --------------------------------------------- |
| `get_commits`      | `c["sha"]`                                        | `c["commit_hash"]`                            |
| `get_file_content` | list of `{file_path, content}` objects            | dict `{"filename": "content", ...}`           |
| `get_branches`     | list of `{name, latest_commit_sha}` objects       | list of strings `["main", "develop"]`         |
| `get_languages`    | `self._scenario["language_data"]` list of objects | `self._scenario["languages"]` list of strings |

## Implementation

### Step 1 — Fix FixtureExtractor (`tests/fixtures/fixture_extractor.py`)

**`get_file_content`** — manifests is a dict keyed by filename:

```python
def get_file_content(self, repo_id, file_path, branch=None) -> str | None:
    manifests = self._scenario.get("manifests", {})
    if isinstance(manifests, dict):
        return manifests.get(file_path)
    for m in manifests:  # legacy list fallback
        if m["file_path"] == file_path:
            return m["content"]
    return None
```

**`get_commits`** — field is `commit_hash`, not `sha`:

```python
sha=c.get("sha") or c.get("commit_hash"),
```

**`get_branches`** — branches are plain strings:

```python
def get_branches(self, repo_id) -> list[BranchData]:
    branches = self._scenario.get("branches", [])
    if branches and isinstance(branches[0], str):
        return [BranchData(name=b, latest_commit_sha="") for b in branches]
    return [BranchData(name=b["name"], latest_commit_sha=b["latest_commit_sha"]) for b in branches]
```

**`get_languages`** — languages is a list of strings, not dicts:

```python
def get_languages(self, repo_id) -> list[LanguageData]:
    lang_data = self._scenario.get("language_data") or self._scenario.get("languages", [])
    if lang_data and isinstance(lang_data[0], str):
        return [LanguageData(language=l, byte_count=0, percentage=None) for l in lang_data]
    return [LanguageData(language=d["language"], byte_count=d["byte_count"], percentage=d.get("percentage")) for d in lang_data]
```

### Step 2 — New Integration Test File (`tests/contract/integration/test_fixture_scenarios.py`)

**Pattern**: mirrors `test_github_extraction_e2e.py` — call storage functions directly, assert on DB state. Uses `test_session` and `organization` conftest fixtures already provided by `tests/contract/integration/conftest.py`.

**Key difference from live-API tests**: `FixtureExtractor.get_repository()` raises `NotImplementedError`, so the test creates the `Repository` row manually via `store_repository()` + `sample_repository_data()`.

**Scenarios** (diverse coverage, edge case included):

```python
SCENARIOS = [
    "go-microservice",       # Go, go.mod
    "java-maven-jenkins",    # Java, pom.xml, Jenkins CI
    "fullstack-monorepo",    # Python + TypeScript, dual manifests
    "dual-ci-analytics",     # Python, dual CI
    "deep-nested-manifests", # Nested manifest paths
    "empty-stub",            # Edge case: no commits, no manifests
]
```

**Test class structure** (3 parametrized tests × 6 scenarios = 18 test cases):

```python
class TestFixtureScenarioPipeline:

    @pytest.mark.parametrize("scenario_name", SCENARIOS)
    def test_commits_stored(self, scenario_name, test_session, organization): ...

    @pytest.mark.parametrize("scenario_name", SCENARIOS)
    def test_pull_requests_stored(self, scenario_name, test_session, organization): ...

    @pytest.mark.parametrize("scenario_name", SCENARIOS)
    def test_languages_stored(self, scenario_name, test_session, organization): ...
```

**Repo creation helper** (module-level function):

```python
def _create_fixture_repo(session, organization, scenario_name) -> Repository:
    project = store_project(session, organization, name="fixture-project", description="")
    repo_data = sample_repository_data(
        repo_id=f"fixture/{scenario_name}",
        name=scenario_name,
        url=f"https://example.com/{scenario_name}",
    )
    repo = store_repository(session, project, repo_data)
    session.commit()
    return repo
```

**Key imports**:

```python
from tests.fixtures.fixture_extractor import FixtureExtractor
from tests.fixtures.sample_data import sample_repository_data
from src.database.storage import store_project, store_repository, store_commit, store_pull_request, store_languages
from src.database.models.commit import Commit
from src.database.models.pull_request import PullRequest
from src.database.models.repository_language import RepositoryLanguage
```

### Step 3 — Verify

```bash
bash scripts/run-tests-docker.sh
```

Expected:

- All existing unit tests pass (untouched)
- All existing live-API tests pass (skip if no credentials, untouched)
- 18 new fixture-backed integration tests pass

## Files to Modify

| File                                                   | Change                  |
| ------------------------------------------------------ | ----------------------- |
| `tests/fixtures/fixture_extractor.py`                  | Fix 4 schema mismatches |
| `tests/contract/integration/test_fixture_scenarios.py` | New file                |
