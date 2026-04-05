# Requirements

## Document Information

| Field            | Value                      |
| ---------------- | -------------------------- |
| Project Name     | Repository Analysis System |
| Document Version | 3.0                        |
| Status           | Active                     |
| Last Updated     | 2026-04-05                 |

_Version 3.0 merges `business-requirements.md` (v1.3) and `requirements-status.md` (v2.5) into a single source of truth. Each requirement now shows its definition and current implementation status together._

## Status Legend

| Status      | Icon | Description                                |
| ----------- | ---- | ------------------------------------------ |
| Complete    | ✅   | Fully implemented and tested               |
| Partial     | 🔶   | Partially implemented, some work remaining |
| Not Started | ❌   | Not yet implemented                        |
| Paused      | ⏸️  | Implemented but temporarily disabled       |
| N/A         | ⬛   | Not applicable or out of scope             |

---

## Executive Summary

The Repository Analysis System is a platform designed to provide comprehensive insights into code repositories hosted on Azure DevOps and GitHub. It enables engineering leaders and teams to monitor code quality, security vulnerabilities, contributor activity, and development patterns through automated analysis and visualization dashboards.

---

## Business Objectives

### Primary Objectives

| ID   | Objective                       | Success Criteria                                                                   |
| ---- | ------------------------------- | ---------------------------------------------------------------------------------- |
| BO-1 | Improve code quality visibility | 90% of repositories analyzed weekly with quality metrics available in dashboards   |
| BO-2 | Reduce security vulnerabilities | Identify and flag 100% of known CVEs in dependencies within 24 hours of scan       |
| BO-3 | Increase development efficiency | Provide actionable insights on PR patterns and contributor activity                |
| BO-4 | Enable data-driven decisions    | Dashboards accessible to all stakeholders with real-time metrics                   |
| BO-5 | Track library health            | Comprehensive visibility into EOL and vulnerability status across all dependencies |

### Secondary Objectives

| ID   | Objective                  | Success Criteria                                                   |
| ---- | -------------------------- | ------------------------------------------------------------------ |
| BO-6 | Support multiple platforms | Full feature parity between Azure DevOps and GitHub integrations   |
| BO-7 | Automate reporting         | Scheduled analysis runs without manual intervention                |
| BO-8 | Track trends over time     | Historical data retained for minimum 2 years for trend analysis    |
| BO-9 | Establish tech strategy    | Quarterly tech radar published with organizational recommendations |

---

## Stakeholders

| Role                   | Responsibilities                         | Interests                                                |
| ---------------------- | ---------------------------------------- | -------------------------------------------------------- |
| Engineering Leadership | Strategic decisions, resource allocation | High-level metrics, security posture, team productivity  |
| Development Team Leads | Team management, code reviews            | Team-specific metrics, PR patterns, contributor activity |
| Security Team          | Vulnerability management, compliance     | Vulnerability reports, dependency health, EOL tracking   |
| Individual Developers  | Code contribution, self-improvement      | Personal metrics, code quality feedback                  |
| DevOps/Platform Team   | System maintenance, infrastructure       | System health, job scheduling, data freshness            |

---

## Functional Requirements

### FR-1: Repository Discovery and Tracking

| ID     | Requirement                                                                       | Priority | Status | Notes                                                                                                                                   |
| ------ | --------------------------------------------------------------------------------- | -------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------- |
| FR-1.1 | System shall discover all repositories within configured organizations            | High     | ✅     | Azure DevOps and GitHub extractors with identical API surface in `src/extractors/`                                                      |
| FR-1.2 | System shall track repository metadata (name, URL, default branch, creation date) | High     | ✅     | `Repository` entity captures all metadata — `src/entities/repository.py`                                                               |
| FR-1.3 | System shall support marking repositories as active/inactive                      | Medium   | ✅     | `is_active` flag on Repository entity                                                                                                   |
| FR-1.4 | System shall track multiple branches per repository                               | High     | ✅     | `Branch` entity with full tracking — `src/entities/branch.py`                                                                           |
| FR-1.5 | System shall extract repository metadata from `repository.json` metadata files    | High     | ✅     | `team_name` and `service_name` extracted for both GitHub and Azure DevOps via `repository.json` at repo root — implemented 2026-01-25  |

**Summary:** 5/5 Complete

---

### FR-2: Language and Technology Detection

