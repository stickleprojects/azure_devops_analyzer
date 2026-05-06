# Implementation & Future Planning

_Last reviewed: 2026-04-30_

## Overview

This folder contains planning documents for future initiatives, architectural decisions, and scaling strategies for the Repository Analysis System.

## Contents

- **[caching-strategy.md](caching-strategy.md)** — Current caching architecture, tradeoffs, and guardrails
- **[extractor-caching-plan.md](extractor-caching-plan.md)** — Extractor cache rollout plan and repository impact
- **[file-cache-plan.md](file-cache-plan.md)** — File-based cache implementation details
- **[generated-test-data-assessment.md](generated-test-data-assessment.md)** — Assessment of generated fixture data and follow-up actions
- **[github-private-repo-access.md](github-private-repo-access.md)** — Private repository authentication approach
- **[contributor-team-allocation-strategy.md](contributor-team-allocation-strategy.md)** — Team assignment architecture
- **[integration-testing-priority-assessment.md](integration-testing-priority-assessment.md)** — Testing strategy and priorities
- **[parallelization-plan.md](parallelization-plan.md)** — Multi-worker repository processing strategy, rate limiting, scaling from 1 to 10+ workers
- **[infrastructure-options.md](infrastructure-options.md)** — Kubernetes vs Docker Compose evaluation, pros/cons, migration strategy

## Quick Links

| Document                                   | Focus                        | Status                |
| ------------------------------------------ | ---------------------------- | --------------------- |
| caching-strategy.md                        | Current cache design         | Implemented           |
| integration-testing-priority-assessment.md | Test strategy and sequencing | Reference             |
| contributor-team-allocation-strategy.md    | Team mapping architecture    | Implemented           |
| parallelization-plan.md                    | Scaling to 5-10 workers      | Active planning phase |
| infrastructure-options.md                  | Infrastructure architecture  | High-level evaluation |

## Recommended Reading Order

1. **[parallelization-plan.md](parallelization-plan.md)** — Understand the multi-worker strategy, rate limiting approach, and migration path
2. **[infrastructure-options.md](infrastructure-options.md)** — Evaluate Kubernetes vs Docker Compose, understand tradeoffs
3. **[integration-testing-priority-assessment.md](integration-testing-priority-assessment.md)** — Review the testing backlog and validation priorities

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

## Architecture Guardian

Implementation plans in this folder still have to respect the core system
boundaries:

- Extractors stay focused on platform-specific data collection
- Analyzers stay platform-agnostic and return data structures, not writes
- Database writes flow through the database layer rather than ad hoc callers
- Workflows coordinate components instead of absorbing business logic

---

## Current Implementation Guides

### Completed Features

- ✅ **File-based caching** - [file-cache-plan.md](file-cache-plan.md) & [caching-strategy.md](caching-strategy.md)
- ✅ **GitHub private repo access** - [github-private-repo-access.md](github-private-repo-access.md)
- ✅ **Contributor/team allocation** - [contributor-team-allocation-strategy.md](contributor-team-allocation-strategy.md)
- ✅ **Fixture data assessment** - [generated-test-data-assessment.md](generated-test-data-assessment.md)

### Future Planning

- 📋 **Parallelization** - [parallelization-plan.md](parallelization-plan.md) - Multi-worker strategy
- 📋 **Infrastructure scaling** - [infrastructure-options.md](infrastructure-options.md) - K8s vs Docker Compose
- 📋 **Extractor caching rollout** - [extractor-caching-plan.md](extractor-caching-plan.md) - Cache behavior and adoption

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
