# Business Requirements Document

## Document Information

| Field            | Value                      |
| ---------------- | -------------------------- |
| Project Name     | Repository Analysis System |
| Document Version | 1.3                        |
| Status           | Draft                      |
| Last Updated     | 2026-02-21                 |

## Executive Summary

The Repository Analysis System is a platform designed to provide comprehensive insights into code repositories hosted on Azure DevOps and GitHub. It enables engineering leaders and teams to monitor code quality, security vulnerabilities, contributor activity, and development patterns through automated analysis and visualization dashboards.

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

## Stakeholders

| Role                   | Responsibilities                         | Interests                                                |
| ---------------------- | ---------------------------------------- | -------------------------------------------------------- |
| Engineering Leadership | Strategic decisions, resource allocation | High-level metrics, security posture, team productivity  |
| Development Team Leads | Team management, code reviews            | Team-specific metrics, PR patterns, contributor activity |
| Security Team          | Vulnerability management, compliance     | Vulnerability reports, dependency health, EOL tracking   |
| Individual Developers  | Code contribution, self-improvement      | Personal metrics, code quality feedback                  |
| DevOps/Platform Team   | System maintenance, infrastructure       | System health, job scheduling, data freshness            |

## Functional Requirements

### FR-1: Repository Discovery and Tracking

| ID     | Requirement                                                                       | Priority | Acceptance Criteria                                               |
| ------ | --------------------------------------------------------------------------------- | -------- | ----------------------------------------------------------------- |
| FR-1.1 | System shall discover all repositories within configured organizations            | High     | All repos from Azure DevOps orgs and GitHub orgs/users are listed |
| FR-1.2 | System shall track repository metadata (name, URL, default branch, creation date) | High     | Metadata stored and queryable for all tracked repositories        |
| FR-1.3 | System shall support marking repositories as active/inactive                      | Medium   | Inactive repos excluded from scheduled analysis                   |
| FR-1.4 | System shall track multiple branches per repository                               | High     | Branch-level analysis available for all tracked branches          |

### FR-2: Language and Technology Detection

| ID     | Requirement                                                       | Priority | Acceptance Criteria                                              |
| ------ | ----------------------------------------------------------------- | -------- | ---------------------------------------------------------------- |
| FR-2.1 | System shall detect programming languages used in each repository | High     | Languages identified with percentage, line count, and byte count |
| FR-2.2 | System shall track language distribution over time                | Medium   | Historical language data available for trend analysis            |
| FR-2.3 | System shall identify key technologies and frameworks             | Medium   | Technology stack documented per repository                       |

### FR-3: Dependency Analysis

| ID     | Requirement                                                              | Priority | Acceptance Criteria                              |
| ------ | ------------------------------------------------------------------------ | -------- | ------------------------------------------------ |
| FR-3.1 | System shall extract dependencies from package manifest files            | High     | Support for PyPI, npm, Maven, NuGet ecosystems   |
| FR-3.2 | System shall identify current and latest versions of dependencies        | High     | Version comparison available for each dependency |
| FR-3.3 | System shall flag end-of-life (EOL) dependencies                         | High     | EOL status and date tracked for known packages   |
| FR-3.4 | System shall distinguish between production and development dependencies | Medium   | is_dev_dependency flag populated correctly       |

### FR-4: Security Vulnerability Scanning

| ID     | Requirement                                                                     | Priority | Acceptance Criteria                             |
| ------ | ------------------------------------------------------------------------------- | -------- | ----------------------------------------------- |
| FR-4.1 | System shall identify known vulnerabilities (CVEs) in dependencies              | Critical | CVE IDs and severity levels recorded            |
| FR-4.2 | System shall classify vulnerabilities by severity (Critical, High, Medium, Low) | Critical | Severity categorization aligned with CVSS       |
| FR-4.3 | System shall provide remediation guidance (fixed version)                       | High     | fixed_in_version populated when available       |
| FR-4.4 | System shall track vulnerability publication and modification dates             | Medium   | Timestamps recorded for vulnerability lifecycle |

### FR-5: Dependency Vulnerability and EOL Tracking Dashboard

