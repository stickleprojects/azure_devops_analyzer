# Repository-Level Parallelization Plan

## Overview

This document outlines the plan to adjust repository processing to split work across multiple Celery workers. Instead of processing per-organization, we'll process per-repository to better utilize worker parallelization while avoiding rate throttling on both GitHub and Azure DevOps.

**Created**: January 19, 2026

---

## 1. Architecture Overview

### Current Flow

```
Single Task → Process All Orgs → Process All Repos (Sequential)
```

### New Flow

```
Coordinator Task → Discover Repos → Queue Individual Repo Tasks → Workers Process in Parallel
```

### Redis Role in This Plan

**Redis** serves as a distributed coordination layer for **rate limit management** across the worker pool. Since GitHub and Azure DevOps enforce strict API rate limits (GitHub: 5000 requests/hour, Azure DevOps: 150 requests/minute), multiple concurrent workers must share a single rate limit budget. Redis implements a token bucket mechanism that:

- Tracks cumulative API requests across all workers in real-time
- Provides atomic operations to acquire/release rate limit tokens
- Prevents individual workers from independently consuming the shared quota, which would cause violations
- Allows dynamic adjustment of rate limits based on API response headers

Without Redis coordination, each worker would operate in isolation and likely exceed platform rate limits collectively. With Redis, the rate limiter acts as a shared "gatekeeper" ensuring the entire worker pool stays within acceptable API usage boundaries.

---

## 2. Key Components to Modify

### A. Task Structure Changes

#### 1. New Coordinator Task (`discover_and_queue_repositories`)

- Fetches all organizations
- Fetches all repositories for each organization
- Filters repositories based on `should_scan_repository` check
- Queues individual repository processing tasks with rate limiting

#### 2. New Repository Processing Task (`process_single_repository`)

- Processes a single repository (branches, commits, PRs, dependencies)
- Includes retry logic with exponential backoff
- Handles rate limit errors gracefully

#### 3. Rate Limiter Helper (new module: `src/scheduler/rate_limiter.py`)

- Token bucket or Redis-based rate limiter
- Platform-specific (GitHub vs Azure DevOps)
- Coordinates across multiple workers using Redis

### B. Database Schema Changes

Add a new table for tracking task execution (optional but recommended):

```sql
CREATE TABLE repository_task_log (
    id SERIAL PRIMARY KEY,
    repository_id VARCHAR(255),
    task_id VARCHAR(255),
    status VARCHAR(50), -- pending, running, completed, failed
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    retry_count INT DEFAULT 0
);
```

---

## 3. Rate Limiting Strategy

### GitHub Rate Limits

- **5000 requests/hour** for authenticated requests
- Use Redis to track request count per hour
- Reserve 20% buffer (4000 usable requests/hour)
- Calculate delay between tasks based on worker count

### Azure DevOps Rate Limits

- **150 requests/minute** (more restrictive)
- Use Redis to track requests per minute
- Reserve 20% buffer (120 usable requests/minute)
- More aggressive throttling required

### Implementation Approach

- Use **Celery rate limits** + **Redis semaphore**
- Each repository task acquires tokens before API calls
- Workers wait/retry if rate limit approached
- Monitor rate limit headers and adjust dynamically

---

## 4. Celery Configuration Changes

```python
# Celery task routing and rate limiting
celery_app.conf.task_routes = {
    'tasks.process_single_repository': {
        'queue': 'repo_processing',
        'rate_limit': '10/m'  # Adjust based on worker count
    },
    'tasks.discover_and_queue_repositories': {
        'queue': 'coordination'
    }
}

# Task prioritization
celery_app.conf.task_default_priority = 5
celery_app.conf.task_priority_steps = 10
```

---

## 5. Worker Configuration

Deploy multiple workers with different configurations:

- **Coordinator Worker**: 1 instance, handles discovery
- **Repository Workers**: N instances (e.g., 5-10), process repositories
- Use Celery autoscaling: `--autoscale=10,3`

Example worker startup:

```bash
# Coordinator worker
celery -A src.scheduler.celery_app worker --queue=coordination --concurrency=1

# Repository processing workers
celery -A src.scheduler.celery_app worker --queue=repo_processing --autoscale=10,3
```

---

## 6. Error Handling & Retry Logic

```python
@celery_app.task(
    bind=True,
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,  # 10 minutes
    retry_jitter=True,
    autoretry_for=(RateLimitError, ConnectionError)
)
def process_single_repository(self, repo_id, org_name, platform):
    # Implementation
    pass
```

---

## 7. Monitoring & Observability

- Add Celery Flower for task monitoring
- Log rate limit consumption metrics
- Track processing time per repository
- Alert on failed tasks

### Recommended Metrics

- Repositories processed per hour
- Average processing time per repository
- API rate limit consumption (requests/hour)
- Task failure rate
- Worker utilization

---

## 8. Platform Compatibility

### GitHub Compatibility

