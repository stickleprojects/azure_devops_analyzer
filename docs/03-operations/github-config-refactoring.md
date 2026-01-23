# GitHub Configuration Refactoring Summary

## Overview

Refactored GitHub configuration to eliminate direct `os.environ` reads and centralize all configuration through the `GitHubExtractorConfig` class. This provides better testability, maintainability, and consistency.

## Changes Made

### 1. Enhanced `GitHubExtractorConfig` (src/config/github.py)

Added credential fields to the config dataclass:
```python
@dataclass
class GitHubExtractorConfig:
    # ... existing fields ...
    token: Optional[str] = None
    organization: Optional[str] = None
    user: Optional[str] = None
```

These fields are now populated from environment variables during `from_env()`.

### 2. Updated `get_github_client()` (src/extractors/github/client.py)

**Before:**
```python
def get_github_client(env_file: Optional[str | Path] = None) -> Github:
    token = os.environ.get("GITHUB_TOKEN")
    # ...
```

**After:**
```python
def get_github_client(
    config: Optional[GitHubExtractorConfig] = None,
    env_file: Optional[str | Path] = None
) -> Github:
    if config is None:
        config = GitHubExtractorConfig.from_env(env_file=env_file)
    token = config.token
    # ...
```

### 3. Updated Helper Functions (src/extractors/github/client.py)

`get_organization_name()` and `get_user_name()` now accept optional config:

```python
def get_organization_name(config: Optional[GitHubExtractorConfig] = None) -> str | None:
    if config is not None:
        return config.organization
    return os.environ.get("GITHUB_ORG")  # Fallback for backward compatibility
```

### 4. Updated `GitHubExtractor` (src/extractors/github/extractor.py)

**Before:**
```python
def __init__(self, config: Optional[GitHubExtractorConfig] = None):
    self._org_name = get_organization_name()
    self._user_name = get_user_name()
    self.config = config or GitHubExtractorConfig.from_env()
```

**After:**
```python
def __init__(self, config: Optional[GitHubExtractorConfig] = None):
    self.config = config or GitHubExtractorConfig.from_env()
    self._org_name = self.config.organization
    self._user_name = self.config.user
```

## Benefits

### 1. **Centralized Configuration**
- All GitHub-related configuration in one place
- Single source of truth for credentials and settings
- Easier to understand and maintain

### 2. **Better Testability**
- Can pass mock config objects in tests
- No need to manipulate `os.environ` in tests
- More isolated and reliable tests

### 3. **Consistent Behavior**
- All components use the same config instance
- No risk of different parts reading different env values
- Config is loaded once and reused

### 4. **Backward Compatible**
- Existing code still works without changes
- Helper functions still check `os.environ` as fallback
- Gradual migration path available

### 5. **Indirect Variable Resolution**
- Credentials like `GITHUB_TOKEN=$AZURE_VAULT_SECRET` are resolved automatically
- Works seamlessly with `.env.resolved` files
- No manual resolution needed

## Usage Examples

### Basic Usage (Unchanged)
```python
# Automatically loads from .env.resolved or .env
extractor = GitHubExtractor()
```

### With Custom Config
```python
config = GitHubExtractorConfig(
    token="ghp_custom_token",
    user="myuser",
    page_size=50
)
extractor = GitHubExtractor(config=config)
```

### With Custom .env File
```python
config = GitHubExtractorConfig.from_env(env_file="/path/to/test.env")
extractor = GitHubExtractor(config=config)
```

### In Tests
```python
def test_something():
    config = GitHubExtractorConfig(
        token="test_token",
        user="testuser"
    )
    extractor = GitHubExtractor(config=config)
    # No os.environ manipulation needed!
```

## Remaining os.environ Usage

The following files still use `os.environ` directly (non-GitHub related):

1. **src/database/connection.py** - PostgreSQL configuration
   - `DATABASE_URL`, `POSTGRES_HOST`, `POSTGRES_PORT`, etc.
   - Consider creating `DatabaseConfig` class

2. **src/extractors/azure_devops/** - Azure DevOps configuration
   - `AZURE_DEVOPS_ORG_URL`, `AZURE_DEVOPS_PAT`
   - Consider creating `AzureDevOpsConfig` class

3. **src/scheduler/celery_app.py** - Celery broker configuration
   - Could be moved to a `CeleryConfig` class

4. **src/config/github.py** - Internal usage for env file loading
   - Required for the load_env_file() functionality

## Testing

All tests pass (31 passed, 3 skipped):
- ✅ 18 config tests including new credential fields
- ✅ 2 extractor unit tests
- ✅ 11 import/structure tests
- ⏭️ 3 live integration tests (skip when no credentials)

## Migration Path for Other Modules

To refactor database or Azure DevOps configs similarly:

1. Create config dataclass in `src/config/`
2. Add fields for all configuration values
3. Implement `from_env()` class method
4. Update modules to accept config parameter
5. Add tests for new config class
6. Document usage patterns

## Documentation

- Updated: `docs/03-operations/github-config-env-loading.md`
- All configuration options documented
- Examples for all usage patterns
