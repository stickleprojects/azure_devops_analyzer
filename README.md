# Azure DevOps Repository Analysis System

## Overview

This system analyzes Azure DevOps repositories and stores comprehensive metrics for visualization in Grafana dashboards. It provides insights into code quality, security vulnerabilities, contributor activity, pull request patterns, and repository health.

## Key Features

- **Multi-language support**: Detects and analyzes code in various programming languages
- **Security scanning**: Identifies vulnerabilities in dependencies and code
- **Code quality analysis**: Static analysis for best practices and structural issues
- **Contributor analytics**: Tracks developer activity and patterns
- **Pull request metrics**: Analyzes PR size, quality, and review patterns
- **Branch-level analysis**: Supports per-branch metrics and comparisons
- **Incremental updates**: Efficiently refreshes data as changes occur
- **Grafana dashboards**: Rich visualizations for all metrics

## Documentation Structure

- [01-architecture.md](docs/01-architecture.md) - System architecture and component overview
- [02-data-extraction.md](docs/02-data-extraction.md) - Azure DevOps API integration details
- [03-analysis-engine.md](docs/03-analysis-engine.md) - Code analysis and metrics calculation
- [04-data-storage.md](docs/04-data-storage.md) - Database schema and storage strategy
- [05-orchestration.md](docs/05-orchestration.md) - Job scheduling and workflow management
- [06-visualization.md](docs/06-visualization.md) - Grafana dashboard configuration
- [07-implementation-plan.md](docs/07-implementation-plan.md) - Phased implementation roadmap
- [08-technology-stack.md](docs/08-technology-stack.md) - Technologies and tools used

## Quick Start

See [07-implementation-plan.md](docs/07-implementation-plan.md) for the phased implementation approach.

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
