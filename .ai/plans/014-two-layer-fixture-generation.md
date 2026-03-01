# Plan 014: Two-Layer Fixture Generation

**Status**: 🔶 In progress — Layer 1 seeds complete; Layer 2 enrichment prompt fixed; 2/33 repos enriched
**Depends on**: Plan 013 (fixture factory infrastructure already in place)
**Problem**: Ollama context window overflow when scaling up commits/PRs per scenario
**Solution**: Split the single monolithic generation call into seeds + per-repo enrichment layers

---

## Problem Summary

`fixture-scenarios.md` (used in Plan 013 Step A) asks Ollama to generate a single Python file
that hardcodes ALL scenario data for all 10 repos in one response — including commits and PRs.
When the `commits` array is pushed beyond ~5 entries per repo, or `pull_requests` beyond ~3, the
combined prompt + output tokens exceed the model's context window and generation truncates.

Root cause: one call must produce ~300+ objects (10 repos × 20 commits + 10 repos × 10 PRs)
as hardcoded Python data. That is too large for a single context window.

---

## Solution: Two-Layer Generation + Python Orchestrator

### Layer 1 — Repository Seeds (one Ollama call)

Prompt: `.ai/ollama-prompts/fixture-repo-seeds.md`

Generates a Python script (`scripts/generated/generate-repo-seeds.py`) that writes one
`{name}.json` seed file per repository. Seeds contain only structural metadata:

- `name`, `description`, `file_names`, `language_data`, `manifests`, `branches`
- **No `commits` or `pull_requests`** — explicitly excluded to keep output compact

Same 10 repository identities as the current `fixture-scenarios.md` (stable names mean
downstream code — FixtureExtractor, sample_data.py — needs no changes).

### Layer 2 — Per-Repo Enrichment (one Ollama call per repo)

Prompt: `.ai/ollama-prompts/fixture-repo-enrichment.md`

Called once per seed file. The seed JSON is passed via `--context` so Ollama can see the
language mix, manifests, and branch names and generate a realistic, stack-appropriate response.

Each call generates a Python enrichment script (`scripts/generated/enrich-{name}.py`) with
this interface:

```python
# enrich-{name}.py — accepts seed file path as sys.argv[1]
import json, pathlib, sys
path = pathlib.Path(sys.argv[1])
data = json.loads(path.read_text())
data["commits"] = [...]        # 15–30 entries, language-appropriate commit messages
data["pull_requests"] = [...]  # 5–15 entries, mix of "merged" / "open" / "closed"
path.write_text(json.dumps(data, indent=2) + "\n")
print(f"[OK] Enriched {path.name}")
```

Target scale (much larger than before, now feasible because each call handles one repo):

- `commits`: 15–30 entries, ordered oldest→newest by `commit_date`
- `pull_requests`: 5–15 entries, dates aligned with commits

### Enrichment Script Robustness

Each enrichment script generated in Layer 2 must be **idempotent and fault-tolerant**:

**Idempotency**:

- If enrichment is run twice on the same seed file, the result is identical
- Before writing, backup the existing file (if any): `shutil.copy(path, path.with_suffix('.json.bak'))`
- Load the seed, merge `commits` and `pull_requests` only if not already present
- If `data` already has >0 commits, skip enrichment (assume already done)

**Error handling**:

- Before modifying: validate seed JSON schema (must have `name`, `file_names`, `language_data`)
- Generate commits/PRs; if any field is missing, use sensible defaults (e.g., `author_name` → `"Author"`)
- Write atomically: write to a temp file, then `rename()` (prevents partial writes on crash)
- On error: print to stderr, exit with code 1; orchestrator (`generate-fixtures.py`) will catch and report

**Partial failure recovery**:

- If enrichment step E fails mid-run (e.g., Step A2 for repo N fails but A2 for N-1 succeeded):
  - Repos 0..N-1 have complete enrichment (commits + PRs)
  - Repo N seed exists but lacks commits/PRs
  - User can re-run `bash scripts/generate-fixtures.sh --step A2` to retry just enrichment
  - Idempotency ensures repos 0..N-1 are not re-enriched (no duplication)

### Architecture