| ID     | Requirement                                                       | Priority | Status | Notes                                                                                                                       |
| ------ | ----------------------------------------------------------------- | -------- | ------ | --------------------------------------------------------------------------------------------------------------------------- |
| FR-2.1 | System shall detect programming languages used in each repository | High     | ✅     | `RepositoryLanguage` entity; GitHub uses API, Azure DevOps uses heuristic file analysis — implemented 2026-01-24           |
| FR-2.2 | System shall track language distribution over time                | Medium   | ✅     | TimescaleDB hypertable with monthly chunks; `_process_languages()` populates percentage/byte_count — implemented 2026-01-24 |
| FR-2.3 | System shall identify key technologies and frameworks             | High     | ✅     | `TechnologyDetector` detects 8 categories (languages, frameworks, databases, platforms, build tools, testing, CI/CD, docs) — 2026-01-24 |

**Summary:** 3/3 Complete

---

### FR-3: Dependency Analysis

| ID     | Requirement                                                              | Priority | Status | Notes                                                                                                                     |
| ------ | ------------------------------------------------------------------------ | -------- | ------ | ------------------------------------------------------------------------------------------------------------------------- |
| FR-3.1 | System shall extract dependencies from package manifest files            | High     | ✅     | 7 ecosystem parsers: PyPI (requirements.txt, pyproject.toml, Pipfile), npm, Maven, NuGet (*.csproj, packages.config), Go, Ruby, Rust |
| FR-3.2 | System shall identify current and latest versions of dependencies        | High     | ✅     | OSVClient queries OSV.dev for latest versions; integrated into DependencyEnricher — 2026-01-24                            |
| FR-3.3 | System shall flag end-of-life (EOL) dependencies                         | High     | ✅     | EndOfLifeClient queries endoflife.date; `eol_date` and `is_eol` fields populated — 2026-01-24                             |
| FR-3.4 | System shall distinguish between production and development dependencies | Medium   | ✅     | `is_dev_dependency` field populated by parsers based on file names, sections, and package indicators                     |

**Summary:** 4/4 Complete

---

### FR-4: Security Vulnerability Scanning

| ID     | Requirement                                                                     | Priority | Status | Notes                                                                                                                     |
| ------ | ------------------------------------------------------------------------------- | -------- | ------ | ------------------------------------------------------------------------------------------------------------------------- |
| FR-4.1 | System shall identify known vulnerabilities (CVEs) in dependencies              | Critical | ✅     | OSVClient extracts CVE/OSV IDs and vulnerability data from OSV.dev API — 2026-01-24                                      |
| FR-4.2 | System shall classify vulnerabilities by severity (Critical, High, Medium, Low) | Critical | ✅     | `severity` enum on Vulnerability entity; CVSS score mapping implemented                                                  |
| FR-4.3 | System shall provide remediation guidance (fixed version)                       | High     | ✅     | `fixed_in_version` field on Vulnerability entity; extracted from OSV.dev data                                            |
| FR-4.4 | System shall track vulnerability publication and modification dates             | Medium   | ✅     | `published_at` and `modified_at` fields; populated from OSV.dev — 2026-01-24                                             |
| FR-4.5 | System shall track GitHub security features enabled per repository              | High     | ✅     | GitHub extractor captures vulnerability alerts, secret scanning, and Dependabot alerts — 2026-01-18                      |

**Summary:** 5/5 Complete

---

### FR-5: Dependency Vulnerability and EOL Tracking Dashboard

| ID     | Requirement                                                                                 | Priority | Status | Notes                                                                        |
| ------ | ------------------------------------------------------------------------------------------- | -------- | ------ | ---------------------------------------------------------------------------- |
| FR-5.1 | System shall provide a comprehensive dashboard showing all dependencies across repositories | High     | ❌     | Dashboard aggregation of unique libraries and usage patterns not yet built   |
| FR-5.2 | System shall display dependency versions, EOL status, and vulnerability counts per library  | High     | ❌     | Library card views with version, EOL date, and CVE count not yet built       |
| FR-5.3 | System shall allow filtering dashboard by organization, team, service, and repository       | High     | ❌     | Filter controls for drill-down from portfolio to repository level            |
| FR-5.4 | System shall highlight libraries with critical vulnerabilities or upcoming EOL dates        | High     | ❌     | Visual indicators (badges/colors) for Critical CVEs and EOL < 90 days        |
| FR-5.5 | System shall show which repositories depend on each library                                 | Medium   | ❌     | Repository list with version information for each dependency                 |
| FR-5.6 | System shall track library adoption trends (how many repos using over time)                 | Medium   | ❌     | Historical adoption curve for each library                                   |
| FR-5.7 | System shall integrate EOL data from endoflife.date and vulnerability data from OSV.dev     | High     | ✅     | Data sources integrated via EOLClient and OSVClient — 2026-01-24             |

**Summary:** 1/7 Complete, 6/7 Not Started

---

### FR-6: Thoughtworks Tech Radar Publication

