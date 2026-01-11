# Quick Reference Guide

## System Overview

The Azure DevOps Repository Analysis System is a Python-based solution that:

- Analyzes Azure DevOps repositories for code quality, security, and team metrics
- Uses APScheduler + Celery (with RabbitMQ) for job orchestration
- Stores data in PostgreSQL with TimescaleDB
- Visualizes metrics in Grafana dashboards

## Architecture at a Glance

```
Azure DevOps → Python Extractors → Analyzers → PostgreSQL → Grafana
                      ↓
                APScheduler (schedules jobs)
                      ↓
                Celery Workers (process jobs)
```

## Key Components

| Component  | Technology               | Purpose                              |
| ---------- | ------------------------ | ------------------------------------ |
| Scheduler  | APScheduler              | Schedule analysis jobs               |
| Job Queue  | Redis + RQ               | Distribute work to workers           |
| Extractors | Python + Azure SDK       | Fetch repo data from Azure DevOps    |
| Analyzers  | Python + Various tools   | Analyze code quality, security, etc. |
| Database   | PostgreSQL + TimescaleDB | Store all metrics                    |
| Dashboards | Grafana                  | Visualize data                       |

## Job Types

1. **Full Scan** (Weekly): Complete analysis of all repositories
2. **Incremental Update** (Hourly): Process only changes since last run
3. **Branch Scan** (On-demand): Analyze specific branch
4. **Maintenance** (Daily): Cleanup and backups

## Tech Stack Summary

- **Language**: Python 3.11+
- **Orchestration**: APScheduler 3.10.4, Celery 5.3.4
- **Message Broker**: Redis 7.0+
- **Database**: PostgreSQL 15+, TimescaleDB 2.x
- **Visualization**: Grafana 10+
- **Analysis Tools**: SonarQube, OSV.dev, language-specific linters
- **AI**: Claude/GPT-4 for repository summarization

## Quick Commands

### Start the System

```bash
# Start Redis
sudo systemctl start redis

# Start scheduler
python src/scheduler/main.py

# Start workers (separate terminal)
bash workers/worker_start.sh
```

### Monitor Jobs

```python
from utils.job_tracker import JobTracker

tracker = JobTracker()
stats = tracker.get_queue_stats()
print(stats)
```

### Trigger Manual Scan

```python
from scheduler.main import AnalyzerScheduler

scheduler = AnalyzerScheduler()
job_id = scheduler.trigger_full_scan()
```

## Database Quick Access

```sql
-- View repository health
SELECT name, last_analyzed_at
FROM repositories
WHERE is_active = true;

-- Check for vulnerabilities
SELECT COUNT(*)
FROM vulnerabilities v
JOIN dependencies d ON v.dependency_id = d.id
WHERE v.severity = 'CRITICAL';

-- Recent PR metrics
SELECT * FROM pull_requests
WHERE created_at > NOW() - INTERVAL '7 days'
ORDER BY created_at DESC;
```

## Grafana Dashboards

Access Grafana at `http://localhost:3000`

Default dashboards:

- Repository Overview
- Security Dashboard
- Code Quality Dashboard
- Contributor Dashboard
- Pull Request Dashboard

## Troubleshooting

**Jobs not running?**

- Check Redis: `redis-cli ping`
- Check workers: `ps aux | grep rq`
- Check scheduler: `ps aux | grep scheduler`

**Database issues?**

- Test connection: `psql -U postgres -d azure_devops_analyzer`
- Check TimescaleDB: `SELECT * FROM timescaledb_information.hypertables;`

**Azure DevOps API errors?**

- Verify PAT is valid
- Check rate limits
- Ensure PAT has correct scopes

## Implementation Timeline

12-week phased approach:

- **Phase 1-2**: Foundation and database (Weeks 1-2)
- **Phase 3**: Core analysis (Weeks 3-5)
- **Phase 4**: Metrics collection (Weeks 6-7)
- **Phase 5**: Orchestration (Week 8)
- **Phase 6**: Visualization (Weeks 9-10)
- **Phase 7**: Production hardening (Weeks 11-12)

## Documentation Index

1. [Architecture](01-architecture.md) - System design
2. [Data Extraction](02-data-extraction.md) - Azure DevOps integration
3. [Analysis Engine](03-analysis-engine.md) - Code analysis
4. [Data Storage](04-data-storage.md) - Database design
5. [Orchestration](05-orchestration.md) - Job scheduling
6. [Visualization](06-visualization.md) - Grafana dashboards
7. [Implementation Plan](07-implementation-plan.md) - Development roadmap
8. [Technology Stack](08-technology-stack.md) - All technologies used

## Support

For issues or questions, refer to the detailed documentation in the respective files above.
