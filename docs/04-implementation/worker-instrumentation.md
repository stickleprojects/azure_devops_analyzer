# Worker Instrumentation - Implementation Guide

## Overview

This guide details how to instrument Celery workers for comprehensive observability including metrics, structured logging, and health checks.

**Requirements Addressed:**

- **NFR-3.1**: Workers shall emit structured metrics for extraction progress
- **NFR-3.2**: Workers shall emit health check endpoints
- **NFR-3.3**: Workers shall log extraction events with correlation IDs
- **NFR-3.4**: System shall store extraction metrics in TimescaleDB
- **NFR-3.6**: System shall track Celery task metrics

---

## Architecture Overview

### Instrumentation Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                    External Monitoring                           │
│                  (Grafana, Health Checks)                        │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Metrics & Logs Layer                           │
│  - ExtractionMetricsTracker (DB writes)                         │
│  - Structured Logger (JSON logs)                                │
│  - Celery Signals (task lifecycle)                              │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Workflow Execution Layer                        │
│  - GitHubAnalysisWorkflow                                       │
│  - AzureDevOpsAnalysisWorkflow                                  │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Celery Task Layer                             │
│  - extract_github_organization                                  │
│  - extract_azure_devops_organization                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Implementation

### 1. Structured Logging Configuration

**File**: `src/observability/logging_config.py` (new)

```python
"""Structured logging configuration for workers."""

import logging
import sys
from typing import Optional

import structlog


def configure_structlog(
    log_level: str = "INFO",
    correlation_id: Optional[str] = None
):
    """Configure structured logging for worker processes.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        correlation_id: Optional correlation ID to include in all logs
    """

    # Shared processors for all loggers
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    # Configure structlog
    structlog.configure(
        processors=shared_processors + [
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

    # Get logger instance
    logger = structlog.get_logger()

    # Bind correlation ID if provided
    if correlation_id:
        logger = logger.bind(correlation_id=correlation_id)

    return logger


# Usage example
"""
from src.observability.logging_config import configure_structlog

logger = configure_structlog(log_level="INFO", correlation_id=str(uuid.uuid4()))
logger.info(
    "extraction_started",
    repository_id="github/org/repo",
    platform="github",
    worker_id=socket.gethostname()
)
"""
```

**Example Log Output**:

```json
{
  "event": "extraction_started",
  "repository_id": "github/octocat/Hello-World",
  "platform": "github",
  "worker_id": "worker-01",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "level": "info",
  "timestamp": "2026-01-25T21:45:30.123456Z"
}
```

---

### 2. Celery Task Instrumentation

**File**: `src/scheduler/celery_signals.py` (new)

```python
"""Celery signal handlers for task monitoring."""

import time
from celery import signals
from src.observability.logging_config import configure_structlog

# Initialize logger
logger = None


@signals.worker_process_init.connect
def init_worker_process(**kwargs):
    """Initialize worker process with structured logging."""
    global logger
    logger = configure_structlog(log_level="INFO")
    logger.info("worker_process_started", **kwargs)


@signals.task_prerun.connect
def task_prerun(sender=None, task_id=None, task=None, args=None, kwargs=None, **extra):
    """Log task start."""
    task.start_time = time.time()
    logger.info(
        "task_started",
        task_id=task_id,
        task_name=sender.name,
        args=str(args)[:200],  # Truncate long args
    )


@signals.task_postrun.connect
def task_postrun(sender=None, task_id=None, task=None, state=None, **extra):
    """Log task completion."""
    duration = time.time() - getattr(task, 'start_time', 0)
    logger.info(
        "task_completed",
        task_id=task_id,
        task_name=sender.name,
        state=state,
        duration_seconds=round(duration, 2)
    )


@signals.task_failure.connect
def task_failure(sender=None, task_id=None, exception=None, traceback=None, **extra):
    """Log task failure."""
    logger.error(
        "task_failed",
        task_id=task_id,
        task_name=sender.name,
        exception=str(exception),
        traceback=str(traceback)[:500]  # Truncate long tracebacks
    )


@signals.task_retry.connect
def task_retry(sender=None, task_id=None, reason=None, **extra):
    """Log task retry."""
    logger.warning(
        "task_retrying",
        task_id=task_id,
        task_name=sender.name,
        reason=str(reason)
    )
```

**File**: `src/scheduler/celery_app.py` (modify)

```python
# Add this import
from src.scheduler import celery_signals  # noqa: F401 - signals auto-register
```

---

### 3. Extraction Metrics Tracking

**File**: `src/observability/extraction_metrics.py` (already in design doc)

