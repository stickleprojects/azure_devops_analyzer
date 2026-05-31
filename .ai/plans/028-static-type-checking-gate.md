# Plan 028: Static Type-Checking Gate (mypy in CI)

## Status: IN REVIEW — implemented in PR #126 (2026-05-31)

All 29 baseline errors fixed and the `Type Check` CI gate added. mypy clean (76
files); full Docker suite 904 passed / 0 failed. Notable: a **real latent bug**
surfaced in `github/extractor.py` (`self.backoff_seconds` → `self.config.backoff_seconds`,
would `AttributeError` on the rate-limit path), and the `readme_analyzer.py`
duplicate methods were resolved by deleting the 3 dead shadowed copies (no runtime
change). Only the last box (branch-protection) is left — a maintainer action on merge.

## Motivation

A real Azure DevOps token run surfaced **runtime failures that were really
compile-time problems** — call sites passing wrongly-named / wrong-count
parameters, and references to attributes and names that don't exist. They were
fixed by hand, but nothing in the pipeline would have caught them before they
hit a live run.

The tooling to catch them is **already installed but never executed**:
`requirements.txt` pins `mypy>=1.8.0`, `flake8>=7.0.0`, and `pylint>=3.0.3`, yet
no CI job, pre-commit hook, or local gate runs any of them. So type/parameter
regressions can only be discovered at runtime against real credentials — the
most expensive place to find them.

Plan 027 (shared env/config loader) removes the *duplication* that let one of
these bugs hide in a single copy, but it explicitly makes **no behavioural
change** and adds **no static verification** — by design. This plan is the
complementary half: it stops the *bug class* (parameter/type/attribute errors)
from reaching a live run at all. The two are independent and can land in either
order.

### Evidence: what mypy catches right now

Running `mypy src/ --ignore-missing-imports` today (default config, no strict
flags) finds **29 errors in 11 files**. The mix is dominated by exactly the
runtime-risk categories that bit us:

| Code | Count | What it is | Example |
| ---- | ----- | ---------- | ------- |
| `var-annotated` | 7 | missing collection annotation | `loaded_vars` in `config/github.py:100` |
| `no-redef` | 5 | name defined twice (real shadowing bug or dup import) | `_calculate_documentation_score` redefined in `readme_analyzer.py:477` |
| `valid-type` | 3 | `any` used as a type (meant `Any`) | `technology_detector.py:259` |
| `call-arg` | 3 | **wrong argument count/name** | "Too many arguments for `_extract_purpose`" `readme_analyzer.py:166` |
| `return-value` | 2 | returns a type the signature forbids | `base.py:739` returns `list[str \| None]` not `list[str]` |
| `attr-defined` | 2 | **attribute that doesn't exist** | `GitHubExtractor has no attribute "backoff_seconds"` `extractor.py:627` |
| `assignment` | 2 | incompatible assignment | `datetime` into `str` field `extractor.py:390` |
| `arg-type` | 2 | **wrong argument type** | `readme_analyzer.py:530` |
| `union-attr` | 1 | attr access on possibly-`None` | `dependency_analyzer.py:164` |
| `operator` | 1 | `None + str` | `base.py:736` |
| `name-defined` | 1 | **undefined name → NameError** | `LanguageData is not defined` `extractor.py:333` |

The **bolded** rows (`call-arg`, `attr-defined`, `arg-type`, `name-defined`) are
the precise failure modes of the live-token incident. They are all caught in
**default** mode — no strict configuration is required to get the value.

Two of these are not "add an annotation" cosmetics but **genuine latent bugs**
worth understanding before fixing:

- **`readme_analyzer.py` duplicate methods.** `_calculate_documentation_score`,
  `_extract_purpose`, and `_extract_features` are each **defined twice** with
  different signatures. The second definition silently shadows the first, and
  the call sites (lines 157/166/167) pass arguments that match the *intended*
  signature, not the shadowing one — hence the `call-arg` "Too many arguments"
  errors. Resolve by deciding which definition is correct and deleting the
  other; do **not** just annotate the symptom away.
- **`extractor.py` `LanguageData is not defined`** (line 333) and
  **`backoff_seconds` / `max_backoff_seconds`** attrs (627/628) — confirm
  whether these paths are dead or genuinely broken before patching.

## Goal

1. Fix the 29 current `mypy src/` errors (real fixes, not silencing).
2. Add a CI job that runs `mypy src/ --ignore-missing-imports` and **fails the
   build on any error**, so the bug class cannot regress.
3. Pin the mypy invocation in one place shared by CI and local runs.

## Non-goals

- **No strict mode** (`disallow-untyped-defs`, `--check-untyped-defs`,
  per-module strict overrides). That is a sensible *follow-up* once the baseline
  is green, but it would balloon the error count and the scope. Default mypy
  already catches the incident's bug class — that's the bar for this plan.
- **No flake8 / pylint gate** in this plan. They're installed and worth wiring
  later, but mypy is the one that catches parameter/type/attribute errors. Keep
  this plan to a single, high-signal gate.
- **No `tests/` type-checking** yet. Scope is `src/`. Test files have looser
  typing conventions and would add noise; revisit after `src/` is clean.
- **No behavioural change** to any runtime code beyond what a correct type fix
  requires.

## Approach

### Step 1 — Fix the 29 errors (one PR, real fixes)

Work file-by-file. For each error, prefer a real fix over suppression:

- `var-annotated` → add the annotation the hint suggests (`dict[str, str]`,
  `list[str]`, etc.).
- `valid-type` (`any` → `Any`) → import `Any` from `typing` and use it; the
  lowercase `any` is the builtin function, almost certainly a typo.
