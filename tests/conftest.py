"""Pytest configuration for environment setup."""

import os
import sys
from pathlib import Path


def pytest_configure(config):
    """Load environment variables before any tests run.
    
    This ensures that .env.resolved (or .env) is loaded for all tests,
    including when running from VS Code's test runner.
    """
    # Import here to avoid circular dependencies
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    
    from src.config.github import load_env_file
    
    # Try .env.resolved first (resolved variable references), then .env
    env_resolved = project_root / ".env.resolved"
    env_regular = project_root / ".env"
    
    env_file_used = None
    if env_resolved.exists():
        load_env_file(env_resolved, override=True)
        env_file_used = env_resolved
    elif env_regular.exists():
        load_env_file(env_regular, override=True)
        env_file_used = env_regular
    
    # Debug: verify GITHUB_TOKEN is set
    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        print(f"\n⚠️ WARNING: GITHUB_TOKEN not set after loading {env_file_used}")
        print(f"   File exists: {env_file_used and env_file_used.exists()}")
    else:
        print(f"\n✓ GITHUB_TOKEN loaded successfully from {env_file_used.name if env_file_used else 'unknown'}")
        print(f"  Token starts with: {github_token[:20]}...")
