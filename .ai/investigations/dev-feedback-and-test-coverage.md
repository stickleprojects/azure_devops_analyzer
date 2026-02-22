# Investigation: Development Feedback Loop & Realistic Test Coverage

**Status**: Complete — all answers filled in; solution design in `.ai/plans/013-fixture-factory-plan.md`
**Created**: 2026-02-21
**Related plans**: `.ai/plans/011-technology-detection-persistence-plan.md`

---

## The Two Problems

### Problem 1 — Development Feedback Loop Friction

After making a code change, the current verification process is:

1. Trigger a scan (full or single-repo)
2. Wait for the scan to finish
3. Query the database manually with SQL to check rows/values
4. Open Grafana to check if panels display correctly

This is slow, manual, and non-reproducible. There is no automated path from "code change" to "confidence it worked."

### Problem 2 — Realistic Test Coverage Gap

New features are often triggered by patterns observed in real-world repositories (unusual directory structures, specific file combinations, monorepo layouts, legacy dependency formats). The test repositories don't contain these patterns, and there is no structured way to:

- Capture a real-world pattern as a reproducible test scenario
- Replay it in CI without a live platform connection

---

## How to Use This Document

Work through each theme below. Write your answers in the answer-capture boxes. The synthesis table at the end maps your answers to solution decision points.

**Rule**: Do not look at solution options until the synthesis table is at least half filled in. The questions are designed to surface what you actually need, not what sounds appealing.

---

## Problem 1: Development Feedback Loop

### Theme A — Iteration Cost

_Goal: Understand where time is actually lost._

**Questions:**

1. How long does a full scan take end-to-end (wall clock, typical case)?
2. How long does a single-repository scan take?
3. Which scan phase takes the longest — extraction, dependency parsing, enrichment (OSV/EOL API calls), or metrics computation?
4. After triggering a scan, how many minutes pass before you can check a result?
5. When you check the database, how long do you spend writing/running SQL?
6. When you check Grafana, how long does that step take?
7. What proportion of the total time is "waiting for scan" vs "doing the verification"?

**Answers:**

> _Iteration cost_: 30 min full scan (needed frequently during development for regression detection). Scan is primarily API-bound reading from GitHub/Azure (already optimized, some metrics disabled).
>
> _Bottleneck phase_: Platform API reads (extraction layer). This is the dominant cost and is non-negotiable.
>
> _Time split (wait vs. verify)_: ~30 min waiting for scan, ~few minutes active verification. The scan dominates. Verification is 100% active manual checking (not waiting on tools).

---

### Theme B — What "Correct" Looks Like

_Goal: Determine whether the expected outcome can be expressed as assertions._

**Questions:**

1. When you check the database after a scan, exactly what are you looking for?
   - Specific table? Which one?
   - Specific columns? Which values?
   - Row count? A particular range?
   - The presence of a row that didn't exist before?
2. Is the check always the same, or does it vary with each feature you're testing?
3. Could you write the check down before running the scan (i.e., "I expect `repository_stack` to have a row with `category='framework'` and `name='Django'` for repo X")?
4. When you check Grafana: are you checking that data appears at all, or that it looks visually correct (colours, layout)?
5. Has the Grafana check ever revealed something the SQL check missed?
6. Is there a "minimum viable check" — the one SQL query that, if it returns the right result, gives you 90% confidence?

**Answers:**

> _What I look for in the DB_: All core tables are populated with data for the scanned repositories. Specifically: commits, pull requests, languages, dependencies, and repository.json metadata.
>
> _Is the check consistent or ad-hoc?_: Consistent. Identify a "canary" repository known to have 100% complete data coverage, then verify all datasets are present for that repo.
>
> _Can it be pre-stated as an assertion?_: Yes, exactly. Inner join query: `SELECT r.id FROM repositories r INNER JOIN commits c ON r.id = c.repository_id INNER JOIN pull_requests pr ON r.id = pr.repository_id INNER JOIN dependencies d ON r.id = d.repository_id INNER JOIN languages l ON r.id = l.repository_id WHERE r.id = <canary_repo_id>`. If result exists, the pipeline works.
>
> _What the Grafana check adds_: All dashboard panels display data (confirms data visualization layer works).
>
> _Minimum viable SQL check_: The canary repo inner join query above. If it returns a row, 90% confidence the pipeline worked correctly.

