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
| Dashboard screenshots | Not automated | Requires a running Docker/Grafana stack; not feasible in a standard CI runner without significant setup time and infrastructure cost |
| Network/architecture diagram regeneration | Not automated | Diagrams are maintained as Mermaid or image assets; regeneration requires human judgment about accuracy |
| Semantic content rewriting | Not automated | Content quality requires human review; auto-rewrite risks introducing inaccuracies |

---

## Implementation

### Components

- **`scripts/doc_audit.py`** – audit logic, ~300 lines of Python, no
  third-party dependencies (stdlib only)
- **`.github/workflows/update-docs-bot.yml`** – GitHub Actions workflow
  (runs on schedule + `workflow_dispatch`)

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
| Dashboard screenshots | ⚠️ Feasible but costly – needs running Docker services in CI |
| Diagram regeneration | ⚠️ Feasible for Mermaid diagrams; rendered images require additional tooling |

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
| Schedule | Weekly (52 runs per year) |
| Minutes per year | ~260 minutes |
| Free tier (public repo) | Unlimited |
| Free tier (private repo) | 2 000 minutes/month included |
| Overage rate | $0.008 per minute (ubuntu-latest) |
| **Estimated annual cost** | **$0** (well within free tier) |

### Maintenance cost

| Activity | Estimated effort |
|----------|-----------------|
| Initial setup | Already complete |
| Tuning false-positive thresholds | 1–2 hours/quarter |
| Adding new check types | 2–4 hours per check |
| Reviewing and acting on bot PRs | 30–60 minutes per weekly run (human time) |

### Screenshot automation (optional enhancement)

If dashboard screenshots are added as a future enhancement:

| Item | Estimate |
|------|---------|
| Docker service startup in CI | +5–10 minutes per run |
| Grafana headless screenshot tooling | 4–8 hours of setup |
| Additional runner minutes per year | ~520 extra minutes |
| Storage for screenshot artifacts | Negligible (GitHub artifact storage) |
| **Additional annual compute cost** | **< $5** (still within free tier for most repos) |

---

## Recommendations

### Immediate (already implemented)

- Static documentation audit running weekly via GitHub Actions
- PR-based review workflow so no changes land without approval

### Short-term (next sprint)

- Add `--fix` mode to `scripts/doc_audit.py` to auto-correct trivial issues
  (e.g., updating stale "Last Updated" markers to today's date) so the bot PR
  contains ready-to-merge fixes
- Configure the `documentation` label in the repository so bot PRs are
  automatically labelled

### Medium-term (next quarter)

- Add Mermaid diagram regeneration: parse `docker-compose.yml` service
  definitions and regenerate the architecture diagram in `docs/02-architecture/`
- Integrate with the existing `validate-documentation.sh` script to catch
  code-to-prose ratio violations

### Long-term (future)

- Dashboard screenshots via headless Grafana in Docker: start the stack,
  wait for Grafana to be healthy, use the Grafana HTTP API to render panel
  PNGs, commit them into `docs/images/`
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
