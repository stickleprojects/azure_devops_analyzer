# Copilot Agent Prompt — Plan 027: Shared Environment / Config Loader Refactor

> **Usage**: Paste the contents of the **Prompt** section below into GitHub
> Copilot agent. Everything above the horizontal rule is meta-context for the
> human; everything below it is the agent instruction.
>
> **Nature of this task**: a *pure relocation + de-duplication* refactor with
> **no behavioural change**, plus the test coverage that was missing. The risky
> part is not the move — it's (a) not breaking the several existing importers of
> the private helpers, and (b) actually adding the regression test that protects
> the `3fbd866` fix. Both are spelled out below.

**Branch to create**: `feature/027-shared-env-config-loader`
**PR target**: `main`
**PR title**: `Plan 027: shared env/config loader (de-dup + missing tests)`

---

## Prompt

You are implementing **Plan 027** for the `azure_devops_analyzer` repository. The
plan is at `.ai/plans/027-shared-env-config-loader.md` — **read it first**, in
full. This prompt is the executable distillation of that plan; if the two ever
disagree, the plan wins and you should flag the discrepancy.

### What this is

`src/config/github.py` currently *owns* the `.env` discovery/loading helpers
(`load_env_file`, `_find_project_root`, `_get_env_int`, `_get_env_float`), and
`src/config/azure_devops.py` reaches across to import the underscored ones. You
are going to **move those helpers into a new `src/config/env_loader.py`**, have
both config modules import from there, and **add the test coverage** that's
currently missing on the Azure side.

This is a **backend Python** task. Python in this repo **always runs inside
Docker** (never on the host); the test command is
`bash scripts/run-tests-docker.sh`.

### Hard constraint: NO behavioural change

The body of `load_env_file` — the **two-pass `$VAR` resolution**, chained
references, environment fallback, quote-stripping, comment handling, and
`override` semantics — must be preserved **byte-for-byte**. Move it; do not
rewrite, "clean up", or "improve" it. Same for `_find_project_root`,
`_get_env_int`, `_get_env_float`. The public `from_env()` signatures on both
config classes stay identical. No new public API.

---

### Step 1 — Create `src/config/env_loader.py`

Move the four helpers out of `src/config/github.py` into a new
`src/config/env_loader.py`, **promoting the underscore-prefixed ones to public
names** (the leading underscore goes — these are now a published utility):

| Old name (in `github.py`) | New public name (in `env_loader.py`) |
| ------------------------- | ------------------------------------ |
| `load_env_file`           | `load_env_file` (unchanged)          |
| `_find_project_root`      | `find_project_root`                  |
| `_get_env_int`            | `get_env_int`                        |
| `_get_env_float`          | `get_env_float`                      |

Keep `from __future__ import annotations` and the same imports the helpers need
(`os`, `re`, `pathlib.Path`). Copy the bodies **verbatim**.

### Step 2 — Re-export shim in `src/config/github.py` (DO NOT SKIP)

`github.py` must **stop defining** the helpers but **keep the old names working**
as thin re-exports, because **multiple other modules still import the private
names**. Add:

```python
from src.config.env_loader import (
    load_env_file,
    find_project_root as _find_project_root,
    get_env_int as _get_env_int,
    get_env_float as _get_env_float,
)
```

Then update `GitHubExtractorConfig.from_env` to call the (now imported) helpers —
the call sites already use `load_env_file` / `_find_project_root` / `_get_env_int`
/ `_get_env_float`, so they keep working unchanged through the shim.

> **Why the shim is mandatory — these are the current external importers of the
> underscored names (verified by grep). They must all still work after your
> change without being edited in this PR:**
>
> - `src/config/__init__.py` → `from src.config.github import ... load_env_file`
> - `src/config/azure_devops.py` → imports all four (you rewire this one in Step 3)
> - `src/extractors/cache.py` → `from src.config.github import _find_project_root`
>   (and calls `_find_project_root()` at module use)
> - `tests/conftest.py` → imports `load_env_file` **and** `_find_project_root`
> - `tests/unit/test_github_config.py` → imports the loader helpers (you relocate
>   these tests in Step 4)
>
> Only `azure_devops.py` and `test_github_config.py` get rewired in this PR. The
> rest (`__init__.py`, `cache.py`, `conftest.py`) must keep resolving through the
> shim — **do not edit them**, and do not delete the shim. Deleting the shim is
> an explicit follow-up issue (Step 8), not this PR.

### Step 3 — Rewire `src/config/azure_devops.py`

Change its import from:

