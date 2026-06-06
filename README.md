# Multi-Platform Repository Analysis System

<!-- LOGO PLACEHOLDER: replace with <img src="docs/images/logo.png" alt="logo" width="200"> -->

_Last reviewed: 2026-06-06_

Analyzes repositories from Azure DevOps and GitHub, stores comprehensive metrics, and visualizes them in Grafana dashboards. Covers code quality, security vulnerabilities, contributor activity, pull request patterns, and repository health.

## Key Features

- **Multi-language support** — detects and analyzes code across multiple languages
- **Dependency extraction** — parses manifests from 7 ecosystems (PyPI, npm, Maven, NuGet, Go, RubyGems, Cargo)
- **Security scanning** — identifies vulnerabilities in dependencies and code
- **Vulnerability & EOL dashboards** — org-wide health buckets, per-package CVE lists, version usage, and exposed repos
- **Thoughtworks Tech Radar** — auto-generated from package adoption, CVE exposure, and EOL signals; ring movements tracked publication-to-publication
- **Code quality analysis** — static analysis for best practices and structural issues
- **Contributor analytics** — tracks developer activity and patterns
- **Pull request metrics** — analyzes PR size, quality, and review patterns
- **Extraction health observability** — named database invariants checked after every extraction; violations surfaced in the Extraction Health Grafana dashboard

## Requirements

- Docker with Compose V2
- Bash 4.0+ for `Start-RepoAnalysis.sh`
- Azure DevOps organization access with a Personal Access Token (PAT)
- PostgreSQL 15+ with TimescaleDB
- Grafana 10+
- RabbitMQ 3.12+

## Quick Start

```bash
./Start-RepoAnalysis.sh --regenerate-env
```

This bootstraps the full stack and starts extraction. See [docs/03-operations/quickstart.md](docs/03-operations/quickstart.md) for the detailed walkthrough, first-launch checklist, and troubleshooting.

## Repository Structure

```
azure-devops-analyzer/
├── docs/                    # Documentation (see docs/README.md for navigation)
├── src/
│   ├── analyzers/          # Platform-agnostic analysis modules
│   ├── api/                # Flask API entry points
│   ├── config/             # Runtime configuration
│   ├── database/           # Database models and storage layer
│   ├── extractors/         # GitHub and Azure DevOps data extraction
│   ├── scheduler/          # Job scheduling and task submission
│   ├── utils/              # Cross-cutting utilities (health checks, metrics)
│   └── workflows/          # Orchestration across extractors and analyzers
├── web/
│   └── admin-ui/           # React + Vite admin UI (served on :8080)
├── dashboards/             # Grafana dashboard JSON definitions
├── database/
│   ├── migrations/         # Numbered SQL migrations (apply in order)
│   └── views.sql           # All reporting views (sourced by contract tests)
├── tests/
│   ├── unit/               # Unit tests (no DB, no network)
│   ├── contract/
│   │   ├── database/       # View contract tests (require test DB)
│   │   ├── integration/    # Pipeline e2e tests (fixture- or live-API-backed)
│   │   └── api/            # Flask API contract tests
│   └── fixtures/
│       ├── scenarios/
│       │   ├── generated/  # 27 JSON fixture scenarios (auto-generated)
│       │   └── adversarial/# 10 edge-case scenarios (hand-crafted)
│       └── fixture_extractor.py  # Fake RepositoryExtractor backed by JSON
├── workers/                # Celery worker entrypoints
└── scripts/                # Run-tests, validate-docs, resolve-env helpers
```

## Documentation

- [docs/README.md](docs/README.md) — role-based navigation across all docs
- [docs/01-strategy/](docs/01-strategy/) — business requirements, status, and project rules
- [docs/02-architecture/](docs/02-architecture/) — system design, stack, data flow, storage, orchestration
- [docs/03-operations/](docs/03-operations/) — quickstart, developer guide, deployment, Docker setup, extraction health
- [docs/04-implementation/README.md](docs/04-implementation/README.md) — implementation backlog and future work

### AI Agent Guides

- [.ai/principles.md](.ai/principles.md) — 7 core development principles
- [agents/02a-architecture-guardian.md](agents/02a-architecture-guardian.md) — architecture boundary validation
- [agents/04a-test-guardian.md](agents/04a-test-guardian.md) — test integrity and contract testing
- [agents/07-session-continuity-agent.md](agents/07-session-continuity-agent.md) — session tracking and progress
