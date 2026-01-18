# Orchestration Layer

## Overview

The orchestration layer manages job scheduling and distributed task execution using a pure Python stack. **APScheduler** handles time-based triggering, while **Celery** manages distributed execution of extraction and analysis tasks via **RabbitMQ**.

## Technology Stack

- **Scheduler**: APScheduler (Advanced Python Scheduler)
- **Task Queue**: Celery
- **Message Broker**: RabbitMQ
- **Result Backend**: PostgreSQL (via SQLAlchemy)
- **Monitoring**: Flower (Celery monitoring tool)

## Architecture

### Scheduling (APScheduler)

The scheduler runs as a standalone service. It does not execute tasks directly but pushes messages to the RabbitMQ broker.

- **Job Stores**: Uses `SQLAlchemyJobStore` to persist scheduled jobs in PostgreSQL.
- **Executors**: Uses `ThreadPoolExecutor` for submitting tasks to Celery.
- **Triggers**:
  - **Cron**: For weekly full scans.
  - **Interval**: For hourly incremental updates.
  - **Date**: For one-off on-demand scans.

### Execution (Celery)

Celery workers consume messages from RabbitMQ and execute the actual logic.

- **Queues**:
  - `default`: General tasks.
  - `extraction`: I/O bound tasks (Azure DevOps API calls).
  - `analysis`: CPU bound tasks (Static analysis, parsing).
- **Concurrency**: Configured based on available CPU cores.

## Workflow Definitions

### 1. Full Repository Scan

**Schedule**: Weekly (Sunday 02:00 UTC)

**Flow**:

1.  **Trigger**: APScheduler enqueues `run_full_scan` task.
2.  **Discovery**: Worker fetches list of all repositories.
3.  **Fan-out**: Iterates through repositories and spawns `analyze_repository` tasks for each.
4.  **Execution**: Workers process repositories in parallel.
5.  **Storage**: Results are written to the database.

### 2. Incremental Update

**Schedule**: Hourly

**Flow**:

1.  **Trigger**: APScheduler enqueues `run_incremental_update`.
2.  **Detection**: Worker queries database for last run time and fetches changes from Azure DevOps.
3.  **Fan-out**: Spawns tasks only for repositories with new commits or PRs.
4.  **Processing**: Analyzes only changed files and updates metrics.

## Monitoring

### Flower

Flower provides a web-based UI for monitoring Celery clusters.

- **Real-time**: View active tasks and worker status.
- **History**: Review completed and failed tasks.
- **Control**: Rate limit or revoke tasks.

### Health Checks

- **Broker Connection**: Verifies connectivity to RabbitMQ.
- **Worker Status**: Checks if workers are online and accepting tasks.

## Checklist

- [ ] RabbitMQ installed and running
- [ ] Celery app configured with broker URL
- [ ] Task queues defined (default, extraction, analysis)
- [ ] APScheduler configured with SQLAlchemy job store
- [ ] Scheduled jobs registered (full scan, incremental, maintenance)
- [ ] Celery workers deployed and consuming tasks
- [ ] Flower installed for monitoring
- [ ] Health check tasks implemented

## Further Reading

- [Celery Documentation](https://docs.celeryq.dev/en/stable/)
- [APScheduler Documentation](https://apscheduler.readthedocs.io/en/stable/)
- [RabbitMQ Tutorials](https://www.rabbitmq.com/tutorials)
- [Flower - Celery Monitoring](https://flower.readthedocs.io/en/latest/)

## Next Steps

- See [06-visualization.md](06-visualization.md) for Grafana dashboard setup
- Review [07-implementation-plan.md](07-implementation-plan.md) for deployment timeline
