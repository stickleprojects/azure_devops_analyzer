# Platform Parity: Azure DevOps vs GitHub

## Overview

This document provides a comprehensive comparison of the Azure DevOps and GitHub extractor implementations, demonstrating functional parity for core features.

**Status:** ✅ **Functional Parity Achieved** (as of 2026-01-24)

---

## Extractor API Comparison

Both platforms implement identical interface methods for extraction operations:

| Method                            | GitHub | Azure DevOps | Return Type          | Purpose                            |
| --------------------------------- | ------ | ------------ | -------------------- | ---------------------------------- |
| `get_organizations()`             | ✅     | ✅           | `OrganizationData[]` | List all orgs/users                |
| `get_projects(org)`               | ✅     | ✅           | `ProjectData[]`      | List projects within organization  |
| `get_repositories(org, project)`  | ✅     | ✅           | `RepositoryData[]`   | List repos in project              |
| `get_repository(repo_id)`         | ✅     | ✅           | `RepositoryData`     | Get single repo metadata           |
| `get_branches(repo_id)`           | ✅     | ✅           | `BranchData[]`       | List branches                      |
| `get_languages(repo_id)`          | ✅     | ✅           | `LanguageData[]`     | Get language statistics            |
| `get_commits(repo_id)`            | ✅     | ✅           | `CommitData[]`       | List commits                       |
| `get_pull_requests(repo_id)`      | ✅     | ✅           | `PullRequestData[]`  | List PRs with reviews and comments |
| `get_file_tree(repo_id)`          | ✅     | ✅           | `FileData[]`         | Get repo file structure            |
| `get_file_content(repo_id, path)` | ✅     | ✅           | `FileContent`        | Read specific file content         |

**Note:** Both extractors use the same data models from `src/extractors/models.py`, ensuring consistent data structures.

---

## Workflow Comparison

Both workflows follow identical orchestration patterns:

### GitHub Workflow (`src/workflows/github_analysis.py`)

```
run()
  ├─ _fetch_organizations()
  └─ _process_organization(org_data)
       └─ _process_repository(repo_data)
            ├─ _process_branches(repo_data)
            ├─ _process_languages(repo_data)
            ├─ _process_technologies(repo_data)
            ├─ _process_readme_files(repo_data)        # GitHub-specific
            ├─ _process_commits(repo_data)
            ├─ _process_pull_requests(repo_data)
            └─ _process_dependencies(repo_data)
```

### Azure DevOps Workflow (`src/workflows/azure_devops_analysis.py`)

```
run()
  ├─ _fetch_organizations()
  └─ _process_organization(org_data)
       ├─ _fetch_projects(org_data)
       └─ _process_project(org_data, project_data)
            └─ _process_repository(org_data, repo_data)
                 ├─ _process_branches(repo_data)
                 ├─ _process_languages(repo_data)
                 ├─ _process_technologies(repo_data)
                 ├─ _process_commits(repo_data)
                 ├─ _process_pull_requests(repo_data)
                 └─ _process_dependencies(repo_data)
```

**Key Differences:**

- Azure DevOps has explicit project layer (organizations → projects → repositories)
- GitHub has flatter structure (organizations/users → repositories)
- Both use identical storage layer (`src/database/storage.py`)

---

## Language Detection Implementation

### GitHub

- **Method:** API-based (`GET /repos/{owner}/{repo}/languages`)
- **Accuracy:** High (GitHub analyzes repo on push)
- **Data:** Byte counts per language
- **Implementation:** Direct API call returns language distribution

### Azure DevOps

- **Method:** File-based heuristics
- **Accuracy:** High (scans all files in tree)
- **Data:** File counts and byte estimates per language
- **Implementation:** `get_languages()` uses file extensions and filename patterns

Both store identical data structures in `RepositoryLanguage` table with time-series support.

---

## Technology Detection

**Shared Implementation:** Both platforms use `TechnologyDetector` (`src/analyzers/technology_detector.py`)

### Detection Categories (8 Total)

1. **Programming Languages** (26+ languages)
   - Python, JavaScript, TypeScript, Java, C#, Go, Rust, PHP, etc.
2. **Frameworks** (10+ frameworks)
   - React, Angular, Vue, Django, Flask, .NET, Spring Boot, etc.
3. **Databases** (6+ databases)
   - PostgreSQL, MySQL, MongoDB, Redis, Elasticsearch, etc.
