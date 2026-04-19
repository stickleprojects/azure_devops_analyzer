# Plan 018: Contributor ↔ Pull-Request Linking Regression Tests

## Status: IMPLEMENTED

## Problem

In production runs, contributors were not linking correctly to pull requests they authored or reviewed. The root cause was **contributor identity fragmentation**: the same person stored under multiple `contributors` rows because `get_or_create_contributor()` compared emails with exact-string equality. A single person with both `alice@example.com` and `Alice@Example.COM` produced two `contributors` rows, so `pull_requests.author_id` and `pr_reviews.reviewer_id` pointed at fragmented records. Reporting views grouping by `contributors.id` split one person's activity across rows.

The bug was fixed in commit `8b4d124` by [database/migrations/012_normalize_contributor_emails.sql](../../database/migrations/012_normalize_contributor_emails.sql) and normalisation (`email.strip().lower()`) inside [src/database/storage.py](../../src/database/storage.py) `get_or_create_contributor()`. A related PR-review dating issue was fixed in commit `a28a95f` ([src/extractors/azure_devops/extractor.py](../../src/extractors/azure_devops/extractor.py)) by falling back to the PR date when no per-reviewer timestamp is available.

**The test suite did not catch either bug.** Investigation found:

1. The email-normalisation regression tests at [tests/contract/database/test_storage_contract.py:440-501](../../tests/contract/database/test_storage_contract.py) cover **commits only**, not pull requests.
2. [tests/contract/database/test_storage_contract.py](../../tests/contract/database/test_storage_contract.py) `test_contract_store_pull_request_creates_new_pr` asserts `pr.author_id is not None` but never verifies the FK resolves to the *correct* contributor, or that two PRs with case-variant author emails collapse to one contributor.
3. [tests/contract/integration/test_fixture_scenarios.py:112-125](../../tests/contract/integration/test_fixture_scenarios.py) `test_pull_requests_stored` counts stored PRs — no join or identity assertion.
4. [tests/contract/database/test_reporting_views.py](../../tests/contract/database/test_reporting_views.py) hardcodes `reviewer_id = pr.author_id` inside test setup, so it cannot expose fragmentation.
5. Fixture scenarios ([tests/fixtures/fixture_extractor.py:77-98](../../tests/fixtures/fixture_extractor.py)) model PR authors but **not reviewers**, so the DASH-REVIEW-003 shape has no fixture path.
6. Live-API tests are gated behind credentials and disabled in CI (`-m "not live_api"`), so real-API case variation never runs on the PR path.

Net: the path `extractor output → storage write → join query → reporting view` is not asserted end-to-end for the PR↔contributor relationship.

## Decision

Add three categories of tests, entirely inside `tests/` — no production code changes, because the fix is already in place. The goal is a suite that would have **failed** against a pre-`8b4d124` checkout.

1. **Contract-level**: PR-author and PR-reviewer email-normalisation regression tests, mirroring the existing commit-level ones.
2. **Integration-level**: join-integrity assertions on fixture scenarios — every stored PR's `author_id` resolves to a contributor whose normalised email matches the source data, zero orphans.
3. **Reporting-view level**: a fragmentation-resistance test that inserts one person via three case-variant emails (as commit author, PR author, PR reviewer) and asserts `v_top_contributors_30d` / `v_top_reviewers_30d` / `v_contributor_activity_30d` each return a single row with combined counts.

Fixtures are extended once (add `reviews` to each PR in generated scenarios) so the reviewer path becomes exercisable by the integration layer without ad-hoc SQL setup.

## Architecture

### Data flow covered by new tests