| ID     | Requirement                                                                                 | Priority | Acceptance Criteria                                                   |
| ------ | ------------------------------------------------------------------------------------------- | -------- | --------------------------------------------------------------------- |
| FR-5.1 | System shall provide a comprehensive dashboard showing all dependencies across repositories | High     | Dashboard aggregates unique libraries and their usage patterns        |
| FR-5.2 | System shall display dependency versions, EOL status, and vulnerability counts per library  | High     | Library cards show current version, EOL date, and CVE count           |
| FR-5.3 | System shall allow filtering dashboard by organization, team, service, and repository       | High     | Filter controls enable drill-down from portfolio to repository level  |
| FR-5.4 | System shall highlight libraries with critical vulnerabilities or upcoming EOL dates        | High     | Visual indicators (badges/colors) for Critical CVEs and EOL < 90 days |
| FR-5.5 | System shall show which repositories depend on each library                                 | Medium   | Repository list with version information for each dependency          |
| FR-5.6 | System shall track library adoption trends (how many repos using over time)                 | Medium   | Historical adoption curve available for each library                  |
| FR-5.7 | System shall integrate EOL data from endoflife.date and vulnerability data from OSV.dev     | High     | Data sources continuously synchronized                                |

### FR-6: Thoughtworks Tech Radar Publication

| ID     | Requirement                                                                                       | Priority | Acceptance Criteria                                                              |
| ------ | ------------------------------------------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------- |
| FR-6.1 | System shall generate a Thoughtworks Tech Radar based on actual library usage across organization | High     | Radar generated in JSON format compatible with Thoughtworks Radar viewer         |
| FR-6.2 | System shall categorize libraries into Thoughtworks Tech Radar rings (Adopt, Trial, Assess, Hold) | High     | Categorization based on adoption metrics and organizational recommendations      |
| FR-6.3 | System shall populate radar with organization's actual technology stack from dependency analysis  | High     | All detected libraries with 2+ repositories appear on radar                      |
| FR-6.4 | System shall include Thoughtworks recommended libraries as potential Trial/Assess options         | Medium   | Recommended libraries highlighted separately with rationale                      |
| FR-6.5 | System shall display radar with configurable move history and publication timeline                | Medium   | Radar shows technology migrations and categorization changes over time           |
| FR-6.6 | System shall provide endpoint to publish/export radar for sharing with stakeholders               | High     | REST API endpoint available; HTML visualization compatible with standard viewers |
| FR-6.7 | System shall track blips with metadata (adoption date, vulnerability status, EOL impact)          | Medium   | Each technology entry includes context-specific metadata                         |

### FR-7: Code Quality Analysis

| ID     | Requirement                                                                    | Priority | Acceptance Criteria                               |
| ------ | ------------------------------------------------------------------------------ | -------- | ------------------------------------------------- |
| FR-7.1 | System shall calculate code complexity metrics                                 | High     | Complexity scores available per repository/branch |
| FR-7.2 | System shall identify code issues by category (bug, vulnerability, code smell) | High     | Issues categorized and counted by severity        |
| FR-7.3 | System shall calculate maintainability index                                   | Medium   | Index calculated using industry-standard formula  |
| FR-7.4 | System shall track test coverage percentage                                    | Medium   | Coverage data integrated from test runs           |
| FR-7.5 | System shall estimate technical debt in time units                             | Medium   | Debt expressed in minutes for remediation effort  |

### FR-8: Contributor Analytics

| ID     | Requirement                                                              | Priority | Acceptance Criteria                             |
| ------ | ------------------------------------------------------------------------ | -------- | ----------------------------------------------- |
| FR-8.1 | System shall track unique contributors per repository                    | High     | Contributors identified by email                |
| FR-8.2 | System shall calculate contributor metrics (commits, lines changed, PRs) | High     | Metrics aggregated by configurable time periods |
| FR-8.3 | System shall track commit patterns (frequency, message quality)          | Medium   | Commit message quality scored                   |
| FR-8.4 | System shall track active days per contributor                           | Medium   | Active days counted per period                  |

### FR-9: Pull Request Analysis