---

### Theme C — Data Injection vs. Scan Execution

_Goal: Identify whether the scan itself is necessary for verification, or just the data it produces._

**Questions:**

1. Is the thing you're verifying produced by the **extractor** (platform API call), the **analyzer** (Python logic), the **storage layer** (database write), or the **Grafana query** (SQL)?
2. If you could inject rows directly into the database (bypassing the scan), would that be enough to verify most of what you care about?
3. Are there checks that genuinely require a real scan to be meaningful (e.g., because they depend on live data from an actual repo)?
4. Does the Grafana dashboard SQL query itself need testing, separate from whether the data was correctly populated?
5. Could a script that runs the Grafana panel SQL queries against known fixture data give you confidence in the dashboards?

**Answers:**

> _What layer produces the thing I'm verifying?_: The entire pipeline end-to-end: extractor (platform APIs) → analyzer (Python logic) → storage (database writes).
>
> _Would direct DB injection be sufficient for most checks?_: No. Because the requirement is to verify the pipeline works correctly, not just that the data exists. Need to test that the extraction, analysis, and storage all function together properly.
>
> _What genuinely requires a real scan?_: The full flow. There's no way to validate that "scanning works to identify source information AND populate it correctly in the DB" without running a real scan against real repositories.
>
> _Does Grafana SQL itself need testing?_: Yes, implicitly — need to verify that panels display data correctly, which requires both correct data in the DB and correct dashboard SQL queries.

---

### Theme D — Automation Boundary

_Goal: Decide the minimum acceptable level of automation._

**Questions:**

1. What is the minimum automation you would find genuinely useful?
   - A Python script that asserts specific DB rows after a scan?
   - A set of SQL scripts that can be run manually to verify a state?
   - A pytest test that runs the full workflow with a mock extractor and asserts the DB result?
   - A CI check that runs on every PR?
2. Would "semi-automated" be acceptable — e.g., a single command you run after a scan that prints PASS/FAIL for each check?
3. Is there a natural checkpoint in the current workflow (e.g., after a single-repo scan) where an assertion could be inserted?
4. Would you want the assertion to run as part of the scan itself, or as a separate post-scan verification step?

**Answers:**

> _Minimum useful automation_: **Option C** — Python API for dynamic fixture generation + JSON files for storage and replay. This enables: (1) Unit tests with mocked realistic data (< 1 sec), and (2) Post-scan automatic verification using the canary repo query. Additionally, the ability to generate test mock data on-demand (e.g., "create a mock repo with 200 commits, React + C# dependencies, and a repository.json with random team/service names") would accelerate test development and capture real-world scenarios.
>
> _Semi-automated acceptable?_: Not explicitly stated, but the preference for Option C indicates full automation is desired (not just semi-automated).
>
> _Natural insertion point_: After a scan completes, automatically run the canary repo verification query and report PASS/FAIL for each dataset (commits, PRs, deps, langs).

---

## Problem 2: Realistic Test Coverage Gap

### Theme A — Inventory of Real-World Patterns

_Goal: Name the patterns that triggered features but couldn't be tested._

**Questions:**

1. List the real-world repository structures or patterns that have prompted new feature ideas in the last month.
   - Example: "A repo with a `Pipfile` and a `requirements.txt` at the same time"
   - Example: "A monorepo where each subdirectory has its own `package.json`"
   - Example: "A repo that uses GitHub Actions AND a separate Jenkins config"
2. For each pattern: was it observable from the file tree alone, or did it require reading file contents?
3. For each pattern: could it be reproduced by controlling which files exist in a test repo (without specific content), or does file content matter too?
4. Which of these patterns are "rare but important" (edge cases that break assumptions) vs. "common baseline" (things most repos have)?

**Answers:**

