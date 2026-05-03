# Coding-agent prompts

Ready-to-paste prompts for delegating work to GitHub Copilot agents (or equivalents). Each prompt is self-contained — assume the agent has not seen any prior conversation.

## Wave 1 (parallel — disjoint files, no merge conflicts)

| Prompt | Plan | Description |
|---|---|---|
| [wave-1a-grafana-uniform-top-link-bar.md](wave-1a-grafana-uniform-top-link-bar.md) | Plan 025 Phase 2 | Uniform 6-entry `links[]` across 11 dashboards |
| [wave-1b-tech-radar-schema-and-categorizer.md](wave-1b-tech-radar-schema-and-categorizer.md) | Plan 022 Track A | Radar schema migration + categorization engine |
| [wave-1c-property-based-identity-tests.md](wave-1c-property-based-identity-tests.md) | Plan 020 Component 1 | Hypothesis-based property tests for `get_or_create_contributor` |
| [wave-1d-extraction-health-observability.md](wave-1d-extraction-health-observability.md) | Plan 020 Component 3 | `extraction_health.py` + Prometheus emission + new dashboard |

## Wave 2 (after Wave 1 PRs merged)

Drafted on demand. Likely:

- Plan 025 Phase 3 (drill-down data links) — sequenced after Wave 1A to avoid `dashboards/*.json` merge conflicts
- Plan 022 Track B (radar workflow) — depends on Wave 1B's schema
- Plan 020 Component 2 (live-API nightly) — depends on canary secrets being provisioned manually first

## Why this folder exists

Previous Copilot agent rounds on this project have ended with the agent declaring done while CI was red, costing 2+ feedback rounds per task. Every prompt here includes a non-negotiable acceptance block requiring `gh pr checks --watch` and root-cause fixing on red. Reuse the block when drafting new prompts.