```
generate-fixtures.sh          (host — bash, thin launcher only)
  └── docker run python:3.12-slim python scripts/generate-fixtures.py [args]
        │  (everything below runs inside Docker)
        │
        ├── Step A1: ollama-generate.py --prompt fixture-repo-seeds.md
        │           python scripts/generated/generate-repo-seeds.py
        │           → writes 10 seed JSONs to tests/fixtures/scenarios/generated/
        │
        ├── Step A2: for each seed JSON:
        │     ├── ollama-generate.py --prompt fixture-repo-enrichment.md --context {seed}
        │     └── python scripts/generated/enrich-{name}.py {seed.json}
        │           → appends commits + PRs in place
        │
        ├── Step B:  ollama-generate.py --prompt fixture-extractor.md      (unchanged)
        ├── Step C:  ollama-generate.py --prompt fixture-factories.md       (unchanged)
        ├── Step D:  ollama-generate.py --prompt repo-snapshot.md           (unchanged)
        └── Step E:  ollama-generate.py --prompt canary-verification.md     (unchanged)
```

Key properties:

- **No Python on host** — bash launcher only runs `docker run`
- **No Docker-in-Docker** — orchestrator and all subprocesses share the same container
- **`ollama-generate.py` unchanged** — orchestrator calls it via `subprocess`
- **Final JSON schema unchanged** — downstream consumers need no modifications

---

## Sizing & Data Distribution

Per-repository target counts (for enrichment layer):

| Repo                  | Lang(s)     | Commits | PRs | Commit Message Style                         | PR Status Mix                    |
| --------------------- | ----------- | ------- | --- | -------------------------------------------- | -------------------------------- |
| python-docker         | Python      | 20      | 8   | Docker, pytest, Flask                        | 60% merged, 30% open, 10% closed |
| react-spa             | TypeScript  | 18      | 6   | React, component, async/await                | 70% merged, 20% open, 10% closed |
| java-maven-jenkins    | Java        | 25      | 10  | Spring, Maven plugin, Jenkins stages         | 65% merged, 25% open, 10% closed |
| fullstack-monorepo    | Python + TS | 22      | 9   | Backend API, frontend, monorepo              | 70% merged, 20% open, 10% closed |
| dotnet-legacy         | C#          | 20      | 8   | Nuget, legacy packages, csproj               | 60% merged, 30% open, 10% closed |
| dual-ci               | Python      | 15      | 5   | Jenkinsfile, GitHub Actions, CI/CD           | 80% merged, 20% open, 0% closed  |
| python-dual-deps      | Python      | 16      | 6   | Pipenv, requirements.txt, dependency upgrade | 75% merged, 25% open, 0% closed  |
| go-microservice       | Go          | 18      | 7   | Gin-gonic, go mod, HTTP handler              | 70% merged, 20% open, 10% closed |
| empty-stub            | —           | 0       | 0   | N/A                                          | N/A                              |
| deep-nested-manifests | Python + TS | 20      | 8   | Service, monorepo structure                  | 65% merged, 25% open, 10% closed |

**Commit dating strategy**:

- Oldest commit: ~90 days ago from today
- Newest commit: ~1 day ago
- Distribute evenly across this range using `timedelta` in enrichment script
- PR `created_at` must be before any commit it references
- PR `merged_at` must be after `created_at`
- PR `closed_at` only populated for closed PRs (if status == "closed")

---

## Deliverables

### 1. `.ai/ollama-prompts/fixture-repo-seeds.md`

Prompt for Layer 1. Specifies:

### 1. `.ai/ollama-prompts/fixture-repo-seeds.md`

### 2. `.ai/ollama-prompts/fixture-repo-enrichment.md`

Prompt for Layer 2. Structurally similar to `fixture-repo-seeds.md` but focused on enrichment logic.

**Context window guidance**:

**Commit generation rules**:

- Commit messages must be appropriate to the repository's language/stack:
  - **Python/Docker**: "Add Flask endpoint", "Fix pytest configuration", "Update requirements.txt"
  - **Java/Maven**: "Add Spring component", "Configure Maven plugin", "Update dependency version"
  - **Go**: "Implement Gin router", "Add HTTP handler", "Update go.mod"
  - **TypeScript/React**: "Add React component", "Update TypeScript config", "Refactor async/await"
  - **C#/.NET**: "Add Nuget dependency", "Update csproj", "Migrate from packages.config"
- Each commit should include realistic metadata:
  - `author_name`, `author_email`, `committer_name`, `committer_email`
  - `files_changed` (2–8 files per commit)
  - `lines_added` (10–100 per commit)
  - `lines_removed` (0–50 per commit, higher for refactors)

**Pull request generation rules**:

- Generate 5–15 PRs, status distribution per repo (see Sizing table)
- PR `created_at` must be ≤ the oldest commit date (PRs created before commits are merged)
- PR `merged_at` must be within the commit date range if status is "merged"
- PR `closed_at` only present if status is "closed"
- PR titles and descriptions should match commit themes
- Example: if commits mention Docker, PR titles should be like "Add Docker support", "Containerize application"

