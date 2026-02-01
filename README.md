# Multi-Platform Repository Analysis System

## Overview

This system analyzes repositories from multiple platforms (Azure DevOps and GitHub) and stores comprehensive metrics for visualization in Grafana dashboards. It provides insights into code quality, security vulnerabilities, contributor activity, pull request patterns, and repository health.

## Key Features

- **Multi-language support**: Detects and analyzes code in various programming languages
- **Dependency extraction**: Parses manifest files from 7 ecosystems (PyPI, npm, Maven, NuGet, Go, RubyGems, Cargo)
- **Security scanning**: Identifies vulnerabilities in dependencies and code
- **Organization-wide security dashboard**: Tracks vulnerabilities and EOL dependencies across all repositories with drilldown capabilities
- **Code quality analysis**: Static analysis for best practices and structural issues
- **Contributor analytics**: Tracks developer activity and patterns
- **Pull request metrics**: Analyzes PR size, quality, and review patterns
- **Branch-level analysis**: Supports per-branch metrics and comparisons
- **Incremental updates**: Efficiently refreshes data as changes occur
- **Grafana dashboards**: Rich visualizations for all metrics

## Local Repository Analysis Quickstart

Run the PowerShell helper to bootstrap the Docker stack, create `.env`, apply migrations, and start extraction:

- PowerShell (Windows/macOS/Linux): `pwsh ./Start-RepoAnalysis.ps1 -RegenerateEnv`

See [Start-RepoAnalysis.ps1](Start-RepoAnalysis.ps1#L1-L50) for parameters and examples.

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

- Azure DevOps organization access
- Personal Access Token (PAT) with appropriate permissions
- PostgreSQL 15+ with TimescaleDB
- Python 3.11+
- Grafana 10+
- RabbitMQ 3.12+

## Repository Structure

```
azure-devops-analyzer/
├── docs/                    # This documentation
├── src/
│   ├── extractors/         # Azure DevOps data extraction
│   ├── analyzers/          # Code analysis modules
│   ├── storage/            # Database models and operations
│   ├── scheduler/          # Job scheduling and tasks
│   └── utils/              # Shared utilities
├── dashboards/             # Grafana dashboard definitions
├── database/               # Database schema and migrations
├── tests/                  # Unit and integration tests
├── workers/                # Background job workers