4. **Deployment Platforms** (8+ platforms)
   - Docker, Kubernetes, AWS, Azure, GCP, Heroku, etc.
5. **Build Tools** (8+ tools)
   - Maven, Gradle, npm, Webpack, CMake, Make, etc.
6. **Testing Frameworks** (9+ frameworks)
   - pytest, Jest, JUnit, NUnit, RSpec, etc.
7. **CI/CD Platforms** (7+ platforms)
   - GitHub Actions, Azure Pipelines, Jenkins, GitLab CI, etc.
8. **Documentation Tools**
   - Sphinx, Doxygen, etc.

### Detection Method

Both platforms extract file tree and pass to `TechnologyDetector.detect(file_names)`:

- File extension mapping (`.py` → Python, `.tsx` → TypeScript + React)
- Project file patterns (`pom.xml` → Maven, `package.json` → npm)
- Config file detection (`.github/workflows/*.yml` → GitHub Actions)

---

## Dependency Analysis

**Shared Implementation:** Both platforms use `DependencyAnalyzer` (`src/analyzers/dependency_analyzer.py`)

### Supported Ecosystems (7 Total)

| Ecosystem | Manifest Files                                  | Parser                     |
| --------- | ----------------------------------------------- | -------------------------- |
| PyPI      | `requirements.txt`, `pyproject.toml`, `Pipfile` | `PythonRequirementsParser` |
| npm       | `package.json`, `package-lock.json`             | `NpmParser`                |
| Maven     | `pom.xml`                                       | `MavenParser`              |
| NuGet     | `*.csproj`, `packages.config`                   | `NuGetParser`              |
| Go        | `go.mod`, `go.sum`                              | `GoModParser`              |
| Ruby      | `Gemfile`, `Gemfile.lock`                       | `GemfileParser`            |
| Rust      | `Cargo.toml`, `Cargo.lock`                      | `CargoParser`              |

### Enrichment Process (Both Platforms)

1. **Extract Dependencies:** Parse manifest files from file tree
2. **Enrich with OSV.dev:** Get latest versions and vulnerability data
3. **Check EOL Status:** Query endoflife.date for lifecycle info
4. **Store Results:** Save to `repository_dependencies` table

**Storage:** Both use `store_enriched_dependencies()` with identical schema.

---

## Test Coverage Comparison

### GitHub Tests (`tests/contract/integration/test_github_extraction_e2e.py`)

- ✅ **14 tests total**
- Repository metadata extraction
- Private repo flags
- Branch tracking
- Commit tracking
- Contributor tracking
- Repository constraints
- Foreign key relationships
- Timezone handling
- Language detection (3 tests)
- Technology detection (3 tests)

### Azure DevOps Tests (`tests/contract/integration/test_azure_devops_extraction_e2e.py`)

- ✅ **10 tests total**
- Repository metadata extraction
- Branch tracking
- Commit tracking with metadata
- Database constraints
- Timezone-aware timestamps
- Language detection (2 tests)
- Technology detection (3 tests)
- Cross-platform schema validation

### Shared Tests

- ✅ `test_both_platforms_same_database_schema()` - Validates both platforms write to identical schema
- ✅ `test_dependency_enrichment_e2e.py` - Tests dependency extraction for both platforms

---

## Platform-Specific Features

### Features Required for Both Platforms

#### 1. README Extraction

- **Requirement:** FR-8.2 (High Priority)
- **GitHub Status:** ✅ Implemented
  - Method: `get_readme_files(repo_id)`
  - Storage: `store_readme()` → `repository_readmes` table
  - Extracts multiple README files (root and subdirectories)
- **Azure DevOps Status:** ⚠️ Required, Not Yet Implemented
  - **Implementation Plan:**
    1. Add `get_readme_files()` method to `AzureDevOpsExtractor`
    2. Use `get_file_tree()` to find README files (case-insensitive: readme.md, README.txt, etc.)
    3. Use `get_file_content()` to fetch content
    4. Return list of `ReadmeData` objects
    5. Add `_process_readme_files()` to `AzureDevOpsAnalysisWorkflow`
  - **Estimated Effort:** 2-4 hours

#### 2. Repository Metadata (Team/Service Mapping)

- **Requirement:** FR-1.5 (High Priority)
- **GitHub Status:** ✅ Implemented
  - Method: `get_repository_metadata(repo_id)`
  - Source: `.github/metadata.json` file
  - Fields: `team_name`, `service_name`
  - Storage: Populates `Repository.team_name` and `Repository.service_name`
