# Investigation: Development Feedback Loop & Realistic Test Coverage

**Status**: Open — answers to be filled in before solution design begins
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

> _Patterns encountered (list)_:
>
> 1. [To be filled in via AI analysis of real repositories and GitHub browsing]
> 2. [To be filled in via AI analysis of real repositories and GitHub browsing]
> 3. [To be filled in via AI analysis of real repositories and GitHub browsing]
>
> _File tree alone vs. content required_: [Pending pattern collection]
>
> _Rare-but-important vs. common-baseline_: [Pending pattern collection]

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

> _How extractor is currently mocked_: [To be investigated]
>
> _TechnologyDetector inputs needed_: [To be investigated]
>
> _File path list sufficient for detector?_: [To be investigated]
>
> _Manifest files used as fixtures?_: [To be investigated]
>
> _Most realistic existing fixture_: [To be investigated]

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
| P2-A: Real-world pattern inventory | [Pending AI analysis of real repositories and GitHub]                                        | Fixture factory design depends on these patterns. High priority to collect.                                                                             |
| P2-B: Current mock strategy        | [To be investigated]                                                                         | May inform whether existing mock infrastructure can be extended or needs redesign for fixture factory.                                                  |
| P2-C: Capture/replay feasibility   | Snapshot utility + JSON format viable. No structured capture process currently exists.       | Solution should include a utility to capture extractor output as JSON from real repos, commit as fixtures.                                              |
| P2-D: Fixture vs. live repo        | Fixture + real scan coexistence model preferred. Fixture extractor likely viable.            | Fixtures for fast iteration and edge-case testing; real scans for end-to-end validation. Reduces test repo dependencies.                                |

**Decision checklist** (answer after synthesis table is filled):

- [ ] Is a fixture library the right foundation, or is a different approach indicated?
- [ ] Does the feedback loop problem require new test infrastructure, or just better use of what exists?
- [ ] Are there any patterns that genuinely cannot be represented as fixtures and require live platform access?
- [ ] What is the smallest change that would meaningfully improve day-to-day development?
- [ ] Should both problems be solved together (shared fixture strategy) or separately?

---

## Next Step

Once this document is filled in: schedule a solution design session using the synthesis table as the starting point. Create a plan in `.ai/plans/` that proposes concrete changes with the decisions above as constraints.