> _Patterns encountered (list)_: Derived from TechnologyDetector detection rules and common real-world repository structures.
>
> **Common baseline** (detector handles these well — good regression anchors):
>
> 1. **Python service** — `requirements.txt` + `Dockerfile` + `.github/workflows/ci.yml`. Single language, clear stack.
> 2. **React SPA** — `package.json` + `tsconfig.json` + `.github/workflows/`. Pure frontend, no backend manifest.
> 3. **Java Maven + Jenkins** — `pom.xml` + `Jenkinsfile`. No containerisation, traditional CI.
>
> **Rare-but-important** (edge cases that expose detection assumptions):
>
> 4. **Full-stack monorepo** — Python backend at root (`requirements.txt`) + React frontend in `frontend/` (`frontend/package.json`). Both package managers present simultaneously. Tests multi-language co-detection.
> 5. **Legacy .NET migration** — `.csproj` + `packages.config` both present alongside `azure-pipelines.yml`. Tests that both old and new .NET dependency signals are captured.
> 6. **Dual CI migration** — both `Jenkinsfile` AND `.github/workflows/ci.yml` in same repo. Tests that both CI platforms are reported (not just the first match).
> 7. **Python dependency ambiguity** — both `Pipfile` AND `requirements.txt` at root. Tests behaviour when multiple Python package manager signals conflict.
> 8. **Go microservice** — only `go.mod` + `Dockerfile`. No CI config, no test framework config, sparse file tree. Tests minimal-signal detection.
> 9. **Empty/stub repo** — only `README.md`. No code or config files. Should return an empty (or near-empty) `TechnologyDetection` without errors.
> 10. **Deeply-nested manifests** — no manifests at root; all under `services/api/requirements.txt` and `services/web/package.json`. Tests whether manifest discovery and language detection traverse subdirectories correctly.
>
> _File tree alone vs. content required_:
> - Patterns 1–9: **File tree alone** is sufficient to exercise technology detection (`TechnologyDetector.detect()` only uses path strings).
> - Pattern 10: File tree alone sufficient for detection; file content only needed for manifest parsing / dependency extraction tests.
> - File content (manifest strings) is only needed when testing dependency parsing specifically.
>
> _Rare-but-important vs. common-baseline_:
> - Patterns 1–3: Common baseline — every realistic scenario library should include these.
> - Patterns 4–10: Rare-but-important — each exposes a specific assumption in the detector or manifest discovery logic.

---

### Theme B — Current Test Data Strategy

_Goal: Understand what already exists and what the actual gap is._

**Questions:**

1. In the current tests, how is the extractor mocked?
   - Does the mock return hardcoded data structures?
   - Does it read from fixture files?
   - Is it a hand-written fake class?
2. What data does `TechnologyDetector.detect()` require as input? (file names? file tree? language list?)
3. If you gave `TechnologyDetector` a list of file paths like `["src/main.py", "Jenkinsfile", "docker-compose.yml"]`, would that be a meaningful test input?
4. For dependency parsing: are manifest files (e.g., `requirements.txt`, `package.json` content) used as test fixtures anywhere?
5. What's the most realistic test fixture that currently exists in `tests/fixtures/`?

**Answers:**

> _How extractor is currently mocked_: Primary pattern is `mocker.patch.object(extractor, "get_file_tree", return_value=[...])` and `mocker.patch.object(extractor, "get_file_content", side_effect=fn)` (pytest-mock). Secondary patterns: direct attribute injection (`ext._git_client = Mock()`) and `@patch` decorator. No fake extractor class exists. No JSON fixture files exist for extractor output. Manifest content is inline string literals in test functions.
>
> _TechnologyDetector inputs needed_: `file_names: List[str]` — just the path strings from `FileTreeItem.path` (required). `language_data: List[Dict]` — `[{"language": "Python"}]` from repository_stack (optional). The `file_tree` parameter exists but is not used by the current detector logic at all.
>
> _File path list sufficient for detector?_: Yes. The detector does not read file contents — it only pattern-matches against path strings and file extensions. A list like `["requirements.txt", "Dockerfile", ".github/workflows/ci.yml"]` is a complete, meaningful test input.
>
> _Manifest files used as fixtures?_: Yes — as inline strings in test functions (e.g., `"flask==2.0.1\nrequests>=2.28.0"`). No separate fixture files exist. File tree is mocked using `FileTreeItem` objects, not real files on disk.
>
> _Most realistic existing fixture_: `tests/fixtures/sample_data.py` — 8 factory functions for `RepositoryData`, `CommitData`, `PullRequestData`, `BranchData`, `DependencyData`, `ReadmeData`, `OrganizationData`. No `TechnologyDetection` factory. No composite "full repo" scenario builder. No file-tree scenario fixtures.

