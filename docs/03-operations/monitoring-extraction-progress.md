# Monitoring Extraction Progress

When Celery workers are running, there are multiple ways to monitor repository extraction progress.

## Prerequisites

All monitoring methods require Docker services to be running:

```bash
# Start all services (database, workers, Flower, Grafana)
docker compose up -d

# Or start minimal set for monitoring
docker compose up -d db worker flower
```

## Monitoring Options

### 1. **Flower Web UI** ⭐ Recommended

Celery monitoring dashboard with task tracking:

```bash
# Start the entire stack (includes Flower)
docker compose up -d

# Or start Flower separately
docker compose up -d flower
```

**Access:** http://localhost:5555

**Features:**

- Active/completed/failed tasks
- Task execution time
- Worker status
- Task success/failure rates
- Real-time task streams

---

### 3. **Docker Logs**

View worker logs in real-time:

```bash
# All services
docker compose logs -f

# Worker only
docker compose logs -f worker

# Last 100 lines
docker compose logs --tail=100 worker

# GitHub workflow logs specifically
docker compose logs -f worker | grep "github_analysis"

# Azure DevOps workflow logs
docker compose logs -f worker | grep "azure_devops_analysis"
```

**Look for log entries:**

- `Processing: <org>` - Organization being processed
- `Found X repositories` - Repos discovered
- `Processing repo: <name>` - Current repo
- `Stored X commits` - Data extraction progress

---

### 4. **Direct Database Queries**

Quick SQL queries to check progress:

```bash
# Connect to database
docker compose exec db psql -U analyzer -d analyzer

# Or from host (if port 5432 is exposed)
psql -h localhost -U analyzer -d analyzer
```

**Useful queries:**

```sql
-- Repositories by platform
SELECT
    SPLIT_PART(repo_id, '/', 1) as platform,
    COUNT(*) as total,
    COUNT(last_analyzed_at) as analyzed,
    COUNT(*) - COUNT(last_analyzed_at) as pending
FROM repositories
GROUP BY platform;

-- Recently analyzed repositories
SELECT
    name,
    last_analyzed_at,
    NOW() - last_analyzed_at as age
FROM repositories
WHERE last_analyzed_at IS NOT NULL
ORDER BY last_analyzed_at DESC
LIMIT 10;

-- Extraction progress for last hour
SELECT
    SPLIT_PART(repo_id, '/', 1) as platform,
    COUNT(*) as analyzed_last_hour
FROM repositories
WHERE last_analyzed_at > NOW() - INTERVAL '1 hour'
GROUP BY platform;

-- Data extraction counts
SELECT
    (SELECT COUNT(*) FROM repositories) as repos,
    (SELECT COUNT(*) FROM commits) as commits,
    (SELECT COUNT(*) FROM pull_requests) as prs,
    (SELECT COUNT(*) FROM branches) as branches;

-- Never analyzed repos
SELECT name, repo_id
FROM repositories
WHERE last_analyzed_at IS NULL
LIMIT 20;
```

---

### 5. **Grafana Dashboard** (Future Enhancement)

Create a real-time extraction monitoring dashboard:

**Panel Ideas:**

- Repository extraction rate (repos/hour)
- Current extraction queue depth
- Platform comparison (GitHub vs Azure DevOps)
- Failed vs successful extractions
- Average extraction time per repository
- Data growth over time (commits, PRs)

**Create dashboard:**

1. Add new dashboard in Grafana (http://localhost:3000)
2. Add panels with queries like:

```sql
-- Extraction rate (last hour)
SELECT
    time_bucket('5 minutes', last_analyzed_at) as time,
    COUNT(*) as repos_analyzed
FROM repositories
WHERE last_analyzed_at > NOW() - INTERVAL '1 hour'
GROUP BY time
ORDER BY time;

-- Platform progress
SELECT
    SPLIT_PART(repo_id, '/', 1) as platform,
    COUNT(*) FILTER (WHERE last_analyzed_at IS NOT NULL) as analyzed,
    COUNT(*) as total
FROM repositories
GROUP BY platform;
```

---

## Enhanced Logging

### Option A: Increase Worker Log Verbosity

Edit `docker-compose.yml`:

```yaml
worker:
  environment:
    - LOG_LEVEL=INFO # Or DEBUG for more detail
```

### Option B: Structured Progress Logging

Add progress logging to workflows (already implemented):

**GitHub Workflow logs:**

```
Processing: octocat
  Found 15 repositories
    Processing repo: Hello-World
      Found 3 branches
      Found 10 languages
      Found 25 recent commits
      Stored 25 new commits
      Found 5 pull requests
      Stored 5 new pull requests
```

**Azure DevOps Workflow logs:**

```
Processing: myorg
  Fetching projects for myorg...
  Found 3 projects
    Processing project: MyProject
      Found 10 repositories
        Processing repo: my-repo
          Found 2 branches
          Found 5 languages
          Found 30 recent commits
```

---

## Recommended Monitoring Workflow

**During Development:**

1. Use `python scripts/check_progress.py --watch` in separate terminal
2. Monitor Flower UI (http://localhost:5555) for task failures
3. Check docker logs if issues occur

**In Production:**

1. Create Grafana dashboard for real-time monitoring
2. Set up alerts for:
   - Failed tasks exceeding threshold
   - Extraction rate drops below minimum
   - Repos not analyzed in > 24 hours

**Troubleshooting:**

1. Check Flower for failed tasks
2. Review docker logs for errors
3. Query database for stuck/never-analyzed repos

---

## Adding Task Progress Updates (Future Enhancement)

For even better visibility, you can add progress callbacks:

```python
# In src/scheduler/tasks.py
from celery import current_task

@celery_app.task(bind=True)
def extract_repository(self, repo_id: str):
    # Update task state
    self.update_state(
        state='PROGRESS',
        meta={'current': 0, 'total': 100, 'status': 'Starting...'}
    )

    # ... do work ...

    self.update_state(
        state='PROGRESS',
        meta={'current': 50, 'total': 100, 'status': 'Extracting commits...'}
    )
```

Then Flower will show real-time progress bars for each task.

---

## Summary

| Method            | Real-time | Detail Level | Setup Required     |
| ----------------- | --------- | ------------ | ------------------ |
| Flower UI         | ✅        | High (tasks) | Already configured |
| Docker Logs       | ✅        | Very High    | None               |
| Database Queries  | ❌        | High (data)  | Manual queries     |
| Grafana Dashboard | ✅        | Medium       | Create dashboard   |

**Best combination:** Flower UI + Docker Logs + Grafana dashboard
