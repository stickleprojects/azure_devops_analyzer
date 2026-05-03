# Wave 1C — Plan 020 Component 1: Property-based contributor identity tests

## Goal

Add Hypothesis-based property tests for `get_or_create_contributor` in `src/database/storage.py`. The tests target invariants of contributor identity normalisation — idempotency, case-insensitivity, whitespace handling, unicode preservation, and uniqueness — using generated inputs rather than hand-picked cases. This catches "unknown unknown" pathologies that the existing adversarial fixture corpus (Plan 019 Layer A) doesn't cover.

This prompt covers **Component 1 only** of Plan 020. Components 2 (live-API nightly) and 3 (production observability) are separate PRs.

## Source plan

`.ai/plans/020-property-based-live-api-observability.md`. Read **Component 1** sections 1.1 through 1.4. Skip Components 2 and 3 — out of scope.

## Files to create

- `tests/unit/strategies.py` — Hypothesis strategies for emails, case-perturbed variants, and unicode display names. Plan 020 Section 1.2 has the full skeleton (`email_strategy`, `case_variants`, `unicode_name_strategy`).
- `tests/unit/test_contributor_identity_properties.py` — at least the 6 property tests in Plan 020 Section 1.3 (`test_idempotent`, `test_normalisation_stable`, `test_case_variants_collapse`, `test_whitespace_variants_collapse`, `test_distinct_emails_do_not_collide`, `test_unicode_names_round_trip`).

## Files to modify (only if necessary)

- `requirements-test.txt` — add `hypothesis` ONLY if it is not already present. Check first with `grep -i hypothesis requirements*.txt`. Do not duplicate.

## Architecture rules

- Tests live in `tests/unit/` because `get_or_create_contributor` is a unit-testable function (it just normalises and queries — no external API calls).
- Mark tests with `@pytest.mark.unit` per the project's test conventions. They must complete within the existing unit-test timeout budget (use `@settings(max_examples=...)` to tune if needed; don't crank examples up to 1000 for "more coverage" — slow unit tests block everyone).
- Tests must run via the existing `pytest tests/unit/` step in `scripts/run-tests-docker.sh` and `.github/workflows/tests.yml` — **no workflow changes needed**.
- The strategies must generate emails that the existing normalisation can handle. If Hypothesis finds a real bug in `get_or_create_contributor`, **stop and report** — fixing normalisation is out of scope for this PR.

## Verification step (the proof that these tests work)

Plan 020 Verification step 2: temporarily revert `.strip().lower()` in `get_or_create_contributor`, run only the new tests, confirm Hypothesis shrinks to a minimal failing case (likely a 2-character case-variant email), then restore. This is a **manual verification** to do once before opening the PR — record the shrunk failing input in the PR body to prove the tests have teeth. Do **not** commit the reverted state.

## Acceptance criteria

- [ ] `hypothesis` is available in the test environment (added to `requirements-test.txt` only if not already there)
- [ ] `tests/unit/strategies.py` exists with `email_strategy`, `case_variants`, and `unicode_name_strategy` per Plan 020 Section 1.2
- [ ] `tests/unit/test_contributor_identity_properties.py` contains the 6 property tests from Plan 020 Section 1.3
- [ ] All property tests pass: `bash scripts/run-tests-docker.sh` exits 0
- [ ] Manual verification: reverting `.strip().lower()` causes `test_idempotent`, `test_case_variants_collapse`, and `test_whitespace_variants_collapse` to fail. PR body records the failure.
- [ ] Tests complete within the existing unit-test timeout — no `@settings(max_examples=1000)` or similar; default 100 is fine
- [ ] No changes to `src/database/storage.py` or any production code
- [ ] No changes to existing tests in `tests/unit/` (additive only)

## Branch and PR conventions

- Branch from `main`: `git checkout -b plan-020/component-1-property-tests`
- PR title: `test(plan-020): property-based identity tests for get_or_create_contributor`
- PR body: link to `.ai/plans/020-property-based-live-api-observability.md`, brief summary of strategies + tests, the manual-verification record (failing input from the reverted-`.strip().lower()` run), and an explicit "Components 2 and 3 are separate PRs" note.

## ACCEPTANCE — DO NOT STOP UNTIL CI IS GREEN

This is non-negotiable. Previous Copilot agents on this project have declared work done while CI was red, costing the user 2+ feedback rounds per task.

1. **Before pushing**, run the full test suite locally: `bash scripts/run-tests-docker.sh`. Catch failures here, not in CI.
2. After pushing and opening the PR, run: `gh pr checks <PR#> --watch`
3. If any required check fails:
   1. `gh run view <run-id> --log-failed` to read the failure logs
   2. Identify root cause; do **NOT** skip with `--no-verify`, disable tests, weaken assertions, or use `@pytest.mark.skip` to make CI pass
   3. Fix the actual problem, commit, push
   4. Repeat from step 2
4. Required check: the `tests` workflow (`.github/workflows/tests.yml`).
5. Only declare done when:
   - All required checks are green
   - PR has no merge conflicts
   - Final PR comment links to the green check run **and** shows the manual-verification record

If Hypothesis finds a real bug (test fails with `.strip().lower()` intact), **stop and report** — that's a production bug that needs the user's attention, not a "fix it and ship" situation. Comment on the PR with the failing input and wait for guidance.

If you cannot get CI green after 3 attempts (and Hypothesis hasn't surfaced a real bug), stop and post a comment explaining what you tried and what's blocking.

## Out of scope

- Plan 020 Component 2 (live-API nightly) — separate PR
- Plan 020 Component 3 (production observability) — separate PR
- Cross-platform identity resolution — explicitly out of scope per Plan 020
- Changes to `get_or_create_contributor` or any other production code
- Changes to existing fixtures or test infrastructure

## Estimated size

~2–3 hours. Pure test code; no production changes; lowest risk of all Wave 1 prompts. Independent of all others.