See [extraction-progress-monitoring.md](../02-architecture/extraction-progress-monitoring.md#worker-instrumentation) for `ExtractionMetricsTracker` implementation.

---

### 4. Workflow Integration

**File**: `src/workflows/github_analysis.py` (enhance)

```python
import socket
from celery import current_task
from src.observability.extraction_metrics import ExtractionMetricsTracker
from src.observability.logging_config import configure_structlog


class GitHubAnalysisWorkflow:
    def __init__(self, extractor, storage):
        self.extractor = extractor
        self.storage = storage
        self.platform = "github"

        # Initialize logger with correlation ID
        self.logger = configure_structlog()

    def run(self, org_name: str, max_repos: int = None):
        """Run extraction with full instrumentation."""

        self.logger.info(
            "organization_extraction_started",
            organization=org_name,
            platform=self.platform,
            max_repos=max_repos
        )

        # Get repositories
        repositories = self.extractor.get_repositories(org_name)

        if max_repos:
            repositories = repositories[:max_repos]

        self.logger.info(
            "repositories_discovered",
            organization=org_name,
            repository_count=len(repositories)
        )

        # Process each repository
        for idx, repo_data in enumerate(repositories, 1):
            self._process_repository_with_instrumentation(
                repo_data,
                idx,
                len(repositories)
            )

        self.logger.info(
            "organization_extraction_completed",
            organization=org_name,
            repositories_processed=len(repositories)
        )

    def _process_repository_with_instrumentation(
        self,
        repo_data,
        current_idx: int,
        total_repos: int
    ):
        """Process single repository with metrics and logging."""

        # Initialize metrics tracker
        tracker = ExtractionMetricsTracker(self.storage.session)

        # Get Celery task context if available
        task_id = None
        worker_hostname = socket.gethostname()
        if current_task:
            task_id = current_task.request.id

        # Start metrics tracking
        metric_id = tracker.start_extraction(
            repository_id=repo_data.repo_id,
            platform=self.platform,
            celery_task_id=task_id,
            worker_hostname=worker_hostname
        )

        self.logger.info(
            "repository_extraction_started",
            repository=repo_data.name,
            repository_id=repo_data.repo_id,
            progress=f"{current_idx}/{total_repos}",
            metric_id=metric_id
        )

        try:
            # Existing extraction logic
            stored_repo = self.storage.store_repository(repo_data)

            branches = self._process_branches(repo_data)
            commits = self._process_commits(repo_data, branches)
            prs = self._process_pull_requests(repo_data)
            contributors = self._count_contributors()

            # Complete metrics
            tracker.complete_extraction(
                metric_id,
                commits=len(commits),
                pull_requests=len(prs),
                branches=len(branches),
                contributors=contributors
            )

            self.logger.info(
                "repository_extraction_completed",
                repository=repo_data.name,
                repository_id=repo_data.repo_id,
                commits=len(commits),
                pull_requests=len(prs),
                branches=len(branches),
                contributors=contributors,
                metric_id=metric_id
            )

        except Exception as e:
            # Record failure
            tracker.fail_extraction(metric_id, str(e))

            self.logger.error(
                "repository_extraction_failed",
                repository=repo_data.name,
                repository_id=repo_data.repo_id,
                error=str(e),
                metric_id=metric_id,
                exc_info=True
            )

            raise

    def _count_contributors(self) -> int:
        """Count distinct contributors in current session."""
        from src.database.models import Contributor
        return self.storage.session.query(Contributor.id).count()
```

---

### 5. Health Check Endpoint (Optional)

**File**: `src/observability/health_check.py` (new)

```python
"""Worker health check HTTP endpoint."""

import socket
from datetime import datetime, timezone
from flask import Flask, jsonify
from sqlalchemy import create_engine, text
from src.config.database import get_database_url

app = Flask(__name__)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for worker monitoring.

    Returns:
        JSON with worker status, database connectivity, last extraction
    """

    hostname = socket.gethostname()
    now = datetime.now(timezone.utc)

    # Check database connectivity
    try:
        engine = create_engine(get_database_url())
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    # Get last extraction time
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT MAX(extraction_completed_at) as last_extraction
                FROM extraction_metrics
                WHERE worker_hostname = :hostname
                  AND status = 'completed'
            """), {"hostname": hostname})
            row = result.fetchone()
            last_extraction = row[0] if row else None
    except:
        last_extraction = None

    return jsonify({
        "status": "healthy" if db_status == "healthy" else "degraded",
        "worker": {
            "hostname": hostname,
            "timestamp": now.isoformat()
        },
        "database": {
            "status": db_status
        },
        "extraction": {
            "last_completed_at": last_extraction.isoformat() if last_extraction else None
        }
    })


def run_health_server(port=8080):
    """Run health check server in background thread."""
    app.run(host='0.0.0.0', port=port)
```

**Docker Compose Integration** (optional):

```yaml
celery-worker:
  # ... existing config ...
  ports:
    - "8080:8080" # Health check endpoint
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

---

## Testing Strategy

### 1. Unit Tests

**File**: `tests/unit/test_extraction_metrics.py` (new)

```python
"""Tests for extraction metrics tracking."""

import pytest
from datetime import datetime, timezone
from src.observability.extraction_metrics import ExtractionMetricsTracker


def test_start_extraction_creates_record(db_session):
    """Test that starting extraction creates database record."""
    tracker = ExtractionMetricsTracker(db_session)

    metric_id = tracker.start_extraction(
        repository_id="github/test/repo",
        platform="github",
        celery_task_id="test-task-123",
        worker_hostname="worker-01"
    )

    assert metric_id is not None
    assert metric_id > 0


def test_complete_extraction_updates_record(db_session):
    """Test that completing extraction updates the record."""
    tracker = ExtractionMetricsTracker(db_session)

    metric_id = tracker.start_extraction(
        repository_id="github/test/repo",
        platform="github"
    )

    tracker.complete_extraction(
        metric_id,
        commits=10,
        pull_requests=5,
        branches=3,
        contributors=2
    )

    # Verify record updated
    from src.database.models import ExtractionMetric
    metric = db_session.query(ExtractionMetric).get(metric_id)

    assert metric.status == 'completed'
    assert metric.commits_extracted == 10
    assert metric.pull_requests_extracted == 5
    assert metric.extraction_duration_seconds > 0
```

### 2. Integration Tests

**File**: `tests/contract/integration/test_workflow_instrumentation.py` (new)

```python
"""Test workflow instrumentation end-to-end."""

import pytest
from src.workflows.github_analysis import GitHubAnalysisWorkflow
from src.database.models import ExtractionMetric


@pytest.mark.live_api
@pytest.mark.integration
def test_workflow_creates_extraction_metrics(github_extractor, db_session):
    """Test that workflow creates extraction metrics."""

    workflow = GitHubAnalysisWorkflow(github_extractor, storage)
    workflow.run("octocat", max_repos=1)

    # Verify metrics created
    metrics = db_session.query(ExtractionMetric).all()
    assert len(metrics) >= 1

    metric = metrics[0]
    assert metric.platform == 'github'
    assert metric.status == 'completed'
    assert metric.extraction_duration_seconds > 0
```

---

## Monitoring & Troubleshooting

### Log Queries

**Find failed extractions:**

```bash
docker compose logs worker | grep "repository_extraction_failed"
```

**Trace specific repository:**

```bash
docker compose logs worker | grep "repo_id=github/octocat/Hello-World"
```

**Find correlation ID:**

```bash
docker compose logs worker | grep "correlation_id=550e8400-e29b-41d4-a716-446655440000"
```

### Database Queries

**Find slow extractions:**

```sql
SELECT
    repository_id,
    extraction_duration_seconds,
    commits_extracted,
    pull_requests_extracted
FROM extraction_metrics
WHERE status = 'completed'
  AND extraction_duration_seconds > 60  -- Over 1 minute
ORDER BY extraction_duration_seconds DESC
LIMIT 10;
```

**Find recent failures:**

```sql
SELECT
    repository_id,
    error_message,
    extraction_started_at,
    worker_hostname
FROM extraction_metrics
WHERE status = 'failed'
  AND extraction_started_at > NOW() - INTERVAL '24 hours'
ORDER BY extraction_started_at DESC;
```

---

## Implementation Checklist

- [ ] Create database migration for `extraction_metrics` table
- [ ] Implement `ExtractionMetricsTracker` class
- [ ] Configure structured logging with `structlog`
- [ ] Add Celery signal handlers
- [ ] Integrate metrics tracking into `GitHubAnalysisWorkflow`
- [ ] Integrate metrics tracking into `AzureDevOpsAnalysisWorkflow`
- [ ] Add unit tests for metrics tracker
- [ ] Add integration tests for workflow instrumentation
- [ ] Create Grafana dashboard (see extraction-progress-monitoring.md)
- [ ] Update documentation
- [ ] (Optional) Add health check HTTP endpoint

**Estimated Effort**: 6-8 hours
