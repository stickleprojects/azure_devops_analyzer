# Update-Docs Bot – Feasibility & Cost Assessment

## Document Information

| Field        | Value                          |
| ------------ | ------------------------------ |
| Last Updated | 2026-04-05                     |
| Status       | Complete                       |
| Owner        | Engineering                    |

---

## Overview

This document assesses the feasibility and ongoing cost of an automated
"update-docs bot" that audits project documentation and opens pull requests
with corrections or recommendations rather than writing directly to the main
branch.

---

## What the Bot Does

The bot is implemented as a scheduled GitHub Actions workflow
(`.github/workflows/update-docs-bot.yml`) backed by a pure-Python audit
script (`scripts/doc_audit.py`).

### Checks performed on every run

| Check | Description |
|-------|-------------|
| **README freshness** | Detects broken internal links and stale "Last Updated" markers |
| **PROGRESS.md drift** | Compares session entries against recent commit history |
| **Requirements status** | Flags items still at Draft or Not Started |
| **Plan staleness** | Identifies plans in `docs/04-implementation/` that appear complete but lack a Closed status |
| **Readability** | Flags missing headings, oversized sections, and stale date markers across all docs |

### What the bot does NOT do automatically

| Capability | Status | Reason |
|------------|--------|--------|
| Dashboard screenshots | Automated | `refresh-dashboard-screenshots.yml` workflow – spins up Grafana + Image Renderer in Docker, seeds the database from e2e fixtures, captures PNGs, and opens a PR |
| Network/architecture diagram regeneration | Automated | `refresh-mermaid-diagrams.yml` workflow – renders `.mmd` source files to SVG via `@mermaid-js/mermaid-cli` and opens a PR |
| Semantic content rewriting | Not automated | Content quality requires human review; auto-rewrite risks introducing inaccuracies |

---

## Implementation

### Components

- **`scripts/doc_audit.py`** – audit logic, ~300 lines of Python, no
  third-party dependencies (stdlib only)
- **`.github/workflows/update-docs-bot.yml`** – documentation audit workflow
  (manual `workflow_dispatch` trigger only)
- **`.github/workflows/refresh-dashboard-screenshots.yml`** – captures Grafana
  dashboard PNGs using a Docker stack seeded from e2e fixture data
- **`.github/workflows/refresh-mermaid-diagrams.yml`** – renders `.mmd` Mermaid
  source files to SVG via `@mermaid-js/mermaid-cli`

### Workflow summary

1. Run audit script, write `artifacts/doc-audit/report.md`
2. Upload report as a workflow artifact
3. If errors or warnings are found, push to a dated bot branch and open a
   pull request targeting `main`
4. PR must be reviewed and approved before merging – the bot never writes
   directly to `main`

---

## Feasibility Assessment

### Technical feasibility

| Aspect | Assessment |
|--------|------------|
| Static doc checks | ✅ Fully feasible using stdlib Python and `git log` |
| Commit-to-PROGRESS.md cross-check | ✅ Feasible; implemented via `git log` heuristics |
| Automated PR creation | ✅ Fully feasible via `gh pr create` in GitHub Actions |
| Dashboard screenshots | ✅ Implemented – `refresh-dashboard-screenshots.yml` runs fully in CI using Docker services |
| Diagram regeneration | ✅ Implemented – `refresh-mermaid-diagrams.yml` renders `.mmd` sources to SVG via `@mermaid-js/mermaid-cli` |

### Operational risk

- **False positives** – heuristic checks may flag content that is intentionally
  structured. Threshold tuning reduces noise over time.
- **Branch conflicts** – the bot branch is force-pushed on each run; old bot
  branches should be deleted after merging.
- **GitHub token scope** – the default `GITHUB_TOKEN` is sufficient; no
  personal access token is required.

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

### Screenshot automation (implemented)

Dashboard screenshots are captured by the `refresh-dashboard-screenshots.yml` workflow
(manual trigger only).

| Item | Estimate |
|------|---------|
| Docker service startup in CI | +5–10 minutes per run |
| Grafana headless screenshot tooling | Implemented |
| Mermaid diagram rendering | Implemented via `refresh-mermaid-diagrams.yml` |
| Storage for screenshot artifacts | Negligible (GitHub artifact storage) |
| **Additional annual compute cost** | **$0** (manual runs; no scheduled execution) |

---

## Recommendations

### Immediate (already implemented)

- Static documentation audit running on demand (manual `workflow_dispatch`) via GitHub Actions
- PR-based review workflow so no changes land without approval
- Dashboard screenshots via `refresh-dashboard-screenshots.yml` (Docker + Grafana Image Renderer)
- Mermaid diagram refresh via `refresh-mermaid-diagrams.yml`

### Short-term (next sprint)

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
- No database writes; no extractor or analyzer boundaries violated
- Workflow file is additive (new file in `.github/workflows/`)

---

## References

- [feature-development-workflow.md](../03-operations/feature-development-workflow.md)
- [github-actions-tests.md](../03-operations/github-actions-tests.md)
- [agents/00-documentation-standards.md](../../agents/00-documentation-standards.md)
- [scripts/doc_audit.py](../../scripts/doc_audit.py)
- [.github/workflows/update-docs-bot.yml](../../.github/workflows/update-docs-bot.yml)
