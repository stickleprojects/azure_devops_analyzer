# Investigation: Ollama Codegen Bugs in Layer 2 Enrichment Scripts

**Date**: 2026-03-01
**Context**: Plan 014, Layer 2 — per-repo enrichment script generation via Ollama
**Model tested**: `qwen2.5-coder:14b`

**Status**: SUPERSEDED (2026-04-19) — the Ollama-based enrichment-codegen approach this document investigates was removed in PR #62 (`chore/remove-ollama`). Fixture generation is now deterministic seeded-PRNG and no longer involves an LLM. The artifacts referenced below no longer exist: `.ai/ollama-prompts/fixture-repo-enrichment.md` and the hand-patched `scripts/generated/enrich-*.py` scripts. Current pipeline: `scripts/generated/generate-repo-seeds.py` → `scripts/run-enrich.py` (`scripts/enrich-repo.py`) → `tests/fixtures/fixture_extractor.py`. Retained for historical context only — no action remains.

---

## Config Structure (clarified during investigation)

The fixture config (`tests/fixtures/scenarios/config.json`) has three top-level sections:

```
patterns       → commit/PR sizing by pattern type (single-language, frontend-spa, etc.)
                 Each pattern defines: commits {min,max,median}, pr {min,max,median},
                 commit_metadata ranges, pr_metadata ranges, pr_status percentages

repo_templates → per-template themes + pattern reference
                 Each template defines: commit_message_themes[], pr_title_themes[],
                 languages[], pattern (references patterns key above)
                 Key names: python-docker, react-spa, dual-ci, legacy-migration, etc.

repo_sets      → instances: maps templates → actual seed files
                 e.g. {template: "python-docker", name_template: "python-docker-{service}",
                        services: ["billing", "inventory", "payroll", ...]}
```

**Key implication**: seed files like `python-docker-billing.json` do NOT have a direct
entry in the config. Ollama must match by prefix to find the `python-docker` template.
In testing, the model correctly navigated this — embedding the right sizing and themes.

---

## Architecture Validation

The two-layer split works correctly for its stated goals:

| Goal | Result |
|------|--------|
| Avoid context limit | ✅ Each enrichment call = 1 seed (~KB) + config (~KB) + prompt. Well within 8192 tokens. |
| Unique seed structure | ✅ Layer 1 already produced 33 distinct seeds (file names, languages, manifests) |
| Template-appropriate themes | ✅ Model correctly matched `python-docker-billing` → `python-docker` template |
| Unique commits/PRs per repo | ✅ Random hashes, dates, authors, quantities within min–max range |
| No cross-repo duplication | ✅ Service-family repos share theme pool but generate different data each run |

**Expected same-family behaviour**: all `python-docker-*` repos share commit/PR themes
(Flask, pytest, Docker). This is intentional and realistic — they're all Python/Docker services.
The structural variety (file names, manifests) comes from Layer 1 seeds.

---

## Bugs Found in Generated Scripts (2 scripts tested)

Each bug is listed with: symptom, root cause, fix applied to script, fix applied to prompt.

### Bug 1 — Missing `import tempfile`

- **Symptom**: `NameError: name 'tempfile' is not defined`
- **Root cause**: Model used `tempfile.NamedTemporaryFile` but omitted the import
- **Script fix**: Added `import tempfile` to imports
- **Prompt fix**: "Use `pathlib.Path`, `json`, `tempfile`, `shutil`, `random`, `datetime` from stdlib — import all of them"

### Bug 2 — `NamedTemporaryFile` opened in binary mode

- **Symptom**: `TypeError: a bytes-like object is required, not 'str'`
- **Root cause**: Default mode is `'rb'`; `json.dump()` writes str, not bytes
- **Script fix**: Added `mode='w'` and `suffix='.json'`
- **Prompt fix**: Updated atomic write instruction to include `mode='w'` with explanation

### Bug 3 — Schema validation checks wrong field name

- **Symptom**: `Error: Seed JSON must contain 'name', 'file_names', and 'languages' fields`
- **Root cause**: Prompt example used `languages`; actual seeds use `language_data`
- **Script fix**: Removed `languages` from validation check; kept only `name` and `file_names`
- **Prompt fix**: "do NOT check for `languages`, seeds use `language_data`"

### Bug 4 — Idempotency check triggers on Layer 1 placeholder commit

- **Symptom**: Enrichment silently skipped despite seed having only 1 placeholder commit
- **Root cause**: Check was `if "commits" in seed_data` or `if seed_data.get("commits")` —
  both are truthy when seed has 1 Layer 1 placeholder commit
- **Script fix**: Changed to `if len(seed_data.get("commits", [])) >= COMMIT_MIN:`
- **Prompt fix**: Explicit instruction with the exact expression and the reason

### Bug 5 — Variables used in dict literal before assignment

- **Symptom**: `NameError: name 'author_name' is not defined`
- **Root cause**: Model wrote `"author_email": generate_realistic_email(author_name)` inside
  a dict literal where `author_name` was set as a prior key's value, not a local variable
- **Script fix**: Pre-assigned `author_name`, `author_email`, `committer_name`, `committer_email`
  to local variables before the dict
- **Prompt fix**: "Always assign variables before using them in dict literals"

### Bug 6 — PR date range reads from `seed_data["commits"]`

- **Symptom**: `ValueError: time data '2026-01-15T10:30:00' does not match format '%Y-%m-%dT%H:%M:%SZ'`
- **Root cause**: `generate_pull_requests` tried to parse the Layer 1 placeholder commit's
  date to get a date range. Placeholder dates don't have trailing `Z`. Also wrong approach.
- **Script fix**: Replaced with `datetime.now() - timedelta(days=90)` / `- timedelta(days=1)`
  (same fixed range as `generate_commits`)
- **Prompt fix**: "Do NOT read dates from `seed_data["commits"]` — the seed may only have placeholder data"

---

## Prompt Evolution

All fixes are now incorporated into `.ai/ollama-prompts/fixture-repo-enrichment.md`.

The prompt was also updated to clarify the config embed pattern:
- Removed ambiguous "Config data will be provided as `--context` to Ollama" (caused sys.argv[2] bug)
- Replaced with: "The repo config and seed JSON are already visible to you in the system context.
  Extract the config entry matching this repo's `name` field and embed values as hardcoded constants."

---

## Remaining Risk

Despite all prompt fixes, Ollama may still produce subtly buggy scripts on future runs.
The bugs above are consistent patterns across two different scripts tested:
- Missing imports
- Dict-literal variable scoping errors
- Reading from seed data instead of computing fresh values

**Mitigation options** (not yet implemented):
1. Add a post-generation validator script that checks for `sys.argv[2]`, missing imports, etc.
2. Write a fixed template script and use Ollama only to fill in the constants section
3. Accept the current approach and fix individual scripts as needed (feasible for 33 repos)

---

## Scripts Manually Patched

The following generated scripts were hand-patched during this investigation and are correct:

- `scripts/generated/enrich-deep-nested-manifests.py` — bugs 1, 2, 3, 4 fixed
- `scripts/generated/enrich-python-docker.py` — bugs 3, 4, 5, 6 fixed; verified `[OK]` output