---

### Theme C — Capture and Replay

_Goal: Evaluate whether real-world data can be captured as fixtures._

**Questions:**

1. When you encounter a real-world repository pattern that triggers a feature idea, do you have a way to save what you saw (file tree, manifest contents, language breakdown)?
2. Would a utility that captures a real repo's extractor output to a JSON file (a "snapshot") be useful? You'd run it once against a real repo, commit the snapshot, and reuse it in tests forever.
3. Is the blocker for real-world test scenarios about **what files exist** (file tree / names) or **what files contain** (file content)?
4. For the patterns you listed in Theme A: could each one be represented as a JSON snapshot of extractor output? Or would some require more structure?
5. Would you want snapshots to be tied to named scenarios? (e.g., `fixtures/scenarios/dotnet-monorepo.json`, `fixtures/scenarios/python-legacy-deps.json`)

**Answers:**

> _Currently save anything when encountering new patterns?_: No structured capture process currently exists.
>
> _Snapshot utility useful?_: Yes, very. Would enable: (1) reuse of discovered patterns across multiple tests, (2) version control of test scenarios, (3) reproducible CI runs.
>
> _Blocker: file names vs. file contents?_: [To be determined when real patterns are collected]
>
> _Could patterns be captured as JSON snapshots?_: Likely yes for most patterns. The fixture factory (Option C approach) will determine the exact JSON schema needed.

---

### Theme D — Test Repo vs. Fixture Boundary

_Goal: Decide whether live repositories are needed, or whether fixtures can replace them._

**Questions:**

1. Is the reason test repos don't have these patterns because:
   (a) You'd need to push real files to a real Azure DevOps / GitHub repo?
   (b) The test repos exist but you can't easily change their contents?
   (c) Something else?
2. The extractor interface is well-defined (`get_file_tree()`, `extract_manifests()`, etc.). Could a "fixture extractor" — a fake implementation that reads from local JSON — replace the need for a live test repo?
3. Would a local Git server (e.g., Gitea running in Docker alongside the test suite) solve the problem in a way that fixtures can't? What would that enable that fixtures wouldn't?
4. Is there a risk that fixture-based tests would fail to catch bugs that only appear with a real API (e.g., pagination, encoding, auth edge cases)?
5. Could real-platform tests and fixture-based tests coexist — fixtures for logic correctness, live API for integration smoke tests?

**Answers:**

> _Why test repos lack these patterns_: [To be investigated when gathering real patterns]
>
> _Fixture extractor viable?_: Likely yes — the extractor interface is well-defined (get_file_tree, extract_manifests, etc.), so a fake implementation reading from JSON should work for most logic testing.
>
> _What a live Git server would add over fixtures_: [To be evaluated after fixture factory is designed]
>
> _Risk of fixture-only approach_: Possible but manageable — real scan tests (Option A: post-scan verification) mitigate the risk that fixtures miss edge cases with real APIs (pagination, encoding, auth, etc.).
>
> _Coexistence model acceptable?_: Yes. Fixture-based tests for logic correctness + fast iteration. Real scan verification for end-to-end pipeline validation. Both together give full confidence.

---

## Connection Between Problems

These two problems are related: both stem from the same gap.

```
Real repo (unknown structure)
        ↓
   Extractor (live API call)
        ↓
   Analyzer (Python logic)
        ↓
   Storage (DB write)
        ↓
   Grafana (SQL query)
        ↓
  Manual human check ← this is where both problems live
```

If we can define what a "repository with specific characteristics" looks like as a **fixture**, we can:

- Use that fixture to drive automated assertions (solving Problem 1)
- Reuse that fixture to test new detectors and parsers (solving Problem 2)

