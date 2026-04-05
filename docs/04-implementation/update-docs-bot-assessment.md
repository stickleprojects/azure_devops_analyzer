# Update-Docs Bot – Implementation Reference

## Document Information

| Field        | Value                          |
| ------------ | ------------------------------ |
| Last Updated | 2026-04-05                     |
| Status       | Implemented                    |
| Owner        | Engineering                    |

---

## Overview

The update-docs bot is a fully implemented GitHub Actions workflow that keeps
project documentation up to date. It audits documentation for quality issues,
captures Grafana dashboard screenshots, and regenerates Mermaid diagrams –
opening pull requests for human review rather than writing directly to the main
branch.

---

## What the Bot Does

The bot runs as a manual GitHub Actions workflow
(`.github/workflows/update-docs-bot.yml`) with three independent parallel jobs,
each backed by dedicated scripts or tooling.

### Checks performed by the `audit` job

| Check | Description |
|-------|-------------|
| **README freshness** | Detects broken internal links and stale "Last Updated" markers |
| **PROGRESS.md drift** | Compares session entries against recent commit history |
| **Requirements status** | Flags items still at Draft or Not Started |
| **Plan staleness** | Identifies plans in `docs/04-implementation/` that appear complete but lack a Closed status |
| **Readability** | Flags missing headings, oversized sections, and stale date markers across all docs |

### Automated documentation tasks

| Capability | Job | Details |
|------------|-----|---------|
| Dashboard screenshots | `screenshots` | Spins up Grafana + Image Renderer in Docker, seeds the database from e2e fixtures, captures PNGs for all dashboards, and opens a PR |
| Mermaid diagram rendering | `mermaid` | Renders every `.mmd` source file to SVG via `@mermaid-js/mermaid-cli` and opens a PR |
| Semantic content rewriting | Not automated | Content quality requires human review; auto-rewrite risks introducing inaccuracies |

---

## Implementation

### Components

- **`scripts/doc_audit.py`** – audit logic, ~300 lines of Python, no
  third-party dependencies (stdlib only)
- **`.github/workflows/update-docs-bot.yml`** – single manual workflow with
  three parallel jobs:
  - **`audit`** – static documentation audit; opens a PR when issues are found
  - **`screenshots`** – captures Grafana dashboard PNGs using a Docker stack
    seeded from e2e fixture data
  - **`mermaid`** – renders `.mmd` Mermaid source files to SVG via
    `@mermaid-js/mermaid-cli`

### Workflow summary

1. Run audit script, write `artifacts/doc-audit/report.md`
2. Upload report as a workflow artifact
3. If errors or warnings are found, push to a dated bot branch and open a
   pull request targeting `main`
4. PR must be reviewed and approved before merging – the bot never writes
   directly to `main`

---

## Implementation Status

| Aspect | Status |
|--------|--------|
| Static doc checks | ✅ Implemented – stdlib Python + `git log` |
| Commit-to-PROGRESS.md cross-check | ✅ Implemented – `git log` heuristics |
| Automated PR creation | ✅ Implemented – `gh pr create` in GitHub Actions |
| Dashboard screenshots | ✅ Implemented – `update-docs-bot.yml` (`screenshots` job) runs fully in CI using Docker services |
| Diagram regeneration | ✅ Implemented – `update-docs-bot.yml` (`mermaid` job) renders `.mmd` sources to SVG via `@mermaid-js/mermaid-cli` |

---

## Cost Estimate

All costs are based on GitHub-hosted runners (ubuntu-latest) and the current
GitHub Actions pricing for public and private repositories.

### Compute cost

| Metric | Value |
|--------|-------|
| Estimated job duration | 3–5 minutes per run |
| Schedule | Manual (`workflow_dispatch`) only |
| Minutes per year | Only on demand |
| Free tier (public repo) | Unlimited |
| Free tier (private repo) | 2 000 minutes/month included |
| Overage rate | $0.008 per minute (ubuntu-latest) |
| **Estimated annual cost** | **$0** (manual runs only; well within free tier) |

### Maintenance cost

| Activity | Estimated effort |
|----------|-----------------|
| Initial setup | Already complete |
| Tuning false-positive thresholds | 1–2 hours/quarter |
| Adding new check types | 2–4 hours per check |
| Reviewing and acting on bot PRs | 30–60 minutes per weekly run (human time) |

### Screenshot automation

| Item | Details |
|------|---------|
| Docker service startup in CI | +5–10 minutes per run |
| Grafana headless screenshot tooling | ✅ Implemented via `update-docs-bot.yml` (`screenshots` job) |
| Mermaid diagram rendering | ✅ Implemented via `update-docs-bot.yml` (`mermaid` job) |
| Storage for screenshot artifacts | Negligible (GitHub artifact storage) |
| **Additional annual compute cost** | **$0** (manual runs; no scheduled execution) |

---

## Operational Notes

- **False positives** – heuristic checks may flag content that is intentionally structured. Threshold tuning reduces noise over time.
- **Branch conflicts** – the bot branch is force-pushed on each run; delete merged bot branches promptly to avoid confusion.
- **GitHub token scope** – the default `GITHUB_TOKEN` is sufficient; no personal access token is required.

---

## Enhancements (Next Steps)

- Add `--fix` mode to `scripts/doc_audit.py` to auto-correct trivial issues
  (e.g., updating stale "Last Updated" markers to today's date) so the bot PR
  contains ready-to-merge fixes
- Configure the `documentation` label in the repository so bot PRs are
  automatically labelled

### Medium-term (next quarter)

- Integrate with the existing `validate-documentation.sh` script to catch
  code-to-prose ratio violations
- Semantic drift detection: compare README against merged PR titles over the
  last quarter and flag features that appear in commits but not in docs

### Long-term (future)

- Semantic drift detection: compare README against merged PR titles over the
  last quarter and flag features that appear in commits but not in docs

---

## Decision Log

**Decision**: Use heuristic checks rather than LLM-based analysis  
**Rationale**: Heuristics run in seconds, cost nothing, and are fully
deterministic – easier to maintain and audit than a prompt-based approach.  
**Date**: 2026-04-05  
**Alternatives considered**: OpenAI / Copilot API (rejected: adds secret management
complexity, per-call cost, and non-determinism; LLM analysis is better reserved
for human-in-the-loop review sessions)

**Decision**: Bot opens PRs; never commits directly to `main`  
**Rationale**: Documentation changes require human judgment. The bot surfaces
issues; humans apply fixes. This matches the project's existing PR-first workflow
(Principle 4: Feature Branches Always).  
**Date**: 2026-04-05  
**Alternatives considered**: Auto-merge for trivial fixes (rejected: increases
risk of incorrect automated changes landing without review)

---

## Architecture Guardian Validation

- The bot introduces no new Python source-code dependencies
- The audit script lives in `scripts/` (utilities), not in `src/` (application
  logic) – consistent with Principle 2 (Architecture Guards Isolation)
- No database writes from the audit job; no extractor or analyzer boundaries violated
- All three jobs are contained in a single workflow file in `.github/workflows/`

---

## References

- [feature-development-workflow.md](../03-operations/feature-development-workflow.md)
- [github-actions-tests.md](../03-operations/github-actions-tests.md)
- [agents/00-documentation-standards.md](../../agents/00-documentation-standards.md)
- [scripts/doc_audit.py](../../scripts/doc_audit.py)
- [.github/workflows/update-docs-bot.yml](../../.github/workflows/update-docs-bot.yml)