**Interface specification**:

- The generated script accepts: `python scripts/generated/enrich-{repo}.py <seed.json>`
- Must read seed JSON, add `commits` and `pull_requests` fields, write back to same path
- Must print `[OK] Enriched <filename>` on success
- Must exit with code 1 on any error (file not found, invalid JSON, missing schema fields)

**Output instruction**: "Write the complete, runnable Python source for `scripts/generated/enrich-{repo}.py`."

### 3. `scripts/generate-fixtures.py`

Python orchestrator. Runs inside Docker (`python:3.12-slim`). Stdlib only. Must handle Step A1/A2 plus inherit Steps B–E from Plan 013.

**Key features**:

- Arg parsing: `--model`, `--step`, `--ollama-url`
- Lazy Ollama verification (check once, reuse for all calls)
- Validation: py_compile + line count check per generated file
- Error recovery: on Step A2 enrichment failure, print failed repo name, continue others, final exit code 1 if any failed
- Progress reporting: print `[step X] <description>` before each step

**Core interface**:

```python
def run_ollama_generate(prompt_path, output_path, min_lines, context_files=()):
    """Call ollama-generate.py with context files. Raises on error."""

def validate_python_file(path, min_lines=20):
    """Check file exists, has ≥min_lines, compiles successfully. Raises ValueError on failure."""

def require_ollama(model, url):
    """Verify Ollama is running and model is available. Raises RuntimeError if not."""

def step_a(model, url, step_filter=None):
    """Layer 1 + 2: generate seeds, then enrich each seed.

    A1: ollama-generate.py --prompt fixture-repo-seeds.md → generate-repo-seeds.py
        python generate-repo-seeds.py → 10 seed JSONs

    A2: for each seed, ollama-generate.py --prompt fixture-repo-enrichment.md --context seed.json
        python enrich-{name}.py seed.json → enriched with commits/PRs

    Failures in A2 are tracked; all repos attempted; final error if any failed.
    """

def step_b(model, url): """Generate FixtureExtractor (from Plan 013, unchanged)."""
def step_c(model, url): """Generate factory functions (from Plan 013, unchanged)."""
def step_d(model, url): """Generate capture_snapshot.py (from Plan 013, unchanged)."""
def step_e(model, url): """Generate verify_canary.py (from Plan 013, unchanged)."""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen2.5-coder:14b")
    parser.add_argument("--ollama-url", default="http://host.docker.internal:11434")
    parser.add_argument("--step", choices=["A", "B", "C", "D", "E", "all"], default="all")
    args = parser.parse_args()

    try:
        require_ollama(args.model, args.ollama_url)

        steps = {"A": step_a, "B": step_b, "C": step_c, "D": step_d, "E": step_e}

        if args.step == "all":
            for name, func in [("A", step_a), ("B", step_b), ("C", step_c), ("D", step_d), ("E", step_e)]:
                print(f"\n==> Step {name}")
                func(args.model, args.ollama_url)
        else:
            print(f"\n==> Step {args.step}")
            steps[args.step](args.model, args.ollama_url)

        print("\n==> All steps completed successfully.")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
```

### 4. `scripts/generate-fixtures.sh`

Thin bash launcher. Host-side code only handles Docker invocation:

        ## Sizing & Data Distribution

if ! docker info &>/dev/null; then echo "ERROR: Docker not running"; exit 1; fi

MSYS_NO_PATHCONV=1 docker run --rm \
 -e PYTHONUNBUFFERED=1 \
 -v "$PROJECT_ROOT:/app" \
 -w /app \
 python:3.12-slim \

```


---
| ---------- | ----------------------------------------------- | ----------------------------------------------------------------------- |
| Create     | `.ai/ollama-prompts/fixture-repo-seeds.md`      | Layer 1 seed generation                                                 |
| Create     | `.ai/ollama-prompts/fixture-repo-enrichment.md` | Layer 2 per-repo enrichment                                             |
| **Delete** | `.ai/ollama-prompts/fixture-scenarios.md`       | Superseded by fixture-repo-seeds.md + fixture-repo-enrichment.md        |
| Unchanged  | `scripts/ollama-generate.py`                    | Used by both old and new systems                                        |
| Unchanged  | Steps B–E prompts                               | Reused from Plan 013 (fixture-extractor.md, fixture-factories.md, etc.) |
| Unchanged  | `tests/fixtures/fixture_extractor.py`           | Final JSON schema unchanged, extractor still works                      |
| Unchanged  | `tests/fixtures/sample_data.py`                 | Factory functions unchanged                                             |
### Rationale for Deleting Legacy Scripts

`scripts/generate-test-fixtures.sh` (old) called 5 generation steps sequentially:

- Step A: monolithic scenario generation (now split into A1 + A2)
- Steps B–E: fixture extractor, factories, snapshot, canary (reused as-is)


Old script is deleted when Plan 014 merges; updating documentation will guide developers.

    ### 2. `.ai/ollama-prompts/fixture-repo-enrichment.md`
### Step A (Seed + Enrichment Generation)

1. **Run seeds + enrichment**:


   Expected: Script runs without error, prints `[step A]`, shows progress for A1 (seed generation) then A2 (enrichment for each repo).
```

