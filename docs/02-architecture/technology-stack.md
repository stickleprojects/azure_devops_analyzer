# Technology Stack

## Overview

This document provides a comprehensive overview of all technologies, tools, and libraries used in the Repository Analysis System, which supports both Azure DevOps and GitHub platforms.

## Core Technologies

### Programming Languages

| Language | Version       | Purpose                        | Justification                                              |
| -------- | ------------- | ------------------------------ | ---------------------------------------------------------- |
| Python   | 3.11+         | Primary application language   | Rich ecosystem for data processing, good Azure SDK support |
| SQL      | PostgreSQL 15 | Database queries               | Standard for data storage and retrieval                    |
| Bash     | 4.0+          | Deployment scripts, automation | System administration and CI/CD                            |
| YAML     | 1.2           | Configuration files            | Scheduler config, CI/CD pipelines                          |

## Backend Stack

### Data Storage

#### PostgreSQL

- **Version**: 15.x
- **Purpose**: Primary relational database
- **Key Features**:
  - ACID compliance
  - Advanced indexing (B-tree, GIN, GiST)
  - Full-text search
  - JSON/JSONB support
  - Robust transaction management

#### TimescaleDB

- **Version**: 2.x
- **Purpose**: Time-series data optimization
- **Key Features**:
  - Hypertables for time-series data
  - Automatic data partitioning
  - Data compression
  - Continuous aggregates
  - Efficient time-based queries

### Python Core Libraries

#### Azure DevOps SDK

- `azure-devops`
- `msrest`
- **Purpose**: Azure DevOps REST API integration
- **Features**: Repository access, PR management, commit history

#### GitHub SDK

- `PyGithub>=2.1.0`
- **Purpose**: GitHub REST API integration
- **Features**: Repository access, PR management, commit history, reviews, comments
- **Rate Limiting**: Built-in handling for GitHub's rate limits
- **Authentication**: PAT or GitHub App authentication

#### Database Libraries

- `sqlalchemy`, `psycopg2-binary`, `alembic`

#### Data Processing

- `pandas`, `numpy`

#### HTTP and API

- `requests`, `tenacity`

## Analysis Tools

### Language Detection

#### Option 1: GitHub Linguist

- **Technology**: Ruby gem
- **Pros**: Highly accurate, GitHub-standard
- **Cons**: Ruby dependency

#### Option 2: Custom Parser

- **Technology**: Python file extension mapping
- **Pros**: No external dependencies
- **Cons**: Less accurate than linguist

### Dependency Analysis

#### Tools

- **Python**: `pip-audit`, `safety`, `pipdeptree`
- **Node.js**: `npm audit`, `yarn audit`
- **Universal**: `osv-scanner` (OSV.dev database)
- **Java**: OWASP Dependency-Check

#### OWASP Dependency-Check

- **Version**: 9.0+
- **Language**: Java
- **Purpose**: Multi-language dependency scanning

### Code Quality Analysis

#### SonarQube

- **Version**: Community Edition 10.3+
- **Purpose**: Comprehensive code quality analysis
- **Languages**: 25+ languages

#### Language-Specific Linters

**Python**:

- `pylint`, `flake8`, `bandit`, `black`, `mypy`

**JavaScript/TypeScript**:

- `eslint`, `@typescript-eslint/parser`

**Java**:

- PMD 7.0+
- SpotBugs 4.8+
- Checkstyle 10.12+

**C#**:

- Roslyn Analyzers (built into .NET SDK)
- StyleCop Analyzers

### AI/LLM Integration

#### Anthropic Claude

- `anthropic` SDK
- **Model**: claude-sonnet-4-20250514
- **Purpose**: Repository summarization
- **Use Cases**: README analysis, purpose detection

#### Alternative: OpenAI

- `openai` SDK
- **Model**: gpt-4-turbo
- **Purpose**: Same as Claude (backup option)

### Security Scanning

#### Secret Detection

- `detect-secrets`, `truffleHog`

#### Container Scanning

- `trivy`

## Orchestration Stack

### Scheduler

#### APScheduler

- **Version**: 3.10+
- **Purpose**: Job scheduling (Cron/Interval)
- **Features**:
  - Persistent job stores (SQLAlchemy)
  - Missed job execution handling

### Task Queue

#### Celery

- **Version**: 5.3+
- **Purpose**: Distributed task execution
- **Features**:
  - Distributed processing
  - Retries and error handling
  - Canvas (Chords, Chains, Groups)

### Message Queue

#### RabbitMQ

- **Version**: 3.12+
- **Purpose**: Message broker for Celery (Open Source / MPL)

#### Alternative: Valkey

- **Version**: 7.2+
- **Purpose**: Open source (BSD) drop-in replacement for Redis

## Visualization Stack

### Grafana

- **Version**: 10.2+
- **Purpose**: Dashboard and visualization
- **Features**:
  - PostgreSQL data source
  - Time-series visualization
  - Alerting
  - Variables and templating

### Alternative: Apache Superset

- **Version**: 3.0+
- **Purpose**: Alternative BI tool

## Supporting Tools

### Version Control

#### Git

- **Version**: 2.40+
- **Purpose**: Source code management

#### GitHub/GitLab

- **Purpose**: Remote repository hosting
- **Features**: CI/CD integration, issue tracking

### CI/CD

- **GitHub Actions**: For CI pipeline.
- **Azure DevOps Pipelines**: Alternative CI.

### Containerization

#### Docker