| ID     | Requirement                                                                                       | Priority | Status | Notes                                                           |
| ------ | ------------------------------------------------------------------------------------------------- | -------- | ------ | --------------------------------------------------------------- |
| FR-6.1 | System shall generate a Thoughtworks Tech Radar based on actual library usage across organization | High     | ❌     | Radar generation in JSON format compatible with TW Radar viewer |
| FR-6.2 | System shall categorize libraries into Thoughtworks Tech Radar rings (Adopt, Trial, Assess, Hold) | High     | ❌     | Categorization based on adoption metrics and recommendations    |
| FR-6.3 | System shall populate radar with organization's actual technology stack from dependency analysis  | High     | ❌     | All detected libraries with 2+ repositories appear on radar     |
| FR-6.4 | System shall include Thoughtworks recommended libraries as potential Trial/Assess options         | Medium   | ❌     | Recommended libraries highlighted separately with rationale     |
| FR-6.5 | System shall display radar with configurable move history and publication timeline                | Medium   | ❌     | Radar shows technology migrations and categorization changes    |
| FR-6.6 | System shall provide endpoint to publish/export radar for sharing with stakeholders               | High     | ❌     | REST API endpoint; HTML visualization compatible with viewers   |
| FR-6.7 | System shall track blips with metadata (adoption date, vulnerability status, EOL impact)          | Medium   | ❌     | Each technology entry includes context-specific metadata        |

**Summary:** 0/7 Complete, 7/7 Not Started

---

### FR-7: Code Quality Analysis

| ID     | Requirement                                                                    | Priority | Status | Notes                                                                                            |
| ------ | ------------------------------------------------------------------------------ | -------- | ------ | ------------------------------------------------------------------------------------------------ |
| FR-7.1 | System shall calculate code complexity metrics                                 | High     | 🔶     | `CodeQualityMetric` has complexity fields; analysis engine not yet implemented                   |
| FR-7.2 | System shall identify code issues by category (bug, vulnerability, code smell) | High     | 🔶     | `CodeIssue` entity with type and severity defined; no analysis logic yet                         |
| FR-7.3 | System shall calculate maintainability index                                   | Medium   | 🔶     | `maintainability_index` field exists; no calculation logic yet                                   |
| FR-7.4 | System shall track test coverage percentage                                    | Medium   | 🔶     | `test_coverage` field exists; no integration with test runners yet                               |
| FR-7.5 | System shall estimate technical debt in time units                             | Medium   | 🔶     | `technical_debt_minutes` field exists; no calculation logic yet                                  |
| FR-7.6 | System shall track repository health metrics                                   | Medium   | ✅     | Repository size, issue counts, archive status, and license info captured — 2026-01-18            |
| FR-7.7 | System shall track commit GPG signature verification                           | Medium   | ✅     | GPG verification status and reason captured for all commits — 2026-01-18                         |

**Summary:** 2/7 Complete, 5/7 Partial

---

### FR-8: Contributor Analytics

> **Status: PAUSED** — Implementation complete but disabled for performance optimization. See `CONTRIBUTOR_METRICS_GUIDE.md` for re-enablement steps.

| ID     | Requirement                                                              | Priority | Status | Notes                                                                                                                      |
| ------ | ------------------------------------------------------------------------ | -------- | ------ | -------------------------------------------------------------------------------------------------------------------------- |
| FR-8.1 | System shall track unique contributors per repository                    | High     | ✅     | `Contributor` entity with email-based identification; integrated into both workflows                                      |
| FR-8.2 | System shall calculate contributor metrics (commits, lines changed, PRs) | High     | ⏸️    | Implementation complete but calculation disabled — complex 7-query aggregation impacts extraction speed — 2026-01-25       |
| FR-8.3 | System shall track commit patterns (frequency, message quality)          | Medium   | ✅     | `ContributorAnalyzer.analyze_commit_message()` scores conventional commits, imperative mood, issue references — 2026-01-24 |
| FR-8.4 | System shall track active days per contributor                           | Medium   | ⏸️    | Implementation complete but disabled; re-enable when metrics calculation optimized                                        |

**Summary:** 2/4 Active Complete, 2/4 Paused (code complete)

---

### FR-9: Pull Request Analysis

