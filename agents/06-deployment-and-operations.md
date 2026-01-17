# Deployment and Operations Agent

## Purpose
This agent handles deployment, monitoring, and operational concerns to ensure smooth production releases and reliable system operation.

## Core Responsibilities

### 1. Deployment Management
- Plan and execute safe deployments
- Implement rollback strategies
- Manage environment configurations
- Coordinate release schedules
- Ensure zero-downtime deployments

### 2. Monitoring and Observability
- Set up logging, metrics, and tracing
- Configure alerts and notifications
- Create dashboards for visibility
- Track system health and performance
- Monitor error rates and anomalies

### 3. Incident Response
- Detect and diagnose issues quickly
- Implement fixes or rollbacks
- Communicate status to stakeholders
- Conduct post-incident reviews
- Document lessons learned

### 4. Infrastructure Management
- Provision and configure infrastructure
- Implement security hardening
- Manage scaling and capacity
- Optimize costs
- Maintain disaster recovery plans

## Deployment Strategies

### Blue-Green Deployment
```
Production Traffic
      ↓
[Load Balancer]
      ├─→ Blue Environment (Current v1.0) ← 100% traffic
      └─→ Green Environment (New v1.1) ← 0% traffic

After validation:
      ├─→ Blue Environment (Old v1.0) ← 0% traffic [Keep for rollback]
      └─→ Green Environment (New v1.1) ← 100% traffic
```

**Advantages:**
- Instant rollback by switching traffic back
- Full environment testing before going live
- Zero downtime

**Implementation:**
```yaml
# docker-compose.blue-green.yml
version: '3.8'

services:
  app-blue:
    image: myapp:v1.0
    environment:
      - VERSION=blue
    networks:
      - app-network

  app-green:
    image: myapp:v1.1
    environment:
      - VERSION=green
    networks:
      - app-network

  nginx:
    image: nginx:latest
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    ports:
      - "80:80"
    networks:
      - app-network
```

### Canary Deployment
```
Production Traffic
      ↓
[Load Balancer]
      ├─→ Stable v1.0 ← 95% traffic
      └─→ Canary v1.1 ← 5% traffic

Monitor canary metrics, gradually increase:
      ├─→ Stable v1.0 ← 50% traffic
      └─→ Canary v1.1 ← 50% traffic

Finally:
      └─→ New Stable v1.1 ← 100% traffic
```

**Advantages:**
- Gradual rollout reduces risk
- Real user testing with minimal impact
- Easy to detect issues early

**Implementation with Kubernetes:**
```yaml
# canary-deployment.yaml
apiVersion: v1
kind: Service
metadata:
  name: myapp
spec:
  selector:
    app: myapp
  ports:
    - port: 80

---
# Stable deployment (95% traffic)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp-stable
spec:
  replicas: 19  # 95% of traffic
  selector:
    matchLabels:
      app: myapp
      version: stable
  template:
    metadata:
      labels:
        app: myapp
        version: stable
    spec:
      containers:
      - name: myapp
        image: myapp:v1.0

---
# Canary deployment (5% traffic)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp-canary
spec:
  replicas: 1  # 5% of traffic
  selector:
    matchLabels:
      app: myapp
      version: canary
  template:
    metadata:
      labels:
        app: myapp
        version: canary
    spec:
      containers:
      - name: myapp
        image: myapp:v1.1
```

### Rolling Deployment
```
Initial State: [v1.0] [v1.0] [v1.0] [v1.0]

Step 1:        [v1.1] [v1.0] [v1.0] [v1.0]
Step 2:        [v1.1] [v1.1] [v1.0] [v1.0]
Step 3:        [v1.1] [v1.1] [v1.1] [v1.0]
Step 4:        [v1.1] [v1.1] [v1.1] [v1.1]
```

**Advantages:**
- No additional infrastructure needed
- Gradual replacement of instances
- Can pause and rollback at any step

**Implementation:**
```yaml
# kubernetes-rolling.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 4
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1        # Max 1 extra pod during update
      maxUnavailable: 1  # Max 1 pod can be unavailable
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: myapp
        image: myapp:v1.1
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
```

## CI/CD Pipeline

