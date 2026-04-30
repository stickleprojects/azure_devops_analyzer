# Multi-Platform Repository Analysis System

_Last reviewed: 2026-04-30_

## Overview

This system analyzes repositories from multiple platforms (Azure DevOps and GitHub) and stores comprehensive metrics for visualization in Grafana dashboards. It provides insights into code quality, security vulnerabilities, contributor activity, pull request patterns, and repository health.

## Key Features

- **Multi-language support**: Detects and analyzes code in various programming languages
- **Dependency extraction**: Parses manifest files from 7 ecosystems (PyPI, npm, Maven, NuGet, Go, RubyGems, Cargo)
- **Security scanning**: Identifies vulnerabilities in dependencies and code
- **Dependency vulnerability & EOL dashboards**: Two Grafana dashboards — `dependency-vulnerability-portfolio` (org-wide health buckets, adoption timelines, team breakdowns) and `library-detail-deep-dive` (per-package CVE list, version usage, exposed repos). Backed by API endpoints `/api/packages/health`, `/api/packages/adoption`, `/api/packages/library/<name>/<ecosystem>`.
- **Thoughtworks Tech Radar**: Auto-generated Tech Radar publication from package adoption, CVE exposure, and EOL signals. Packages are categorised into Adopt / Trial / Assess / Hold rings across Infrastructure / Platforms / Tools / Languages & Frameworks quadrants. Ring movements (incl. `repo_count_delta` and `vulnerability_change`) are tracked publication-to-publication. Endpoints: `/api/radar` (Thoughtworks JSON format), `/api/radar/history`, `/api/radar/export` (CSV/JSON).
- **Code quality analysis**: Static analysis for best practices and structural issues
- **Contributor analytics**: Tracks developer activity and patterns
- **Pull request metrics**: Analyzes PR size, quality, and review patterns
- **Branch-level analysis**: Supports per-branch metrics and comparisons
- **Incremental updates**: Efficiently refreshes data as changes occur
- **Grafana dashboards**: Rich visualizations for all metrics

## Local Repository Analysis Quickstart

Use the helper to bootstrap the Docker stack, create `.env`, initialize the schema, and start extraction:

- Bash (macOS/Linux/Git Bash on Windows): `./Start-RepoAnalysis.sh --regenerate-env`

What happens:

1. Prompts for GitHub/Azure DevOps credentials and writes `.env`
2. Starts Docker services (TimescaleDB, RabbitMQ, workers, scheduler)
3. Initializes the database schema
4. Submits an extraction task to Celery (background mode)

To start analysis manually without the helper:

1. Copy and edit `.env` from `.env.example`
2. Resolve environment variable references: `bash ./scripts/resolve_env.sh > .env.resolved`
3. Start services: `docker compose --env-file .env.resolved up -d`
4. Submit a run: `docker compose --env-file .env.resolved run --rm scheduler python /app/scripts/submit_extraction_task.py`

How to know it is running:

- Scheduler logs show `Enqueuing task=...`
- Worker logs show tasks executing
- Flower UI at `http://localhost:5555`
- Grafana dashboards at `http://localhost:3000` (admin/admin)

See [Start-RepoAnalysis.sh](Start-RepoAnalysis.sh#L1-L50) for parameters and examples.

## Documentation Structure

### Development Progress

- **[PROGRESS.md](PROGRESS.md)** — Session-by-session development log with key findings and technical insights

### How to navigate

- [docs/README.md](docs/README.md) — entry point with role-based navigation across strategy, architecture, operations, and implementation
- [docs/01-strategy/](docs/01-strategy/) — business requirements, status, and project rules
- [docs/02-architecture/](docs/02-architecture/) — system design, stack, data flow, storage, orchestration
- [docs/03-operations/](docs/03-operations/) — deployment plan, visualization, session continuity, Docker setup
- [docs/04-implementation/README.md](docs/04-implementation/README.md) — implementation backlog and future work

### AI Agent Guides

The `agents/` directory contains comprehensive guides for AI-driven development:

- [.ai/principles.md](.ai/principles.md) - **START HERE** - 7 core development principles
- [agents/00-documentation-standards.md](agents/00-documentation-standards.md) - Documentation and code examples standards
- [agents/02a-architecture-guardian.md](agents/02a-architecture-guardian.md) - Architecture boundary validation
- [agents/04a-test-guardian.md](agents/04a-test-guardian.md) - Test integrity and contract testing
- [agents/07-session-continuity-agent.md](agents/07-session-continuity-agent.md) - Session tracking and progress

See [agents/](agents/) directory for complete guide collection.

## Session Start Guide

At the start of your session:

1. Give a greeting to your AI assistant (e.g., "good afternoon" or "hi, what's next?")
2. The agent will catch you up on prior work and show backlog priorities
3. When finished, say "let's wrap up this session" for a summary and commit prompts

## Quick Start

Start with [docs/README.md](docs/README.md) for role-based navigation, then review [docs/04-implementation/README.md](docs/04-implementation/README.md) for the current backlog and future work.

## Requirements

- Docker with Compose V2
- Bash 4.0+ for `Start-RepoAnalysis.sh`
- Azure DevOps organization access
- Personal Access Token (PAT) with appropriate permissions
- PostgreSQL 15+ with TimescaleDB
- Grafana 10+
- RabbitMQ 3.12+

## Repository Structure

```
azure-devops-analyzer/
├── docs/                    # This documentation
├── src/
│   ├── analyzers/          # Platform-agnostic analysis modules
│   ├── api/                # API-facing entry points and integration surfaces
│   ├── config/             # Runtime configuration
│   ├── database/           # Database models and storage layer
│   ├── extractors/         # GitHub and Azure DevOps data extraction
│   ├── scheduler/          # Job scheduling and task submission
│   └── workflows/          # Orchestration across extractors and analyzers
├── dashboards/             # Grafana dashboard definitions
├── database/               # Database schema and migrations
├── tests/                  # Unit and integration tests
├── workers/                # Background job workers
```