| ID     | Requirement                                                                 | Priority | Status | Notes                                                                         |
| ------ | --------------------------------------------------------------------------- | -------- | ------ | ----------------------------------------------------------------------------- |
| FR-9.1 | System shall track PR lifecycle (created, updated, merged, closed)          | High     | ✅     | `PullRequest` entity with status, timestamps for all state transitions        |
| FR-9.2 | System shall calculate PR size metrics (files changed, lines added/removed) | High     | ✅     | `size_classification` enum: small, medium, large, extra_large                 |
| FR-9.3 | System shall track review activity (reviewers, votes, comments)             | High     | ✅     | `PRReview` entity with reviewer, vote (−10 to +10), and timestamps            |
| FR-9.4 | System shall identify PR quality issues                                     | Medium   | ❌     | `quality_flags` array field exists but no analysis logic                      |
| FR-9.5 | System shall track extraction progress metrics per run and repository       | High     | ✅     | `extraction_metrics` table tracks run/repo timing, status, and record counts — 2026-02-09 |

**Summary:** 4/5 Complete, 1/5 Not Started

---

### FR-10: Repository Summarization

| ID      | Requirement                                              | Priority | Status | Notes                                                                                                      |
| ------- | -------------------------------------------------------- | -------- | ------ | ---------------------------------------------------------------------------------------------------------- |
| FR-10.1 | System shall generate AI-powered repository summaries    | Medium   | 🔶     | `RepositorySummary` entity defined; AI integration not yet wired                                           |
| FR-10.2 | System shall extract and index README content            | High     | ✅     | `ReadmeFile` entity with full-text search index; both platforms implemented via `_process_readme_files()` — 2026-01-25 |
| FR-10.3 | System shall track which AI model generated each summary | Low      | ✅     | `model_used` field on `RepositorySummary` entity                                                           |

**Summary:** 2/3 Complete, 1/3 Partial

---

### FR-11: Visualization and Reporting

| ID      | Requirement                                                           | Priority | Status | Notes                                                                                                                                         |
| ------- | --------------------------------------------------------------------- | -------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------- |
| FR-11.1 | System shall provide Grafana dashboards for all metrics               | High     | ✅     | 9 dashboards: Admin, Team Overview, Repo Overview, Repo Deep-Dive, Service Overview, Pull Requests, Contributor Analytics, Security, Home     |
| FR-11.2 | System shall support time-range filtering on all visualizations       | High     | ✅     | All dashboards use Grafana time picker; navigation preserves time range                                                                       |
| FR-11.3 | System shall support drill-down from organization to repository level | Medium   | ✅     | Repository names in tables link to Deep-Dive dashboard; cross-dashboard navigation on all dashboards                                          |
| FR-11.4 | System shall provide security-focused dashboard views                 | High     | ✅     | Dedicated Security Dashboard (`security-dashboard.json`); security metrics also in Team Overview and Repository Deep-Dive                     |

**Summary:** 4/4 Complete

---

### FR-12: Service-Repository Mapping

| ID      | Requirement                                                                       | Priority | Status | Notes                                                                                           |
| ------- | --------------------------------------------------------------------------------- | -------- | ------ | ----------------------------------------------------------------------------------------------- |
| FR-12.1 | System shall support defining services with name, purpose, and CMDB identifier    | High     | ✅     | `Service` entity with name, description, cmdb_id, tags — `src/entities/service.py`             |
| FR-12.2 | System shall support many-to-many relationships between repositories and services | High     | ✅     | `RepositoryService` junction table implemented                                                  |
| FR-12.3 | System shall track which repositories contribute to each service                  | High     | ✅     | Relationship queryable via ORM                                                                  |
| FR-12.4 | System shall aggregate metrics at the service level                               | Medium   | ❌     | No aggregation queries or views implemented yet                                                 |
| FR-12.5 | System shall support repositories belonging to multiple services                  | Medium   | ✅     | Many-to-many relationship supports this natively                                                |

**Summary:** 4/5 Complete, 1/5 Not Started

---

### FR-13: Team Management and Contributor Linking

| ID      | Requirement                                                                        | Priority | Status | Notes                                                                                                                                                               |
| ------- | ---------------------------------------------------------------------------------- | -------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FR-13.1 | System shall support defining teams with name, description, and optional CMDB link | High     | ✅     | `Team` entity with name, description, organization_id — `src/database/models/team.py`                                                                              |
| FR-13.2 | System shall support many-to-many relationships between contributors and teams     | High     | ✅     | `TeamContributor` junction table with unique constraint — `src/database/models/team_contributor.py` — 2026-01-29                                                    |
| FR-13.3 | System shall track team membership with effective dates (start/end)                | Medium   | ✅     | `TeamContributor` tracks `effective_start_date` and `effective_end_date` — 2026-01-29                                                                               |
| FR-13.4 | System shall support team hierarchy (parent/child teams)                           | Low      | ❌     | Optional nested team structure — not required for current phase                                                                                                     |
| FR-13.5 | System shall aggregate contributor metrics at the team level                       | High     | ✅     | `TeamMetric` model with 6 aggregate functions in `team_analytics.py` — 2026-01-29                                                                                  |
| FR-13.6 | System shall provide Individual Contributor Dashboard                              | Medium   | ❌     | Personal dashboard (commits, PRs, reviews across repos) — blocked pending dashboard integration                                                                    |
| FR-13.7 | System shall display team member aggregates on Team Overview dashboard             | Medium   | ❌     | Per-member stats with drill-down to Individual Contributor — blocked pending dashboard integration                                                                  |
| FR-13.8 | System shall support filtering dashboards by team                                  | Medium   | ✅     | Team variable in Team Overview with view-backed queries; DASH-TEAM-001 resolved in Plan 016 — 2026-03-26                                                            |