- **Azure DevOps Status:** ⚠️ Required, Not Yet Implemented
  - **Implementation Plan:**
    1. Define standard metadata file location (e.g., `.azure/metadata.json` or reuse `.github/metadata.json`)
    2. Add `get_repository_metadata()` method to `AzureDevOpsExtractor`
    3. Use `get_file_content()` to read metadata file
    4. Parse JSON and return metadata object
    5. Update `_process_repository()` in workflow to fetch and apply metadata
  - **Estimated Effort:** 2-3 hours
  - **Note:** Consider using `.github/metadata.json` for cross-platform consistency

### Platform-Unique Features

These features are only available on specific platforms due to platform API limitations:

#### GitHub-Specific: Security Features

- **Fields:** `has_vulnerability_alerts`, `has_secret_scanning`, `has_dependabot_alerts`
- **Source:** GitHub Security API
- **Purpose:** Track security feature enablement
- **Status:** ✅ Implemented
- **Note:** Azure DevOps has different security model (not directly comparable)

---

## Database Schema

Both platforms write to **identical database schema**:

### Core Tables

- `repositories` - Repo metadata
- `branches` - Branch tracking
- `commits` - Commit history
- `contributors` - User contributions
- `pull_requests` - PR tracking
- `pull_request_reviews` - PR reviews
- `pull_request_review_comments` - Review comments

### Analysis Tables

- `repository_languages` - Language distribution (TimescaleDB hypertable)
- `repository_dependencies` - Dependency tracking
- `vulnerabilities` - Security issues

### Shared Fields

All platform-specific fields (GitHub security features) are nullable, allowing Azure DevOps repos to leave them null.

---

## Configuration

### GitHub Configuration (`src/config/github.py`)

```python
class GitHubConfig:
    token: str
    base_url: str = "https://api.github.com"
    organizations: list[str]
    timeout: int = 30
```

### Azure DevOps Configuration (`src/config/azure_devops.py`)

```python
class AzureDevOpsConfig:
    org_url: str
    personal_access_token: str
    api_version: str = "7.1-preview.1"
    timeout: int = 30
```

Both support environment variable configuration.

---

## Performance Characteristics

### GitHub

- **Rate Limit:** 5,000 requests/hour (authenticated)
- **Pagination:** Link headers, 100 items per page
- **Language API:** Single call per repo
- **File Tree:** Recursive tree API (single call)

### Azure DevOps

- **Rate Limit:** No documented limit
- **Pagination:** Continuation tokens
- **Language Detection:** File tree scan (multiple calls)
- **File Tree:** Single API call for full tree

Both implement identical rate limit handling and retry logic.

---

## Integration Points

### Workflow Triggers

Both workflows can be triggered via:

- `scripts/submit_extraction_task.py` with `--platform` flag
- Scheduler (`config/scheduler.yaml`)
- Direct Python invocation

### Storage Layer

Both use:

- `src/database/storage.py` - Unified storage functions
- `src/database/models.py` - SQLAlchemy ORM models
- `src/database/connection.py` - Session management

### Analyzers

Both use:

- `src/analyzers/dependency_analyzer.py` - Dependency extraction
- `src/analyzers/technology_detector.py` - Technology detection
- `src/analyzers/enrichers/osv_client.py` - Vulnerability enrichment
- `src/analyzers/enrichers/endoflife_client.py` - EOL detection

---

## Conclusion

✅ **Azure DevOps and GitHub have achieved functional parity** for all core extraction features (FR-1 through FR-4):

- Identical extractor API surface
- Shared data models and storage layer
- Same analyzer implementations
- Comprehensive test coverage for both
- Unified workflow orchestration patterns

⚠️ **Outstanding Cross-Platform Requirements:**

1. **README Extraction (FR-8.2):** GitHub implemented, Azure DevOps needs implementation
2. **Repository Metadata (FR-1.5):** GitHub implemented, Azure DevOps needs implementation

Both features are **required for both platforms** to achieve full parity. Implementation is straightforward using existing file tree and file content APIs.

**Platform Differences:**

1. **Organizational structure** (Azure DevOps explicit projects vs GitHub flat orgs)
2. **API implementation details** (REST endpoints, authentication, pagination)
3. **Security features** (GitHub-specific APIs not available in Azure DevOps)

Once README and metadata extraction are implemented for Azure DevOps, both platforms will have identical capabilities for repository discovery, analysis, and metadata tracking.
