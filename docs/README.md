# Documentation Navigator

Welcome to the **Repository Analysis System** documentation. This folder contains strategic, architectural, operational, and implementation guidance organized for easy navigation.

## Quick Navigation

### [PROGRESS.md](../PROGRESS.md) — Development Progress Log

_Session-by-session log of development activities, key findings, and technical insights_

### [01-strategy/](01-strategy/) — Business & Planning

_For understanding what we're building and why_

- [requirements.md](01-strategy/requirements.md) — Requirements, acceptance criteria, and implementation status in one document
- [project-rules.md](01-strategy/project-rules.md) — Guidelines for documentation, coding, and architecture

**Start here if you're**: Product owner, new to the project, need to understand objectives

---

### 🏗️ [02-architecture/](02-architecture/) — System Design

_For understanding how the system works_

- [architecture/](architecture/) — LikeC4 architecture-as-code diagrams (System Context + Containers, C4 Level 1 & 2)
- [system-architecture.md](02-architecture/system-architecture.md) — High-level architecture, components, workflows
- [technology-stack.md](02-architecture/technology-stack.md) — Tools, libraries, frameworks, versions
- [data-flow.md](02-architecture/data-flow.md) — Data extraction from repositories (Azure DevOps, GitHub)
- [analysis-pipeline.md](02-architecture/analysis-pipeline.md) — Analysis engines, language detection, security scanning
- [data-storage.md](02-architecture/data-storage.md) — Database schema, TimescaleDB design, storage patterns
- [job-orchestration.md](02-architecture/job-orchestration.md) — APScheduler, Celery, task management

**Start here if you're**: Developer, architect, need to understand system design

---

### ⚙️ [03-operations/](03-operations/) — Deployment & Runtime

_For getting the system running and maintaining it_

- [visualization.md](03-operations/visualization.md) — Grafana dashboards, metrics, visualization design
- [deployment-plan.md](03-operations/deployment-plan.md) — Implementation timeline, phases, checklist
- [docker-setup.md](03-operations/docker-setup.md) — Docker environment setup and service lifecycle
- [github-actions-tests.md](03-operations/github-actions-tests.md) — CI test execution and parity notes
- [monitoring-extraction-progress.md](03-operations/monitoring-extraction-progress.md) — Extraction monitoring and troubleshooting
- [session-continuity.md](03-operations/session-continuity.md) — Session management, context tracking, reproducibility
- [feature-development-workflow.md](03-operations/feature-development-workflow.md) — Development process and PR workflow
- [branch-protection-setup.md](03-operations/branch-protection-setup.md) — Branch protection configuration

**Code Quality & Architecture**:

- [Architecture Guardian](../agents/02a-architecture-guardian.md) — Automatic architecture protection
- [Test Guardian](../agents/04a-test-guardian.md) — Automatic test quality enforcement

**Start here if you're**: DevOps engineer, system operator, deploying to production

---

### 🚀 [04-implementation/](04-implementation/) — Future Work & Decisions

_For planning what comes next and evaluating options_

- [parallelization-plan.md](04-implementation/parallelization-plan.md) — Multi-worker strategy, rate limiting, scaling
- [infrastructure-options.md](04-implementation/infrastructure-options.md) — Kubernetes vs Docker Compose evaluation, pros/cons
- [integration-testing-priority-assessment.md](04-implementation/integration-testing-priority-assessment.md) — Testing strategy and priorities
- [caching-strategy.md](04-implementation/caching-strategy.md) — Current caching design and tradeoffs
- [extractor-caching-plan.md](04-implementation/extractor-caching-plan.md) — Extractor cache implementation plan
- [contributor-team-allocation-strategy.md](04-implementation/contributor-team-allocation-strategy.md) — Team assignment architecture

**Start here if you're**: Planning next phase, evaluating infrastructure options, scaling decisions

---

### 🤖 [AI Patterns & Tools](../.ai/patterns/) — Development Automation

_For leveraging AI-powered code generation and development patterns_

