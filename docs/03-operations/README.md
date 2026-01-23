# Operations & Deployment

## Overview

This folder contains documentation for deploying, running, and maintaining the Repository Analysis System in production or development environments.

## Contents

- **[visualization.md](visualization.md)** — Grafana dashboards, metrics, visualization design, and dashboard setup
- **[deployment-plan.md](deployment-plan.md)** — Implementation timeline, phases, deployment checklist, and rollout strategy
- **[session-continuity.md](session-continuity.md)** — Session management, context tracking, and reproducibility for long-running analysis
- **[github-config-env-loading.md](github-config-env-loading.md)** — Environment variable loading with indirect reference resolution
- **[github-config-refactoring.md](github-config-refactoring.md)** — GitHubExtractorConfig refactoring for centralized configuration
- **[github-private-repos-finding.md](github-private-repos-finding.md)** — ⚠️ Critical: GitHub API behavior for private repository access

## Quick Links

| Document                          | Focus                                  | For                            |
| --------------------------------- | -------------------------------------- | ------------------------------ |
| visualization.md                  | Grafana setup, dashboards              | DevOps, dashboarding           |
| deployment-plan.md                | Rollout strategy, timeline             | Deployment, project management |
| session-continuity.md             | Context persistence                    | Reproducibility, debugging     |
| github-config-env-loading.md      | Environment variable resolution        | Configuration, security        |
| github-config-refactoring.md      | Configuration centralization           | Code maintainability           |
| github-private-repos-finding.md   | ⚠️ GitHub API private repo behavior    | Critical implementation detail |

## Recommended Reading Order

1. **[deployment-plan.md](deployment-plan.md)** — Understand implementation phases and timeline
2. **[visualization.md](visualization.md)** — Set up Grafana dashboards for stakeholders
3. **[session-continuity.md](session-continuity.md)** — Ensure long-running jobs maintain state

## Key Topics

- **Grafana Dashboards**: Team Overview, Repository Overview, Security, Contributor Analytics
- **Deployment Phases**: Preparation, implementation, testing, production rollout
- **Health Checks**: Monitoring system status and data freshness
- **Maintenance**: Backups, cleanup, data retention policies
- **GitHub Configuration**: Environment loading, indirect variable resolution, centralized config
- **⚠️ Critical Finding**: GitHub API requires authenticated user endpoint for private repositories

---

**Navigate to**: [Parent Docs](../) | [Strategy](../01-strategy/) | [Architecture](../02-architecture/) | [Implementation](../04-implementation/)
