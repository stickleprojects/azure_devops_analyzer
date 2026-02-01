# Operations & Deployment

## Overview

This folder contains documentation for deploying, running, and maintaining the Repository Analysis System in production or development environments.

## Contents

- **[visualization.md](visualization.md)** — Grafana dashboards, metrics, visualization design, and dashboard setup
- **[deployment-plan.md](deployment-plan.md)** — Implementation timeline, phases, deployment checklist, and rollout strategy
- **[docker-setup.md](docker-setup.md)** — Docker configuration, building images, environment variables
- **[session-continuity.md](session-continuity.md)** — Session management, context tracking, and reproducibility for long-running analysis
- **[github-actions-tests.md](github-actions-tests.md)** — GitHub Actions CI/CD workflow and test execution
- **[feature-development-workflow.md](feature-development-workflow.md)** — Feature branch workflow and development process
- **[branch-protection-setup.md](branch-protection-setup.md)** — Branch protection rules and automated enforcement
- **[monitoring-extraction-progress.md](monitoring-extraction-progress.md)** — Monitoring extraction jobs and progress tracking

## Quick Links

| Document                     | Focus                     | For                      |
| ---------------------------- | ------------------------- | ------------------------ |
| visualization.md             | Grafana setup, dashboards | DevOps, dashboarding     |
| deployment-plan.md           | Rollout strategy, timeline | Deployment, PM          |
| docker-setup.md              | Docker configuration      | Infrastructure, setup    |
| session-continuity.md        | Context persistence       | Reproducibility, debugging |
| github-actions-tests.md      | CI/CD pipelines           | Testing, automation      |
| feature-development-workflow.md | Git workflow           | Development, code review |
| branch-protection-setup.md   | Branch protection rules   | Repository governance    |
| monitoring-extraction-progress.md | Job monitoring        | Operations, support      |

## Recommended Reading Order

1. **[deployment-plan.md](deployment-plan.md)** — Understand implementation phases and timeline
2. **[docker-setup.md](docker-setup.md)** — Set up Docker environment locally or in production
3. **[visualization.md](visualization.md)** — Configure Grafana dashboards for stakeholders
4. **[session-continuity.md](session-continuity.md)** — Ensure long-running jobs maintain state

## Key Topics

- **Docker Setup**: Building images, environment configuration, compose files
- **Grafana Dashboards**: Team Overview, Repository Overview, Security, Contributor Analytics
- **Deployment Phases**: Preparation, implementation, testing, production rollout
- **GitHub Actions**: CI/CD pipelines and automated testing
- **Development Workflow**: Feature branches, code review, pull requests
- **Branch Protection**: Rules, automation, governance

---

**Navigate to**: [Parent Docs](../) | [Strategy](../01-strategy/) | [Architecture](../02-architecture/) | [Implementation](../04-implementation/)
