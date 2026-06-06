# Coding-agent prompts

Ready-to-paste prompts for delegating work to GitHub Copilot agents (or equivalents). Each prompt is self-contained — assume the agent has not seen any prior conversation.

## Wave 1 — ✅ all merged 2026-05-03

| Prompt | Plan | Description | PR |
|---|---|---|---|
| [wave-1a-grafana-uniform-top-link-bar.md](wave-1a-grafana-uniform-top-link-bar.md) | Plan 025 Phase 2 | Uniform 6-entry `links[]` across 11 dashboards | [#85](https://github.com/stickleprojects/azure_devops_analyzer/pull/85) |
| [wave-1b-tech-radar-schema-and-categorizer.md](wave-1b-tech-radar-schema-and-categorizer.md) | Plan 022 Track A | Radar schema migration + categorization engine | [#86](https://github.com/stickleprojects/azure_devops_analyzer/pull/86) |
| [wave-1c-property-based-identity-tests.md](wave-1c-property-based-identity-tests.md) | Plan 020 Component 1 | Hypothesis-based property tests for `get_or_create_contributor` | [#87](https://github.com/stickleprojects/azure_devops_analyzer/pull/87) |
| [wave-1d-extraction-health-observability.md](wave-1d-extraction-health-observability.md) | Plan 020 Component 3 | `extraction_health.py` + Prometheus emission + new dashboard | [#88](https://github.com/stickleprojects/azure_devops_analyzer/pull/88) |

The wave prompts above remain in this folder as reference templates for drafting future agent prompts (esp. the CI-green acceptance block at the end of each).

## Wave 3 — Plan 025 Phase 1c + 1d (✅ run in parallel)

These two close out the remaining deferred phases of Plan 025. They are
**designed to run at the same time**: each does most of its work in new,
feature-scoped files and gets its own `src/api/*.ts` module instead of appending
to the shared `client.ts`/`types.ts`.

| Prompt | Plan | Description |
|---|---|---|
| [025-phase1c-tech-radar-viewer.md](025-phase1c-tech-radar-viewer.md) | Plan 025 Phase 1c | `/radar` + `/radar/history` — visual radar via the MIT-licensed Zalando tech-radar (D3), plus history table |
| [025-phase1d-library-detail-page.md](025-phase1d-library-detail-page.md) | Plan 025 Phase 1d | `/library/:ecosystem/:name` — library detail page over `GET /api/packages/library/<name>/<ecosystem>` |

**Parallel-safety contract:** the *only* file both PRs edit is
`web/admin-ui/src/App.tsx`. Each prompt pins a **different insertion anchor**
(1c after the `/health` route; 1d after the `/repositories` route) so git
auto-merges. 1c additionally (and exclusively) touches `Layout.tsx` and
`package.json` (adds `d3`); 1d touches no other shared file. Whichever PR merges
second should auto-merge; if `App.tsx` ever conflicts it's a 2-line resolve (keep
both route sets). Merge order doesn't matter.

> **Licensing note for 1c:** the renderer is Zalando tech-radar (**MIT**), *not*
> Thoughtworks build-your-own-radar (**AGPL-3.0**) — the swap was a deliberate
> decision to keep copyleft off the frontend bundle. The prompt forbids
> substituting BYOR. See `.ai/plans/025-bespoke-admin-and-navigation-ui.md`
> Task C and `PROGRESS.md` (2026-05-25).

## Wave 2 (drafting on demand)

- **Plan 020 Component 2** (live-API nightly monitoring) — ✅ merged 2026-05-03 in [PR #90](https://github.com/stickleprojects/azure_devops_analyzer/pull/90). Carved out of Wave 1 because it required provisioning live API tokens manually. Plan 020 is now fully complete.
- **Plan 025 Phase 3** (drill-down data links) — ready to draft; sequenced after Wave 1A to avoid `dashboards/*.json` merge conflicts. ~12 specific `fieldConfig.overrides[]` edits enumerated in `.ai/plans/025-bespoke-admin-and-navigation-ui.md`.
- **Plan 022 Track B** (radar publication workflow) — ready to draft; depends on the schema landed in PR #86.
- **Plan 022 Track C** (radar API endpoints `/api/radar`, `/api/radar/history`, `/api/radar/export`) — ready to draft; depends on schema (PR #86) and ideally Track B.
- **Plan 025 Phase 1** (React + Vite + TS admin MVP at `web/admin-ui/`) — sequenced after Phases 2+3 per Theme E.2's 80/20 finding.

## Why this folder exists

Previous Copilot agent rounds on this project have ended with the agent declaring done while CI was red, costing 2+ feedback rounds per task. Every prompt here includes a non-negotiable acceptance block requiring `gh pr checks --watch` and root-cause fixing on red. Reuse the block when drafting new prompts.

## Reusable block: model self-check preamble

Paste this as the **first section** of every new agent prompt. The convention is to back the Copilot agent with **Claude Sonnet 4.6** (Opus 4.6 for hard tasks); this block surfaces a mis-dispatch *before* any work happens.

> **Caveat (read before relying on this):** the agent **cannot change its own model** — that is fixed by the model picker at dispatch time — and a model's self-reported identity is **not reliable** (models often misstate or don't know which model they are). So this is a best-effort *declare-and-halt* signal, not a guarantee. The real guard is the human picking the right model in the Copilot UI before dispatch.

```md
## STEP 0 — Model self-check (do this FIRST, before anything else)

This task is intended to run on **Claude Sonnet 4.6** (or **Claude Opus 4.6** for harder work). Before doing any other step:

1. State, as the first line of your first response and in your opening PR/issue comment: **"Running as: <model name/version>"**.
2. If you are confident you are NOT one of the expected models (Claude Sonnet 4.6 / Claude Opus 4.6) — e.g. you are a GPT or Gemini model — **STOP immediately. Do not write code, do not open a PR.** Post a comment: *"⚠️ Model mismatch: dispatched on <model>, but this task expects Claude Sonnet 4.6 / Opus 4.6. Please re-dispatch with the correct model selected in the Copilot model picker."* Then halt.
3. If you cannot reliably determine which model you are, say so explicitly ("Cannot confirm model identity") and **proceed with caution**, flagging it in the PR body so the human can verify the picker.

You cannot switch your own model — only the human can, via the model picker at dispatch. Do not attempt to.
```
