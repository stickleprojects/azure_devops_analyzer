# Plan 027: Shared Environment / Config Loader Refactor

> **Renumber note (2026-05-30):** Originally drafted as Plan 026. Renumbered to
> 027 because PR #114 (merged 2026-05-30) reserved Plan 026 for the admin-ui
> vite 6 upgrade. Content unchanged.

## Status: COMPLETE ✅ (PR #121, merged 2026-05-31)

Loader helpers moved to `src/config/env_loader.py` (public names); back-compat
shim kept in `github.py` for the remaining importers (`__init__.py`, `cache.py`,
`conftest.py`); `azure_devops.py` rewired off `github`. New `test_env_loader.py`
+ `test_azure_devops_config.py`, and the override-of-stale-environment regression
test added to **both** config suites (with try/finally env cleanup). CI Tests
green. **Follow-up:** delete the `github.py` shim once nothing imports the
underscored helper names — tracked as **issue #123**.

> **Related:** [Plan 028](028-static-type-checking-gate.md) adds a static
> type-checking (mypy) CI gate. It is the complementary half of this work — 027
> removes the loader duplication that *hid* an asymmetric-parameter bug; 028
> catches the parameter/type/attribute bug class statically so it can't reach a
> live run. Independent; either can land first.

## Motivation

`src/config/github.py` and `src/config/azure_devops.py` currently duplicate the
`.env` discovery and loading logic. The loader itself (`load_env_file`,
`_find_project_root`, `_get_env_int`, `_get_env_float`) lives entirely inside
`src/config/github.py`, and the Azure DevOps config file imports the private
helpers from there (`from src.config.github import load_env_file, _find_project_root, ...`).

Consequences observed in production:

1. **Tests were duplicated by omission.** `tests/unit/test_github_config.py`
   covers `load_env_file` extensively (~15 tests), but there is no equivalent
   `test_azure_devops_config.py`. The recent fix
   (`load_env_file(regular_env, override=True)`, commit `3fbd866`) was not
   protected by any test on either side — the GitHub variant got the fix in
   one place (`elif regular_env.exists():`) but not the other
   (`if resolved_env.exists():`), and the Azure variant got it in both. Either
   asymmetry could regress without notice.

2. **Cross-module private import.** `azure_devops.py` reaches into
   `github.py`'s underscored helpers (`_find_project_root`, `_get_env_int`,
   `_get_env_float`). This couples two unrelated config modules.

3. **The "indirect `$VAR` resolution" behaviour is non-trivial** (two-pass
   resolver, chained references, environment fallback) but the implementation
   only lives next to GitHub config, where a reader is unlikely to expect it.

## Goal

Move the loader and discovery code into a dedicated module, have both config
classes use it, and consolidate the tests so the loader is verified once.

## Non-goals

- No behavioural change to `load_env_file`. The two-pass `$VAR` resolution,
  quote-stripping, comment handling, and override semantics must be preserved
  exactly. This is a pure relocation + de-duplication.
- No change to `AzureDevOpsExtractorConfig` / `GitHubExtractorConfig` public
  surface. `from_env()` signatures remain identical.

## Proposed structure

```
src/config/
├── env_loader.py          # NEW: load_env_file, _find_project_root, _get_env_int, _get_env_float
├── github.py              # imports from env_loader; keeps GitHubExtractorConfig only
└── azure_devops.py        # imports from env_loader; keeps AzureDevOpsExtractorConfig only

tests/unit/
├── test_env_loader.py     # NEW: tests for load_env_file + helpers (moved from test_github_config.py)
├── test_github_config.py  # SLIMMED: only GitHubExtractorConfig.from_env scenarios
└── test_azure_devops_config.py  # NEW: AzureDevOpsExtractorConfig.from_env scenarios
```

### Public names exported by `src/config/env_loader.py`

- `load_env_file(env_file, override=False)` — unchanged signature.
- `find_project_root()` — promoted from `_find_project_root`. The leading
  underscore goes; this is now a published utility.
- `get_env_int(var_name, default)` — promoted from `_get_env_int`.
- `get_env_float(var_name, default)` — promoted from `_get_env_float`.