### Complete Pipeline Example
```yaml
# .github/workflows/deploy.yml
name: Deploy Pipeline

on:
  push:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run linter
        run: npm run lint

      - name: Run unit tests
        run: npm run test:unit

      - name: Run integration tests
        run: npm run test:integration

      - name: Check test coverage
        run: npm run test:coverage
        env:
          COVERAGE_THRESHOLD: 80

  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run Snyk security scan
        uses: snyk/actions/node@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}

      - name: Run OWASP dependency check
        run: npm audit --audit-level=moderate

  build:
    needs: [test, security-scan]
    runs-on: ubuntu-latest
    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
    steps:
      - uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Login to Container Registry
        uses: docker/login-action@v2
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v4
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=sha,prefix={{branch}}-

      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - name: Deploy to staging
        run: |
          kubectl set image deployment/myapp \
            myapp=${{ needs.build.outputs.image-tag }} \
            --namespace=staging

      - name: Wait for rollout
        run: |
          kubectl rollout status deployment/myapp \
            --namespace=staging \
            --timeout=5m

      - name: Run smoke tests
        run: |
          curl -f https://staging.example.com/health || exit 1
          npm run test:e2e:staging

  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Deploy to production (canary)
        run: |
          # Deploy canary with 5% traffic
          kubectl apply -f k8s/canary-deployment.yaml

      - name: Monitor canary metrics
        run: |
          # Wait 10 minutes and check error rates
          sleep 600
          ./scripts/check-canary-health.sh || exit 1

      - name: Promote canary to stable
        run: |
          kubectl set image deployment/myapp-stable \
            myapp=${{ needs.build.outputs.image-tag }} \
            --namespace=production

      - name: Cleanup canary
        run: |
          kubectl delete deployment myapp-canary \
            --namespace=production
```

## Monitoring and Observability

### The Three Pillars

#### 1. Logging
```javascript
// Structured logging with Winston
const winston = require('winston');

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  defaultMeta: {
    service: 'user-service',
    version: process.env.APP_VERSION
  },
  transports: [
    new winston.transports.File({ filename: 'error.log', level: 'error' }),
    new winston.transports.File({ filename: 'combined.log' })
  ]
});

// In production, log to stdout for container logging
if (process.env.NODE_ENV === 'production') {
  logger.add(new winston.transports.Console({
    format: winston.format.simple()
  }));
}

// Usage with context
app.post('/api/users', async (req, res) => {
  const correlationId = req.headers['x-correlation-id'] || uuidv4();

  logger.info('Creating user', {
    correlationId,
    email: req.body.email,
    userAgent: req.headers['user-agent']
  });

  try {
    const user = await createUser(req.body);

    logger.info('User created successfully', {
      correlationId,
      userId: user.id
    });

    res.status(201).json(user);
  } catch (error) {
    logger.error('Failed to create user', {
      correlationId,
      error: error.message,
      stack: error.stack
    });

    res.status(500).json({ error: 'Internal server error' });
  }
});
```

#### 2. Metrics
```python
# Prometheus metrics with Flask
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from flask import Flask, Response
import time

app = Flask(__name__)

# Define metrics
request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

active_users = Gauge(
    'active_users',
    'Number of active users'
)

db_connection_pool = Gauge(
    'db_connection_pool_size',
    'Database connection pool size'
)

# Middleware to track metrics
@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request
def after_request(response):
    duration = time.time() - request.start_time

    request_count.labels(
        method=request.method,
        endpoint=request.endpoint,
        status=response.status_code
    ).inc()

    request_duration.labels(
        method=request.method,
        endpoint=request.endpoint
    ).observe(duration)

    return response

# Expose metrics endpoint
@app.route('/metrics')
def metrics():
    return Response(generate_latest(), mimetype='text/plain')

# Business metrics
@app.route('/api/orders', methods=['POST'])
def create_order():
    order = process_order(request.json)

    # Track business metric
    order_value.labels(currency='USD').observe(order.total)

    return jsonify(order), 201
```

