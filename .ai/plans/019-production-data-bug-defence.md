# Plan 019: Production-Data-Shaped Bug Defence

_Last reviewed: 2026-04-30_

## Status: IMPLEMENTED

## Problem

The contributor↔pull-request linking bug (addressed narrowly by [Plan 018](018-contributor-pr-linking-regression-tests.md)) was one instance of a broader class: **bugs that only manifest against real production data**. The current test suite is well-structured (unit / contract / integration) but has two structural gaps that let the whole class through:

**Gap 1 — Fixtures are aspirational, not adversarial.** Scenarios in `tests/fixtures/scenarios/generated/` are produced by a seeded-PRNG generator pipeline (`scripts/generated/generate-repo-seeds.py` + `scripts/enrich-repo.py`) that reflects our mental model of the data. They inherit our blind spots. Happy-path is tested; the ugly edges — nulls, case variation, unicode, ghost users, force-pushed PRs, bot committers — are not represented.

**Gap 2 — No cross-cutting invariants.** Every test asserts "this specific thing in this specific scenario." Nothing asserts "after *any* extraction, these DB-level truths hold." Invariants like "no case-variant contributor twins" or "every FK resolves" would fire regardless of which scenario triggered the data, but they don't exist as a reusable post-condition.

**Gap 3 — Extraction idempotency is untested.** Re-running an extractor against the same repository is a routine production event (scheduled re-scans, retries, backfills). Nothing asserts re-extraction produces stable DB state; duplication or orphaning on re-run would only surface in production.

**Gap 4 — Real-API shape is never exercised in CI.** Live-API tests are gated behind credentials and excluded by `-m "not live_api"`. The class of bug triggered by real-API quirks (case variation, null fields, unexpected nesting) has no CI-safe coverage.

## Decision

Add four infrastructure layers that operate *across* scenarios rather than within a single one. Plan 018's tests then land naturally inside this framework — its Step 5 (invariant script) is superseded by Layer B; its adversarial test shapes belong in Layer A.

| Layer | Addresses gap | Artefact |
|---|---|---|
| A. Adversarial fixture corpus | 1 | `tests/fixtures/scenarios/adversarial/*.json` |
| B. DB-invariant framework | 2 | `tests/db_invariants.sql` + pytest fixture + `scripts/verify-extraction.sh` |
| C. Idempotency harness | 3 | `tests/contract/integration/test_idempotency.py` |
| D. Recorded real-API snapshots | 4 | `tests/fixtures/snapshots/*.json` + `SnapshotExtractor` |

Out of scope for this plan (noted as follow-ups):

- Property-based identity tests (Hypothesis).
- Nightly live-API smoke workflow and production observability hook.

## Architecture

```
                    ┌──────────────────────────────────────┐
                    │      Integration test execution      │
                    └──────────────────────────────────────┘
                                      │
      ┌───────────────────────────────┼───────────────────────────────┐
      ▼                               ▼                               ▼
┌───────────────┐         ┌────────────────────┐           ┌──────────────────┐
│ Happy-path    │         │ Adversarial        │           │ Real-API         │
│ scenarios     │   (A)   │ scenarios          │    (D)    │ snapshots        │
│ (generated/)  │         │ (adversarial/)     │           │ (snapshots/)     │
└───────────────┘         └────────────────────┘           └──────────────────┘
      │                               │                               │
      └───────────────┬───────────────┴───────────────┬───────────────┘
                      ▼                               ▼
              ┌──────────────────────┐    ┌──────────────────────┐
              │ Full pipeline:       │    │ (C) Idempotency:     │
              │ extractor → store    │    │ run pipeline twice   │
              │ → reporting views    │    │ assert stable        │
              └──────────────────────┘    └──────────────────────┘
                      │                               │
                      └───────────────┬───────────────┘
                                      ▼
                     ┌──────────────────────────────┐
                     │ (B) DB invariants            │
                     │ tests/db_invariants.sql      │
                     └──────────────────────────────┘
```

### Reuse

- `FixtureExtractor` at [tests/fixtures/fixture_extractor.py](../../tests/fixtures/fixture_extractor.py) — extend to accept an additional scenario root directory.
- `_load_scenario` / `_enrich_scenario` style helpers in [tests/contract/database/test_full_pipeline_e2e.py](../../tests/contract/database/test_full_pipeline_e2e.py) — reuse their shape for the idempotency harness.
- Storage layer [src/database/storage.py](../../src/database/storage.py) — no changes.
- Existing Docker runner [scripts/run-tests-docker.sh](../../scripts/run-tests-docker.sh) — append invariant-check tail.

## Implementation Steps

### Layer A — Adversarial fixture corpus

#### A.1 Create directory and initial scenario set

