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
- [docs/03-operations/](docs/03-operations/) — deployment plan, visualization, session continuity, **critical GitHub API findings**
- [docs/04-implementation/README.md](docs/04-implementation/README.md) — implementation backlog and future work
  - [docs/04-implementation/parallelization-plan.md](docs/04-implementation/parallelization-plan.md) — multi-worker strategy and rate limiting
  - [docs/04-implementation/infrastructure-options.md](docs/04-implementation/infrastructure-options.md) — Docker Compose vs Kubernetes evaluation

### AI Agent Guides

The `agents/` directory contains comprehensive guides for AI-driven development across all stages of the SDLC:

- [00-documentation-standards.md](agents/00-documentation-standards.md) - **START HERE** - Standards for documentation and code examples
- [01-requirements-gathering.md](agents/01-requirements-gathering.md) - Requirements elicitation and documentation
- [02-architecture-and-design.md](agents/02-architecture-and-design.md) - System design and technical decisions
- [03-implementation.md](agents/03-implementation.md) - Coding best practices and patterns
- [04-testing.md](agents/04-testing.md) - Testing strategies and quality assurance
- [05-code-review.md](agents/05-code-review.md) - Code review processes and checklists
- [06-deployment-and-operations.md](agents/06-deployment-and-operations.md) - Deployment strategies and operational excellence

**Important**: All guides follow the standards in `00-documentation-standards.md`, emphasizing concepts over code.

## Using the AI Agent Guides

The AI agent guides in the `agents/` directory follow best practices for AI-driven development. Each guide is designed to be used as a reference or context document for AI assistants at different stages of development.

### How to Use the Guides

#### Typical Session
At the start of your sesssion, give a greeting to your AI engine (open the copilot window and type "good afternoon" or "hi, what shall we do today")
The agent will give you a greeting and catch you up on what you were doing and whats next priority
When you've finised  a session, tell copilot "lets wrap this session" and it will summarise the things and prompt you to commit/etc.


#### 1. **Sequential Workflow**

Follow the guides in order for new projects:

```
Requirements → Architecture → Implementation → Testing → Code Review → Deployment
```

Each stage builds upon the previous one, with clear handoff checklists to ensure nothing is missed.

#### 2. **For AI Assistants**

When working with an AI assistant (like Claude, GPT-4, etc.):

**Option A: Provide as Context**

```
"I'm implementing a new feature. Please review the implementation guide
at agents/03-implementation.md and follow those best practices."
```

**Option B: Reference Specific Sections**

```
"Review the security implementation section in the implementation guide
and check if my code follows those patterns."
```

**Option C: Use for Code Review**

```
"Use the code review checklist from agents/05-code-review.md to review
this pull request."
```

#### 3. **For Human Developers**

- **Before starting**: Read the relevant guide to understand best practices
- **During development**: Reference specific sections as needed
- **Code review**: Use checklists to ensure completeness
- **Onboarding**: Share guides with new team members

### Best Practices for AI-Assisted Development

#### When Gathering Requirements

1. Load `agents/01-requirements-gathering.md` into your AI context
2. Have the AI ask clarifying questions following the guide's patterns
3. Ensure all non-functional requirements are captured
4. Document using the provided templates

#### When Designing Architecture

1. Reference `agents/02-architecture-and-design.md`
2. Create Architecture Decision Records (ADRs) for major decisions
3. Consider trade-offs explicitly
4. Document technology choices with rationale

#### When Implementing

1. Follow clean code principles from `agents/03-implementation.md`
2. Check security patterns before writing authentication/authorization code
3. Use the anti-patterns section to avoid common mistakes
4. Write self-documenting code with meaningful names

#### When Testing

1. Follow the testing pyramid from `agents/04-testing.md`
2. Write tests before or alongside implementation
3. Use provided patterns for different test types
4. Ensure tests are fast, independent, and deterministic

#### When Reviewing Code

1. Use the comprehensive checklist from `agents/05-code-review.md`
2. Provide constructive feedback using the provided labels
3. Focus on critical security and correctness issues first
4. Acknowledge good practices in the code

#### When Deploying

1. Follow deployment strategies from `agents/06-deployment-and-operations.md`
2. Set up monitoring and observability before deploying
3. Have rollback plans ready
4. Use infrastructure as code for reproducibility

### Integration with Development Tools

#### IDE Integration

Add agent guides as workspace snippets or quick reference:

```json
// .vscode/settings.json
{
  "aiAssistant.contextFiles": [
    "agents/03-implementation.md",
    "agents/04-testing.md"
  ]
}
```

#### CI/CD Integration

Reference guides in pull request templates:

```markdown
## Code Review Checklist

- [ ] Follows implementation best practices (agents/03-implementation.md)
- [ ] Tests added per testing guide (agents/04-testing.md)
- [ ] Security checklist reviewed (agents/05-code-review.md)
```

#### Git Commit Hooks

Use guides to validate commits:

```bash
# .git/hooks/pre-commit
# Check if code follows implementation patterns
python scripts/validate_patterns.py --guide agents/03-implementation.md
```

### Example Workflow: Adding a New Feature

```bash
# 1. Requirements Phase
# AI prompt: "Using agents/01-requirements-gathering.md, help me document
# requirements for user authentication feature."

# 2. Design Phase
# AI prompt: "Following agents/02-architecture-and-design.md, create an ADR
# for choosing OAuth 2.0 vs JWT-based authentication."

# 3. Implementation Phase
# AI prompt: "Implement the authentication feature following the security
# patterns in agents/03-implementation.md."

# 4. Testing Phase
# AI prompt: "Create unit and integration tests following the patterns in
# agents/04-testing.md."

# 5. Code Review
# Review using checklist from agents/05-code-review.md

# 6. Deployment
# Deploy using strategies from agents/06-deployment-and-operations.md
```

### Customizing the Guides

These guides are templates. Adapt them to your organization:

1. **Add team-specific standards**: Include your coding conventions
2. **Update technology examples**: Replace with your tech stack
3. **Adjust checklists**: Add/remove items based on your needs
4. **Include organization policies**: Add compliance requirements
5. **Create shortcuts**: Extract frequently-used sections

### Key Principles

All agent guides follow these core principles:

- ✅ **Security-first**: Security considerations at every stage
- ✅ **Practical examples**: Real code, not just theory
- ✅ **Good vs Bad patterns**: Learn by comparison
- ✅ **Checklist-driven**: Ensure completeness
- ✅ **Stage-specific**: Focused on current phase
- ✅ **Handoff clarity**: Clear transitions between stages

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
├── sql/                    # Database schema and migrations
├── tests/                  # Unit and integration tests
├── docker/                 # Docker configurations
└── config/                 # Configuration files
```

## License

[To be determined]

## Contributing

[To be determined]
