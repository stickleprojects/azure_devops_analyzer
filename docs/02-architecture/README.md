# System Architecture

## Overview

This folder contains technical architecture documentation describing how the Repository Analysis System is designed and implemented.

## Contents

- **[system-architecture.md](system-architecture.md)** — High-level architecture overview, core components, workflows, and data flow
- **[technology-stack.md](technology-stack.md)** — Complete list of technologies, versions, frameworks, and tools used
- **[data-flow.md](data-flow.md)** — How data is extracted from Azure DevOps and GitHub repositories
- **[analysis-pipeline.md](analysis-pipeline.md)** — Analysis engines, language detection, security scanning, code quality
- **[data-storage.md](data-storage.md)** — Database schema design, TimescaleDB optimization, storage patterns
- **[job-orchestration.md](job-orchestration.md)** — Scheduling with APScheduler, task distribution with Celery

## Quick Links

| Document               | Focus                     | For                                        |
| ---------------------- | ------------------------- | ------------------------------------------ |
| system-architecture.md | Overall design, workflows | System overview                            |
| technology-stack.md    | Tools and versions        | Dependency management                      |
| data-flow.md           | Extraction process        | Understanding data sources                 |
| analysis-pipeline.md   | Analysis components       | Code quality, security, language detection |
| data-storage.md        | Database schema           | Data model, persistence                    |
| job-orchestration.md   | Task management           | Background job execution                   |

## Recommended Reading Order

1. **[system-architecture.md](system-architecture.md)** — Understand the big picture (components, workflows)
2. **[data-flow.md](data-flow.md)** — See how data enters the system
3. **[data-storage.md](data-storage.md)** — Learn how data is stored
4. **[analysis-pipeline.md](analysis-pipeline.md)** — Understand what analysis happens
5. **[job-orchestration.md](job-orchestration.md)** — See how jobs are scheduled and executed
6. **[technology-stack.md](technology-stack.md)** — Reference for specific tools and versions

## Core Concepts

- **Multi-platform**: Supports Azure DevOps and GitHub simultaneously
- **Parallel Processing**: Uses Celery workers + RabbitMQ for distributed job execution
- **Time-series Database**: TimescaleDB for efficient historical data storage
- **Flexible Analysis**: Modular analysis engines for language detection, security, quality
- **Workflow Orchestration**: APScheduler for cron jobs + Celery for task queues

---

**Navigate to**: [Parent Docs](../) | [Strategy](../01-strategy/) | [Operations](../03-operations/) | [Implementation](../04-implementation/)