**Summary:** 5/8 Complete, 3/8 Not Started

---

### FR-14: Administrative Dashboard

| ID      | Requirement                                                                          | Priority | Status | Notes                                                                                                                                                        |
| ------- | ------------------------------------------------------------------------------------ | -------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| FR-14.1 | System shall provide a dedicated administrative dashboard                            | High     | ✅     | `dashboards/admin-dashboard.json` (uid: `admin-dashboard`) — linked from Home dashboard nav card — 2026-02-21                                                |
| FR-14.2 | Admin dashboard shall include contextual help text for all administrative operations | High     | ✅     | Markdown text panels explain extraction controls, per-repo rescan API usage, and staleness criteria — 2026-02-21                                             |
| FR-14.3 | System shall provide force rescan functionality through the admin dashboard          | High     | ✅     | "Force Rescan — GitHub" and "Force Rescan — Azure DevOps" stat panels link to `/api/rescan/{platform}` — 2026-02-21                                         |
| FR-14.4 | Admin dashboard shall consolidate all administrative controls in one location        | Medium   | ✅     | Single dashboard: extraction controls, system status, extraction activity, recent runs, repository staleness — 2026-02-21                                    |
| FR-14.5 | System shall provide status visibility for ongoing administrative operations         | Medium   | ✅     | Active Runs stat, Latest Run Progress %, Extraction Rate timeseries, Recent Runs table, Recent Repository Activity table, links to API Health and Flower UI |
| FR-14.6 | Admin dashboard shall support per-platform administrative actions                    | Medium   | ✅     | Separate "Force Rescan — GitHub" and "Force Rescan — Azure DevOps" panels with platform-specific API endpoints                                              |

**Summary:** 6/6 Complete

---

## Non-Functional Requirements

### NFR-1: Performance

| ID      | Requirement                            | Target                                      | Status | Notes                                      |
| ------- | -------------------------------------- | ------------------------------------------- | ------ | ------------------------------------------ |
| NFR-1.1 | Full organization scan completion time | < 4 hours for 500 repositories              | ❌     | No benchmarking done yet                   |
| NFR-1.2 | Incremental update scan time           | < 30 minutes for changed repositories       | ❌     | Incremental update is skeleton only        |
| NFR-1.3 | Dashboard query response time          | < 3 seconds for 95th percentile             | ❌     | No load testing performed                  |
| NFR-1.4 | Database query performance             | Optimized indexes for common query patterns | 🔶     | Indexes defined in schema; not load tested |

**Summary:** 0/4 Complete, 1/4 Partial, 3/4 Not Started

---

### NFR-2: Scalability

| ID      | Requirement               | Target                                     | Status | Notes                                            |
| ------- | ------------------------- | ------------------------------------------ | ------ | ------------------------------------------------ |
| NFR-2.1 | Repository capacity       | Support 10,000+ repositories               | 🔶     | Architecture supports this; not tested at scale  |
| NFR-2.2 | Historical data retention | 2+ years of time-series data               | ✅     | TimescaleDB hypertables with chunking configured |
| NFR-2.3 | Concurrent analysis jobs  | Support parallel processing via task queue | ✅     | Celery with RabbitMQ configured                  |

**Summary:** 2/3 Complete, 1/3 Partial

---

### NFR-3: Reliability

| ID      | Requirement            | Target                                      | Status | Notes                                          |
| ------- | ---------------------- | ------------------------------------------- | ------ | ---------------------------------------------- |
| NFR-3.1 | System availability    | 99% uptime during business hours            | ❌     | No monitoring or health checks configured      |
| NFR-3.2 | Data durability        | Daily backups with 30-day retention         | 🔶     | Backup task defined; scheduling not configured |
| NFR-3.3 | Point-in-time recovery | WAL archiving enabled for disaster recovery | ❌     | Not configured in Docker setup                 |
| NFR-3.4 | Job failure handling   | Automatic retry with exponential backoff    | ✅     | Celery retry configuration in place            |