- `no-redef` from a duplicate `import tomllib` → drop the redundant import (the
  `rust_parser.py` / `python_parser.py` cases are likely a
  `try: import tomllib except: import tomli as tomllib` pattern mypy flags —
  guard with `if sys.version_info` or `# type: ignore[no-redef]` *with a
  one-line reason*, since this is the one legitimate suppression case).
- `no-redef` + `call-arg` in `readme_analyzer.py` → **investigate the duplicate
  methods** (see Motivation); delete the wrong definition, keep call sites
  correct.
- `attr-defined` / `name-defined` → fix the reference (define the missing
  symbol, correct the attribute name, or remove dead code).
- `arg-type` / `assignment` / `return-value` / `operator` / `union-attr` →
  correct the type at the source (guard `None`, convert, or fix the
  annotation), don't cast the error away.

**Suppression policy:** `# type: ignore[code]` is allowed **only** with an
inline one-line justification and only where the code is provably correct and
mypy is wrong (e.g. the version-guarded `tomllib` import). Never blanket
`# type: ignore`. Never widen a signature to `Any` just to silence a real
mismatch.

After fixes:

```bash
# Python runs in Docker per project convention
MSYS_NO_PATHCONV=1 docker run --rm -v "$PWD":/app -w /app python:3.12-slim \
  sh -c "pip install -q 'mypy>=1.8.0' && mypy src/ --ignore-missing-imports"
# expect: Success: no issues found in 75 source files
```

### Step 2 — Pin the invocation

Add a `[tool.mypy]` section to `pyproject.toml` so the config lives with the
other tool config and CI/local can't drift:

```toml
[tool.mypy]
files = ["src"]
ignore_missing_imports = true
# Default checks only. Strict per-module overrides are a deliberate follow-up
# (see Plan 028 non-goals) — do not add disallow_untyped_defs here yet.
```

With this, the canonical command is just `mypy` (no flags) from the repo root,
both in CI and locally.

### Step 3 — Add the CI gate

Add a **standalone `typecheck` job** to `.github/workflows/tests.yml`, modelled
on the existing `docs` job (separate, fast, no Postgres). It does not need the
DB services the `test` job spins up.

```yaml
  typecheck:
    name: Type Check
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
          cache: 'pip'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Run mypy
        run: mypy   # config in pyproject.toml [tool.mypy]
```

> Keep this in sync with the runner note at the top of `tests.yml`
> ("Keep this workflow in sync with `scripts/run-tests-docker.sh`"). If a local
> type-check entry point is added (Step 4), mirror the command there.

Once merged to `main`, add **`Type Check`** to the branch-protection required
checks (alongside `CI Tests` and `Documentation Validation`) — see
`docs/03-operations/branch-protection-setup.md`.

### Step 4 — (optional, same PR) local parity

Add a one-liner to the local flow so contributors catch it before pushing —
either a `typecheck` step in `scripts/run-tests-docker.sh` (guarded like the
existing python-scope check) or a documented `make`/script target. Keep it
optional to avoid scope-creep; the CI gate is the hard requirement.

## Acceptance criteria

- [x] `mypy src/ --ignore-missing-imports` (or bare `mypy` with the new config)
      reports **Success: no issues found** — all 29 baseline errors fixed.
- [x] Fixes are real; any `# type: ignore` carries an inline one-line reason and
      is justified (only the version-guarded `tomllib` import qualified).
- [x] The `readme_analyzer.py` duplicate-method bug is resolved by removing the
      dead shadowed copies, not by annotation — decision noted in the PR.
- [x] `pyproject.toml` has a `[tool.mypy]` section pinning `files = ["src"]` and
      `ignore_missing_imports = true`, **without** strict flags.
- [x] `.github/workflows/tests.yml` has a `Type Check` job that fails on any
      mypy error.
- [x] `bash scripts/run-tests-docker.sh` still passes (904 passed, 0 failed).
- [ ] `Type Check` added to `main` branch-protection required checks. *(maintainer action on merge)*

## Risks

| Risk | Likelihood | Mitigation |
| ---- | ---------- | ---------- |
| A "fix" changes behaviour (e.g. the duplicate-method resolution picks the wrong survivor) | Medium | Each non-trivial fix is covered by, or checked against, an existing test; run the full suite. The duplicate-method choice is explained in the PR for review. |
| `ignore_missing_imports` hides a genuinely missing dependency | Low | It only silences *third-party* stubs, not first-party `src` symbols; first-party `name-defined`/`attr-defined` still fire. Revisit per-library `ignore` overrides if a real missing dep is masked. |
| New errors appear between authoring and merge (code moves under us) | Low | Re-run mypy at PR time; the gate itself prevents future drift. |
| Contributors blocked by the new required check on unrelated PRs | Low | Baseline is green before the check becomes required; failures then mean a real new type error. |

## Relationship to other plans

- **Plan 027 (shared env/config loader)** — complementary, independent. 027
  de-duplicates the loader; 028 adds the static gate that would have caught the
  asymmetric-parameter bug 027 describes. Either can land first. If 027 lands
  first, re-run the mypy baseline (the file moves may shift line numbers but not
  the error count materially).

## Follow-ups (out of scope, capture as issues)

- Ratchet `src/extractors/` and `src/config/` to per-module strict mypy
  (`disallow_untyped_defs`, `check_untyped_defs`) once the baseline holds.
- Wire `flake8` and/or `pylint` (both already in `requirements.txt`) as
  additional non-blocking-then-required gates.
- Extend type-checking to `tests/`.
