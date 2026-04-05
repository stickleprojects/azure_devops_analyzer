# Visualization Layer — Grafana Dashboards

## Overview

Grafana provides interactive dashboards to visualize all collected metrics and enable data-driven insights about repository health, code quality, and team performance. All dashboards are stored in `dashboards/` and auto-provisioned by Grafana on startup.

## Grafana Setup

Grafana connects to the PostgreSQL/TimescaleDB database using a dedicated read-only user. TimescaleDB support is enabled in the data source configuration. Access Grafana at `http://localhost:3000` after running `docker compose up`.

## Capturing Screenshots

Screenshots in `docs/images/screenshots/` are captured manually from a running stack. See [docs/images/screenshots/README.md](../images/screenshots/README.md) for instructions.

---

## Implemented Dashboards

### 1. Dashboard Home (`dashboard-home.json`)

**UID**: `dashboard-home`
**Purpose**: Entry point and navigation hub for the system

**Panels**:

- **Welcome**: Markdown introduction and quick-start guidance
- **Summary Stats**: Total Repositories, Active Contributors (30d), Commits (30d), Pull Requests (30d), Teams, Open PRs
- **Dashboard Navigation**: Nav cards linking to all other dashboards (Repository Overview, Deep-Dive, Pull Requests, Contributors, Team Overview, Service Overview, Administration)

---

### 2. Team Overview (`team-overview.json`)

**UID**: `team-overview`
**Purpose**: High-level team metrics aggregated across all repositories

**Sections**:

- **Team Summary**: 6 stat panels — repositories, active contributors, commits, PRs created/merged, open PRs
- **Team Activity Trends**: Commit activity, PR throughput, daily active contributors, lines changed
- **Repository Health Matrix**: Color-coded table with commits, contributors, open PRs, vulnerabilities, stale branches — click to drill down
- **Team Velocity & Quality**: PR merge time, approvals, vulnerabilities by severity, top languages
- **Top Contributors**: Bar charts for top 10 by commits and reviews
- **Recent Activity**: Table of PRs from last 7 days

---

### 3. Repository Overview (`repository-overview.json`)

**UID**: `repo-overview`
**Purpose**: List and compare all repositories

**Panels**:

- **Total Repositories**: Count of active repositories
- **Total Commits/PRs/Contributors**: Aggregate stats
- **Commit Activity**: Time series of commits per day (30 days)
- **Top 10 Active Repositories**: Table with clickable repo names → Deep-Dive
- **All Repositories**: Full table with organization, branch, URLs, last analyzed, commit/PR counts

---

### 4. Repository Deep-Dive (`repository-deep-dive.json`)

**UID**: `repo-deep-dive`
**Purpose**: Comprehensive view of a single repository selected via dropdown

**Template Variable**: Repository selector

**Sections**:

- **Header & Summary**: Repository name, total commits, PRs, contributors
- **Quick Health Indicators**: Active contributors, test coverage, vulnerabilities, open PRs, stale branches, tech debt
- **Development Activity**: Commit activity, lines changed, top contributors, top reviewers
- **Pull Request Health**: Status/size distribution, throughput, merge time, approvals, issues
- **Code Health**: Quality trends by severity, test coverage trend, tech debt trend, maintainability/complexity gauges
- **Security & Dependencies**: Vulnerabilities by severity, outdated/EOL deps, ecosystems, vulnerability details table
- **Branch Health**: Active branches, staleness chart, divergence from main, branch details table
- **Technology Stack**: Language distribution donut, AI-generated summary
- **Recent Activity**: Recent commits table, open PRs table

---

### 5. Service Overview (`service-overview.json`)

**UID**: `service-overview`
**Purpose**: Metrics aggregated at the service level (a service groups one or more repositories)

**Sections**:

- **Service Summary**: Total Repositories, Active Repositories, Unique Contributors, Total Commits, PRs Merged, Critical Vulnerabilities — stat panels
- **Services at a Glance**: Table comparing all services
- **Activity Trends**: Commit Activity by Service (timeseries), PR Throughput Created vs Merged (timeseries)
- **Quality Metrics**: Avg Test Coverage, Avg Maintainability Index, Total Quality Issues, Avg PR Review Time — stats + timeseries
- **Security & Dependencies**: Critical/High Vulnerabilities, EOL Dependencies, Total Dependencies — stats + severity pie + vulnerability trend
- **Repository Breakdown**: Table of repositories with per-service drill-down

---

### 6. Pull Request Analysis (`pull-requests.json`)

**UID**: `pull-requests`
**Purpose**: Track PR quality and review efficiency across all repositories

**Panels**:

- **Open/Merged/Closed PRs**: Stat panels with 30-day counts
- **Avg PR Size**: Lines changed per PR
- **PR Status Distribution**: Pie chart (open/merged/closed)
- **PR Size Distribution**: Pie chart (small/medium/large/extra_large)
- **PR Throughput**: Created vs merged over time
- **Recent Pull Requests**: Table with clickable repo names → Deep-Dive

---

### 7. Contributor Analytics (`contributor-analytics.json`)

**UID**: `contributor-analytics`
**Purpose**: Developer activity across all repositories over the last 30 days

**Panels**:

- **Active Contributors (30 Days)**: Count stat panel
- **Commits (30 Days)**: Count stat panel
- **PR Reviews (30 Days)**: Count stat panel
- **Top 10 Contributors by Commits**: Bar chart
- **Top 10 Reviewers**: Bar chart
- **Contributor Activity Summary (30 Days)**: Full table with per-contributor breakdown