#### 3. Distributed Tracing
```javascript
// OpenTelemetry tracing
const { NodeTracerProvider } = require('@opentelemetry/sdk-trace-node');
const { registerInstrumentations } = require('@opentelemetry/instrumentation');
const { HttpInstrumentation } = require('@opentelemetry/instrumentation-http');
const { ExpressInstrumentation } = require('@opentelemetry/instrumentation-express');
const { JaegerExporter } = require('@opentelemetry/exporter-jaeger');

// Initialize tracer
const provider = new NodeTracerProvider();
const exporter = new JaegerExporter({
  endpoint: 'http://jaeger:14268/api/traces'
});

provider.addSpanProcessor(
  new BatchSpanProcessor(exporter)
);

provider.register();

// Auto-instrument HTTP and Express
registerInstrumentations({
  instrumentations: [
    new HttpInstrumentation(),
    new ExpressInstrumentation()
  ]
});

// Manual instrumentation for custom spans
const tracer = provider.getTracer('user-service');

async function processOrder(orderId) {
  const span = tracer.startSpan('process_order');
  span.setAttribute('order.id', orderId);

  try {
    // Validate order
    const validateSpan = tracer.startSpan('validate_order', {
      parent: span
    });
    await validateOrder(orderId);
    validateSpan.end();

    // Process payment
    const paymentSpan = tracer.startSpan('process_payment', {
      parent: span
    });
    const payment = await processPayment(orderId);
    paymentSpan.setAttribute('payment.amount', payment.amount);
    paymentSpan.end();

    // Update inventory
    const inventorySpan = tracer.startSpan('update_inventory', {
      parent: span
    });
    await updateInventory(orderId);
    inventorySpan.end();

    span.setStatus({ code: SpanStatusCode.OK });
    return { success: true };

  } catch (error) {
    span.setStatus({
      code: SpanStatusCode.ERROR,
      message: error.message
    });
    span.recordException(error);
    throw error;

  } finally {
    span.end();
  }
}
```

### Alerting Rules

```yaml
# prometheus-alerts.yml
groups:
  - name: application
    interval: 30s
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m])) by (service)
          /
          sum(rate(http_requests_total[5m])) by (service)
          > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate on {{ $labels.service }}"
          description: "Error rate is {{ $value | humanizePercentage }}"

      # High latency
      - alert: HighLatency
        expr: |
          histogram_quantile(0.95,
            rate(http_request_duration_seconds_bucket[5m])
          ) > 1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected"
          description: "P95 latency is {{ $value }}s"

      # Low success rate
      - alert: LowSuccessRate
        expr: |
          sum(rate(http_requests_total{status=~"2.."}[5m]))
          /
          sum(rate(http_requests_total[5m]))
          < 0.95
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Success rate dropped below 95%"

      # High memory usage
      - alert: HighMemoryUsage
        expr: |
          (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes)
          /
          node_memory_MemTotal_bytes
          > 0.90
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage on {{ $labels.instance }}"
          description: "Memory usage is {{ $value | humanizePercentage }}"

      # Pod restarts
      - alert: PodRestartingFrequently
        expr: |
          rate(kube_pod_container_status_restarts_total[1h]) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Pod {{ $labels.pod }} is restarting frequently"
```

### Dashboards

#### Grafana Dashboard JSON
```json
{
  "dashboard": {
    "title": "Application Overview",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "sum(rate(http_requests_total[5m])) by (service)"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "sum(rate(http_requests_total{status=~\"5..\"}[5m])) by (service)"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Latency (P95)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Active Users",
        "targets": [
          {
            "expr": "active_users"
          }
        ],
        "type": "stat"
      }
    ]
  }
}
```

## Infrastructure as Code

### Terraform Example
```hcl
# main.tf
provider "aws" {
  region = var.aws_region
}

# VPC
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "${var.project_name}-vpc"
    Environment = var.environment
  }
}

# Subnets
resource "aws_subnet" "public" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "${var.project_name}-public-${count.index}"
  }
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# ECS Task Definition
resource "aws_ecs_task_definition" "app" {
  family                   = "${var.project_name}-app"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"

  container_definitions = jsonencode([
    {
      name      = "app"
      image     = "${var.ecr_repository}:${var.app_version}"
      essential = true

      portMappings = [
        {
          containerPort = 8080
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "NODE_ENV"
          value = var.environment
        }
      ]

      secrets = [
        {
          name      = "DATABASE_URL"
          valueFrom = aws_secretsmanager_secret.db_url.arn
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.app.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])
}

# ECS Service with Auto Scaling
resource "aws_ecs_service" "app" {
  name            = "${var.project_name}-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.app_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.app.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "app"
    container_port   = 8080
  }

  depends_on = [aws_lb_listener.app]
}

# Auto Scaling
resource "aws_appautoscaling_target" "ecs" {
  max_capacity       = 10
  min_capacity       = 2
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.app.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "cpu" {
  name               = "${var.project_name}-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 70.0
  }
}
```

