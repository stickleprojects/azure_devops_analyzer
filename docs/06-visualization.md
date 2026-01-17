# Visualization Layer - Grafana Dashboards

## Overview

Grafana provides interactive dashboards to visualize all collected metrics and enable data-driven insights about repository health, code quality, and team performance.

## Grafana Setup

Grafana is configured to connect to the PostgreSQL database using a dedicated read-only user. The data source is set up with TimescaleDB support enabled.

## Dashboard Designs

### 1. Repository Overview Dashboard

**Purpose**: High-level view of all repositories

**Panels**:

- **Total Repositories**: Count of active repositories.
- **Language Distribution**: Pie chart showing bytes of code per language.
- **Top 10 Most Active Repositories**: Bar gauge based on commit count in the last 30 days.
- **Repository Health Score**: Table combining critical issues, vulnerabilities, and EOL dependencies to assign a status (Healthy, Warning, Critical).
- **Activity Timeline**: Time series of commits per day.

### 2. Security Dashboard

**Purpose**: Track vulnerabilities and security issues

- **Critical Vulnerabilities by Repository**: Bar chart of repositories with the most critical issues.
- **Vulnerability Severity Distribution**: Pie chart breakdown (Critical, High, Medium, Low).
- **Top Vulnerable Dependencies**: Table listing packages with known vulnerabilities and the number of affected repos.
- **EOL Dependencies**: List of packages that have reached End-of-Life.
- **Vulnerability Trends**: Time series showing the count of vulnerabilities by severity over time.

### 3. Code Quality Dashboard

**Purpose**: Monitor code health and technical debt

- **Code Quality Trends**: Time series of issue counts (Critical, High, etc.).
- **Maintainability Index**: Gauge showing the current maintainability score.
- **Issue Breakdown**: Bar chart of issues by category (Bug, Code Smell, etc.).
- **Top Files with Most Issues**: Table identifying hotspots in the codebase.
- **Technical Debt Estimate**: Total estimated hours to fix issues.

### 4. Contributor Dashboard

**Purpose**: Analyze team productivity and collaboration

- **Top Contributors**: Bar chart of commit counts.
- **Contributor Activity Heatmap**: Table showing commits, lines added/removed, PRs created, and reviews.
- **Commit Activity**: Heatmap of commits by day of week and hour of day.
- **PR Approval Rates**: Percentage of reviews that result in approval.

### 5. Pull Request Dashboard

**Purpose**: Track PR quality and review efficiency

- **PR Size Distribution**: Breakdown of PRs by size (Small, Medium, Large).
- **Average Time to Merge**: Trend of how long it takes to merge PRs.
- **PRs with Issues**: List of PRs flagged for issues (e.g., no description, too large).
- **Review Comments Distribution**: Histogram of comment counts per PR.
- **PR Throughput**: Created vs. Merged PRs over time.

### 6. Repository Deep Dive Dashboard

**Purpose**: Comprehensive view of a single repository

**Panels**: Combination of all metrics filtered by selected repository

- **Repository Summary**: AI-generated summary of the repo.
- **Branch Comparison**: Metrics for active branches (commits, contributors, staleness).

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

- [ ] Grafana installed and accessible
- [ ] PostgreSQL data source configured with read-only user
- [ ] TimescaleDB support enabled in data source
- [ ] Repository Overview dashboard created
- [ ] Security dashboard created
- [ ] Code Quality dashboard created
- [ ] Contributor dashboard created
- [ ] Pull Request dashboard created
- [ ] Alerting rules configured
- [ ] Dashboard provisioning set up for version control

## Further Reading

- [Grafana Documentation](https://grafana.com/docs/grafana/latest/)
- [Grafana PostgreSQL Data Source](https://grafana.com/docs/grafana/latest/datasources/postgres/)
- [Grafana Alerting](https://grafana.com/docs/grafana/latest/alerting/)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/best-practices/)

## Next Steps

- See [07-implementation-plan.md](07-implementation-plan.md) for deployment roadmap
- Review [08-technology-stack.md](08-technology-stack.md) for complete technology overview