- [ollama-fixture-and-code-generation.md](../.ai/patterns/ollama-fixture-and-code-generation.md) — Local LLM-based code generation pattern
  - Generate test fixtures, utilities, and boilerplate code
  - Example workflows are documented in `scripts/README.md`
  - Uses Ollama with Docker for reproducible, local AI assistance

**Prompts** (`.ai/ollama-prompts/`):

- `fixture-repo-seeds.md` — Seed generator for config-driven scenarios
- `fixture-repo-enrichment.md` — Per-repo enrichment (adds commits/PRs)
- `fixture-extractor.md` — FixtureExtractor class generation
- `fixture-factories.md` — Test data factory functions
- `repo-snapshot.md` — Live repo snapshot capture
- `canary-verification.md` — Post-scan verification script

**Start here if you're**: Setting up test fixtures, automating code generation, creating test data

---

## Document Types

| Type             | Purpose                        | Example                                            |
| ---------------- | ------------------------------ | -------------------------------------------------- |
| **Requirements** | What the system must do        | requirements.md                                    |
| **Architecture** | How the system is designed     | system-architecture.md                             |
| **Design**       | Technical details              | data-storage.md, analysis-pipeline.md              |
| **Operations**   | How to run and maintain it     | deployment-plan.md, visualization.md               |
| **Planning**     | Future direction and decisions | parallelization-plan.md, infrastructure-options.md |
| **Guidelines**   | How to work on the project     | project-rules.md                                   |

---

## Key Concepts

- **Repository Analysis System**: Automated extraction and analysis of code repositories across Azure DevOps and GitHub
- **Multi-platform**: Supports both Azure DevOps and GitHub with consistent data model
- **Time-series Data**: Uses TimescaleDB for efficient historical analysis
- **Parallel Processing**: Celery + RabbitMQ for distributed job execution
- **Dashboards**: Grafana for visualization and reporting

---

## Recommended Reading Order

### For Product / Leadership

1. [requirements.md](01-strategy/requirements.md) — Understand objectives and see current progress
2. [visualization.md](03-operations/visualization.md) — View what's available to users

### For Engineers / Architects

1. [system-architecture.md](02-architecture/system-architecture.md) — Understand design
2. [technology-stack.md](02-architecture/technology-stack.md) — Know what we're using
3. [data-storage.md](02-architecture/data-storage.md) — Learn data model
4. [analysis-pipeline.md](02-architecture/analysis-pipeline.md) — See analysis components
5. [project-rules.md](01-strategy/project-rules.md) — Follow coding standards

### For DevOps / Operations

1. [deployment-plan.md](03-operations/deployment-plan.md) — Understand setup
2. [system-architecture.md](02-architecture/system-architecture.md) — Know services
3. [visualization.md](03-operations/visualization.md) — Configure dashboards
4. [infrastructure-options.md](04-implementation/infrastructure-options.md) — Plan scaling

---

## Related Files

- **[scripts/README.md](../scripts/README.md)** — Script entry points and Docker-first command reference
- **[requirements.txt](../requirements.txt)** — Python dependencies
- **[docker-compose.yml](../docker-compose.yml)** — Local development stack
- **[src/](../src/)** — Application code

---

## Documentation Maintenance

Use the repository validator before committing documentation changes:

- Validate the docs tree: `bash scripts/validate-documentation.sh docs`
- Validate a single file: `bash scripts/validate-documentation.sh docs/path/to/file.md`

This validator enforces documentation standards from
`agents/00-documentation-standards.md` and helps catch code-heavy docs early.

---

## Getting Help

- **Lost?** Start with your role above and read in order
- **Need quick info?** Check [scripts/README.md](../scripts/README.md)
- **Looking for specific feature?** Use [requirements.md](01-strategy/requirements.md)
- **Want to understand a component?** Navigate to [02-architecture/](02-architecture/)

---

**Last Updated**: 2026-04-05
**Organized for**: Easy navigation and discovery
