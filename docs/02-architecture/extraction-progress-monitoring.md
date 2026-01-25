# Extraction Progress Monitoring - Design Document

## Overview

This document defines the architecture for real-time extraction progress monitoring using Grafana dashboards and worker instrumentation.

**Requirements Addressed:**
- **FR-9.5**: System shall provide real-time extraction progress monitoring
- **NFR-3.1-3.6**: Worker observability, metrics, health checks, structured logging

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────────┐
│                     Grafana Dashboard                            │
│  - Extraction Progress                                          │
│  - Worker Health                                                │
│  - Platform Comparison                                          │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 │ SQL Queries
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    TimescaleDB                                   │
│  - repositories (last_analyzed_at, extraction_duration)         │
│  - extraction_metrics (new table)                               │
│  - commits, pull_requests (data growth)                         │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 │ Write Metrics
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│              Celery Workers (Instrumented)                       │
│  - Structured logging with correlation IDs                      │
│  - Extraction event tracking                                    │
│  - Metrics emission to database                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Model

### New Table: `extraction_metrics`

Stores detailed extraction progress for monitoring and troubleshooting.

```sql
CREATE TABLE extraction_metrics (
    id SERIAL PRIMARY KEY,
    repository_id VARCHAR(255) NOT NULL REFERENCES repositories(repo_id),
    platform VARCHAR(50) NOT NULL,  -- 'github' or 'azure_devops'
    
    -- Timing
    extraction_started_at TIMESTAMPTZ NOT NULL,
    extraction_completed_at TIMESTAMPTZ,
    extraction_duration_seconds INTEGER,
    
    -- Status
    status VARCHAR(50) NOT NULL,  -- 'started', 'completed', 'failed'
    error_message TEXT,
    
    -- Extraction results
    commits_extracted INTEGER DEFAULT 0,
    pull_requests_extracted INTEGER DEFAULT 0,
    branches_extracted INTEGER DEFAULT 0,
    contributors_extracted INTEGER DEFAULT 0,
    
    -- Worker info
    celery_task_id VARCHAR(255),
    worker_hostname VARCHAR(255),
    
    -- Correlation
    correlation_id UUID NOT NULL,  -- For tracing across logs
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Convert to hypertable for time-series performance
SELECT create_hypertable('extraction_metrics', 'extraction_started_at');

-- Indexes for dashboard queries
CREATE INDEX idx_extraction_metrics_platform_status 
    ON extraction_metrics(platform, status, extraction_started_at DESC);
    
CREATE INDEX idx_extraction_metrics_correlation 
    ON extraction_metrics(correlation_id);
```

### Enhancements to Existing Tables

**repositories table** (already exists, add indexes):

```sql
-- Add index for progress tracking queries
CREATE INDEX IF NOT EXISTS idx_repositories_last_analyzed 
    ON repositories(last_analyzed_at DESC NULLS LAST);
    
CREATE INDEX IF NOT EXISTS idx_repositories_platform_analyzed 
    ON repositories(
        SPLIT_PART(repo_id, '/', 1),  -- platform
        last_analyzed_at DESC NULLS LAST
    );
```

---

## Grafana Dashboard: Extraction Progress

### Panel Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  Extraction Progress                     Last Updated: 2s ago    │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────┐  ┌─────────────────────┐               │
│  │  Extraction Rate    │  │  Repository Status  │               │
│  │  (repos/hour)       │  │  (Pie Chart)        │               │
│  │  [Line Chart]       │  │  - Analyzed: 450    │               │
│  │                     │  │  - Pending:  50     │               │
│  └─────────────────────┘  └─────────────────────┘               │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Platform Comparison (Bar Chart)                          │  │
│  │  GitHub:      250 analyzed  |  50 pending                 │  │
│  │  Azure DevOps: 200 analyzed |  0 pending                  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Worker Health                                            │  │
│  │  Active: 4 workers  |  Queue Depth: 12 tasks              │  │
│  │  Last Success: 2s ago  |  Failure Rate: 0.2%              │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Recent Activity (Table)                                  │  │
│  │  Repo Name    | Platform | Analyzed At | Duration | Status│  │
│  │  my-service   | github   | 1m ago     | 45s      | ✓     │  │
│  │  web-app      | azure    | 2m ago     | 32s      | ✓     │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Data Growth Over Time (Line Chart)                       │  │
│  │  - Commits (blue)                                         │  │
│  │  - Pull Requests (green)                                  │  │
│  │  - Contributors (orange)                                  │  │
│  └───────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### Panel Queries