| ID     | Requirement                                                                 | Priority | Acceptance Criteria                                     |
| ------ | --------------------------------------------------------------------------- | -------- | ------------------------------------------------------- |
| FR-9.1 | System shall track PR lifecycle (created, updated, merged, closed)          | High     | All PR state transitions captured with timestamps       |
| FR-9.2 | System shall calculate PR size metrics (files changed, lines added/removed) | High     | Size categorization (small, medium, large, extra_large) |
| FR-9.3 | System shall track review activity (reviewers, votes, comments)             | High     | Review data linked to contributors                      |
| FR-9.4 | System shall identify PR quality issues                                     | Medium   | Issue flags populated for problematic PRs               |

### FR-10: Repository Summarization

| ID      | Requirement                                              | Priority | Acceptance Criteria                              |
| ------- | -------------------------------------------------------- | -------- | ------------------------------------------------ |
| FR-10.1 | System shall generate AI-powered repository summaries    | Medium   | Summary, purpose, and target audience documented |
| FR-10.2 | System shall extract and index README content            | Medium   | Full-text search available on README content     |
| FR-10.3 | System shall track which AI model generated each summary | Low      | Model identifier stored with summary             |

### FR-11: Visualization and Reporting

| ID      | Requirement                                                           | Priority | Acceptance Criteria                                 |
| ------- | --------------------------------------------------------------------- | -------- | --------------------------------------------------- |
| FR-11.1 | System shall provide Grafana dashboards for all metrics               | High     | Dashboards cover all metric categories              |
| FR-11.2 | System shall support time-range filtering on all visualizations       | High     | Users can select custom date ranges                 |
| FR-11.3 | System shall support drill-down from organization to repository level | Medium   | Hierarchical navigation available                   |
| FR-11.4 | System shall provide security-focused dashboard views                 | High     | Vulnerability and EOL metrics prominently displayed |

### FR-12: Service-Repository Mapping

| ID      | Requirement                                                                       | Priority | Acceptance Criteria                                                                            |
| ------- | --------------------------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------- |
| FR-12.1 | System shall support defining services with name, purpose, and CMDB identifier    | High     | Services can be created with all required attributes                                           |
| FR-12.2 | System shall support many-to-many relationships between repositories and services | High     | A repository can belong to zero or more services; a service can have zero or more repositories |
| FR-12.3 | System shall track which repositories contribute to each service                  | High     | Service composition queryable showing all associated repositories                              |
| FR-12.4 | System shall aggregate metrics at the service level                               | Medium   | Dashboard views available showing combined metrics for all repositories in a service           |
| FR-12.5 | System shall support repositories belonging to multiple services                  | Medium   | Cross-service repository contributions tracked without duplication                             |

### FR-13: Team Management and Contributor Linking

| ID      | Requirement                                                                        | Priority | Acceptance Criteria                                                                         |
| ------- | ---------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------- |
| FR-13.1 | System shall support defining teams with name, description, and optional CMDB link | High     | Teams can be created with all required attributes                                           |
| FR-13.2 | System shall support many-to-many relationships between contributors and teams     | High     | A contributor can belong to zero or more teams; a team can have zero or more contributors   |
| FR-13.3 | System shall track team membership with effective dates (start/end)                | Medium   | Historical team membership queryable for past periods                                       |
| FR-13.4 | System shall support team hierarchy (parent/child teams)                           | Low      | Nested teams with aggregated metrics at parent level                                        |
| FR-13.5 | System shall aggregate contributor metrics at the team level                       | High     | Team-level totals for commits, PRs, reviews, lines changed                                  |
| FR-13.6 | System shall provide Individual Contributor Dashboard                              | Medium   | Dashboard showing personal commits, PRs authored, reviews given across all repositories     |
| FR-13.7 | System shall display team member aggregates on Team Overview dashboard             | Medium   | Team Overview shows per-member stats (commits, PRs, reviews) with drill-down to contributor |
| FR-13.8 | System shall support filtering dashboards by team                                  | Medium   | All relevant dashboards can be filtered to show only team members' activity                 |

### FR-14: Administrative Dashboard