- ✅ PyGithub library handles rate limits (returns headers)
- ✅ Can check `core_rate_limit` and `search_rate_limit`
- ✅ Built-in retry mechanisms available
- **Rate Limit**: 5000 requests/hour (authenticated)

### Azure DevOps Compatibility

- ✅ Azure SDK provides retry policies
- ✅ Rate limit info in response headers (`X-RateLimit-*`)
- ⚠️ More restrictive limits, needs careful tuning
- **Rate Limit**: 150 requests/minute (9000/hour)

---

## 9. Implementation Files

### New Files to Create

1. **`src/scheduler/rate_limiter.py`**
   - Redis-based rate limiter
   - Platform-specific rate limit management
   - Token bucket algorithm implementation

2. **`src/scheduler/repository_tasks.py`**
   - `discover_and_queue_repositories` task
   - `process_single_repository` task
   - Task coordination logic

3. **`src/workflows/repository_workflow.py`**
   - Single repository processing logic
   - Extracted from `GitHubAnalysisWorkflow`
   - Platform-agnostic interface

4. **`database/migrations/005_add_repository_task_log.sql`**
   - Create task tracking table
   - Add indexes for performance

### Files to Modify

1. **`src/scheduler/tasks.py`**
   - Import new tasks
   - Update existing `run_github_extraction` to use coordinator
   - Add backward compatibility

2. **`src/scheduler/celery_app.py`**
   - Update Celery configuration
   - Add task routing
   - Configure rate limits

3. **`src/workflows/github_analysis.py`**
   - Extract single-repository processing logic
   - Keep coordinator logic
   - Maintain backward compatibility

4. **`config/scheduler.yaml`**
   - Add rate limit configuration
   - Add worker configuration
   - Add retry policies

5. **`docker-compose.yml`**
   - Add multiple worker services
   - Add Redis service (if not present)
   - Configure worker scaling

6. **`requirements.txt`**
   - Add `redis` package
   - Add `celery[redis]` if not present
   - Add `flower` for monitoring

---

## 10. Migration Strategy

### Phase 1: Preparation (Day 1-2)

- [ ] Add `redis` to requirements.txt
- [ ] Create rate limiter module (`rate_limiter.py`)
- [ ] Extract single-repository processing logic
- [ ] Add configuration parameters to `scheduler.yaml`
- [ ] Create database migration for task tracking

### Phase 2: Implementation (Day 3-5)

- [ ] Create new Celery tasks in `repository_tasks.py`
- [ ] Create `repository_workflow.py` module
- [ ] Update `celery_app.py` configuration
- [ ] Modify `github_analysis.py` to use new tasks
- [ ] Add backward compatibility flag

### Phase 3: Testing (Day 6-7)

- [ ] Test with single worker (should work as before)
- [ ] Test with 2-3 workers on small dataset
- [ ] Monitor rate limiting behavior
- [ ] Test error handling and retry logic
- [ ] Validate database task tracking

### Phase 4: Deployment (Day 8-10)

- [ ] Update `docker-compose.yml` with multiple workers
- [ ] Deploy with gradual worker scaling (1→3→5→10)
- [ ] Monitor API rate consumption
- [ ] Adjust rate limits dynamically
- [ ] Deploy Celery Flower for monitoring

---

## 11. Expected Benefits

### Performance

- **5-10x faster** processing with 5-10 workers
- Parallel processing of repositories
- Better resource utilization

### Scalability

- Can handle more organizations/repositories
- Horizontal scaling by adding more workers
- Independent scaling of coordinator vs workers

### Resilience

- Individual repository failures don't block others
- Automatic retries with exponential backoff
- Better error isolation

### Flexibility

- Can prioritize certain repositories/organizations
- Dynamic rate limit adjustment
- Easy to add new platforms

---

## 12. Configuration Example

Add to `config/scheduler.yaml`:

```yaml
# Rate limiting configuration
rate_limits:
  github:
    requests_per_hour: 4000 # 80% of 5000
    max_concurrent_workers: 10
    backoff_threshold: 100 # requests remaining before slowdown
    requests_per_repository: 50 # Average API calls per repo

  azure_devops:
    requests_per_minute: 120 # 80% of 150
    max_concurrent_workers: 5
    backoff_threshold: 20
    requests_per_repository: 30

# Celery worker configuration
celery:
  worker_concurrency: 4 # Per worker process
  max_repository_workers: 10
  task_soft_time_limit: 600 # 10 minutes per repo
  task_hard_time_limit: 900 # 15 minutes hard limit
  retry_backoff_max: 600 # 10 minutes max backoff
  max_retries: 3

# Task routing
task_routing:
  coordination_queue: coordination
  repository_queue: repo_processing
```

---

## 13. Risk Mitigation

### Risk: Rate Limit Violations

**Impact**: API throttling, failed requests  
**Mitigation**:

- Conservative rate limits (80% of max)
- Redis coordination across workers
- Exponential backoff on failures
- Monitor rate limit headers

### Risk: Database Connection Pool Exhaustion

**Impact**: Failed database operations  
**Mitigation**:

