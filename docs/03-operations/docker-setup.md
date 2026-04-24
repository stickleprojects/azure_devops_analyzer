# Docker Setup for Azure DevOps Analyzer

## Overview

This guide explains how to run the platform analysis stack in Docker for both GitHub and Azure DevOps workflows.

## What Docker Provides

- Reproducible runtime for scheduler, workers, and supporting services
- Isolated test execution aligned with CI behavior
- A shared local environment for dashboards and task monitoring

## Required Build Dependencies

The application image includes native build and runtime dependencies required by core Python packages and SDK clients.

- gcc, g++, make
- libpq-dev
- postgresql-client (provides `psql` for in-container DB scripts such as `scripts/verify-extraction.sh`)
- libffi-dev
- libssl-dev
- python3-dev
- git

## Build and Start

Use one of these command paths:

- Build image directly: docker build -t analyzer:latest .
- Start full dev stack: docker compose up --build
- Start isolated test stack: docker compose -f docker-compose.test.yml up --build
- Run Dockerized tests: ./scripts/run-tests-docker.sh

## Environment Configuration

Define values in .env before starting services.

### Azure DevOps

- AZURE_DEVOPS_ORG_URL
- AZURE_DEVOPS_PAT
- AZURE_DEVOPS_ORG_NAME

### GitHub

- GITHUB_TOKEN
- GITHUB_ORG
- GITHUB_USER

### Database

- POSTGRES_USER
- POSTGRES_PASSWORD
- POSTGRES_DB
- POSTGRES_HOST
- POSTGRES_PORT

### Broker

- RABBITMQ_DEFAULT_USER
- RABBITMQ_DEFAULT_PASS
- RABBITMQ_HOST
- RABBITMQ_PORT
- CELERY_BROKER_URL

### Extractor Cache

- EXTRACTOR_FILE_CACHE_ENABLED
- EXTRACTOR_FILE_CACHE_PATH

## Service Roles

| Service       | Role                                   |
| ------------- | -------------------------------------- |
| timescaledb   | PostgreSQL plus TimescaleDB storage    |
| db-migrations | Schema and migration execution         |
| rabbitmq      | Celery broker                          |
| scheduler     | Job orchestration                      |
| celery-worker | Extraction and analysis task execution |
| celery-beat   | Periodic scheduling                    |
| flower        | Celery monitoring UI                   |
| grafana       | Dashboard visualization                |

## Common Runtime Modes

- GitHub-only run: set GitHub variables, then run docker compose up scheduler celery-worker.
- Azure DevOps-only run: set Azure variables, then run docker compose up scheduler celery-worker.
- Dual-platform run: set both sets of variables, then run docker compose up scheduler celery-worker.

## Docker Test Path

Primary test entrypoint is ./scripts/run-tests-docker.sh.

The test stack behavior:

- Creates isolated test database services
- Applies migrations before tests
- Runs tests in containers
- Runs post-integration DB invariant checks via `scripts/verify-extraction.sh`
- Cleans up resources when finished

The `test-runner` service in `docker-compose.test.yml` bind-mounts `./scripts`, `./src`, `./tests`, and `./database` into `/app`, so shell and Python changes in those directories apply on the next run without an image rebuild. Rebuild (`docker compose -f docker-compose.test.yml build test-runner`) is only required when `Dockerfile` or `requirements.txt` changes.

## Troubleshooting

### Build or Native Dependency Errors

If image build fails with compiler/toolchain errors, rebuild from a clean state and verify Dockerfile dependency steps are not skipped.

### Azure SDK Import Errors

If runtime fails to import Azure modules, verify dependency install steps executed during image build and compare image tag with expected requirements.

### Database Connectivity Errors

If the app cannot connect to PostgreSQL:

1. Verify the database container is running.
2. Confirm POSTGRES_HOST points to timescaledb in containerized runs.
3. Wait for database readiness before scheduler/worker startup.

### Docker and Local Behavior Divergence

If tests pass locally but fail in Docker, check environment variable propagation, migration timing, and service network consistency.

## Performance Notes

- TimescaleDB is optimized for time-series reporting workloads.
- Worker concurrency is configurable via CELERY_WORKER_CONCURRENCY.
- Layer caching improves rebuild speed when dependency lock files are unchanged.

## Suggested Run Order

1. Populate .env with required platform and service values.
2. Start stack with docker compose up.
3. Monitor workers in Flower at http://localhost:5555.
4. Review dashboards in Grafana at http://localhost:3000.
5. Inspect scheduler logs with docker compose logs -f scheduler.

## See Also

- [README.md](README.md)
- [docs/03-operations/deployment-plan.md](docs/03-operations/deployment-plan.md)