| ID      | Requirement                                                                          | Priority | Acceptance Criteria                                                                            |
| ------- | ------------------------------------------------------------------------------------ | -------- | ---------------------------------------------------------------------------------------------- |
| FR-14.1 | System shall provide a dedicated administrative dashboard                            | High     | Centralized admin interface accessible to system administrators                                |
| FR-14.2 | Admin dashboard shall include contextual help text for all administrative operations | High     | Each administrative function has clear documentation and usage guidance                        |
| FR-14.3 | System shall provide force rescan functionality through the admin dashboard          | High     | Administrators can trigger immediate repository rescans regardless of configured intervals     |
| FR-14.4 | Admin dashboard shall consolidate all administrative controls in one location        | Medium   | All system administrative functions (rescans, configuration, status monitoring) centralized    |
| FR-14.5 | System shall provide status visibility for ongoing administrative operations         | Medium   | Dashboard displays current extraction jobs, queue status, and system health metrics            |
| FR-14.6 | Admin dashboard shall support per-platform administrative actions                    | Medium   | Separate controls for GitHub and Azure DevOps operations with platform-specific configurations |

## Non-Functional Requirements

### NFR-1: Performance

| ID      | Requirement                            | Target                                      |
| ------- | -------------------------------------- | ------------------------------------------- |
| NFR-1.1 | Full organization scan completion time | < 4 hours for 500 repositories              |
| NFR-1.2 | Incremental update scan time           | < 30 minutes for changed repositories       |
| NFR-1.3 | Dashboard query response time          | < 3 seconds for 95th percentile             |
| NFR-1.4 | Database query performance             | Optimized indexes for common query patterns |

### NFR-2: Scalability

| ID      | Requirement               | Target                                     |
| ------- | ------------------------- | ------------------------------------------ |
| NFR-2.1 | Repository capacity       | Support 10,000+ repositories               |
| NFR-2.2 | Historical data retention | 2+ years of time-series data               |
| NFR-2.3 | Concurrent analysis jobs  | Support parallel processing via task queue |

### NFR-3: Reliability

| ID      | Requirement            | Target                                      |
| ------- | ---------------------- | ------------------------------------------- |
| NFR-3.1 | System availability    | 99% uptime during business hours            |
| NFR-3.2 | Data durability        | Daily backups with 30-day retention         |
| NFR-3.3 | Point-in-time recovery | WAL archiving enabled for disaster recovery |
| NFR-3.4 | Job failure handling   | Automatic retry with exponential backoff    |

### NFR-4: Security

| ID      | Requirement           | Target                                                   |
| ------- | --------------------- | -------------------------------------------------------- |
| NFR-4.1 | Credential management | All secrets stored in Azure Key Vault                    |
| NFR-4.2 | Database access       | Read-only user for Grafana, principle of least privilege |
| NFR-4.3 | API authentication    | Personal Access Tokens with minimal required scopes      |
| NFR-4.4 | Data classification   | No source code stored, only metadata and metrics         |

### NFR-5: Maintainability

| ID      | Requirement            | Target                                              |
| ------- | ---------------------- | --------------------------------------------------- |
| NFR-5.1 | Code quality standards | Enforced via pre-commit hooks (black, flake8, mypy) |
| NFR-5.2 | Test coverage          | Minimum 80% coverage for core modules               |
| NFR-5.3 | Documentation          | All modules documented with docstrings              |
| NFR-5.4 | Logging                | Structured logging with correlation IDs             |

### NFR-6: Parallel Repository Processing

| ID      | Requirement                              | Target                                                                                                                                                   |
| ------- | ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| NFR-6.1 | Repository parallelism                   | System must process repositories in parallel via the task queue, with a configurable worker pool supporting at least 5 concurrent workers in production. |
| NFR-6.2 | Parallel throughput                      | With 5+ workers, sustain end-to-end processing of 500 repositories per hour without triggering platform rate limits.                                     |
| NFR-6.3 | Configurable throttling and coordination | Rate limiting and queue routing must be configurable per platform (GitHub, Azure DevOps) to safely scale worker concurrency.                             |

## Constraints

### Technical Constraints