```
Scenario JSON (pull_requests[].author_email, pull_requests[].reviews[].reviewer_email)
       │
       ▼
FixtureExtractor.get_pull_requests()  →  PullRequestData(author_email, reviews=[...])
       │
       ▼
store_pull_request()
       │
       ├─► get_or_create_contributor(email.strip().lower())
       │        │
       │        └─► contributors (unique normalised email)
       │
       └─► pull_requests.author_id  (FK → contributors.id)
            pr_reviews.reviewer_id   (FK → contributors.id)

Reporting views:
  v_top_contributors_30d       GROUP BY contributors.id
  v_top_reviewers_30d          GROUP BY contributors.id
  v_contributor_activity_30d   GROUP BY contributors.id

Expected invariant after any extraction:
  - Every pull_requests.author_id resolves to a contributors row
  - Every pr_reviews.reviewer_id resolves to a contributors row
  - No two contributors rows share a normalised email
```

### Reuse

- `get_or_create_contributor` in [src/database/storage.py](../../src/database/storage.py) — do NOT modify, already normalises.
- `store_pull_request`, `store_pr_review` in [src/database/storage.py](../../src/database/storage.py) — already populate FKs.
- `FixtureExtractor` at [tests/fixtures/fixture_extractor.py](../../tests/fixtures/fixture_extractor.py) — extend to expose `reviews`.
- `DEPENDENCY_SCENARIOS` and helpers in [tests/contract/database/test_full_pipeline_e2e.py](../../tests/contract/database/test_full_pipeline_e2e.py) — reuse the same scenario list / helper style.
- Existing commit-level dedup test `test_contract_mixed_case_email_deduplicates_to_same_contributor` ([tests/contract/database/test_storage_contract.py:440](../../tests/contract/database/test_storage_contract.py)) — mirror its shape for PRs.

## Implementation Steps

### Step 1 — Extend fixture scenarios with `reviews`

Update [tests/fixtures/fixture_extractor.py](../../tests/fixtures/fixture_extractor.py) so `get_pull_requests()` yields a `PullRequestData` that includes a `reviews: list[PRReviewData]` list, populated from the scenario JSON. Fallback to `[]` when the scenario omits the field.

Update the Ollama seed prompt at [.ai/ollama-prompts/fixture-repo-seeds.md](../ollama-prompts/fixture-repo-seeds.md) so generated scenarios include a `reviews` array per PR:

```json
"pull_requests": [
  {
    "pr_number": 1,
    "title": "...",
    "author_email": "alice@example.com",
    "author_name": "Alice",
    "reviews": [
      { "reviewer_email": "Bob@Example.COM", "reviewer_name": "Bob", "state": "APPROVED" },
      { "reviewer_email": "alice@example.com", "reviewer_name": "Alice", "state": "COMMENTED" }
    ]
  }
]
```

Update [scripts/enrich-repo.py](../../scripts/enrich-repo.py) to preserve the `reviews` array when enriching. Regenerate scenarios:

```bash
bash scripts/generate-fixtures.sh
```

At least one scenario must contain **a PR whose reviewer email is a case-variant of the commit author or PR author email on the same repo** — this is the shape that reproduces the production bug. Add a lightweight assertion in `generate-fixtures.sh` (or a small post-generation Python check) that at least one case-variant pair exists; fail fast if the Ollama output loses it.

### Step 2 — PR-level email-normalisation contract tests

Add to [tests/contract/database/test_storage_contract.py](../../tests/contract/database/test_storage_contract.py), directly after `test_contract_contributor_rollup_consistency_across_email_variants`:

#### 2a. `test_contract_store_pull_request_deduplicates_author_across_email_cases`

- Call `store_pull_request()` twice with the same author but different email casings (`alice@example.com`, `Alice@Example.COM`, `  alice@example.com  `).
- Assert: exactly one `contributors` row exists for that person.
- Assert: both `pull_requests` rows share the same `author_id`.

#### 2b. `test_contract_store_pr_review_deduplicates_reviewer_across_email_cases`

- Create one PR.
- Call `store_pr_review()` twice using two email case-variants for the same reviewer.
- Assert: one `contributors` row for the reviewer.
- Assert: both `pr_reviews` rows share the same `reviewer_id`.

#### 2c. `test_contract_pr_author_resolves_to_matching_contributor`

- Call `store_pull_request()` once.
- Load the PR back, follow `author_id` FK.
- Assert: `contributor.email == pr_data.author_email.strip().lower()`.