This means the investigation questions can — and should — be answered together. A fixture strategy that solves Problem 2 is likely the same foundation that unlocks automated verification for Problem 1.

---

## Synthesis Table

Fill this in once you have answered the theme questions above. Each row asks: given what you learned, what does the solution need to do?

| Question group                     | Answer summary                                                                               | Solution implication                                                                                                                                    |
| ---------------------------------- | -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| P1-A: Iteration cost               | 30 min scans (API-bound) + few min manual verification                                       | Cannot optimize scan time; must automate verification. Automation ROI is high (saves minutes per iteration).                                            |
| P1-B: What "correct" looks like    | Canary repo inner join query: all datasets (commits, PRs, deps, langs) present and connected | Verification is deterministic and expressible as a SQL assertion. Easy to automate.                                                                     |
| P1-C: Data injection feasibility   | No—need real scan to validate full pipeline end-to-end                                       | Direct DB injection insufficient. Real scan + automated verification is the path forward.                                                               |
| P1-D: Automation boundary          | Option C: Python fixture API + JSON fixtures for both unit tests and post-scan verification  | Solution must provide: (1) Fixture factory for on-demand mock repo generation, (2) Post-scan verification script, (3) JSON storage for reproducibility. |
| P2-A: Real-world pattern inventory | 10 patterns identified: 3 common baseline (Python service, React SPA, Java Maven) + 7 edge cases (full-stack monorepo, legacy .NET, dual CI, Python ambiguity, Go sparse, empty repo, deep-nested manifests). File tree alone drives detection for all 10. | Fixture library needs ≥1 JSON scenario per pattern. Factory must support nested file paths (e.g., `frontend/package.json`). Edge cases validate detector assumptions. |
| P2-B: Current mock strategy        | `mocker.patch.object` is dominant. No fixture extractor class exists. No JSON fixture files for extractor output. `sample_data.py` has 8 factory functions but no `TechnologyDetection` factory and no composite scenario builder. Manifest content is inline strings. | Fixture factory fills a real gap. Extend `sample_data.py` with `TechnologyDetection` factory. Add `FixtureExtractor` class reading from JSON scenarios. No redesign of existing mocks needed — they coexist. |
| P2-C: Capture/replay feasibility   | Snapshot utility + JSON format viable. No structured capture process currently exists.       | Solution should include a utility to capture extractor output as JSON from real repos, commit as fixtures.                                              |
| P2-D: Fixture vs. live repo        | Fixture + real scan coexistence model preferred. Fixture extractor likely viable.            | Fixtures for fast iteration and edge-case testing; real scans for end-to-end validation. Reduces test repo dependencies.                                |

**Decision checklist** (answer after synthesis table is filled):

- [x] **Is a fixture library the right foundation?** Yes. `TechnologyDetector.detect()` only needs a `List[str]` of file paths — no live API, no file content. Fixtures can drive it completely. A `FixtureExtractor` reading from JSON is a natural fit for the well-defined `RepositoryExtractor` interface.
- [x] **Does the feedback loop problem require new infrastructure?** Yes. The canary verification script does not exist. The post-scan PASS/FAIL check is new work. The fixture factory is also net-new, though it builds on `sample_data.py`'s existing pattern.
- [x] **Are there patterns that genuinely require live platform access?** Yes, one category: extractor-layer edge cases (pagination, auth token handling, encoding of exotic file names). These cannot be covered by fixtures. Mitigated by keeping real-scan integration tests alongside fixture-based unit tests.
- [x] **Smallest meaningful improvement?** Two targeted additions: (1) `sample_technology_detection()` factory in `sample_data.py` so TechnologyDetector tests don't build output by hand, and (2) a `python-docker.json` scenario file + `FixtureExtractor` so the first fixture-driven test can be written immediately.
- [x] **Solve together or separately?** Together. The same JSON scenario files serve as both unit-test inputs (for detector/manifest logic) and canary repo templates (for post-scan verification). A shared fixture strategy is the unifying solution.

---

## Next Step

Once this document is filled in: schedule a solution design session using the synthesis table as the starting point. Create a plan in `.ai/plans/` that proposes concrete changes with the decisions above as constraints.
