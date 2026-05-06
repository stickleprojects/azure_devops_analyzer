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

## Wave 2 (drafting on demand)

- **Plan 020 Component 2** (live-API nightly monitoring) — ✅ merged 2026-05-03 in [PR #90](https://github.com/stickleprojects/azure_devops_analyzer/pull/90). Carved out of Wave 1 because it required provisioning live API tokens manually. Plan 020 is now fully complete.
- **Plan 025 Phase 3** (drill-down data links) — ready to draft; sequenced after Wave 1A to avoid `dashboards/*.json` merge conflicts. ~12 specific `fieldConfig.overrides[]` edits enumerated in `.ai/plans/025-bespoke-admin-and-navigation-ui.md`.
- **Plan 022 Track B** (radar publication workflow) — ready to draft; depends on the schema landed in PR #86.
- **Plan 022 Track C** (radar API endpoints `/api/radar`, `/api/radar/history`, `/api/radar/export`) — ready to draft; depends on schema (PR #86) and ideally Track B.
- **Plan 025 Phase 1** (React + Vite + TS admin MVP at `web/admin-ui/`) — sequenced after Phases 2+3 per Theme E.2's 80/20 finding.

## Why this folder exists

Previous Copilot agent rounds on this project have ended with the agent declaring done while CI was red, costing 2+ feedback rounds per task. Every prompt here includes a non-negotiable acceptance block requiring `gh pr checks --watch` and root-cause fixing on red. Reuse the block when drafting new prompts.