**Summary:** 1/4 Complete, 1/4 Partial, 2/4 Not Started

---

### NFR-4: Security

| ID      | Requirement           | Target                                                   | Status | Notes                                 |
| ------- | --------------------- | -------------------------------------------------------- | ------ | ------------------------------------- |
| NFR-4.1 | Credential management | All secrets stored in Azure Key Vault                    | ❌     | Currently using environment variables |
| NFR-4.2 | Database access       | Read-only user for Grafana, principle of least privilege | ❌     | Not configured yet                    |
| NFR-4.3 | API authentication    | Personal Access Tokens with minimal required scopes      | ✅     | Extractors use token-based auth       |
| NFR-4.4 | Data classification   | No source code stored, only metadata and metrics         | ✅     | Only metadata and metrics stored      |

**Summary:** 2/4 Complete, 2/4 Not Started

---

### NFR-5: Maintainability

| ID      | Requirement            | Target                                              | Status | Notes                                                    |
| ------- | ---------------------- | --------------------------------------------------- | ------ | -------------------------------------------------------- |
| NFR-5.1 | Code quality standards | Enforced via pre-commit hooks (black, flake8, mypy) | 🔶     | Dependencies exist; hooks not yet configured             |
| NFR-5.2 | Test coverage          | Minimum 80% coverage for core modules               | 🔶     | Unit, contract, and integration tests exist; % not measured |
| NFR-5.3 | Documentation          | All modules documented with docstrings              | 🔶     | Some docstrings present; coverage incomplete             |
| NFR-5.4 | Logging                | Structured logging with correlation IDs             | ✅     | Structlog configured                                     |

**Summary:** 1/4 Complete, 3/4 Partial

---

### NFR-6: Parallel Repository Processing

| ID      | Requirement                              | Target                                                                                                                                                   |
| ------- | ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| NFR-6.1 | Repository parallelism                   | System must process repositories in parallel via the task queue, with a configurable worker pool supporting at least 5 concurrent workers in production. |
| NFR-6.2 | Parallel throughput                      | With 5+ workers, sustain end-to-end processing of 500 repositories per hour without triggering platform rate limits.                                     |
| NFR-6.3 | Configurable throttling and coordination | Rate limiting and queue routing must be configurable per platform (GitHub, Azure DevOps) to safely scale worker concurrency.                             |

_Status tracking for NFR-6 is in progress — see [parallelization-plan.md](../04-implementation/parallelization-plan.md)._

---

### NFR-7: Observability

_Added 2026-02-09 to track worker-level visibility requirements._

| ID      | Requirement                                                   | Priority | Status | Notes                                                                              |
| ------- | ------------------------------------------------------------- | -------- | ------ | ---------------------------------------------------------------------------------- |
| NFR-7.1 | Workers shall emit structured metrics for extraction progress | High     | ✅     | Metrics captured per run and repository with platform context                      |
| NFR-7.2 | Workers shall emit health check endpoints                     | Medium   | ❌     | HTTP endpoint returning worker status, queue depth, last successful extraction     |
| NFR-7.3 | Workers shall log extraction events with correlation IDs      | High     | ❌     | Structured logging with repository_id, platform, task_id for tracing               |
| NFR-7.4 | System shall store extraction metrics in TimescaleDB          | High     | ✅     | `extraction_metrics` table tracking run/repo timing, status, and records extracted |
| NFR-7.5 | Grafana shall display worker health and extraction rate       | High     | ✅     | Extraction progress dashboard panels for rate, status, and activity                |
| NFR-7.6 | System shall track Celery task metrics                        | Medium   | ❌     | Task success/failure counts, execution time percentiles, queue depth over time     |

**Summary:** 3/6 Complete, 3/6 Not Started

---

## Implementation Progress Summary

| Category                    | Complete | Partial | Not Started | Total |
| --------------------------- | -------- | ------- | ----------- | ----- |
| Functional Requirements     | 46       | 9       | 17          | 72    |
| Non-Functional Requirements | 9        | 6       | 4           | 19    |

_Last counted: 2026-03-26_

---

## Platform Parity Status

### Core Extraction Features (Both Platforms)

