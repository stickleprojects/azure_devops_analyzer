# Data Storage Layer

## Overview

The storage layer uses PostgreSQL with TimescaleDB extension for efficient time-series data handling and comprehensive querying capabilities for Grafana.

## Database Setup

The system requires PostgreSQL 15 with the TimescaleDB extension enabled. Additional extensions `pg_trgm` and `btree_gin` are used for text search and indexing.

**Schema Location**: See [database/schema.sql](../database/schema.sql) for the complete DDL.

## Database Schema

### Entity Relationship Diagram

> **Note**: The rendered SVG below is auto-generated from the Mermaid source.
> Source file: [../images/database-schema.mmd](../images/database-schema.mmd)
> To regenerate: Actions → Update-Docs Bot → Run workflow (`mermaid` job).

![Database Schema](../images/database-schema.svg)

The inline Mermaid source (also renders in GitHub and VS Code):

```mermaid
erDiagram
    %% Core Entities
    organizations ||--o{ projects : contains
    projects ||--o{ repositories : contains
    repositories ||--o{ branches : has

    %% Service Mapping
    services ||--o{ repository_services : includes
    repositories ||--o{ repository_services : belongs_to

    %% Repository Analysis
    repositories ||--o{ repository_stack : analyzed_for
    repositories ||--o{ dependencies : has
    repositories ||--o{ code_quality_metrics : measured_by
    repositories ||--o{ code_issues : contains
    repositories ||--o{ repository_summaries : described_by
    repositories ||--o{ readme_files : documents
    repositories ||--o{ commits : tracks
    repositories ||--o{ pull_requests : manages
    repositories ||--o{ contributor_metrics : tracks

    %% Branch Analysis
    branches ||--o{ repository_stack : analyzed_for
    branches ||--o{ dependencies : has
    branches ||--o{ code_quality_metrics : measured_by
    branches ||--o{ code_issues : contains
    branches ||--o{ repository_summaries : described_by
    branches ||--o{ readme_files : documents
    branches ||--o{ branch_metrics : tracked_by

    %% Dependencies and Security
    dependencies ||--o{ vulnerabilities : exposes

    %% Contributors
    contributors ||--o{ contributor_metrics : generates
    contributors ||--o{ commits : authors
    contributors ||--o{ pull_requests : creates
    contributors ||--o{ pr_reviews : submits
    contributors ||--o{ pr_comments : writes

    %% Pull Requests
    pull_requests ||--o{ pr_reviews : reviewed_by
    pull_requests ||--o{ pr_comments : discussed_in

    %% Table Definitions
    organizations {
        serial organization_id PK
        varchar name
        text url
        varchar platform
        timestamp created_at
    }

    projects {
        serial project_id PK
        integer organization_id FK
        varchar name
        text description
        timestamp created_at
    }

    repositories {
        varchar repo_id PK
        integer project_id FK
        integer team_id FK
        varchar name
        text url
        varchar default_branch
        bigint platform_repo_id
        timestamp created_at
        timestamp last_analyzed_at
        boolean is_active
        boolean is_private
        boolean is_archived
        integer repository_size
        integer open_issues_count
        varchar license_name
        varchar license_key
        boolean has_vulnerability_alerts
        boolean has_secret_scanning
        boolean has_dependabot_alerts
        timestamptz pushed_at
        timestamptz updated_at
    }

    branches {
        serial branch_id PK
        varchar repo_id FK
        varchar branch_name
        varchar latest_commit_sha
        timestamp created_at
        timestamp last_analyzed_at
        boolean is_active
    }

    repository_stack {
        serial id PK
        varchar repo_id FK
        integer branch_id FK
        varchar category
        varchar name
        varchar source
        decimal percentage
        integer line_count
        bigint byte_count
        decimal confidence
        timestamp first_seen_at
        timestamp last_seen_at
    }

    technologies {
        serial id PK
        varchar name
        varchar category
        boolean is_eol
        date eol_date
        varchar latest_supported_version
        timestamp eol_enriched_at
    }

    dependencies {
        serial id PK
        varchar repo_id FK
        integer branch_id FK
        varchar package_name
        varchar version
        varchar ecosystem
        varchar latest_version
        boolean is_dev_dependency
        boolean has_vulnerabilities
        boolean is_eol
        date eol_date
        timestamp analyzed_at "hypertable"
    }

    vulnerabilities {
        serial id PK
        integer dependency_id FK
        varchar cve_id
        varchar vulnerability_id
        varchar severity
        text summary
        text description
        timestamp published_date
        timestamp modified_date
        varchar fixed_in_version
        jsonb references
        timestamp created_at
    }

    code_quality_metrics {
        serial id PK
        varchar repo_id FK
        integer branch_id FK
        timestamp timestamp "hypertable"
        integer total_issues
        integer critical_issues
        integer high_issues
        integer medium_issues
        integer low_issues
        decimal complexity_score
        decimal maintainability_index
        decimal test_coverage
        integer code_smells
        integer technical_debt_minutes
    }

    code_issues {
        serial id PK
        integer quality_metric_id
        varchar repo_id FK
        integer branch_id FK
        text file_path
        integer line_number
        varchar severity
        varchar category
        varchar rule_id
        text message
        timestamp detected_at
        timestamp resolved_at
    }

    repository_summaries {
        serial id PK
        varchar repo_id FK
        integer branch_id FK
        text summary_text
        text purpose
        text[] key_technologies
        text target_audience
        timestamp generated_at
        varchar generated_by
    }

    readme_files {
        serial id PK
        varchar repo_id FK
        integer branch_id FK
        text file_path
        text content
        text summary
        integer word_count
        timestamp analyzed_at
    }

    contributors {
        serial id PK
        varchar email UK
        varchar name
        timestamp first_seen_at
        timestamp last_seen_at
    }

    contributor_metrics {
        serial id PK
        varchar repo_id FK
        integer contributor_id FK
        timestamp period_start "hypertable"
        timestamp period_end
        integer commit_count
        integer lines_added
        integer lines_removed
        integer files_modified
        integer pr_created
        integer pr_reviews
        integer pr_approvals
        integer active_days
        decimal avg_commit_message_quality
    }

    commits {
        varchar commit_sha PK
        varchar repo_id FK
        varchar branch_name
        integer author_id FK
        integer committer_id FK
        text message
        decimal message_quality_score
        timestamp commit_date
        text[] parent_shas
        integer files_changed
        integer lines_added
        integer lines_removed
        boolean is_verified
        varchar verification_reason
    }

    pull_requests {
        serial id PK
        varchar repo_id FK
        integer pr_number
        varchar platform_pr_id UK
        text title
        text description
        varchar source_branch
        varchar target_branch
        integer author_id FK
        varchar status
        timestamp created_at
        timestamp updated_at
        timestamp merged_at
        timestamp closed_at
        integer files_changed
        integer lines_added
        integer lines_removed
        integer comment_count
        integer approval_count
        varchar size_category
        boolean has_issues
        text[] issue_flags
    }

    pr_reviews {
        serial id PK
        integer pr_id FK
        integer reviewer_id FK
        timestamp review_date
        integer vote
        boolean is_required
        integer comment_count
    }

    pr_comments {
        serial id PK
        integer pr_id FK
        varchar thread_id
        integer author_id FK
        text content
        varchar comment_type
        timestamp published_date
        text file_path
        integer line_number
    }

    branch_metrics {
        serial id PK
        integer branch_id FK
        timestamp timestamp "hypertable"
        integer commit_count
        integer unique_contributors
        integer age_days
        integer staleness_days
        integer total_lines
        integer divergence_from_main
    }

    services {
        serial service_id PK
        varchar name UK
        text purpose
        varchar cmdb_id UK
        timestamp created_at
        timestamp updated_at
    }

    repository_services {
        serial id PK
        varchar repo_id FK
        integer service_id FK
        timestamp linked_at
    }
```