python3 -c "import json; d=json.load(open('tests/fixtures/scenarios/generated/python-docker.json')); print(f'commits: {len(d.get(\"commits\", []))}, PRs: {len(d.get(\"pull_requests\", []))}')"

# Expected output: commits: 18-22, PRs: 6-10 (from sizing table)

python3 -c "import json; d=json.load(open('tests/fixtures/scenarios/generated/go-microservice.json')); msgs=[c['message'] for c in d['commits']]; print('\n'.join(msgs[:3]))"

# Expected: Messages mention Go/Gin, not Java/Spring

```bash
python3 << 'EOF'
import json
from datetime import datetime
d = json.load(open('tests/fixtures/scenarios/generated/python-docker.json'))
for pr in d['pull_requests'][:2]:
    created = datetime.fromisoformat(pr['created_at'])
    merged = datetime.fromisoformat(pr.get('merged_at')) if pr.get('merged_at') else None
    closed = datetime.fromisoformat(pr.get('closed_at')) if pr.get('closed_at') else None
    if pr['status'] == 'merged' and merged:
        assert created < merged, f"PR {pr['pr_number']}: created after merged"
    print(f"PR {pr['pr_number']}: created={created.date()}, merged={merged.date() if merged else 'N/A'}")
EOF
# Expected: All PRs have valid date ordering
```

6. **Spot-check empty stub**:
   ```bash
   python3 -c "import json; d=json.load(open('tests/fixtures/scenarios/generated/empty-stub.json')); print(f'commits: {len(d.get(\"commits\", []))}, PRs: {len(d.get(\"pull_requests\", []))}')"
   # Expected output: commits: 0, PRs: 0
   ```

### Steps B–E (Extractor, Factories, Utilities)

7. **Run all steps**:

   ```bash
   bash scripts/generate-fixtures.sh
   ```

   Expected: Completes with all steps B–E passing.

8. **Verify files generated**:

   ```bash
   ls -lh tests/fixtures/fixture_extractor.py scripts/capture_snapshot.py scripts/verify_canary.py
   # Expected: All files exist, >0 bytes
   ```

9. **Syntax check**:
   ```bash
   python -m py_compile tests/fixtures/fixture_extractor.py scripts/capture_snapshot.py scripts/verify_canary.py
   # Expected: No output (all valid Python)
   ```

### Regression Tests

10. **Existing tests still pass**:

    ```bash
    bash scripts/run-tests-docker.sh
    # Expected: All tests pass (no regressions from new fixtures)
    ```

11. **FixtureExtractor works with new scenarios**:
    ```bash
    python3 << 'EOF'
    from tests.fixtures.fixture_extractor import FixtureExtractor
    e = FixtureExtractor("python-docker")
    files = e.get_file_tree("test-repo")
    commits = e.get_commits("test-repo")
    prs = e.get_pull_requests("test-repo")
    print(f"Files: {len(files)}, Commits: {len(commits)}, PRs: {len(prs)}")
    assert len(commits) >= 15, "Expected ≥15 commits"
    assert len(prs) >= 5, "Expected ≥5 PRs"
    print("[PASS] FixtureExtractor works correctly")
    EOF
    ```

### Integration Test

12. **End-to-end: load scenario, detect technology, verify**:

    ```bash
    python3 << 'EOF'
    from tests.fixtures.fixture_extractor import FixtureExtractor
    from src.analyzers.technology_detector import TechnologyDetector

    extractor = FixtureExtractor("fullstack-monorepo")
    detector = TechnologyDetector()
    result = detector.detect(
        file_tree=extractor.get_file_tree("repo"),
        language_data=extractor.get_languages("repo")
    )

    assert "Python" in result.programming_languages
    assert "TypeScript" in result.programming_languages
    print(f"[PASS] Fullstack repo detected: {result.programming_languages}")
    EOF
    ```
