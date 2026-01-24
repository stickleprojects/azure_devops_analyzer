# Development Progress Log

## Session: 2026-01-24 - Azure DevOps Config, Manifest Extraction & File Naming

### Summary
Implemented manifest extraction system, created Azure DevOps configuration class with full .env support, and enforced naming conventions for single-class Python files.

### Key Accomplishments

#### 1. Manifest File Extraction System
**Issue**: Need to extract dependency manifest files from repositories for vulnerability analysis.

**Implementation**:
- Created `ManifestFileData` dataclass in `src/extractors/base.py`
- Implemented `extract_manifests()` method with 30+ manifest patterns across 7 ecosystems:
  - Python: `requirements.txt`, `setup.py`, `pyproject.toml`, `Pipfile`
  - Node.js: `package.json`, `package-lock.json`, `yarn.lock`
  - Java: `pom.xml`, `build.gradle`, `build.gradle.kts`
  - .NET: `*.csproj`, `*.sln`, `packages.config`
  - Go: `go.mod`, `go.sum`
  - Ruby: `Gemfile`, `Gemfile.lock`
  - Rust: `Cargo.toml`, `Cargo.lock`
- Added cross-platform line ending normalization (CRLF/CR → LF)
- Implemented `_infer_ecosystem()` helper for manifest type detection

**Testing**:
- Created 16 unit tests in `tests/unit/test_manifest_extraction.py`
- Tests cover extraction, line endings, ecosystem inference
- All tests passing (100% success rate)

#### 2. Dependency Analysis Integration
**Refactoring**:
- Updated `DependencyAnalyzer.analyze()` to use new `extract_manifests()` method
- Replaced `_parse_manifest_file()` with simpler `_parse_manifest()`
- Removed obsolete methods: `_find_manifest_files()`, old `_parse_manifest_file()`
- Enabled 4 previously-skipped integration tests
- Fixed API signature mismatches in integration tests

**Results**:
- Full pipeline working: extraction → analysis → enrichment → storage
- 11 live API integration tests passing
- End-to-end vulnerability detection functional

#### 3. Azure DevOps Configuration System
**Issue**: Azure DevOps extractor lacked config management similar to GitHub.

**Implementation**:
- Created `AzureDevOpsExtractorConfig` class in `src/config/azure_devops.py`
- Full parity with `GitHubExtractorConfig`:
  - `.from_env()` method for environment/file loading
  - Support for `.env` files with indirect variable resolution
  - Auto-discovery: `.env.resolved` → `.env` → environment variables
  - Pagination and backoff configuration
- Updated `AzureDevOpsExtractor` to accept optional config (defaults to `from_env()`)
- Updated `client.py` functions to accept config parameter
- Created `azure_config` fixtures for both unit and integration tests

**Environment Variables** (all with `AZURE` prefix):
- `AZURE_DEVOPS_PAT` - Personal Access Token (required)
- `AZURE_DEVOPS_ORG_URL` - Organization URL (required)
- `AZURE_DEVOPS_ORG` - Organization name
- `AZURE_DEVOPS_PROJECT` - Project name
- `AZURE_PAGE_SIZE`, `AZURE_MAX_ITEMS_PER_LIST`, `AZURE_MAX_RETRIES`
- `AZURE_BACKOFF_SECONDS`, `AZURE_MAX_BACKOFF_SECONDS`

**Testing**:
- Verified config instantiation and `.from_env()` loading
- Tested indirect variable resolution (e.g., `$AZURE_PAT_TOKEN`)
- Updated all Azure tests to use config fixtures
- No tests directly access `os.environ` for Azure credentials

#### 4. File Naming Convention Enforcement
**Issue**: Inconsistent naming between filenames and class names.

**Convention Applied**: Single-class Python files should have filenames matching the class name (in snake_case).