New directory: `tests/fixtures/scenarios/adversarial/`. Each file is a scenario modelling one specific pathology. Required initial set:

| Filename | Pathology |
|---|---|
| `mixed-case-emails.json` | One person with three email casings across a commit, a PR author, and a PR reviewer |
| `whitespace-emails.json` | Emails with leading/trailing whitespace and internal spaces |
| `ghost-author.json` | PR with `author_email: null`, `author_name: null` (deleted GitHub user) |
| `unicode-names.json` | `author_name` containing emoji, combining characters, RTL text; non-ASCII in commit messages |
| `force-pushed-pr.json` | PR with `commits: []` (history rewritten after review) |
| `bot-committer.json` | Author email matching `*[bot]@users.noreply.github.com` and Azure DevOps bot equivalent |
| `self-review.json` | PR where author email == reviewer email |
| `dismissed-review.json` | Review with `state: DISMISSED` after an earlier `APPROVED` on the same PR |
| `future-dated-commit.json` | Commit with `commit_date` 24 hours in the future (clock skew) |
| `same-second-commits.json` | Two commits with identical `commit_date` timestamps |

Each JSON follows the same schema as `generated/` scenarios — identical `FixtureExtractor` can read either.

#### A.2 Extend FixtureExtractor to resolve from adversarial path

In [tests/fixtures/fixture_extractor.py](../../tests/fixtures/fixture_extractor.py), change the scenario-lookup logic to search `generated/` then `adversarial/`. No breaking change to existing tests.

#### A.3 Add parametrised integration test class

Create `tests/contract/integration/test_adversarial_scenarios.py`:

```python
ADVERSARIAL_SCENARIOS = [
    "mixed-case-emails", "whitespace-emails", "ghost-author",
    "unicode-names", "force-pushed-pr", "bot-committer",
    "self-review", "dismissed-review",
    "future-dated-commit", "same-second-commits",
]

@pytest.mark.integration
@pytest.mark.parametrize("scenario", ADVERSARIAL_SCENARIOS)
class TestAdversarialScenarios:
    def test_pipeline_completes_without_error(self, scenario, db_session, organization):
        ...  # load, store, commit — must not raise
    def test_db_invariants_hold(self, scenario, db_session, organization, db_invariants_check):
        ...  # invariants fixture from Layer B runs automatically
```

One test per invariant-of-interest per scenario is not required — the DB-invariant fixture covers the cross-cutting assertions once.

### Layer B — DB-invariant framework

#### B.1 Define invariants in SQL

New file `tests/db_invariants.sql`. Each invariant is a named query that **must return zero rows** for the DB to be valid. Example structure:

```sql
-- invariant: no_case_variant_contributor_twins
SELECT lower(trim(email)) AS email_key, count(*)
FROM contributors
GROUP BY lower(trim(email))
HAVING count(*) > 1;

-- invariant: no_orphan_pr_author_fk
SELECT id, repo_id, pr_number, author_id
FROM pull_requests
WHERE author_id IS NULL OR author_id NOT IN (SELECT id FROM contributors);

-- invariant: no_orphan_pr_reviewer_fk
SELECT pr_id, reviewer_id
FROM pr_reviews
WHERE reviewer_id IS NULL OR reviewer_id NOT IN (SELECT id FROM contributors);

-- invariant: no_duplicate_pr_per_repo
SELECT repo_id, pr_number, count(*)
FROM pull_requests
GROUP BY repo_id, pr_number
HAVING count(*) > 1;

-- invariant: no_duplicate_commit_per_repo
SELECT repo_id, sha, count(*)
FROM commits
GROUP BY repo_id, sha
HAVING count(*) > 1;

-- invariant: no_review_before_pr_created
SELECT r.pr_id, r.review_date, pr.created_at
FROM pr_reviews r JOIN pull_requests pr ON r.pr_id = pr.id
WHERE r.review_date < pr.created_at;

-- invariant: no_orphan_repo_dependency
SELECT repo_id, package_id
FROM repository_dependencies
WHERE repo_id NOT IN (SELECT id FROM repositories);

-- invariant: no_vulnerability_without_package
SELECT id, package_id FROM vulnerabilities
WHERE package_id NOT IN (SELECT id FROM package_metadata);
```

Invariant names are parsed from `-- invariant: <name>` comments above each query. Adjust column/table names to the actual schema — Copilot agent: verify against [database/schema.sql](../../database/schema.sql) and recent migrations before wiring.

#### B.2 pytest fixture

In [tests/contract/integration/conftest.py](../../tests/contract/integration/conftest.py) (or a shared conftest):

