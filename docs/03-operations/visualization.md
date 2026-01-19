# Visualization Layer - Grafana Dashboards

## Overview

Grafana provides interactive dashboards to visualize all collected metrics and enable data-driven insights about repository health, code quality, and team performance.

## Grafana Setup

Grafana is configured to connect to the PostgreSQL database using a dedicated read-only user. The data source is set up with TimescaleDB support enabled.

## Implemented Dashboards

All dashboards are stored in `dashboards/` and auto-provisioned by Grafana on startup. Each dashboard includes navigation links to all other dashboards.

### 1. Team Overview Dashboard (`team-overview.json`)

**UID**: `team-overview`
**Purpose**: High-level team metrics aggregated across all repositories

**Sections**:
- **Team Summary**: 6 stat panels (repositories, active contributors, commits, PRs created/merged, open PRs)
- **Team Activity Trends**: Commit activity, PR throughput, daily active contributors, lines changed
- **Repository Health Matrix**: Color-coded table showing all repos with commits, contributors, open PRs, vulnerabilities, stale branches - click to drill down
- **Team Velocity & Quality**: PR merge time, approvals, vulnerabilities by severity, top languages
- **Top Contributors**: Bar charts for top 10 by commits and reviews
- **Recent Activity**: Table of PRs from last 7 days

### 2. Repository Overview Dashboard (`repository-overview.json`)

**UID**: `repo-overview`
**Purpose**: List and compare all repositories

**Panels**:
- **Total Repositories**: Count of active repositories
- **Total Commits/PRs/Contributors**: Aggregate stats
- **Commit Activity**: Time series of commits per day (30 days)
- **Top 10 Active Repositories**: Table with clickable repo names → Deep-Dive
- **All Repositories**: Full table with organization, branch, URLs, last analyzed, commit/PR counts

### 3. Repository Deep-Dive Dashboard (`repository-deep-dive.json`)

**UID**: `repo-deep-dive`
**Purpose**: Comprehensive view of a single repository (selected via dropdown)

**Template Variable**: Repository selector dropdown

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

### 4. Pull Request Analysis Dashboard (`pull-requests.json`)

**UID**: `pull-requests`
**Purpose**: Track PR quality and review efficiency across all repos

**Panels**:
- **Open/Merged/Closed PRs**: Stat panels with 30-day counts
- **Avg PR Size**: Lines changed per PR
- **PR Status Distribution**: Pie chart (open/merged/closed)
- **PR Size Distribution**: Pie chart (small/medium/large/extra_large)
- **PR Throughput**: Created vs. merged over time
- **Recent Pull Requests**: Table with clickable repo names → Deep-Dive

### 6. Security Dashboard (`security-dashboard.json`)

**UID**: `security-dashboard`
**Purpose**: Organization-wide security overview with vulnerability and end-of-life dependency tracking

**Sections**:
- **Organization Security Summary**: Total vulnerabilities, EOL dependencies, repositories affected
- **Vulnerability Analysis**: Severity distribution pie chart, top repositories by critical vulnerabilities
- **End-of-Life Dependencies**: EOL status categorization (expired, expiring soon, future), repository security overview table with drilldown links
- **Security Trends**: Time series of vulnerability counts over time
- **Top Vulnerable Dependencies**: Table of most problematic packages across repositories

## Dashboard Navigation

All dashboards are cross-linked:
- **Header Links**: Each dashboard has navigation links to all other dashboards
- **Data Links**: Repository names in tables are clickable and navigate to the Deep-Dive dashboard with that repository pre-selected
- **Time Preservation**: Navigation links preserve the current time range (`keepTime: true`)

## Dashboard Designs (Planned)

### Security Dashboard (Implemented)

**Purpose**: Track vulnerabilities and security issues

- **Critical Vulnerabilities by Repository**: Bar chart of repositories with the most critical issues
- **Vulnerability Severity Distribution**: Pie chart breakdown (Critical, High, Medium, Low)
- **Top Vulnerable Dependencies**: Table listing packages with known vulnerabilities
- **EOL Dependencies**: List of packages that have reached End-of-Life
- **Vulnerability Trends**: Time series showing vulnerability counts over time

*Note: Security features are currently implemented within the Repository Deep-Dive dashboard under the 'Security & Dependencies' section.*

### Code Quality Dashboard (Not Yet Implemented)

**Purpose**: Monitor code health and technical debt

- **Code Quality Trends**: Time series of issue counts (Critical, High, etc.)
- **Maintainability Index**: Gauge showing current score
- **Issue Breakdown**: Bar chart of issues by category
- **Top Files with Most Issues**: Table identifying hotspots
- **Technical Debt Estimate**: Total estimated hours to fix issues

## Dashboard Templates

### Exporting Dashboards

Dashboards can be exported as JSON via the Grafana API.

### Importing Dashboards

Dashboards can be imported via the API or UI.

### Dashboard Provisioning

Grafana provisioning is used to automatically load dashboards from the filesystem on startup.

## Alerting Rules

- **Critical Vulnerabilities**: Alerts when new critical vulnerabilities are detected.
- **Stale Repository**: Alerts if a repository hasn't been analyzed in 7 days.
- **Code Quality Degradation**: Alerts if critical issues increase significantly between scans.

## Performance Optimization

### Query Optimization

Materialized views are used to pre-calculate complex metrics like repository health summaries, improving dashboard load times.

### Connection Pooling

Grafana is configured to use connection pooling to manage database load efficiently.

## Checklist

- [x] Grafana installed and accessible (Docker Compose)
- [x] PostgreSQL data source configured (TimescaleDB)
- [x] TimescaleDB support enabled in data source
- [x] Dashboard provisioning set up for version control (`grafana/provisioning/`)
- [x] Team Overview dashboard created (`team-overview.json`)
- [x] Repository Overview dashboard created (`repository-overview.json`)
- [x] Repository Deep-Dive dashboard created (`repository-deep-dive.json`)
- [x] Pull Request dashboard created (`pull-requests.json`)
- [x] Contributor dashboard created (`contributor-analytics.json`)
- [x] Cross-dashboard navigation links implemented
- [x] Data links for drill-down navigation (repo → Deep-Dive)
- [x] Security dashboard created (`security-dashboard.json`)
- [ ] Code Quality dashboard created
- [ ] Alerting rules configured

## Further Reading

- [Grafana Documentation](https://grafana.com/docs/grafana/latest/)
- [Grafana PostgreSQL Data Source](https://grafana.com/docs/grafana/latest/datasources/postgres/)
- [Grafana Alerting](https://grafana.com/docs/grafana/latest/alerting/)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/best-practices/)

## Next Steps

- See [07-implementation-plan.md](07-implementation-plan.md) for deployment roadmap
- Review [08-technology-stack.md](08-technology-stack.md) for complete technology overview