**Files Renamed** (using `git mv` to preserve history):
- `src/analyzers/parsers/dotnet_parser.py` → `dot_net_parser.py` (class: `DotNetParser`)
- `src/analyzers/parsers/nodejs_parser.py` → `node_js_parser.py` (class: `NodeJsParser`)
- `src/database/models/language.py` → `repository_language.py` (class: `RepositoryLanguage`)

**Import Updates**:
- Updated `src/analyzers/parsers/__init__.py`
- Updated `src/database/models/__init__.py`
- Updated `src/database/models/repository.py`

**Exceptions Preserved** (intentional multi-purpose files):
- `extractor.py`, `github.py`, `eol_client.py`

### Files Created
- `src/config/azure_devops.py` - Azure DevOps configuration class
- `src/config/__init__.py` - Config module exports
- `tests/unit/test_manifest_extraction.py` - 16 unit tests for manifest extraction

### Files Modified
- `src/extractors/base.py` - Added `ManifestFileData`, `extract_manifests()`, `_infer_ecosystem()`
- `src/extractors/__init__.py` - Added `ManifestFileData` export
- `src/analyzers/dependency_analyzer.py` - Refactored to use `extract_manifests()`
- `src/extractors/azure_devops/extractor.py` - Accept and use config
- `src/extractors/azure_devops/client.py` - Accept config parameter
- `tests/contract/integration/conftest.py` - Added `azure_config` fixture
- `tests/contract/integration/test_dependency_enrichment_e2e.py` - Enabled tests
- `tests/unit/test_azure_devops_language_detection.py` - Use config fixture
- `tests/unit/test_manifest_extraction.py` - Use config fixture
- `docs/03-operations/github-config-refactoring.md` - Updated Azure DevOps status
- `docs/PROGRESS.md` - Marked Azure config work as completed

### Files Renamed
- `src/analyzers/parsers/dotnet_parser.py` → `dot_net_parser.py`
- `src/analyzers/parsers/nodejs_parser.py` → `node_js_parser.py`
- `src/database/models/language.py` → `repository_language.py`

### Test Results
- Unit tests: 16/16 passing (manifest extraction)
- Integration tests: 11/11 passing (dependency enrichment E2E)
- Configuration tests: All imports and environment loading verified
- No syntax or import errors

### Technical Decisions
1. **Line Ending Normalization**: Applied universally to handle Windows/Linux differences
2. **Config Pattern Consistency**: Both GitHub and Azure configs use identical API patterns
3. **Test Fixture Strategy**: Session-scoped fixtures for integration, function-scoped for unit
4. **Git History Preservation**: Used `git mv` for file renames to maintain blame history

### Dependencies
No new dependencies - used existing:
- `PyGithub>=2.1.0`
- `azure-devops>=7.1.0`
- `python-dotenv>=1.0.0`

---

## Session: 2026-01-23 - GitHub Configuration & API Fix

### Summary
Major refactoring of GitHub configuration system and resolution of critical bug preventing private repository extraction.

### Key Accomplishments

#### 1. Environment Variable Resolution System
- **Problem**: `.env` file contained indirect variable references (e.g., `GITHUB_TOKEN=$AZURE_VAULT_SECRET`) that weren't being resolved
- **Solution**: Implemented comprehensive `load_env_file()` function in `src/config/github.py` supporting:
  - Indirect variable resolution (`$VARIABLE_NAME`)
  - Chained references (A→B→C)
  - Quote handling for values with spaces
  - Auto-preference for `.env.resolved` over `.env`
  - Configurable override behavior

#### 2. Centralized Configuration Architecture
- **Refactored** `GitHubExtractorConfig` to include credentials:
  - Added `token`, `organization`, and `user` fields
  - Eliminated direct `os.environ` reads throughout codebase
  - Single source of truth for all GitHub configuration
- **Updated** `get_github_client()` to accept config parameter
- **Improved** testability - can inject config objects instead of manipulating environment

#### 3. **Critical Bug Fix: Private Repository Visibility**
**THE KEY FINDING:**

