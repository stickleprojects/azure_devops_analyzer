# Implementation & Future Planning

## Overview

This folder contains planning documents for future initiatives, architectural decisions, and scaling strategies for the Repository Analysis System.

## Contents

- **[parallelization-plan.md](parallelization-plan.md)** — Multi-worker repository processing strategy, rate limiting, scaling from 1 to 10+ workers
- **[infrastructure-options.md](infrastructure-options.md)** — Kubernetes vs Docker Compose evaluation, pros/cons, migration strategy

## Quick Links

| Document                  | Focus                       | Status                |
| ------------------------- | --------------------------- | --------------------- |
| parallelization-plan.md   | Scaling to 5-10 workers     | Active planning phase |
| infrastructure-options.md | Infrastructure architecture | High-level evaluation |

## Recommended Reading Order

1. **[parallelization-plan.md](parallelization-plan.md)** — Understand the multi-worker strategy, rate limiting approach, and migration path
2. **[infrastructure-options.md](infrastructure-options.md)** — Evaluate Kubernetes vs Docker Compose, understand tradeoffs

## Key Topics

### Parallelization Plan

- **From Sequential to Parallel**: Current single-worker → Proposed 5-10 worker architecture
- **Rate Limiting**: Redis-based coordination across workers to respect GitHub/Azure DevOps API limits
- **Celery Configuration**: Task routing, worker pools, autoscaling
- **Risk Mitigation**: Handling rate limits, database connections, zombie tasks

### Infrastructure Options

- **Docker Compose** (Current): Simpler setup, limited scaling
- **Kubernetes** (Future): Better scalability, auto-healing, rolling updates
- **Hybrid Approach**: Docker Compose for development/testing, Kubernetes for production

---

## Open Issues & Action Items (Prioritized)

- **Critical**: Fix GitHub repo selection and visibility handling to include org/user private repos; add pagination and rate-limit/backoff to repository listing. [src/extractors/github/extractor.py](../../src/extractors/github/extractor.py#L55-L193)
- **Major**: Add pagination/backoff for commits and pull requests to avoid truncation and rate-limit failures. [src/extractors/github/extractor.py](../../src/extractors/github/extractor.py#L139-L193)
- **Major**: Improve workflow transaction model (single unit-of-work per repo) and structured logging with org/repo context; avoid separate sessions for scan decision vs writes. [src/workflows/github_analysis.py](../../src/workflows/github_analysis.py#L63-L206)
- **Major**: Implement real maintenance tasks or unschedule stubs (cleanup/backup) to avoid false confidence. [src/scheduler/tasks.py](../../src/scheduler/tasks.py#L29-L61)
- **Major**: Harden contributor identity (avoid collapsing users on empty/noreply emails; separate author/committer). [src/database/storage.py](../../src/database/storage.py#L118-L178)
- **Major**: Build and wire a code-quality analyzer to populate quality/tech-debt metrics expected by models/dashboards. [src/analyzers](../../src/analyzers) [src/database/models/quality.py](../../src/database/models/quality.py)
- **Minor**: Add input validation and ensure no secret leakage in client logs/config. [src/extractors/github/client.py](../../src/extractors/github/client.py) [src/extractors/azure_devops/client.py](../../src/extractors/azure_devops/client.py)
- **Minor**: Expand tests beyond import checks—cover workflow happy/error paths, pagination/backoff, dependency parsing per ecosystem, and storage idempotency. [tests](../../tests)

## Implementation Phases

### Phase 1: Parallelization (Next 2-4 weeks)

- Add Redis for rate limit coordination
- Implement repository-level task distribution
- Deploy 5-10 Celery workers with Docker Compose

### Phase 2: Infrastructure Upgrade (4-8 weeks)

- Evaluate Kubernetes requirements
- Assess cost vs Docker Compose
- Plan managed services (AKS, managed PostgreSQL)

---

**Navigate to**: [Parent Docs](../) | [Strategy](../01-strategy/) | [Architecture](../02-architecture/) | [Operations](../03-operations/)