### Core Entity Tables

The foundation of the data model consists of hierarchical entities:

- **organizations**: Top-level Azure DevOps organizations with name and URL
- **projects**: Projects within organizations, linked by foreign key
- **repositories**: Individual repos with Azure DevOps ID as primary key, tracking default branch and last analysis timestamp
- **branches**: Branch metadata per repository, tracking latest commit SHA and analysis status

### Language and Dependency Tables

These tables track the technology makeup of each repository:

- **repository_stack**: Unified table storing all per-repository technology data. Rows with `source='platform_api'` and `category='language'` come from the VCS API (byte counts, percentages). Rows with `source='heuristic'` come from the TechnologyDetector (frameworks, databases, CI/CD, etc.).
- **technologies**: Global EOL metadata lookup table, one row per `(name, category)`. Populated by `TechnologyEnricher` from endoflife.date.
- **dependencies**: Package information including name, version, ecosystem (PyPI, npm, Maven, NuGet), and security flags (`has_vulnerabilities`, `is_eol`). Also a hypertable for time-series tracking.
- **vulnerabilities**: CVE and OSV vulnerability records linked to dependencies, storing severity, description, and fix version.

### Code Quality Tables

Quality metrics are stored as time-series data for trend analysis:

- **code_quality_metrics**: Aggregated counts of issues by severity, plus complexity scores, maintainability index, test coverage, and technical debt. Hypertable with weekly chunks.
- **code_issues**: Individual issue records with file path, line number, category (bug, vulnerability, code_smell), and resolution status.