> **When using GitHub's REST API, fetching repositories for a named user (even your own) only returns public repositories. To access private repositories, you MUST use the authenticated user endpoint.**

**The Problem:**
```python
# ❌ This returns only public repos (29 repos)
user = client.get_user('stickleprojects')  
repos = user.get_repos(type="all")

# ✅ This returns all repos including private (60 repos)
user = client.get_user()  # No arguments = authenticated user
repos = user.get_repos(visibility="all")
```

**The Fix:**
Updated `get_repositories()` in `src/extractors/github/extractor.py` to:
1. Check if requested username matches authenticated user
2. Use proper API endpoint based on context
3. Apply correct parameters (`visibility` vs `type`)

**Impact**: The `azure_devops_analyzer` repository (and 31 other private repos) now correctly appear in extraction results.

#### 4. Pagination Implementation Cleanup
- Removed redundant `per_page` parameters from individual API calls
- Configured once on client: `client.per_page = config.page_size`
- Applies globally to all paginated requests (cleaner, more efficient)

#### 5. Comprehensive Test Suite
- **18 new tests** for environment loading and config
  - Simple variables, quoted values, comments
  - Indirect variable resolution (single and chained)
  - Override behavior, invalid values
  - Credential loading and resolution
- **Updated extractor tests** to reflect new API behavior
- **3 live integration tests** now passing with real credentials
  - `test_extractor_returns_azure_devops_analyzer_repo` ✅
  - `test_direct_api_finds_azure_devops_analyzer` ✅
  - `test_debug_extractor_code_path` ✅

### Test Results
```
✅ 34 total tests passing (31 unit + 3 live integration)
  - 18 config/environment tests
  - 2 mock extractor tests  
  - 3 live GitHub API tests
  - 11 import/structure tests
⏱️ 46.44s for live tests (hitting real GitHub API)
```

### Files Modified

#### Core Implementation
- `src/config/github.py` - Enhanced with `load_env_file()`, credentials in config
- `src/extractors/github/client.py` - Accept config parameter, use config values
- `src/extractors/github/extractor.py` - **Critical fix for private repo visibility**

#### Tests
- `tests/test_github_config.py` - 18 comprehensive tests (NEW)
- `tests/test_github_extractor_standalone.py` - Updated for new behavior, live tests enabled

#### Documentation
- `docs/03-operations/github-config-env-loading.md` - Environment loading guide
- `docs/03-operations/github-config-refactoring.md` - Refactoring summary

#### Configuration
- `.env` - Updated with `GITHUB_USER=stickleprojects`
- `.env.resolved` - Regenerated with resolved credentials

### Technical Insights

#### GitHub API Behavior
The GitHub REST API has an important but non-obvious behavior:
- **Authenticated user endpoint** (`/user/repos`): Returns all accessible repos including private
- **Named user endpoint** (`/users/{username}/repos`): Returns only public repos, regardless of authentication
- This applies **even when the named user IS the authenticated user**
- Parameters differ: `visibility` for authenticated, `type` for named users

#### Best Practices Established
1. Always prefer `.env.resolved` over `.env` for Docker/production
2. Use config objects instead of `os.environ` for better testability
3. Set pagination parameters once on client, not per-request
4. For GitHub user repos, detect if it's the authenticated user and use appropriate endpoint

### Remaining Work
- Consider similar refactoring for database config (`src/database/connection.py`)
- ~~Consider similar refactoring for Azure DevOps config (`src/extractors/azure_devops/`)~~ ✅ **COMPLETED** (Jan 24, 2026)
- Add Celery config class (`src/scheduler/celery_app.py`)

### Dependencies Added
No new dependencies - leveraged existing:
- `PyGithub>=2.1.0` (existing)
- `python-dotenv>=1.0.0` (existing, but now supplemented with custom loader)

---

## Previous Sessions
(Add earlier session notes here as needed)