```python
from src.config.github import load_env_file, _find_project_root, _get_env_int, _get_env_float
```

to import the **public** names from `env_loader` directly:

```python
from src.config.env_loader import load_env_file, find_project_root, get_env_int, get_env_float
```

Then update the call sites in `AzureDevOpsExtractorConfig.from_env` to use the
new public names (`find_project_root()`, `get_env_int(...)`, `get_env_float(...)`).
**No logic change** — same arguments, same order, same `override=True` calls.
After this, `azure_devops.py` must have **no import from `src.config.github`**.

---

### Step 4 — Relocate the loader tests → `tests/unit/test_env_loader.py`

Create `tests/unit/test_env_loader.py` and **move** (not copy) the
`TestLoadEnvFile` and `TestFindProjectRoot` classes out of
`tests/unit/test_github_config.py`, **verbatim**, updating only the imports to
point at `src.config.env_loader` and the new public names
(`find_project_root` instead of `_find_project_root`).

### Step 5 — Slim `tests/unit/test_github_config.py`

After the move, `test_github_config.py` keeps **only** `TestGitHubExtractorConfig`
(the `from_env` scenarios). Its imports should reference whatever it still needs;
if it referenced `_find_project_root` / `load_env_file` for the relocated tests,
those references leave with the classes. It may still import via the shim if a
`from_env` test needs it — that's fine.

### Step 6 — Create `tests/unit/test_azure_devops_config.py` (the missing coverage)

This is the **point of the plan** — there is currently *no* Azure config test
file. Create one with a `TestAzureDevOpsExtractorConfig` class that **mirrors**
the `TestGitHubExtractorConfig` cases but exercises the `AZURE_`-prefixed env
vars and the Azure-specific credential fields (`AZURE_DEVOPS_PAT`,
`AZURE_DEVOPS_ORG_URL`, `AZURE_DEVOPS_ORG`, `AZURE_DEVOPS_PROJECT`). Use
`tests/unit/test_github_config.py`'s `TestGitHubExtractorConfig` as the template
for structure, fixtures, and `tmp_path`/`monkeypatch` patterns.

#### The regression test that MUST exist (both suites)

The fix in commit `3fbd866` (`load_env_file(regular_env, override=True)`) had
**no test** protecting it on either side. Add this regression test to **both**
`test_github_config.py` (GitHub vars) **and** `test_azure_devops_config.py`
(Azure vars):

> **Scenario**: `os.environ['AZURE_DEVOPS_PAT']` is pre-set to a **stale** value
> (simulating a leftover from a previous session). A `.env` file sets
> `AZURE_DEVOPS_PAT` to a **different, resolved** value (directly or via an
> indirect `$VAR` reference). After `from_env()` runs against that `.env`,
> `os.environ['AZURE_DEVOPS_PAT']` (and the resulting config field) must hold the
> **`.env` value, not the stale one** — i.e. the file overrides the environment.

Use `monkeypatch.setenv` to plant the stale value and `tmp_path` to write the
`.env`. Assert on the **resolved/overridden** value. This test must **fail** if
the `override=True` is removed and **pass** with it present — that's how you know
it actually guards the fix. (Sanity-check by temporarily flipping `override` to
`False` locally; it should go red. Restore it.)

---

### Step 7 — Validate in Docker

```bash
# from repo root — Python runs in Docker, never on the host
bash scripts/run-tests-docker.sh
```

Expect a fully green run. Targeted iteration while developing:

```bash
bash scripts/run-tests-docker.sh tests/unit/test_env_loader.py
bash scripts/run-tests-docker.sh tests/unit/test_github_config.py
bash scripts/run-tests-docker.sh tests/unit/test_azure_devops_config.py
```

Also confirm nothing that imports the shim broke:

```bash
bash scripts/run-tests-docker.sh tests/   # full suite catches conftest/cache importers
```

### Step 8 — Update the plan status IN THIS PR (no separate docs PR)

As part of **this same PR**, edit `.ai/plans/027-shared-env-config-loader.md` so
we don't need a follow-up docs-only PR just to flip status:

- Change the status line from `## Status: PROPOSED (not started)` to:
  `## Status: IN REVIEW — implemented in PR #<this-PR-number> (YYYY-MM-DD)`
  (fill in the real PR number once GitHub assigns it, and today's date; push the
  edit as a follow-up commit on the same branch after the PR exists).
- **Tick the boxes** in the plan's own "## Acceptance criteria" section (`[ ]` →
  `[x]`) for every item your implementation satisfies. Leave any genuinely unmet
  item unticked with a one-line note rather than ticking it falsely.