### Repository Summary Tables

AI-generated insights and documentation:

- **repository_summaries**: LLM-generated summaries including purpose, key technologies (as array), and target audience. Tracks which model generated each summary.
- **readme_files**: Extracted README content with full-text search index using PostgreSQL's `gin` and `tsvector`.

### Contributor and Activity Tables

Developer metrics and commit history:

- **contributors**: Unique contributors identified by email, with first/last seen timestamps
- **contributor_metrics**: Time-series metrics per contributor per repository, including commit counts, lines changed, PR activity, and commit message quality scores. Monthly hypertable.
- **commits**: Individual commit records with author, message, quality score, and change statistics.

### Pull Request Tables

PR lifecycle and review tracking:

- **pull_requests**: PR metadata including branches, status, timestamps, size metrics, and issue flags
- **pr_reviews**: Individual review records with vote values (-10=rejected, 0=no vote, 5=approved with suggestions, 10=approved)
- **pr_comments**: Thread and comment content with optional file/line associations

### Branch Metrics

Branch-level analytics as time-series:

- **branch_metrics**: Tracks commit count, unique contributors, age, staleness, and divergence from main branch. Weekly hypertable.

### Service Tables

Services represent logical groupings of repositories that together deliver a business capability:

- **services**: Defines services with a unique name, purpose description, and CMDB identifier for integration with configuration management systems. Each service can aggregate metrics from multiple repositories.
- **repository_services**: Junction table implementing the many-to-many relationship between repositories and services. A repository may belong to zero or more services (e.g., an API repo and its database repo both belong to a "user" service), and a service may have zero or more repositories.

## Indexing Strategy

The schema employs several indexing patterns:

- **Foreign key indexes**: All relationship columns indexed for join performance
- **Timestamp indexes**: Time-based columns indexed for range queries
- **Composite indexes**: Common query patterns pre-optimized (e.g., `repo_id + timestamp DESC`)
- **Partial indexes**: Security-focused index on dependencies where vulnerabilities or EOL flags are true
- **Full-text search**: GIN index on README content for text search

## Data Access Layer

The application uses SQLAlchemy for ORM mapping and `psycopg2` for efficient database connections. A `Database` class handles connection pooling and transaction management.

## Backup and Restore

### Backup Strategy

- **Daily backups**: `pg_dump` in custom format, compressed with gzip
- **Storage**: Uploaded to Azure Blob Storage
- **Retention**: 7 days local, 30 days cloud

### Restore Process

1. Download backup from Azure Blob Storage
2. Decompress the archive
3. Use `pg_restore` to populate a clean database instance

### Point-in-Time Recovery

PostgreSQL is configured with WAL archiving (`wal_level = replica`, `archive_mode = on`) to support point-in-time recovery for disaster scenarios.

## Data Retention and Archival

- **Archival threshold**: Data older than 2 years is moved to archive tables
- **Compression**: TimescaleDB chunks older than 6 months are compressed to reduce storage

## Checklist

- [ ] PostgreSQL 15+ installed with TimescaleDB extension
- [ ] Extensions enabled: `timescaledb`, `pg_trgm`, `btree_gin`
- [ ] Schema applied from `database/schema.sql`
- [ ] Read-only user created for Grafana
- [ ] Connection pooling configured
- [ ] Backup automation configured
- [ ] WAL archiving enabled for PITR

## Further Reading

- [TimescaleDB Documentation](https://docs.timescale.com/)
- [PostgreSQL Indexing Best Practices](https://www.postgresql.org/docs/current/indexes.html)
- [SQLAlchemy ORM Tutorial](https://docs.sqlalchemy.org/en/20/orm/tutorial.html)

## Next Steps

- See [job-orchestration.md](job-orchestration.md) for data insertion workflows
- Review [../03-operations/visualization.md](../03-operations/visualization.md) for querying this data in Grafana