## Incident Response

### Incident Response Runbook

#### 1. Detection
```markdown
**Symptoms:**
- Alert fired: HighErrorRate on user-service
- Users reporting 500 errors on login
- Monitoring dashboard shows spike in errors

**Initial Assessment:**
1. Check alert details and affected services
2. Verify scope: How many users affected?
3. Determine severity level
4. Start incident channel/war room
```

#### 2. Triage
```bash
# Check service health
kubectl get pods -n production
kubectl logs -n production user-service-xyz --tail=100

# Check recent deployments
kubectl rollout history deployment/user-service -n production

# Check resource usage
kubectl top pods -n production

# Check external dependencies
curl -I https://external-api.example.com/health
```

#### 3. Mitigation
```markdown
**Quick Fixes:**

Option 1: Rollback recent deployment
```bash
kubectl rollout undo deployment/user-service -n production
kubectl rollout status deployment/user-service -n production
```

Option 2: Scale up if resource constrained
```bash
kubectl scale deployment/user-service --replicas=10 -n production
```

Option 3: Toggle feature flag
```bash
curl -X POST https://api.launchdarkly.com/api/v2/flags/feature-key \
  -H "Authorization: $LD_API_KEY" \
  -d '{"enabled": false}'
```

#### 4. Communication
```markdown
**Status Update Template:**

INCIDENT: Production login failures
STATUS: Investigating | Identified | Monitoring | Resolved
IMPACT: 30% of login attempts failing
ACTIONS: Rolled back deployment to v1.2.3
ETA: Monitoring for 15 minutes before declaring resolved

Last updated: 2024-01-15 14:30 UTC
Next update: 2024-01-15 14:45 UTC
```

#### 5. Resolution
```markdown
**Verification:**
- [ ] Error rate back to normal (<0.1%)
- [ ] Latency within acceptable range (<200ms p95)
- [ ] No user reports of issues
- [ ] All health checks passing
- [ ] Monitoring for 30 minutes with no recurrence

**Close Incident:**
- Update status page
- Notify stakeholders
- Schedule post-incident review
```

### Post-Incident Review Template
```markdown
# Post-Incident Review: [Incident Title]

**Date:** [Date]
**Duration:** [Total time from detection to resolution]
**Severity:** Critical | High | Medium | Low
**Incident Lead:** [Name]

## Summary
[Brief description of what happened]

## Timeline
- **14:00 UTC** - Alert fired: HighErrorRate
- **14:02 UTC** - Team notified, incident channel created
- **14:05 UTC** - Identified recent deployment as likely cause
- **14:10 UTC** - Rollback initiated
- **14:15 UTC** - Rollback complete, error rate decreasing
- **14:30 UTC** - Error rate normal, monitoring
- **15:00 UTC** - Incident resolved

## Root Cause
[Detailed explanation of what caused the incident]

## Impact
- **Users Affected:** ~10,000 (30% of active users)
- **Duration:** 1 hour
- **Failed Requests:** ~50,000
- **Revenue Impact:** Estimated $5,000

## What Went Well
- Alert fired quickly (within 2 minutes)
- Team responded immediately
- Rollback was straightforward
- Communication was clear and timely

## What Went Wrong
- Deployment pipeline didn't catch the bug
- Canary deployment percentage was too high (25%)
- No automated rollback on high error rate
- Insufficient integration tests for this scenario

## Action Items
1. **[Owner: Dev Team]** Add integration test for X scenario - Due: 2024-01-20
2. **[Owner: DevOps]** Reduce canary percentage to 5% - Due: 2024-01-17
3. **[Owner: DevOps]** Implement automated rollback on error threshold - Due: 2024-01-25
4. **[Owner: QA]** Add scenario to smoke test suite - Due: 2024-01-22
5. **[Owner: Team Lead]** Review and update deployment checklist - Due: 2024-01-18

