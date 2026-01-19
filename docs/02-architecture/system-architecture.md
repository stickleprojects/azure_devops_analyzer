# System Architecture

## Overview

The system architecture manages job scheduling, workflow coordination, and incremental updates using Python-based scheduling libraries. This approach provides a lightweight, flexible alternative to heavyweight workflow engines for analyzing repositories across multiple platforms.

## Technology Stack

### Core Libraries

The system utilizes **APScheduler**, **Celery**, **RabbitMQ**, and Python's built-in **multiprocessing** libraries.

### Architecture Choice

We'll use **APScheduler** as the primary scheduler with **Celery** for distributed job execution:

- **APScheduler**: Handles scheduling (cron, interval, one-time jobs)
- **Celery**: Manages job queues and worker processes
- **RabbitMQ**: Message broker
- **multiprocessing**: Parallel execution within jobs

This combination provides:

- Simple setup and maintenance
- Good performance for medium-scale workloads
- Easy debugging and monitoring
- No complex DAG definitions required

## Project Structure

```
azure-devops-analyzer/
├── src/
│   ├── extractors/         # Multi-platform data extraction (Azure DevOps, GitHub)
│   │   ├── base.py         # Abstract extractor interface
│   │   ├── factory.py      # Extractor factory for platform selection
│   │   ├── azure_devops/   # Azure DevOps API client and extractor
│   │   └── github/         # GitHub API client and extractor
│   ├── analyzers/          # Analysis modules (language, security, quality)
│   ├── database/           # ORM models, connection, storage operations
│   ├── workflows/          # Analysis workflow orchestration
│   └── utils/              # Shared utilities
├── database/               # SQL schema and migration files
├── dashboards/             # Grafana dashboard JSON definitions
├── docs/                   # Documentation and guides
├── tests/                  # Unit and integration tests
├── config/                 # Configuration files
├── workers/                # Worker startup scripts
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```
│   └── utils/
│       ├── __init__.py
│       ├── job_tracker.py       # Job status tracking
│       └── notifications.py     # Alert notifications
├── workers/
│   └── worker_start.sh          # Worker startup script
└── config/
    └── scheduler.yaml           # Scheduler configuration
```

## Core Components

### 1. Main Scheduler (APScheduler)

The main scheduler is configured to run:

- **Full Repository Scan**: Weekly on Sunday at 2 AM.
- **Incremental Update**: Every hour.
- **Database Cleanup**: Daily at 3 AM.
- **Database Backup**: Daily at 4 AM.

It uses `SQLAlchemyJobStore` (PostgreSQL) for persistence and `ThreadPoolExecutor` for concurrent execution.

### 2. Full Scan Workflow

The full scan workflow performs the following steps:

1.  **Fetch Organizations/Projects**: Retrieves a list of all organizations/projects from configured platforms.
2.  **Parallel Processing**: Enqueues a separate Celery task for each repository across all platforms.
3.  **Single Repository Pipeline**:
    - **Extract**: Fetches metadata, commits, PRs, and file trees from Azure DevOps or GitHub APIs.
    - **Analyze**: Runs language detection, dependency scanning, code quality checks, and summarization.
    - **Store**: Saves all results to the database in a transaction.
4.  **Monitor**: Tracks job completion and updates scan metadata.

### 3. Incremental Update Workflow

The incremental update workflow minimizes load by:

1.  **Detecting Changes**: Checks for new commits and PR updates since the last run.
2.  **Queueing Jobs**: Enqueues specific jobs for repositories with detected changes.
3.  **Processing Commits**:
    - Updates contributor metrics.
    - Triggers a dependency re-scan if manifest files (e.g., `requirements.txt`) are modified.
4.  **Processing PRs**: Updates PR metadata and analysis for new or modified pull requests.

### 4. Branch-Specific Scan Workflow

This workflow allows on-demand analysis of specific branches, useful for PR validation or ad-hoc checks. It extracts data specific to the branch, runs the analysis suite, and stores branch-scoped results.

## Task Implementations

### 1. Extraction Tasks

Extraction tasks interface with repository hosting platforms (Azure DevOps and GitHub) to retrieve:

- **Repository Data**: Metadata, branches, commits (last 90 days), PRs, and file trees.
- **Branch Data**: Specific commit history and file tree for a branch.
- **Incremental Data**: Commits and PR changes since a specific timestamp.

### 2. Analysis Tasks

Analysis tasks run in parallel using `ThreadPoolExecutor` to maximize throughput. They include:

- **Language Detection**: Identifies programming languages.
- **Dependency Scanning**: Parses manifests and checks for vulnerabilities.
- **Code Quality**: Runs static analysis.
- **Summarization**: Generates AI summaries.
- **Metrics**: Calculates contributor and PR statistics.

### 3. Storage Tasks

Storage tasks handle transactional writes to PostgreSQL/TimescaleDB. They ensure data consistency for repository metadata, metrics, and time-series data.

### 4. Maintenance Tasks

Maintenance tasks include:

- **Cleanup**: Archiving data older than 2 years and compressing old TimescaleDB chunks.
- **Backup**: Daily PostgreSQL dumps, compression, and upload to Azure Blob Storage.

## Monitoring and Alerting

### Health Checks

Automated health checks run every 15 minutes to verify:

- Database connectivity and performance.
- Azure DevOps API availability.
- Stale data detection (repos not analyzed in >7 days).

### Performance Metrics

The system tracks DAG execution times, calculating average, max, and min durations to identify performance bottlenecks.

## Error Handling and Recovery

Robust error handling ensures that failures in one repository or analysis step do not crash the entire workflow. Failed items are marked for retry, and partial results are stored where possible.

## Next Steps

- See [06-visualization.md](06-visualization.md) for Grafana dashboard setup
- Review [07-implementation-plan.md](07-implementation-plan.md) for deployment timeline
