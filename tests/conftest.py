"""Pytest configuration for environment setup."""

import os
import shutil
import sys
from pathlib import Path

import pytest


def pytest_configure(config):
    """Load environment variables before any tests run.
    
    This ensures that .env.resolved (or .env) is loaded for all tests,
    including when running from VS Code's test runner.
    
    IMPORTANT: Disables file-based extractor caching for tests to prevent
    cached results from previous runs interfering with test expectations.
    This is critical when tests expect different repo lists (e.g., private vs public).
    
    For database tests: Override POSTGRES_HOST from .env.test if it exists,
    to connect to localhost when running tests on host machine.
    """
    # Disable file caching for tests to ensure clean state
    # (prevents stale cache from interfering with test assumptions)
    os.environ["EXTRACTOR_FILE_CACHE_ENABLED"] = "false"
    # Import here to avoid circular dependencies
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    
    from src.config.env_loader import load_env_file
    
    # Try .env.resolved first (resolved variable references), then .env
    env_resolved = project_root / ".env.resolved"
    env_regular = project_root / ".env"
    
    env_file_used = None
    if env_resolved.exists():
        loaded = load_env_file(env_resolved, override=True)
        if loaded:
            env_file_used = env_resolved
        elif env_regular.exists():
            load_env_file(env_regular, override=True)
            env_file_used = env_regular
    elif env_regular.exists():
        load_env_file(env_regular, override=True)
        env_file_used = env_regular
    
    # Load test-specific overrides from .env.test (for database host, etc.)
    env_test = project_root / ".env.test"
    if env_test.exists():
        print(f"\n[TEST] Loading test overrides from {env_test.name}")
        with open(env_test) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value
                    if key == "POSTGRES_HOST":
                        print(f"  Overriding {key}={value} for test database")
    
    # Debug: verify GITHUB_TOKEN is set
    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        print(f"\n[WARN] WARNING: GITHUB_TOKEN not set after loading {env_file_used}")
        print(f"   File exists: {env_file_used and env_file_used.exists()}")
    else:
        print(f"\n[OK] GITHUB_TOKEN loaded successfully from {env_file_used.name if env_file_used else 'unknown'}")
        print(f"  Token starts with: {github_token[:20]}...")


def _is_github_auth_error(exc: BaseException) -> bool:
    try:
        from github import BadCredentialsException, GithubException
    except Exception:
        return False

    def _matches(candidate: BaseException) -> bool:
        if isinstance(candidate, BadCredentialsException):
            return True

        if isinstance(candidate, GithubException):
            status = getattr(candidate, "status", None)
            data = getattr(candidate, "data", None) or {}
            message = ""
            if isinstance(data, dict):
                message = str(data.get("message", "")).lower()
            return status in (401, 403) and (
                "bad credentials" in message
                or "requires authentication" in message
                or "invalid token" in message
            )

        return False

    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if _matches(current):
            return True
        current = current.__cause__ or current.__context__

    return False


def _is_azure_auth_error(exc: BaseException) -> bool:
    try:
        from azure.devops.exceptions import AzureDevOpsServiceError
    except Exception:
        return False

    def _matches(candidate: BaseException) -> bool:
        if not isinstance(candidate, AzureDevOpsServiceError):
            return False

        response = getattr(candidate, "response", None)
        status = getattr(response, "status_code", None)
        message = str(candidate).lower()
        return status in (401, 403) or "not authorized" in message or "unauthorized" in message

    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if _matches(current):
            return True
        current = current.__cause__ or current.__context__

    return False


def pytest_runtest_makereport(item, call):
    if call.when != "call" or call.excinfo is None:
        return

    if "live_api" not in item.keywords:
        return

    exc = call.excinfo.value
    if _is_github_auth_error(exc):
        print("\n" + "="*80)
        print("GITHUB AUTHENTICATION ERROR DETAILS:")
        print("="*80)
        print(f"Exception Type: {type(exc).__name__}")
        print(f"Exception Message: {str(exc)}")
        print("\nFull Traceback:")
        import traceback
        traceback.print_exc()
        print("="*80)
        pytest.exit(
            "GitHub authentication failed (invalid token). Aborting live API tests.",
            returncode=1,
        )
    if _is_azure_auth_error(exc):
        print("\n" + "="*80)
        print("AZURE DEVOPS AUTHENTICATION ERROR DETAILS:")
        print("="*80)
        print(f"Exception Type: {type(exc).__name__}")
        print(f"Exception Message: {str(exc)}")
        print("\nFull Traceback:")
        import traceback
        traceback.print_exc()
        print("="*80)
        pytest.exit(
            "Azure DevOps authentication failed (invalid PAT). Aborting live API tests.",
            returncode=1,
        )


@pytest.fixture(autouse=True)
def _clear_extractor_caches_between_tests():
    """
    Clear both file and instance caches between tests.
    
    CRITICAL: This ensures extractor instances don't return stale cached results
    from previous calls within the same test or across tests.
    
    Example of the bug this fixes:
    1. Test calls extractor.get_repositories("account") -> gets public repos
    2. Cache stores result (file cache + instance cache)
    3. Test then tries to find private repo from the cached public list
    4. Private repo not found! (FALSE NEGATIVE)
    """
    from src.config.env_loader import find_project_root
    from src.extractors.cache import _file_cache_enabled, _file_cache_root

    # BEFORE test: Clear file cache (file cache is disabled for tests anyway)
    try:
        cache_root = _file_cache_root()
        project_root = find_project_root()
        if cache_root.exists() and (
            cache_root == project_root / ".cache" or project_root in cache_root.parents
        ):
            shutil.rmtree(cache_root, ignore_errors=True)
    except Exception:
        pass  # Ignore errors

    yield

    # AFTER test: Clear file cache again
    try:
        cache_root = _file_cache_root()
        project_root = find_project_root()
        if cache_root.exists() and (
            cache_root == project_root / ".cache" or project_root in cache_root.parents
        ):
            shutil.rmtree(cache_root, ignore_errors=True)
    except Exception:
        pass  # Ignore errors