| Feature               | GitHub      | Azure DevOps | Notes                                                      |
| --------------------- | ----------- | ------------ | ---------------------------------------------------------- |
| Organizations         | ✅ Complete | ✅ Complete  | Both support multi-org extraction                          |
| Projects              | ✅ Complete | ✅ Complete  | GitHub uses owner/org, Azure DevOps uses explicit projects |
| Repositories          | ✅ Complete | ✅ Complete  | Full metadata including size, visibility, archive status   |
| Branches              | ✅ Complete | ✅ Complete  | Branch name, commit SHA, protection status                 |
| Commits               | ✅ Complete | ✅ Complete  | Author, message, timestamp, parents, GPG verification      |
| Pull Requests         | ✅ Complete | ✅ Complete  | Reviews, comments, state, merge status                     |
| Languages             | ✅ Complete | ✅ Complete  | GitHub via API, Azure DevOps via file analysis             |
| Technology Detection  | ✅ Complete | ✅ Complete  | Both use `TechnologyDetector` with file tree analysis      |
| File Tree             | ✅ Complete | ✅ Complete  | Full repo file structure for analysis                      |
| File Content          | ✅ Complete | ✅ Complete  | Read specific files for dependency/README extraction       |
| Dependencies          | ✅ Complete | ✅ Complete  | Both support 7 ecosystems via `DependencyAnalyzer`         |
| Dependency Enrichment | ✅ Complete | ✅ Complete  | OSV.dev and endoflife.date integration                     |

### Platform-Specific Features

| Feature             | GitHub         | Azure DevOps   | Notes                                                                                    |
| ------------------- | -------------- | -------------- | ---------------------------------------------------------------------------------------- |
| README Extraction   | ✅ Implemented | ✅ Implemented | Both extract via `get_readme_files()` with scope detection — 2026-01-25                  |
| Repository Metadata | ✅ Implemented | ✅ Implemented | Both extract `team_name`/`service_name` from `repository.json` — 2026-01-25             |
| Security Features   | ✅ Implemented | N/A            | GitHub-specific: vulnerability alerts, secret scanning, Dependabot (Azure DevOps has different security model) |
| GPG Verification    | ✅ Implemented | ✅ Implemented | Both track commit signature verification                                                 |

### Test Coverage (Both Platforms)

| Test Suite                 | GitHub      | Azure DevOps | Location                                                        |
| -------------------------- | ----------- | ------------ | --------------------------------------------------------------- |
| Repository Extraction E2E  | 14 tests    | 10 tests     | `tests/contract/integration/test_*_extraction_e2e.py`           |
| Language Detection         | ✅ 3 tests  | ✅ 2 tests   | Validates storage, time-series, and accuracy                    |
| Technology Detection       | ✅ 3 tests  | ✅ 3 tests   | Validates detection logic and structure                         |
| Database Schema            | ✅ Shared   | ✅ Shared    | `test_both_platforms_same_database_schema()`                    |
| Dependency Enrichment      | ✅ Shared   | ✅ Shared    | `test_dependency_enrichment_e2e.py`                             |
| Fixture-Backed Integration | ✅ 23 tests | ✅ 23 tests  | `tests/contract/integration/test_fixture_scenarios.py` — Plan 015 (2026-03-07) |

**Conclusion:** Azure DevOps and GitHub have functional parity for all core features (FR-1 through FR-4).

---

## Implementation Roadmap

### Phase 1: Core Analysis ✅ Largely Complete

- ~~Implement language detection from repository file trees~~ ✅
- ~~Implement dependency extraction from package manifests~~ ✅ (7 ecosystems)
- ~~Connect OSV.dev API for vulnerability scanning~~ ✅
- Implement contributor metrics calculation from commits/PRs (FR-8.2, FR-8.4 — paused)

### Phase 2: Quality & Security ✅ Largely Complete

- Integrate code quality analysis (FR-7.1–FR-7.5 — schema ready, analysis not built)
- ~~Connect endoflife.date API for EOL tracking~~ ✅
- Implement PR quality issue detection (FR-9.4)
- ~~Calculate commit message quality scores~~ ✅

### Phase 3: Visualization 🔶 Mostly Complete

- ~~Add Grafana to Docker Compose~~ ✅
- ~~Create core dashboards (9 dashboards)~~ ✅
- Implement service-level metric aggregation (FR-12.4)
- ~~Add drill-down navigation~~ ✅
- Build Dependency Vulnerability & EOL dashboard (FR-5.1–FR-5.6)

### Phase 4: AI & Advanced Features

- Wire AI integration for repository summarization (FR-10.1)
- ~~Implement README extraction and indexing~~ ✅
- Build Thoughtworks Tech Radar (FR-6)

### Phase 5: Production Readiness

- Configure Azure Key Vault integration (NFR-4.1)
- Set up monitoring and health checks (NFR-3.1, NFR-7.2, NFR-7.3)
- Configure database backups and WAL archiving (NFR-3.2, NFR-3.3)
- Add pre-commit hooks and measure test coverage (NFR-5.1, NFR-5.2)

---

## Technical Constraints