Existing names in `src/config/github.py` (`load_env_file`, `_find_project_root`,
`_get_env_int`, `_get_env_float`) are kept as thin re-exports for one release
so the rename does not require a flag-day update — then deleted in a follow-up
PR once `git grep` confirms no external imports.

## Test relocation

| Test class                  | Current location          | New location              |
| --------------------------- | ------------------------- | ------------------------- |
| `TestLoadEnvFile`           | `test_github_config.py`   | `test_env_loader.py`      |
| `TestFindProjectRoot`       | `test_github_config.py`   | `test_env_loader.py`      |
| `TestGitHubExtractorConfig` | `test_github_config.py`   | `test_github_config.py` (kept) |
| `TestAzureDevOpsExtractorConfig` | *(none — to be created)* | `test_azure_devops_config.py` |

New tests in `test_azure_devops_config.py` should mirror the
`TestGitHubExtractorConfig` cases but exercise the AZURE_-prefixed env vars and
the credentials fields specific to Azure DevOps (`AZURE_DEVOPS_PAT`,
`AZURE_DEVOPS_ORG_URL`, `AZURE_DEVOPS_ORG`, `AZURE_DEVOPS_PROJECT`).

Critically, the regression that motivated commit `3fbd866` must be covered by
both `from_env` test suites:

> When the `.env` file specifies an indirect reference (e.g.
> `AZURE_DEVOPS_PAT=$VAULT_SECRET`) and `os.environ['AZURE_DEVOPS_PAT']` is
> already set to a stale value from a previous session, `from_env()` must
> override `os.environ` with the resolved value from the file.

A test that sets a stale value in `os.environ`, calls `from_env()` with a
`.env` file containing the indirect reference, and asserts `os.environ` has the
resolved value would have caught the original bug.

## Migration steps

1. Create `src/config/env_loader.py` with the moved helpers (rename the
   underscore-prefixed ones).
2. Add backward-compat re-exports in `src/config/github.py`:
   ```python
   from src.config.env_loader import (
       load_env_file,
       find_project_root as _find_project_root,
       get_env_int as _get_env_int,
       get_env_float as _get_env_float,
   )
   ```
3. Update `src/config/azure_devops.py` to import from `env_loader` directly,
   not from `github`.
4. Create `tests/unit/test_env_loader.py`; move `TestLoadEnvFile` and
   `TestFindProjectRoot` classes verbatim, updating imports.
5. Slim `tests/unit/test_github_config.py` to keep only `TestGitHubExtractorConfig`.
6. Create `tests/unit/test_azure_devops_config.py` mirroring the GitHub config
   suite plus the override-of-stale-environment regression test.
7. Run the full test suite via `bash scripts/run-tests-docker.sh` and verify
   the previously-failing-now-fixed regression test from step 6 passes.
8. Open a follow-up issue to delete the re-export shim in `github.py` once
   nothing else imports the underscore-prefixed names.

## Risk

- **Low.** Pure file move + import surface change. The loader's behaviour is
  already exercised; we are relocating tests, not rewriting them.
- **One thing to watch:** the import chain
  `src/config/azure_devops.py → src/config/github.py` is removed. If any other
  module accidentally relies on that side-effect (e.g. importing
  `azure_devops` to pick up GitHub config behaviour), it would surface as a
  test failure. `git grep "from src.config.github"` will reveal any such
  callers before the move.

## Acceptance criteria

- [x] `src/config/env_loader.py` exists and is the only definition of
      `load_env_file`, `find_project_root`, `get_env_int`, `get_env_float`.
- [x] `src/config/github.py` no longer defines those helpers (re-exports for
      back-compat are OK).
- [x] `src/config/azure_devops.py` imports from `env_loader`, not from `github`.
- [x] `tests/unit/test_env_loader.py` exists and contains the relocated
      loader tests.
- [x] `tests/unit/test_azure_devops_config.py` exists and contains
      `from_env` coverage, including the override-of-stale-environment
      regression test.
- [ ] `bash scripts/run-tests-docker.sh` passes.
- [x] No new public API on `GitHubExtractorConfig` or
      `AzureDevOpsExtractorConfig`.
