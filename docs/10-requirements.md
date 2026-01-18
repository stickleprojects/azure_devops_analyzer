# Requirements Documentation

## Overview

This document tracks all dependencies for the Repository Analysis System (supporting Azure DevOps and GitHub), including Python packages, system requirements, and external services.

## Python Dependencies

All Python dependencies are defined in [requirements.txt](../requirements.txt). The file is organized by category for easy maintenance.

### Core Categories

| Category | Key Packages | Purpose |
|----------|--------------|---------|
| Azure DevOps | `azure-devops`, `azure-identity`, `azure-keyvault-secrets` | API integration and secrets management |
| GitHub | `PyGithub` | GitHub API integration |
| Database | `sqlalchemy`, `psycopg2-binary`, `alembic` | ORM, PostgreSQL driver, migrations |
| Task Queue | `celery`, `apscheduler`, `flower` | Distributed tasks and scheduling |
| Data Processing | `pandas`, `numpy` | Data manipulation and analysis |
| HTTP & API | `requests`, `tenacity`, `httpx` | API calls with retry logic |
| AI/LLM | `anthropic`, `openai` | Repository summarization |
| Code Analysis | `pylint`, `bandit`, `safety` | Static analysis and security scanning |
| Configuration | `pyyaml`, `python-dotenv`, `pydantic` | Config management and validation |
| Monitoring | `structlog`, `sentry-sdk` | Logging and error tracking |
| Testing | `pytest`, `pytest-cov`, `pytest-mock` | Test framework and coverage |
| Dev Tools | `black`, `flake8`, `mypy`, `pre-commit` | Code formatting and linting |

### Version Constraints

- **Minimum Python**: 3.11+
- **Pinning Strategy**: Minimum versions specified with `>=` to allow compatible updates
- **Security Updates**: Run `pip-audit` weekly to check for vulnerabilities

## System Requirements

### Runtime Dependencies

| Component | Version | Installation |
|-----------|---------|--------------|
| Python | 3.11+ | `apt install python3.11` or pyenv |
| PostgreSQL | 15+ | `apt install postgresql-15` |
| TimescaleDB | 2.x | [TimescaleDB install guide](https://docs.timescale.com/install/latest/) |
| RabbitMQ | 3.12+ | `apt install rabbitmq-server` |
| Git | 2.40+ | `apt install git` |

### Optional Dependencies

| Component | Version | Purpose |
|-----------|---------|---------|
| Docker | 24.0+ | Containerized deployment |
| SonarQube | 10.3+ | Code quality analysis |
| Grafana | 10.2+ | Visualization dashboards |
| Ruby | 3.0+ | GitHub Linguist (language detection) |

## External Services

### Required APIs

| Service | Purpose | Authentication |
|---------|---------|----------------|
| Azure DevOps | Repository data extraction | Personal Access Token (PAT) |
| GitHub | Repository data extraction | Personal Access Token or GitHub App |
| Azure Key Vault | Secrets management | Azure AD / Managed Identity |
| Azure Blob Storage | Database backups | Connection string |

### Optional APIs

| Service | Purpose | Authentication |
|---------|---------|----------------|
| OSV.dev | Vulnerability scanning | None (public API) |
| endoflife.date | EOL detection | None (public API) |
| Anthropic Claude | Repository summarization | API key |
| OpenAI GPT-4 | Repository summarization (alternative) | API key |

## Environment Variables

Required environment variables for the application:

```
# Database
POSTGRES_USER=analyzer
POSTGRES_PASSWORD=<secure-password>
POSTGRES_DB=devops_analyzer
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Message Broker
RABBITMQ_DEFAULT_USER=analyzer
RABBITMQ_DEFAULT_PASS=<secure-password>
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
CELERY_BROKER_URL=amqp://analyzer:<password>@localhost:5672//

# Azure DevOps
AZURE_DEVOPS_ORG_URL=https://dev.azure.com/your-org
AZURE_DEVOPS_PAT=<personal-access-token>

# GitHub
GITHUB_TOKEN=<personal-access-token>
GITHUB_ORG=<organization-name>
GITHUB_USER=<username>

# Optional: AI Services
ANTHROPIC_API_KEY=<api-key>
OPENAI_API_KEY=<api-key>

# Optional: Monitoring
SENTRY_DSN=<sentry-dsn>
```

See [.env.example](../.env.example) for a complete template.

## Maintenance

### Updating Dependencies

```bash
# Check for outdated packages
pip list --outdated

# Check for security vulnerabilities
pip-audit

# Update a specific package
pip install --upgrade <package-name>

# Regenerate requirements with current versions
pip freeze > requirements-lock.txt
```

### Dependency Audit Schedule

| Frequency | Action |
|-----------|--------|
| Weekly | Run `pip-audit` for security vulnerabilities |
| Monthly | Review and update minor versions |
| Quarterly | Evaluate major version upgrades |

### Adding New Dependencies

When adding a new dependency:

1. Add to the appropriate category in `requirements.txt`
2. Specify minimum version with `>=`
3. Update this document's category table
4. Test with `pip install -r requirements.txt`
5. Run the test suite to verify compatibility

## Checklist

- [ ] Python 3.11+ installed
- [ ] PostgreSQL 15+ with TimescaleDB extension
- [ ] RabbitMQ 3.12+ running
- [ ] All Python dependencies installed (`pip install -r requirements.txt`)
- [ ] Environment variables configured (copy `.env.example` to `.env`)
- [ ] Azure DevOps PAT created with required scopes (if using Azure DevOps)
- [ ] GitHub token created with required scopes (if using GitHub)
- [ ] Database schema applied (`database/schema.sql`)

## Further Reading

- [pip Documentation](https://pip.pypa.io/en/stable/)
- [pip-audit for Security Scanning](https://pypi.org/project/pip-audit/)
- [Python Packaging User Guide](https://packaging.python.org/)
- [Dependabot for Automated Updates](https://docs.github.com/en/code-security/dependabot)

## Next Steps

- See [07-implementation-plan.md](07-implementation-plan.md) for setup sequence
- Review [08-technology-stack.md](08-technology-stack.md) for technology details