- **Version**: 24.0+
- **Purpose**: Application containerization

#### Docker Compose

- **Version**: 2.23+
- **Purpose**: Multi-container orchestration

### Kubernetes (Optional)

- **Version**: 1.28+
- **Purpose**: Production orchestration
- **Components**: Deployments, Services, ConfigMaps, Secrets

## Monitoring and Observability

### Application Monitoring

#### Prometheus

- **Version**: 2.48+
- **Purpose**: Metrics collection

#### Grafana (Metrics)

- Integrated with Prometheus for application metrics

### Logging

#### Python Logging

- Standard library logging.

#### ELK Stack (Optional)

- **Elasticsearch**: Log storage
- **Logstash**: Log processing
- **Kibana**: Log visualization

#### Alternative: Loki + Promtail

- **Loki**: Log aggregation (Grafana Labs)
- **Promtail**: Log shipper

### Error Tracking

#### Sentry

- **Purpose**: Error tracking and alerting
- **Features**: Stack traces, user context, releases

## Testing Stack

### Unit Testing

- `pytest`, `pytest-cov`, `pytest-mock`

### Integration Testing

- `pytest-postgresql`, `responses`

### Load Testing

#### Locust

- **Purpose**: Load and performance testing

#### Apache JMeter

- **Version**: 5.6+
- **Purpose**: Alternative load testing tool

## Development Tools

### Code Quality

#### Pre-commit Hooks

- `black`, `flake8`

#### IDE Support

- **VS Code**: Python extension, Docker extension
- **PyCharm**: Professional (database tools)
- **DataGrip**: Database management

### Documentation

#### Sphinx

- `sphinx`, `sphinx-rtd-theme`

#### MkDocs (Alternative)

- `mkdocs`, `mkdocs-material`

## Security Tools

### Secrets Management

#### Azure Key Vault

- `azure-keyvault-secrets`, `azure-identity`

#### Alternative: HashiCorp Vault

- **Version**: 1.15+
- **Purpose**: Secrets management

### Static Security Analysis

- `bandit`, `safety`

## Infrastructure as Code

### Terraform

- **Version**: 1.6+
- **Purpose**: Infrastructure provisioning

### Azure Resource Manager (ARM)

- **Alternative**: Native Azure IaC

### Ansible

- **Version**: 2.16+
- **Purpose**: Configuration management

## Backup and Storage

### Azure Blob Storage

- `azure-storage-blob`
- **Purpose**: Database backup storage

### Alternative: AWS S3

- `boto3`

## Performance Tools

### Database

#### pg_stat_statements

- Built-in PostgreSQL extension for query performance

#### pgAdmin

- **Version**: 4.x
- **Purpose**: Database administration

### Profiling

#### Python Profiling

- `cProfile`, `line_profiler`, `memory_profiler`

## Development Workflow Tools

### Package Management

#### pip

- **Version**: 23.3+
- **Purpose**: Python package installation

#### Poetry (Alternative)

- **Purpose**: Dependency management and packaging

### Environment Management

#### venv

- Built-in Python virtual environment

#### conda (Alternative)

- **Version**: 23.11+
- **Purpose**: Environment and package management

## Browser Support (for Grafana)

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

## Operating System Requirements

### Development

- **Windows**: 10/11 with WSL2
- **macOS**: 12+
- **Linux**: Ubuntu 22.04+, RHEL 8+, Debian 11+

### Production

- **Recommended**: Ubuntu 22.04 LTS
- **Alternative**: RHEL 8+, Amazon Linux 2

## Hardware Requirements

### Development Environment

- **CPU**: 4+ cores
- **RAM**: 16GB+
- **Storage**: 50GB+ SSD

### Production Environment

- **Application Server**: 8 cores, 16GB RAM
- **Database Server**: 8 cores, 32GB RAM
- **Storage**: 500GB+ SSD (database)

## Network Requirements

- **Outbound HTTPS (443)**: Azure DevOps API, GitHub API, OSV.dev, endoflife.date
- **Inbound**:
  - Port 3000: Grafana
  - Port 5555: Flower (Celery monitoring)
  - Port 15672: RabbitMQ management UI
  - Port 5432: PostgreSQL (internal only)

## License Considerations

### Open Source (Free)

- PostgreSQL, TimescaleDB (Apache 2.0)
- Python, most Python libraries (PSF, MIT, Apache)
- Grafana (AGPL v3)
- Celery (BSD), RabbitMQ (MPL 2.0), APScheduler (MIT)

### Commercial/Paid Options

- SonarQube (Developer/Enterprise editions)
- Claude API (usage-based pricing)
- Azure services (pay-as-you-go)

### Licensing Notes

- All core components use OSS licenses
- Optional commercial tools available for enhanced features
- Ensure compliance with AGPL for Grafana in commercial use

## Version Matrix

| Component   | Minimum | Recommended | Latest Tested |
| ----------- | ------- | ----------- | ------------- |
| Python      | 3.11    | 3.11        | 3.11.7        |
| PostgreSQL  | 15.0    | 15.5        | 15.5          |
| TimescaleDB | 2.0     | 2.13        | 2.13.1        |
| Grafana     | 10.0    | 10.2        | 10.2.3        |
| Docker      | 20.10   | 24.0        | 24.0.7        |

## Next Steps

- Review [system-architecture.md](system-architecture.md) for the architecture overview
- See [../04-implementation/README.md](../04-implementation/README.md) for current implementation planning