> **Note**: FR-8.2 (detailed contributor metrics) and FR-8.4 (active days) are implemented but currently paused for performance reasons. See `CONTRIBUTOR_METRICS_GUIDE.md`.

---

### 8. Security Dashboard (`security-dashboard.json`)

**UID**: `security-dashboard`
**Purpose**: Organization-wide security overview with vulnerability and end-of-life dependency tracking

**Sections**:

- **Organization Security Summary**: Total vulnerabilities, EOL dependencies, repositories affected
- **Vulnerability Analysis**: Severity distribution pie chart, top repositories by critical vulnerabilities
- **End-of-Life Dependencies**: EOL status categorization (expired, expiring soon, future), repository security overview table with drilldown links
- **Security Trends**: Time series of vulnerability counts over time
- **Top Vulnerable Dependencies**: Table of most problematic packages across repositories

---

### 9. Administration (`admin-dashboard.json`)

**UID**: `admin-dashboard`
**Purpose**: Centralized control panel for system administrators — extraction triggers, system status, and repository health monitoring

**Sections**:

- **Overview**: Markdown introduction to admin functions
- **Extraction Controls**: "Force Rescan — GitHub" and "Force Rescan — Azure DevOps" action links to `/api/rescan/{platform}`; "Compute Service Metrics" trigger; contextual help text
- **System Status**: Active Runs, Latest Run Progress %, API Health Check link, Celery Monitor (Flower) link
- **Extraction Activity**: Auth Failures (24h) stat, Extraction Rate timeseries (repos/hour)
- **Recent Runs**: Table of recent extraction runs with status and timing
- **Repository Staleness**: Contextual help text explaining staleness criteria; tables for Stale Repositories (7+ days), Never Scanned, and Recent Repository Activity with errors
- **Auth Errors**: Auth Errors by Platform (24h) table

---

## Code Quality Dashboard (Not Yet Implemented)

**Planned Purpose**: Monitor code health and technical debt

Planned panels:
- Code Quality Trends: time series of issue counts (Critical, High, etc.)
- Maintainability Index: gauge showing current score
- Issue Breakdown: bar chart of issues by category
- Top Files with Most Issues: table identifying hotspots
- Technical Debt Estimate: total estimated hours to remediate

Status blocked on FR-7.1–FR-7.5 (code quality analysis engine not yet built).

---

## Dashboard Navigation

All dashboards are cross-linked:

- **Header Links**: Each dashboard has navigation links to all other dashboards
- **Data Links**: Repository names in tables navigate to the Deep-Dive dashboard with that repository pre-selected
- **Time Preservation**: Navigation links preserve the current time range (`keepTime: true`)

---

## Dashboard Provisioning

Grafana provisioning auto-loads dashboards from `grafana/provisioning/` on startup. To modify a dashboard:

1. Edit via the Grafana UI
2. Export as JSON (Dashboard Settings → JSON Model)
3. Replace the corresponding file in `dashboards/`
4. Commit the updated JSON

### Exporting / Importing via API

```bash
# Export
curl -s http://admin:admin@localhost:3000/api/dashboards/uid/<uid> | jq '.dashboard'

# Import
curl -X POST -H "Content-Type: application/json" \
  -d @dashboards/<name>.json \
  http://admin:admin@localhost:3000/api/dashboards/import
```

---

## Performance Optimization

- **Materialized views** pre-aggregate complex metrics (e.g., repository health summaries) to improve dashboard load times
- **TimescaleDB hypertables** partition time-series data by time chunk for efficient range queries
- **Connection pooling** is configured in Grafana to manage database load

---

## Alerting Rules (Planned)

- **Critical Vulnerabilities**: Alert when new critical vulnerabilities are detected
- **Stale Repository**: Alert if a repository has not been analyzed in 7 days
- **Code Quality Degradation**: Alert if critical issues increase significantly between scans

---

## Checklist

- [x] Grafana installed and accessible (Docker Compose)
- [x] PostgreSQL data source configured (TimescaleDB)
- [x] Dashboard provisioning set up (`grafana/provisioning/`)
- [x] Dashboard Home (`dashboard-home.json`)
- [x] Team Overview dashboard (`team-overview.json`)
- [x] Repository Overview dashboard (`repository-overview.json`)
- [x] Repository Deep-Dive dashboard (`repository-deep-dive.json`)
- [x] Service Overview dashboard (`service-overview.json`)
- [x] Pull Request dashboard (`pull-requests.json`)
- [x] Contributor Analytics dashboard (`contributor-analytics.json`)
- [x] Security dashboard (`security-dashboard.json`)
- [x] Administration dashboard (`admin-dashboard.json`)
- [x] Cross-dashboard navigation links
- [x] Data links for drill-down navigation (repo → Deep-Dive)
- [ ] Code Quality dashboard
- [ ] Alerting rules configured

---

## Further Reading

- [requirements.md](../01-strategy/requirements.md) — FR-11 (Visualization) and FR-14 (Admin Dashboard) requirements
- [Grafana Documentation](https://grafana.com/docs/grafana/latest/)
- [Grafana PostgreSQL Data Source](https://grafana.com/docs/grafana/latest/datasources/postgres/)
- [Grafana Alerting](https://grafana.com/docs/grafana/latest/alerting/)