Do **not** move the plan file into `.ai/plans/completed/` — the maintainer flips
it to COMPLETE and relocates it on merge. Your job is to get it to an accurate
"IN REVIEW, boxes ticked" state so no separate status-only PR is needed.

### Step 9 — Follow-up issue (do NOT do the deletion in this PR)

In the PR description, note that a **follow-up issue** should be opened to delete
the re-export shim in `github.py` once `git grep "from src.config.github import"`
confirms no module still imports the underscored helpers (today `cache.py`,
`conftest.py`, and `__init__.py` still do). Do not delete the shim now.

---

### Architecture constraints

- `src/config/env_loader.py` must depend on **nothing** from `src/extractors/`,
  `src/database/`, `src/analyzers/`, or `src/workflows/` — it is a leaf utility
  (only `os`, `re`, `pathlib`). If you find yourself importing from those, stop.
- No new third-party dependencies. No change to `requirements.txt`.
- Do not touch anything outside `src/config/` and `tests/unit/` except the PR
  description and the plan file `.ai/plans/027-shared-env-config-loader.md`
  (status flip, Step 8). In particular **do not edit** `src/config/__init__.py`,
  `src/extractors/cache.py`, or `tests/conftest.py` — they ride the shim.

### Out of scope

- Deleting the back-compat shim (follow-up issue).
- Any change to `load_env_file` behaviour, or to either `from_env` signature.
- Updating `cache.py` / `conftest.py` / `__init__.py` to the new public names
  (a later cleanup, gated on the shim-deletion issue).
- flake8/pylint/mypy work (that's Plan 028, a separate PR).

---

### Acceptance checklist (reviewer will verify)

- [ ] `src/config/env_loader.py` exists and is the **only** definition of
      `load_env_file`, `find_project_root`, `get_env_int`, `get_env_float`.
- [ ] `src/config/github.py` no longer **defines** those helpers; it re-exports
      them (incl. the underscored aliases) from `env_loader`.
- [ ] `src/config/azure_devops.py` imports from `env_loader` and has **no**
      `from src.config.github import` line.
- [ ] `src/config/__init__.py`, `src/extractors/cache.py`, and
      `tests/conftest.py` are **unchanged** and still pass (shim works).
- [ ] `tests/unit/test_env_loader.py` exists with the relocated `TestLoadEnvFile`
      + `TestFindProjectRoot`.
- [ ] `tests/unit/test_github_config.py` keeps only `TestGitHubExtractorConfig`
      (plus the new GitHub-side override regression test).
- [ ] `tests/unit/test_azure_devops_config.py` exists with
      `TestAzureDevOpsExtractorConfig` **including** the override-of-stale-environment
      regression test.
- [ ] No new public API on `GitHubExtractorConfig` / `AzureDevOpsExtractorConfig`;
      no behavioural change to `load_env_file`.
- [ ] `bash scripts/run-tests-docker.sh` is fully green.
- [ ] `.ai/plans/027-shared-env-config-loader.md` status flipped to
      `IN REVIEW — implemented in PR #<n>` and its acceptance boxes ticked
      **in this same PR** (no separate docs PR).
- [ ] PR description notes the shim-deletion follow-up issue.

---

## ACCEPTANCE — DO NOT STOP UNTIL CI IS GREEN

This is non-negotiable. Previous Copilot agents on this project have declared
work done while CI was red, costing the maintainer 2+ feedback rounds per task.

1. **Before pushing**, run the full suite locally and get it green:
   `bash scripts/run-tests-docker.sh`.
2. After pushing and opening the PR, run: `gh pr checks <PR#> --watch`.
3. If any required check fails:
   1. `gh run view <run-id> --log-failed` to read the actual failure.
   2. Fix the **root cause**. Do **NOT** `--no-verify`, `.skip`/`xfail`/delete
      tests, weaken assertions, or remove the `override=True` to make a test
      pass. The override regression test failing means your loader wiring is
      wrong — fix the wiring, not the test.
   3. Commit, push, repeat from step 2.
4. Required checks on this repo: **CI Tests** and **Documentation Validation**
   (`.github/workflows/tests.yml`).
5. Only declare done when: all required checks are green, the PR has no merge
   conflicts, and the final PR comment links to the green check run.

If you cannot get CI green after 3 attempts, stop and post a comment explaining
what you tried and what's blocking.

---

### Estimated size

~0.5–1 day. The move itself is small; the real work is writing
`test_azure_devops_config.py` and the two override regression tests, and
confirming the shim keeps `cache.py` / `conftest.py` / `__init__.py` working.