#### 1. Extraction Rate (repos/hour)

```sql
SELECT
    time_bucket('5 minutes', extraction_completed_at) as time,
    COUNT(*) * 12 as repos_per_hour  -- 5 min buckets * 12 = hourly rate
FROM extraction_metrics
WHERE 
    extraction_completed_at > NOW() - INTERVAL '1 hour'
    AND status = 'completed'
    AND $__timeFilter(extraction_completed_at)
GROUP BY time
ORDER BY time;
```

#### 2. Repository Status (Pie Chart)

```sql
SELECT
    CASE 
        WHEN last_analyzed_at IS NULL THEN 'Never Analyzed'
        WHEN last_analyzed_at > NOW() - INTERVAL '24 hours' THEN 'Recently Analyzed'
        ELSE 'Needs Update'
    END as status,
    COUNT(*) as count
FROM repositories
WHERE is_active = true
GROUP BY status;
```

#### 3. Platform Comparison (Bar Chart)

```sql
SELECT
    SPLIT_PART(repo_id, '/', 1) as platform,
    COUNT(*) FILTER (WHERE last_analyzed_at IS NOT NULL) as analyzed,
    COUNT(*) FILTER (WHERE last_analyzed_at IS NULL) as pending
FROM repositories
WHERE is_active = true
GROUP BY platform;
```

#### 4. Worker Health Stats

```sql
-- Active tasks in last 5 minutes
SELECT 
    COUNT(DISTINCT worker_hostname) as active_workers,
    COUNT(*) FILTER (WHERE status = 'started') as active_tasks,
    COUNT(*) FILTER (WHERE status = 'failed') as failed_tasks,
    AVG(extraction_duration_seconds) FILTER (WHERE status = 'completed') as avg_duration_seconds,
    MAX(extraction_completed_at) as last_success
FROM extraction_metrics
WHERE extraction_started_at > NOW() - INTERVAL '5 minutes';
```

#### 5. Recent Activity (Table)

```sql
SELECT
    r.name as repository,
    SPLIT_PART(r.repo_id, '/', 1) as platform,
    em.extraction_completed_at as analyzed_at,
    em.extraction_duration_seconds as duration_sec,
    em.status,
    em.commits_extracted,
    em.pull_requests_extracted
FROM extraction_metrics em
JOIN repositories r ON em.repository_id = r.repo_id
WHERE em.extraction_started_at > NOW() - INTERVAL '1 hour'
ORDER BY em.extraction_completed_at DESC
LIMIT 20;
```

#### 6. Data Growth Over Time

```sql
-- Commits over time
SELECT
    time_bucket('1 hour', created_at) as time,
    COUNT(*) as commits
FROM commits
WHERE $__timeFilter(created_at)
GROUP BY time
ORDER BY time;

-- Pull Requests over time
SELECT
    time_bucket('1 hour', created_at) as time,
    COUNT(*) as pull_requests
FROM pull_requests
WHERE $__timeFilter(created_at)
GROUP BY time
ORDER BY time;

-- Contributors over time
SELECT
    time_bucket('1 hour', created_at) as time,
    COUNT(DISTINCT id) as contributors
FROM contributors
WHERE $__timeFilter(created_at)
GROUP BY time
ORDER BY time;
```

---

## Worker Instrumentation

### Code Changes Required

#### 1. Create ExtractionMetrics Service

**File**: `src/observability/extraction_metrics.py` (new)