## Lessons Learned
- Gradual rollout is critical for catching issues early
- Automated rollback would have reduced impact significantly
- Need better visibility into canary metrics during deployment
```

## Security Operations

### Security Checklist
```markdown
## Infrastructure Security
- [ ] All services use TLS/HTTPS
- [ ] SSH key-based authentication only (no passwords)
- [ ] Firewall rules follow principle of least privilege
- [ ] VPC/Network segmentation implemented
- [ ] Bastion host for administrative access
- [ ] Regular security patches applied

## Application Security
- [ ] Secrets stored in secrets manager (not environment variables)
- [ ] API rate limiting enabled
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (output encoding)
- [ ] CSRF protection enabled
- [ ] Security headers configured (CSP, HSTS, etc.)

## Access Control
- [ ] Role-based access control (RBAC) implemented
- [ ] Principle of least privilege applied
- [ ] MFA enabled for all production access
- [ ] Regular access reviews conducted
- [ ] Audit logging enabled
- [ ] Service accounts have minimal permissions

## Monitoring and Response
- [ ] Security alerts configured
- [ ] Failed authentication attempts monitored
- [ ] Unusual traffic patterns detected
- [ ] Vulnerability scanning automated
- [ ] Incident response plan documented
- [ ] Security patches applied within SLA
```

## Handoff Checklist

Before declaring deployment complete:
- [ ] Application deployed successfully to all environments
- [ ] Health checks passing
- [ ] Smoke tests completed
- [ ] Monitoring dashboards show normal metrics
- [ ] Alerts are configured and tested
- [ ] Logs are flowing correctly
- [ ] No increase in error rates
- [ ] Performance metrics within acceptable range
- [ ] Rollback plan tested and documented
- [ ] On-call team notified of deployment
- [ ] Documentation updated
- [ ] Stakeholders informed

## Key Operational Metrics

### Service Level Indicators (SLIs)
- **Availability**: % of successful requests
- **Latency**: Request duration (p50, p95, p99)
- **Error Rate**: % of failed requests
- **Throughput**: Requests per second

### Service Level Objectives (SLOs)
- **Availability**: 99.9% uptime (43 minutes downtime/month)
- **Latency**: p95 < 200ms, p99 < 500ms
- **Error Rate**: < 0.1% of requests
- **Throughput**: Handle 10,000 RPS

### Service Level Agreements (SLAs)
- **Availability**: 99.5% uptime guaranteed
- **Support Response**: Critical issues < 1 hour
- **Data Recovery**: RPO < 1 hour, RTO < 4 hours

## Best Practices Summary

1. **Deploy frequently, deploy safely** - Small, incremental changes with automated rollback
2. **Monitor everything** - Logs, metrics, traces for full observability
3. **Automate relentlessly** - CI/CD, testing, deployments, alerts
4. **Plan for failure** - Graceful degradation, circuit breakers, retries
5. **Practice incident response** - Regular drills, clear runbooks
6. **Learn from incidents** - Post-incident reviews, actionable improvements
7. **Security by default** - Build security into every layer
8. **Cost awareness** - Monitor and optimize cloud spending

Remember: Operations is not just about keeping the lights on—it's about enabling the team to ship quickly and safely.

## Session Resumption

When resuming a deployment/operations session:

1. **Review Current State**
   - Check current deployment status across environments
   - Review any active incidents or alerts
   - Identify in-progress rollouts or changes

2. **Context to Provide**
   - Deployment status (which version where)
   - Active alerts or incidents
   - Pending infrastructure changes
   - Rollback state if applicable

3. **Session Handoff Notes**
   - Update [11-session-continuity.md](../docs/11-session-continuity.md) with:
     - Deployments completed this session
     - Infrastructure changes made
     - Incidents encountered and resolution
     - Pending operations work

4. **Quick Status Commands**
   ```bash
   # Check deployment status
   docker-compose ps
   kubectl get deployments -A

   # Check service health
   curl http://localhost:8080/health

   # Check logs
   docker-compose logs --tail=50
   ```

5. **Critical State Information**
   Always note:
   - Current production version
   - Last successful deployment time
   - Any rollback performed
   - Active feature flags

See [Session Continuity Guide](../docs/11-session-continuity.md) for detailed handoff procedures.
