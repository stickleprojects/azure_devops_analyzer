# GitHub Configuration with Environment Variable Resolution

## Overview

The GitHub configuration module now supports:
- Loading from `.env` files in the project root
- Specifying custom `.env` file paths
- Indirect variable resolution (e.g., `GITHUB_TOKEN=$AZURE_KEYVAULT_SECRET`)
- Automatic preference for `.env.resolved` over `.env`

## Features

### 1. Automatic .env Loading

`GitHubExtractorConfig.from_env()` automatically searches for and loads environment files:

1. First checks for `.env.resolved` (contains resolved secrets)
2. Falls back to `.env` if resolved file doesn't exist
3. Uses existing environment variables if no files found

```python
from src.config.github import GitHubExtractorConfig

# Automatically loads from .env.resolved or .env
config = GitHubExtractorConfig.from_env()
```

### 2. Custom .env File

You can specify a custom environment file:

```python
config = GitHubExtractorConfig.from_env(env_file="/path/to/custom.env")
```

### 3. Indirect Variable Resolution

The `load_env_file()` function resolves indirect variable references:

```bash
# .env file
AZURE_KEYVAULT_SECRET=ghp_actualtoken123
GITHUB_TOKEN=$AZURE_KEYVAULT_SECRET
```

When loaded, `GITHUB_TOKEN` will be resolved to `ghp_actualtoken123`.

#### Resolution Order:
1. Already loaded variables in the same file
2. Existing environment variables
3. Other variables in the file
4. If unresolvable, keeps original value (e.g., `$MISSING_VAR`)

#### Chained References:
```bash
LEVEL1=actual_value
LEVEL2=$LEVEL1
LEVEL3=$LEVEL2
```
All three will resolve to `actual_value`.

### 4. Override Control

```python
from src.config.github import load_env_file

# Don't override existing environment variables (default)
load_env_file(".env", override=False)

# Override existing environment variables
load_env_file(".env", override=True)
```

## Usage in Tests

Tests now automatically load resolved credentials:

```python
from src.config.github import load_env_file
from pathlib import Path

project_root = Path(__file__).parent.parent
env_resolved = project_root / ".env.resolved"
env_regular = project_root / ".env"

if env_resolved.exists():
    load_env_file(env_resolved, override=True)
elif env_regular.exists():
    load_env_file(env_regular, override=True)
```

Live integration tests will skip if credentials are not available:

```python
@pytest.fixture(autouse=True)
def setup(self):
    self.github_token = os.environ.get("GITHUB_TOKEN")
    self.github_user = os.environ.get("GITHUB_USER")
    
    if not self.github_token or not self.github_user:
        pytest.skip("GITHUB_TOKEN and GITHUB_USER must be set in .env for live tests")
```

## Configuration Options

All configuration options can be overridden via environment variables:

| Variable                     | Default | Description                     |
| ---------------------------- | ------- | ------------------------------- |
| `GITHUB_PAGE_SIZE`           | 100     | Number of items per API page    |
| `GITHUB_MAX_ITEMS_PER_LIST`  | 5000    | Maximum items to fetch per list |
| `GITHUB_MAX_RETRIES`         | 3       | Number of retry attempts        |
| `GITHUB_BACKOFF_SECONDS`     | 2.0     | Initial backoff delay           |
| `GITHUB_MAX_BACKOFF_SECONDS` | 60.0    | Maximum backoff delay           |

## Project Workflow

### For Development

1. Copy `.env.example` to `.env`
2. Set actual values or indirect references
3. Run `./scripts/resolve_env.sh` to create `.env.resolved`
4. Code automatically uses `.env.resolved` when available

### For Docker Services

```bash
# Ensure resolved environment is up to date
./scripts/resolve_env.sh

# Start services with resolved environment
docker compose --env-file .env.resolved up -d
```

## Testing

Comprehensive tests are available in `tests/test_github_config.py`:

```bash
pytest tests/test_github_config.py -v
```

Tests cover:
- Simple variable loading
- Quoted values
- Comment and empty line handling
- Indirect variable resolution
- Chained references
- Override behavior
- Invalid value handling