#### 2d. `test_contract_pr_has_no_orphaned_author_fk`

- After `store_pull_request()` + commit, run:
  `SELECT count(*) FROM pull_requests WHERE author_id IS NULL OR author_id NOT IN (SELECT id FROM contributors)`
- Assert: `0`.

All four tests must be `@pytest.mark.integration` and run in the existing transaction-rollback scope.

### Step 3 — Integration join-integrity assertions across scenarios

Extend [tests/contract/integration/test_fixture_scenarios.py](../../tests/contract/integration/test_fixture_scenarios.py) `test_pull_requests_stored` (or add a sibling `test_pull_requests_author_links_are_sound`):

After the existing `store_pull_request` loop and `session.commit()`:

```python
# PR→Contributor link integrity
orphan_count = session.execute(text("""
    SELECT count(*) FROM pull_requests
    WHERE repo_id = :repo_id
      AND (author_id IS NULL
           OR author_id NOT IN (SELECT id FROM contributors))
"""), {"repo_id": repo.repo_id}).scalar()
assert orphan_count == 0

# Each PR's author resolves to the normalised source email
for pr_data in extractor.get_pull_requests(repo.repo_id):
    stored = session.query(PullRequest).filter_by(
        repo_id=repo.repo_id, pr_number=pr_data.pr_number
    ).one()
    contributor = session.get(Contributor, stored.author_id)
    assert contributor is not None
    assert contributor.email == pr_data.author_email.strip().lower()
```

Add a parallel assertion block for reviews once Step 1 lands:

```python
for pr_data in extractor.get_pull_requests(repo.repo_id):
    for review in pr_data.reviews:
        stored = session.query(PRReview).filter_by(...).one()
        reviewer = session.get(Contributor, stored.reviewer_id)
        assert reviewer is not None
        assert reviewer.email == review.reviewer_email.strip().lower()
```

This test is parametrised across the existing scenario list, so every generated scenario exercises the join.

### Step 4 — Reporting-view fragmentation-resistance test

Add to [tests/contract/database/test_reporting_views.py](../../tests/contract/database/test_reporting_views.py) a new class `TestContributorFragmentationResistance`:

```
CONTRACT: views attribute commits, PR authorship, and PR reviews to a single
contributor even when the same person arrives via multiple email casings.
```

Setup:

- Pick one person: `Alice`. Store three events using three casings of her email:
  1. A commit via `store_commit(..., author_email="alice@example.com")`.
  2. A PR via `store_pull_request(..., author_email="Alice@Example.COM")`.
  3. A review via `store_pr_review(..., reviewer_email="  ALICE@example.com  ")`.
- Commit session.
- Refresh any materialised view if applicable; otherwise views query live.

Assertions (select the matching `contributors.id` first, then):

- `v_top_contributors_30d` contains exactly one row for Alice with `commits >= 1` and `prs_authored >= 1`.
- `v_top_reviewers_30d` contains exactly one row for Alice with `reviews_given >= 1`.
- `v_contributor_activity_30d` contains exactly one row for Alice with `commits >= 1 AND prs_authored >= 1 AND reviews_given >= 1`.
- `SELECT count(*) FROM contributors WHERE lower(email) = 'alice@example.com'` equals `1`.

Mark `@pytest.mark.integration`.

### Step 5 — Post-scan invariant script (defence in depth)

> **Note:** This step is **superseded by Plan 019 Layer B**. The three invariants
> defined here are a subset of the full invariant set in `tests/db_invariants.sql`
> (implemented in Plan 019). `scripts/verify-extraction.sh` remains as the shell
> runner for the original three checks; Plan 019's `db_invariants_check` pytest
> fixture covers the broader set automatically after every integration test.

Create [scripts/verify-extraction.sh](../../scripts/verify-extraction.sh) (new). It executes inside the existing Docker test runner and runs three SQL checks against the test database:

1. No `pull_requests` row with `author_id IS NULL` or dangling `author_id`.
2. No `pr_reviews` row with `reviewer_id IS NULL` or dangling `reviewer_id`.
3. No two `contributors` rows sharing `lower(trim(email))`.

Exit non-zero on any violation with a human-readable message and the offending row sample. Wire it into the tail of [scripts/run-tests-docker.sh](../../scripts/run-tests-docker.sh) **after** the integration test stage so it runs automatically on every `bash scripts/run-tests-docker.sh` invocation.

### Step 6 — (Optional) Nightly live-API regression

Add a GitHub Actions workflow `.github/workflows/live-api-nightly.yml` that runs `bash scripts/run-tests-docker.sh --live-api` on a cron schedule using read-only `GITHUB_TOKEN` and `AZURE_DEVOPS_PAT` secrets. It must **not** be a required PR check. Failures open an issue or notify via existing reporting — it is a monitoring net, not a merge gate. This is the only layer that catches real-API shape quirks that mocks and fixtures cannot reproduce.

Mark this step out of scope if secrets management is not already in place; noted so a follow-up plan can pick it up.

## Compatibility Notes

- No production code changes. The fix (`.strip().lower()` in `get_or_create_contributor`, migration 012) is already merged.
- New tests run inside the existing Docker test runner and the `db_session` transaction-rollback scope — all inserts roll back per test.
- `PullRequestData.reviews` may already exist; if not, add the field as `reviews: list[PRReviewData] = field(default_factory=list)` and update the Azure DevOps + GitHub extractors only if the field does not already appear in `PullRequestData` (check [src/extractors/github/extractor.py](../../src/extractors/github/extractor.py) and [src/extractors/azure_devops/extractor.py](../../src/extractors/azure_devops/extractor.py) before touching — do **not** duplicate existing fields).
- Fixture regeneration may produce churn in `tests/fixtures/scenarios/generated/*.json`. Commit the regenerated files alongside the prompt change.

## Scope Boundary

In scope:

- New tests (contract, integration, reporting-view).
- Fixture shape extension for reviews.
- Post-scan invariant script + wiring into `run-tests-docker.sh`.

Out of scope:

- Any changes to `get_or_create_contributor`, `store_pull_request`, `store_pr_review`, or migration 012.
- Any change to production reporting views.
- Changing the CI matrix or required checks (the nightly workflow in Step 6, if added, is non-blocking).
- Backfilling further normalisation (e.g. accent folding, display-name canonicalisation) — bug was case + whitespace only.

## Success Criteria

- [ ] New tests run under `pytest -m "not live_api"` (CI gate) and all pass.
- [ ] Removing `.strip().lower()` from `get_or_create_contributor` **causes the new Step 2 and Step 3 tests to fail** (manually verified once before merging). Restore the line before committing.
- [ ] At least one regenerated fixture scenario contains a case-variant reviewer/author email pair; a `generate-fixtures.sh` check enforces this.
- [ ] `v_top_contributors_30d`, `v_top_reviewers_30d`, `v_contributor_activity_30d` each return exactly one row for the single-person fragmentation test.
- [ ] `bash scripts/verify-extraction.sh` exits 0 against a freshly seeded test DB and exits non-zero when a synthetic orphan is introduced.
- [ ] `bash scripts/run-tests-docker.sh` green on a clean branch.

## Verification

1. `bash scripts/run-tests-docker.sh` — full suite green.
2. Temporarily revert the `.strip().lower()` line in [src/database/storage.py](../../src/database/storage.py) `get_or_create_contributor`; rerun. New Step 2c, 2d, 3, 4 tests must fail. Restore the line — do **not** commit the revert.
3. `bash scripts/generate-fixtures.sh` regenerates scenarios; new case-variant reviewer/author pair is present.
4. `bash scripts/verify-extraction.sh` exits 0 on clean DB; exits 1 when a test inserts a `pull_requests` row with `author_id = 999999` (orphan).
5. If Step 6 pursued: manually trigger the nightly workflow once; confirm it runs `--live-api` and reports without blocking PRs.
