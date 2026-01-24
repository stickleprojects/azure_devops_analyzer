# Docker Setup for Azure DevOps Analyzer

## Overview

The Docker configuration supports both **GitHub** and **Azure DevOps** repository extraction with the new FR-2 language detection and technology stack detection features.

## System Dependencies

The main Dockerfile now includes all necessary build tools for the Azure DevOps SDK:

- `gcc`, `g++`, `make` - C/C++ compilers and build tools (required for Azure SDK)
- `libpq-dev` - PostgreSQL client library
- `libffi-dev` - Foreign Function Interface (Azure SDK requirement)
- `libssl-dev` - OpenSSL development files (TLS/SSL support)
- `python3-dev` - Python development headers
- `git` - Version control (for potential dependencies)

## Building Docker Images

### Build Main Application Image
```bash
docker build -t analyzer:latest .
```

### Build with Docker Compose
```bash
# Development setup with all services
docker compose up --build

# Test environment (isolated)
docker compose -f docker-compose.test.yml up --build

# Run tests
./scripts/run-tests-docker.sh
```

## Environment Variables Required

### Azure DevOps Configuration (for both real and test runs)
```env
AZURE_DEVOPS_ORG_URL=https://dev.azure.com/your-org
AZURE_DEVOPS_PAT=your-personal-access-token
AZURE_DEVOPS_ORG_NAME=your-org-name
```

### GitHub Configuration (for both real and test runs)
```env
GITHUB_TOKEN=github_pat_xxxx...
GITHUB_ORG=your-github-org
GITHUB_USER=your-github-username
```

### Database Configuration
```env
POSTGRES_USER=analyzer_user
POSTGRES_PASSWORD=secure_password
POSTGRES_DB=analyzer
POSTGRES_HOST=timescaledb
POSTGRES_PORT=5432
```

### Message Broker Configuration
```env
RABBITMQ_DEFAULT_USER=guest
RABBITMQ_DEFAULT_PASS=guest
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
CELERY_BROKER_URL=amqp://guest:guest@rabbitmq:5672//
```

## Services in docker-compose.yml

| Service | Purpose | Supports |
|---------|---------|----------|
| **timescaledb** | Database (PostgreSQL + TimescaleDB) | Language time-series, all data |
| **db-migrations** | Schema initialization | Runs at startup |
| **rabbitmq** | Message broker for Celery | Task distribution |
| **scheduler** | APScheduler main process | Both GitHub & Azure DevOps extraction |
| **celery-worker** | Task execution | GitHub & Azure DevOps jobs |
| **celery-beat** | Periodic task scheduler | Job scheduling |
| **flower** | Celery monitoring | Real-time task monitoring |
| **grafana** | Visualization dashboards | Metrics and analytics |

## Running Extraction Workflows

### GitHub Only
```bash
export GITHUB_TOKEN=your_token
export GITHUB_ORG=your-org
docker compose up scheduler celery-worker
```

### Azure DevOps Only
```bash
export AZURE_DEVOPS_ORG_URL=https://dev.azure.com/your-org
export AZURE_DEVOPS_PAT=your-token
export AZURE_DEVOPS_ORG_NAME=your-org-name
docker compose up scheduler celery-worker
```

### Both Platforms
```bash
# Set all env vars above
docker compose up scheduler celery-worker
```

## Running Integration Tests with Docker

### Standard Tests (excludes live API calls)
```bash
./scripts/run-tests-docker.sh
```

This uses `docker-compose.test.yml` which:
- Creates isolated test database
- Runs migrations automatically
- Executes tests in container
- Cleans up resources after completion

### Test with Azure DevOps Support
```bash
export AZURE_DEVOPS_ORG_URL=https://dev.azure.com/test-org
export AZURE_DEVOPS_PAT=test-token
export AZURE_DEVOPS_ORG_NAME=test-org-name
./scripts/run-tests-docker.sh
```

## Troubleshooting

### Build Fails - Missing Build Tools
```
error: Microsoft Visual C++ 14.0 is required
```
**Solution:** Docker build includes all necessary build tools. If using local Python, see SETUP_INSTRUCTIONS.md

### Azure SDK Import Error
```
ModuleNotFoundError: No module named 'azure'
```
**Solution:** Build image includes azure-devops>=7.1.0b4. Ensure `pip install -r requirements.txt` runs during build.

### Database Connection Failed
```
psycopg2.OperationalError: could not connect to server
```
**Solution:** 
1. Check `timescaledb` service is running: `docker ps | grep timescaledb`
2. Verify `POSTGRES_HOST` is set to `timescaledb` (not localhost in containers)
3. Wait for health check: `docker logs analyzer-timescaledb | grep "ready to accept"`

### Tests Fail in Docker but Pass Locally
**Possible causes:**
- Environment variables not propagated (check docker-compose.test.yml)
- Database schema not applied (check test-migrations service)
- Network isolation issues (verify services on same network)

## Performance Notes

- **Database**: TimescaleDB optimized for time-series (language statistics)
- **Concurrency**: Celery worker default 4 processes (configurable via `CELERY_WORKER_CONCURRENCY`)
- **Caching**: Docker layer caching optimized (requirements.txt cached separately)
- **Volumes**: Read-only mounts for immutability, reduces accidental changes

## Next Steps

1. **Set environment variables** in `.env` file
2. **Run full stack**: `docker compose up`
3. **Monitor jobs**: Visit http://localhost:5555 (Flower)
4. **View dashboards**: Visit http://localhost:3000 (Grafana)
5. **Check logs**: `docker compose logs -f scheduler`

## See Also

- [README.md](README.md) - Project overview
- [SETUP_INSTRUCTIONS.md](SETUP_INSTRUCTIONS.md) - Local machine setup
- [docs/03-operations/deployment-plan.md](docs/03-operations/deployment-plan.md) - Deployment guide