| ID   | Constraint                      | Status | Notes                                                        |
| ---- | ------------------------------- | ------ | ------------------------------------------------------------ |
| TC-1 | PostgreSQL 15+ with TimescaleDB | ✅ Met | Docker Compose configured with TimescaleDB                   |
| TC-2 | Python 3.11+                    | ✅ Met | Project configured for Python 3.11+                          |
| TC-3 | RabbitMQ for task queue         | ✅ Met | RabbitMQ in Docker Compose                                   |
| TC-4 | Grafana 10+ for visualization   | ✅ Met | Grafana 11.0.0 in Docker Compose with 9 provisioned dashboards |

---

## External Dependencies Status

| ID  | Dependency           | Status        | Notes                                                                                                  |
| --- | -------------------- | ------------- | ------------------------------------------------------------------------------------------------------ |
| D-1 | Azure DevOps API     | ✅ Integrated | Full extractor implementation                                                                          |
| D-2 | GitHub API           | ✅ Integrated | Full extractor implementation                                                                          |
| D-3 | OSV.dev API          | ✅ Integrated | `src/analyzers/osv_client.py`; enrichment wired into workflow — 2026-01-24                             |
| D-4 | endoflife.date API   | ✅ Integrated | `src/analyzers/eol_client.py`; enrichment wired into workflow — 2026-01-24                             |
| D-5 | Anthropic/OpenAI API | 🔶 Partial    | SDK dependencies installed; not wired into repository summarization flow                               |

---

## Business Constraints

| ID   | Constraint                   | Rationale                                   |
| ---- | ---------------------------- | ------------------------------------------- |
| BC-1 | Azure DevOps PAT rate limits | API throttling requires careful scheduling  |
| BC-2 | GitHub API rate limits       | 5,000 requests/hour for authenticated users |
| BC-3 | AI API costs                 | LLM usage metered, summarization optional   |

---

## Assumptions

| ID  | Assumption                                                                  |
| --- | --------------------------------------------------------------------------- |
| A-1 | Organizations have existing Azure DevOps or GitHub accounts with API access |
| A-2 | Users have appropriate permissions to create Personal Access Tokens         |
| A-3 | Infrastructure team can provision PostgreSQL and RabbitMQ instances         |
| A-4 | Grafana is already deployed or can be deployed alongside this system        |
| A-5 | Network connectivity exists between analysis system and code platforms      |

---

## Out of Scope

| Item                         | Rationale                                                |
| ---------------------------- | -------------------------------------------------------- |
| Source code storage          | System stores only metadata and metrics, not actual code |
| Real-time webhook processing | Batch processing model, not event-driven                 |
| Custom rule engines          | Relies on existing analysis tools (pylint, bandit, etc.) |
| Multi-tenancy                | Single-tenant deployment model                           |
| User authentication UI       | Uses existing Grafana authentication                     |
| Automated remediation        | Provides insights only, no automatic code changes        |

---

## Glossary

| Term       | Definition                                                                                  |
| ---------- | ------------------------------------------------------------------------------------------- |
| CMDB       | Configuration Management Database — centralized repository for IT asset information         |
| CVE        | Common Vulnerabilities and Exposures — standardized vulnerability identifier                |
| EOL        | End of Life — software version no longer receiving updates                                  |
| Hypertable | TimescaleDB concept for time-series partitioned tables                                      |
| PAT        | Personal Access Token — authentication credential for API access                            |
| PR         | Pull Request — code change proposal for review                                              |
| SDLC       | Software Development Life Cycle                                                             |
| Service    | A logical grouping of one or more repositories that together deliver a business capability  |
| Team       | A group of contributors who work together, used for aggregating metrics and filtering views |

---

## Revision History

| Version | Date       | Author | Changes                                                                                           |
| ------- | ---------- | ------ | ------------------------------------------------------------------------------------------------- |
| 1.0     | 2026-01-17 | System | Initial requirements and status assessment                                                        |
| 1.7     | 2026-01-24 | System | Added FR-1.5 (metadata extraction), FR-4.5 (GitHub security features)                            |
| 2.0     | 2026-01-25 | System | README and metadata extraction for both platforms; FR-8.2/FR-8.4 paused for performance           |
| 2.1     | 2026-01-25 | System | Added NFR-7 (Observability) requirements                                                          |
| 2.2     | 2026-02-09 | System | FR-9.5 complete; NFR-7.1/7.4/7.5 complete after extraction progress tracking implemented          |
| 2.5     | 2026-03-26 | System | FR-13.8 Complete; DASH-TEAM-001 resolved in Plan 016; GitHub issues #32, #33 track remaining defects |
| 3.0     | 2026-04-05 | System | Merged `business-requirements.md` + `requirements-status.md` into single document                |