| ID   | Constraint                      | Rationale                                  |
| ---- | ------------------------------- | ------------------------------------------ |
| TC-1 | PostgreSQL 15+ with TimescaleDB | Required for time-series data optimization |
| TC-2 | Python 3.11+                    | Language standardization, async support    |
| TC-3 | RabbitMQ for task queue         | Celery broker requirement                  |
| TC-4 | Grafana 10+ for visualization   | Dashboard compatibility                    |

### Business Constraints

| ID   | Constraint                   | Rationale                                   |
| ---- | ---------------------------- | ------------------------------------------- |
| BC-1 | Azure DevOps PAT rate limits | API throttling requires careful scheduling  |
| BC-2 | GitHub API rate limits       | 5,000 requests/hour for authenticated users |
| BC-3 | AI API costs                 | LLM usage metered, summarization optional   |

## Assumptions

| ID  | Assumption                                                                  |
| --- | --------------------------------------------------------------------------- |
| A-1 | Organizations have existing Azure DevOps or GitHub accounts with API access |
| A-2 | Users have appropriate permissions to create Personal Access Tokens         |
| A-3 | Infrastructure team can provision PostgreSQL and RabbitMQ instances         |
| A-4 | Grafana is already deployed or can be deployed alongside this system        |
| A-5 | Network connectivity exists between analysis system and code platforms      |

## Dependencies

| ID  | Dependency           | Type     | Impact if Unavailable                                   |
| --- | -------------------- | -------- | ------------------------------------------------------- |
| D-1 | Azure DevOps API     | External | Cannot extract Azure DevOps repository data             |
| D-2 | GitHub API           | External | Cannot extract GitHub repository data                   |
| D-3 | OSV.dev API          | External | Vulnerability data unavailable (graceful degradation)   |
| D-4 | endoflife.date API   | External | EOL detection unavailable (graceful degradation)        |
| D-5 | Anthropic/OpenAI API | External | Repository summarization unavailable (optional feature) |

## Out of Scope

The following items are explicitly excluded from this project:

| Item                         | Rationale                                                |
| ---------------------------- | -------------------------------------------------------- |
| Source code storage          | System stores only metadata and metrics, not actual code |
| Real-time webhook processing | Batch processing model, not event-driven                 |
| Custom rule engines          | Relies on existing analysis tools (pylint, bandit, etc.) |
| Multi-tenancy                | Single-tenant deployment model                           |
| User authentication UI       | Uses existing Grafana authentication                     |
| Automated remediation        | Provides insights only, no automatic code changes        |

## Glossary

| Term       | Definition                                                                                  |
| ---------- | ------------------------------------------------------------------------------------------- |
| CMDB       | Configuration Management Database - centralized repository for IT asset information         |
| CVE        | Common Vulnerabilities and Exposures - standardized vulnerability identifier                |
| EOL        | End of Life - software version no longer receiving updates                                  |
| Hypertable | TimescaleDB concept for time-series partitioned tables                                      |
| PAT        | Personal Access Token - authentication credential for API access                            |
| PR         | Pull Request - code change proposal for review                                              |
| SDLC       | Software Development Life Cycle                                                             |
| Service    | A logical grouping of one or more repositories that together deliver a business capability  |
| Team       | A group of contributors who work together, used for aggregating metrics and filtering views |

## Revision History

| Version | Date       | Author | Changes                                                                     |
| ------- | ---------- | ------ | --------------------------------------------------------------------------- |
| 1.0     | 2026-01-17 | System | Initial draft based on README and documentation analysis                    |
| 1.1     | 2026-01-18 | System | Added FR-11: Team Management and Contributor Linking                        |
| 1.2     | 2026-01-19 | System | Added FR-5: Dependency EOL/Vulnerability Dashboard, FR-6: Tech Radar Export |
| 1.3     | 2026-02-21 | System | Added FR-14: Administrative Dashboard with help text and rescan controls    |

## Approval

| Role           | Name | Signature | Date |
| -------------- | ---- | --------- | ---- |
| Product Owner  |      |           |      |
| Technical Lead |      |           |      |
| Security Lead  |      |           |      |