- Use session pooling
- Shorter-lived sessions per task
- Configure appropriate pool size
- Monitor connection usage

### Risk: Stuck/Zombie Tasks

**Impact**: Workers blocked, wasted resources  
**Mitigation**:

- Hard time limits on tasks
- Health checks on workers
- Auto-restart workers
- Task timeout monitoring

### Risk: Uneven Work Distribution

**Impact**: Some workers idle, others overloaded  
**Mitigation**:

- Celery's fair task distribution
- Task priorities for important repos
- Monitor queue depths
- Dynamic worker scaling

### Risk: Redis Single Point of Failure

**Impact**: Rate limiter fails, coordination issues  
**Mitigation**:

- Redis persistence enabled
- Fallback to per-worker rate limiting
- Redis health monitoring
- Consider Redis Sentinel for HA

---

## 14. Docker Compose Updates

Example additions to `docker-compose.yml`:

```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  celery-coordinator:
    build: .
    command: celery -A src.scheduler.celery_app worker --queue=coordination --concurrency=1 --loglevel=info
    environment:
      - CELERY_BROKER_URL=amqp://analyzer:analyzer@rabbitmq:5672//
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - rabbitmq
      - redis

  celery-worker:
    build: .
    command: celery -A src.scheduler.celery_app worker --queue=repo_processing --autoscale=10,3 --loglevel=info
    environment:
      - CELERY_BROKER_URL=amqp://analyzer:analyzer@rabbitmq:5672//
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - rabbitmq
      - redis
    deploy:
      replicas: 5 # Scale to 5 worker instances

  flower:
    build: .
    command: celery -A src.scheduler.celery_app flower --port=5555
    ports:
      - "5555:5555"
    environment:
      - CELERY_BROKER_URL=amqp://analyzer:analyzer@rabbitmq:5672//
    depends_on:
      - rabbitmq

volumes:
  redis_data:
```

---

## 15. Success Metrics

### Performance Metrics

- [ ] Processing time reduced by 5-10x
- [ ] All repositories processed within 4 hours
- [ ] Worker utilization > 70%

### Reliability Metrics

- [ ] Task failure rate < 2%
- [ ] Retry success rate > 90%
- [ ] No rate limit violations

### Operational Metrics

- [ ] Zero manual intervention required
- [ ] All failures automatically retried
- [ ] Monitoring dashboard operational

---

## 16. Next Steps

1. **Review this plan** with the team
2. **Estimate effort** for each phase
3. **Set up development environment** with Redis
4. **Begin Phase 1** implementation
5. **Schedule testing window** for Phase 3

---

## 17. References

- [Celery Documentation - Routing Tasks](https://docs.celeryq.dev/en/stable/userguide/routing.html)
- [GitHub API Rate Limiting](https://docs.github.com/en/rest/overview/resources-in-the-rest-api#rate-limiting)
- [Azure DevOps Rate Limits](https://learn.microsoft.com/en-us/azure/devops/integrate/concepts/rate-limits)
- [Redis Rate Limiting Patterns](https://redis.io/docs/manual/patterns/rate-limiting/)
- [Celery Flower Monitoring](https://flower.readthedocs.io/)

---

## Appendix A: API Call Estimates

### GitHub Repository Processing

- Get repository metadata: 1 request
- Get branches: 1 request
- Get README files: 1-2 requests
- Get commits (50): 1 request
- Get pull requests (20): 1 request
- Get PR details (reviews, comments): 20-40 requests
- Get file tree: 1 request
- **Total per repository: ~25-50 API calls**

### Azure DevOps Repository Processing

- Get repository metadata: 1 request
- Get branches: 1 request
- Get commits: 1 request
- Get pull requests: 1 request
- Get PR details: 10-30 requests
- **Total per repository: ~15-35 API calls**

### Worker Calculation

With 4000 GitHub requests/hour and 40 calls per repo:

- **~100 repositories/hour** with single worker
- **~500 repositories/hour** with 5 workers (with coordination)
- **~1000 repositories/hour** with 10 workers (with coordination)

---

## Appendix B: Testing Checklist

### Unit Tests

- [ ] Rate limiter token acquisition
- [ ] Rate limiter token release
- [ ] Repository workflow single repo processing
- [ ] Error handling and retries
- [ ] Configuration validation

### Integration Tests

- [ ] Coordinator task discovery
- [ ] Repository task processing
- [ ] Redis coordination
- [ ] Database task tracking
- [ ] Multi-worker coordination

### Load Tests

- [ ] 10 repositories with 1 worker
- [ ] 10 repositories with 3 workers
- [ ] 100 repositories with 5 workers
- [ ] Rate limit compliance
- [ ] Error recovery

### Platform Tests

- [ ] GitHub repository processing
- [ ] Azure DevOps repository processing
- [ ] Mixed platform processing
- [ ] Rate limit handling per platform

---

**Document Status**: ✅ Ready for Review  
**Last Updated**: January 19, 2026  
**Owner**: Development Team