```python
@pytest.fixture
def db_invariants_check(db_session):
    """Yields; on teardown, runs all invariants and asserts zero rows each."""
    yield
    invariants = _parse_invariants_sql("tests/db_invariants.sql")
    violations = []
    for name, sql in invariants.items():
        rows = db_session.execute(text(sql)).fetchall()
        if rows:
            violations.append((name, rows[:5]))  # cap sample for readability
    assert not violations, f"DB invariant violations: {violations}"
```

Attach as autouse fixture at the integration-test base class level so it runs automatically after every integration test commits data. Individual tests can depend on it explicitly (as shown in Layer A) for clarity.

#### B.3 Shell script for manual / CI-tail runs

Create [scripts/verify-extraction.sh](../../scripts/verify-extraction.sh). Uses `psql` inside the existing test-runner container. Iterates the invariants in `tests/db_invariants.sql`, prints pass/fail for each, exits non-zero on any violation with up to 5 offending rows per failure.

> Follow-up (2026-04-24, PR #66): the `python:3.12-slim` base had `libpq-dev` but no `psql` client, so this step initially failed with `psql: command not found`. Resolved by adding `postgresql-client` to [Dockerfile](../../Dockerfile) and bind-mounting `./scripts` in `docker-compose.test.yml` so script updates land without a rebuild.

Wire into tail of [scripts/run-tests-docker.sh](../../scripts/run-tests-docker.sh) **after** integration tests complete, before coverage output. This gives a single-command way to validate an extraction run against a real populated DB — not just test-data.

### Layer C — Idempotency harness

#### C.1 Create test file

New file [tests/contract/integration/test_idempotency.py](../../tests/contract/integration/test_idempotency.py):

```python
@pytest.mark.integration
@pytest.mark.parametrize("scenario", IDEMPOTENCY_SCENARIOS)
class TestExtractionIdempotency:
    def test_reextraction_produces_stable_state(
        self, scenario, db_session, organization, db_invariants_check
    ):
        extractor = FixtureExtractor(scenario)
        repo = _create_fixture_repo(db_session, organization, scenario)

        # Pass 1
        _run_full_pipeline(db_session, repo.repo_id, extractor)
        snapshot_1 = _capture_state(db_session, repo.repo_id)

        # Pass 2 — same data, same target repo
        _run_full_pipeline(db_session, repo.repo_id, extractor)
        snapshot_2 = _capture_state(db_session, repo.repo_id)

        assert snapshot_1 == snapshot_2, (
            f"Re-extraction changed DB state for {scenario}:\n"
            f"  before: {snapshot_1}\n"
            f"  after:  {snapshot_2}"
        )
```

#### C.2 State-capture helper

`_capture_state(session, repo_id)` returns a dict of:

- `row_counts`: `{table: count}` for `contributors`, `pull_requests`, `pr_reviews`, `commits`, `repository_dependencies`, `vulnerabilities`, scoped to `repo_id` where applicable.
- `id_hash`: stable hash of the ordered tuple of primary keys per table. Detects id churn even when counts are stable.

Idempotency scenarios are a subset of the existing `DEPENDENCY_SCENARIOS` — start with `python-docker-billing`, `go-microservice`, and one adversarial (`mixed-case-emails`). Expand later.

#### C.3 Wire DB invariants into idempotency

The `db_invariants_check` fixture from Layer B runs after both passes, catching any invariant that only breaks on re-run (e.g. duplicate insertions creating case-variant twins).

### Layer D — Recorded real-API snapshots

#### D.1 Capture script

Create `scripts/capture-api-snapshot.sh`. Run manually with creds. For each platform and each extractor endpoint of interest (PR list, PR reviews, commits, for one small real repo per platform), capture raw JSON to `tests/fixtures/snapshots/<platform>/<endpoint>.json`.

Immediately after capture, run `scripts/anonymise-snapshot.py` (new) that:

- Rewrites emails: `real@example.com` → deterministic `user{N}@fixture.local`, but **preserves case patterns and whitespace** (this is the point — production-shape quirks must survive anonymisation).
- Rewrites display names using a similar deterministic mapping; preserves unicode characters.
- Rewrites org / repo / branch names.
- Leaves null fields, nested structure, field ordering untouched.

Snapshots are committed. Document refresh cadence (quarterly or on API-version change) in a short `tests/fixtures/snapshots/README.md`.

#### D.2 SnapshotExtractor

New file `tests/fixtures/snapshot_extractor.py`. Implements the same `RepositoryExtractor` interface as `FixtureExtractor` but sources data from `snapshots/<platform>/*.json`. The transformation from raw API JSON to the extractor's domain objects (`PullRequestData`, etc.) **must go through the same extractor code paths** as production — otherwise the snapshot doesn't test the extractor, only the storage layer. Two options, pick whichever is lighter:

1. **HTTP-layer mock**: monkey-patch the extractor's HTTP client to return snapshot JSON per URL. Preferred — exercises the whole extractor.
2. **Client-layer shim**: substitute the extractor's API client with a shim that returns snapshot data. Lighter but skips HTTP-layer parsing.

Go with option 1 unless the HTTP client is hard to patch.

#### D.3 Snapshot shape test class

New `tests/contract/integration/test_snapshot_shape.py`:

```python
@pytest.mark.integration
class TestGitHubSnapshot:
    def test_pipeline_completes_on_real_shape(
        self, db_session, organization, db_invariants_check
    ):
        extractor = SnapshotExtractor("github")
        ...  # load, store, commit
        # DB invariants asserted by fixture
```

Parallel class for Azure DevOps.

## Compatibility Notes

- No production code changes.
- New dependencies: none strictly required. If the invariant fixture uses `SQLAlchemy.text` that's already available.
- Schema references in `tests/db_invariants.sql` must match real table/column names — verify against [database/schema.sql](../../database/schema.sql) before committing. If a named table doesn't exist yet (e.g. a future migration), gate that invariant behind an `information_schema` check or omit.
- `tests/fixtures/snapshots/` adds committed JSON files. Size budget: under 500 KB total; prune large nested response bodies during anonymisation if needed.
- Snapshots contain anonymised data only; no live creds, no internal names, no customer PII — call this out in `tests/fixtures/snapshots/README.md`.
- Plan 018 Step 5 (`scripts/verify-extraction.sh` with three invariants) is **superseded** by Layer B of this plan. When Plan 019 lands, update Plan 018 to mark that step as absorbed and defer to 019.

## Scope Boundary

In scope:

- Layers A, B, C, D as described above.
- Updating Plan 018's scope-boundary section once this plan is approved.

Out of scope:

- Property-based / Hypothesis tests on identity normalisation (follow-up Plan 020 candidate).
- Nightly live-API GitHub Actions workflow (follow-up).
- Production observability hook emitting orphan / near-duplicate counts on real extractions (follow-up).
- Cross-platform identity resolution (same human on GitHub + Azure DevOps collapsing to one `contributors` row) — surfaces here as an adversarial scenario but the resolution logic itself is a separate design problem.
- Changing the CI matrix or required checks.

## Success Criteria

- [ ] 10 adversarial scenarios committed under `tests/fixtures/scenarios/adversarial/`.
- [ ] `TestAdversarialScenarios` runs all 10 scenarios through the full pipeline without raising.
- [ ] `tests/db_invariants.sql` defines at least 8 named invariants aligned with the current schema.
- [ ] `db_invariants_check` fixture runs as a post-condition on every integration test class and each adversarial scenario passes it.
- [ ] `scripts/verify-extraction.sh` exits 0 on a clean seeded DB and non-zero when a synthetic orphan or case-variant twin is inserted (verified manually once).
- [ ] `scripts/run-tests-docker.sh` runs `verify-extraction.sh` as its tail step.
- [ ] `TestExtractionIdempotency` parametrised across at least 3 scenarios (2 happy-path + `mixed-case-emails`) passes; row counts and id hashes stable across two passes.
- [ ] Snapshot directory populated for both GitHub and Azure DevOps (at least PR list + PR reviews + commits per platform).
- [ ] `TestGitHubSnapshot` and `TestAzureDevOpsSnapshot` classes pass using `SnapshotExtractor`.
- [ ] Plan 018 Step 5 marked superseded; its invariant set is now a subset of Layer B's.

## Verification

1. `bash scripts/run-tests-docker.sh` — full suite green, includes adversarial, idempotency, and snapshot tests.
2. Manually break an invariant: in a throwaway test, insert a `pull_requests` row with `author_id = 999999`. Confirm `db_invariants_check` fails with the `no_orphan_pr_author_fk` violation name. Revert.
3. Manually break idempotency: temporarily change `store_pull_request` to always INSERT (skip upsert logic). Confirm `TestExtractionIdempotency` fails with a row-count mismatch. Revert.
4. Verify each adversarial scenario round-trips: `pytest tests/contract/integration/test_adversarial_scenarios.py -v` — every scenario reports pass.
5. Refresh one snapshot via `scripts/capture-api-snapshot.sh` + `scripts/anonymise-snapshot.py` against a real repo; re-run snapshot tests; confirm still green.
6. Temporarily revert the `.strip().lower()` line in [src/database/storage.py](../../src/database/storage.py) `get_or_create_contributor`. Run the suite. Confirm **all of these fire**: Plan 018's Step 2/3 tests, the `mixed-case-emails` adversarial scenario, the `no_case_variant_contributor_twins` invariant, and the idempotency test (re-run likely creates more twins). This multi-layer failure pattern is the point — one fix, many alarms. Restore the line.