```python
"""Extraction metrics tracking for observability."""

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from src.database.models import ExtractionMetric


class ExtractionMetricsTracker:
    """Tracks extraction progress for monitoring."""
    
    def __init__(self, db_session: Session):
        self.session = db_session
        self.correlation_id = uuid.uuid4()
        
    def start_extraction(
        self,
        repository_id: str,
        platform: str,
        celery_task_id: Optional[str] = None,
        worker_hostname: Optional[str] = None
    ) -> int:
        """Record extraction start and return metric ID."""
        metric = ExtractionMetric(
            repository_id=repository_id,
            platform=platform,
            extraction_started_at=datetime.now(timezone.utc),
            status='started',
            correlation_id=self.correlation_id,
            celery_task_id=celery_task_id,
            worker_hostname=worker_hostname
        )
        self.session.add(metric)
        self.session.commit()
        return metric.id
    
    def complete_extraction(
        self,
        metric_id: int,
        commits: int = 0,
        pull_requests: int = 0,
        branches: int = 0,
        contributors: int = 0
    ):
        """Record successful extraction completion."""
        metric = self.session.query(ExtractionMetric).get(metric_id)
        if metric:
            metric.extraction_completed_at = datetime.now(timezone.utc)
            metric.extraction_duration_seconds = int(
                (metric.extraction_completed_at - metric.extraction_started_at).total_seconds()
            )
            metric.status = 'completed'
            metric.commits_extracted = commits
            metric.pull_requests_extracted = pull_requests
            metric.branches_extracted = branches
            metric.contributors_extracted = contributors
            self.session.commit()
    
    def fail_extraction(self, metric_id: int, error_message: str):
        """Record extraction failure."""
        metric = self.session.query(ExtractionMetric).get(metric_id)
        if metric:
            metric.extraction_completed_at = datetime.now(timezone.utc)
            metric.extraction_duration_seconds = int(
                (metric.extraction_completed_at - metric.extraction_started_at).total_seconds()
            )
            metric.status = 'failed'
            metric.error_message = error_message[:1000]  # Truncate long errors
            self.session.commit()
```

#### 2. Integrate into Workflows

**File**: `src/workflows/github_analysis.py` (modify)

```python
from src.observability.extraction_metrics import ExtractionMetricsTracker

class GitHubAnalysisWorkflow:
    def run(self, org_name: str, max_repos: int = None):
        # ... existing code ...
        
        for repo_data in repositories:
            tracker = ExtractionMetricsTracker(self.storage.session)
            metric_id = tracker.start_extraction(
                repository_id=repo_data.repo_id,
                platform='github',
                celery_task_id=self.task_id,  # From Celery context
                worker_hostname=socket.gethostname()
            )
            
            try:
                # ... existing extraction logic ...
                
                tracker.complete_extraction(
                    metric_id,
                    commits=len(stored_commits),
                    pull_requests=len(stored_prs),
                    branches=len(branches),
                    contributors=len(contributors)
                )
                
            except Exception as e:
                tracker.fail_extraction(metric_id, str(e))
                raise
```

#### 3. Structured Logging

**File**: `src/workflows/base.py` (enhance)

```python
import logging
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

class BaseWorkflow:
    def log_extraction_event(self, event_type: str, **kwargs):
        """Log extraction events with correlation ID."""
        logger.info(
            event_type,
            correlation_id=str(self.tracker.correlation_id),
            platform=self.platform,
            **kwargs
        )
```

---

## Implementation Plan

### Phase 1: Database Schema (1 hour)

1. Create migration: `006_add_extraction_metrics.sql`
2. Add `extraction_metrics` table
3. Add indexes to `repositories` table
4. Test migration in dev environment

### Phase 2: Worker Instrumentation (3 hours)

1. Create `ExtractionMetricsTracker` class
2. Integrate into `GitHubAnalysisWorkflow`
3. Integrate into `AzureDevOpsAnalysisWorkflow`
4. Add structured logging configuration
5. Test metric recording during extraction

### Phase 3: Grafana Dashboard (2 hours)

1. Create dashboard JSON: `dashboards/extraction-progress.json`
2. Define all 6 panel queries
3. Configure auto-refresh (5 seconds)
4. Add navigation links to other dashboards
5. Test with live data

### Phase 4: Documentation (1 hour)

1. Update monitoring guide with new dashboard
2. Add troubleshooting section
3. Document metric schema and queries

**Total Estimated Effort**: 6-8 hours

---

## Benefits

1. **Real-time Visibility**: See extraction progress as it happens
2. **Performance Monitoring**: Track extraction rate and identify bottlenecks
3. **Troubleshooting**: Correlation IDs link logs to metrics to database records
4. **Historical Analysis**: Time-series data shows trends and patterns
5. **Worker Health**: Monitor worker status and task queue depth
6. **Platform Comparison**: Compare GitHub vs Azure DevOps extraction performance

---

## Future Enhancements

1. **Alerting**: Set up Grafana alerts for:
   - Extraction rate drops below threshold
   - Failure rate exceeds 5%
   - Repositories not analyzed in > 48 hours
   
2. **Health Check Endpoint**: Add HTTP endpoint to workers for external monitoring

3. **Metrics Export**: Export metrics to Prometheus for additional monitoring tools

4. **Predictive Analysis**: Estimate completion time based on current extraction rate
