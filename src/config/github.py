"""Configuration helpers for GitHub extraction."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class GitHubExtractorConfig:
    """Configuration for GitHubExtractor pagination and backoff."""

    page_size: int = 100
    max_items_per_list: int = 5000
    max_retries: int = 3
    backoff_seconds: float = 2.0
    max_backoff_seconds: float = 60.0
    # Credentials
    token: Optional[str] = None
    organization: Optional[str] = None
    user: Optional[str] = None
    private_repo: Optional[str] = None

    @property
    def username(self) -> Optional[str]:
        """Alias for 'user' field for convenience."""
        return self.user
    
    @property
    def org(self) -> Optional[str]:
        """Alias for 'organization' field for convenience."""
        return self.organization

    @classmethod
    def from_env(cls, env_file: Optional[str | Path] = None) -> "GitHubExtractorConfig":
        """
        Build config using environment overrides when present.
        
        Args:
            env_file: Optional path to .env file. If not provided, will try:
                     1. .env.resolved in project root
                     2. .env in project root
                     3. Current environment variables
        """
        # Load environment variables from file if specified
        if env_file:
            load_env_file(env_file)
        else:
            # Try .env.resolved first, then .env
            project_root = _find_project_root()
            resolved_env = project_root / ".env.resolved"
            regular_env = project_root / ".env"
            
            if resolved_env.exists():
                load_env_file(resolved_env)
            elif regular_env.exists():
                load_env_file(regular_env)
        
        return cls(
            page_size=_get_env_int("GITHUB_PAGE_SIZE", cls.page_size),
            max_items_per_list=_get_env_int("GITHUB_MAX_ITEMS_PER_LIST", cls.max_items_per_list),
            max_retries=_get_env_int("GITHUB_MAX_RETRIES", cls.max_retries),
            backoff_seconds=_get_env_float("GITHUB_BACKOFF_SECONDS", cls.backoff_seconds),
            max_backoff_seconds=_get_env_float("GITHUB_MAX_BACKOFF_SECONDS", cls.max_backoff_seconds),
            token=os.environ.get("GITHUB_TOKEN"),
            organization=os.environ.get("GITHUB_ORG"),
            user=os.environ.get("GITHUB_USER"),
            private_repo=os.environ.get("GITHUB_PRIVATE_REPO"),
        )


def load_env_file(env_file: str | Path, override: bool = False) -> dict[str, str]:
    """
    Load environment variables from a .env file with support for indirect variable references.
    
    Args:
        env_file: Path to the .env file
        override: If True, override existing environment variables
        
    Returns:
        Dictionary of loaded variables (resolved values)
        
    Examples:
        >>> # .env file contains:
        >>> # GITHUB_TOKEN=$MY_SECRET_TOKEN
        >>> # MY_SECRET_TOKEN=ghp_abc123
        >>> load_env_file(".env")
        {'GITHUB_TOKEN': 'ghp_abc123', 'MY_SECRET_TOKEN': 'ghp_abc123'}
    """
    env_path = Path(env_file)
    if not env_path.exists():
        return {}
    
    loaded_vars = {}
    raw_vars = {}
    
    # First pass: load all raw values
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Parse KEY=VALUE
            if '=' in line:
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip()
                
                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                
                raw_vars[key] = value
    
    # Second pass: resolve indirect references
    max_iterations = 10  # Prevent infinite loops
    iteration = 0
    
    while raw_vars and iteration < max_iterations:
        iteration += 1
        resolved_any = False
        
        for key, value in list(raw_vars.items()):
            # Check if value is an indirect reference ($VARNAME)
            if value.startswith('$'):
                ref_var = value[1:]
                
                # Try to resolve from already loaded vars
                if ref_var in loaded_vars:
                    loaded_vars[key] = loaded_vars[ref_var]
                    del raw_vars[key]
                    resolved_any = True
                # Try to resolve from environment
                elif ref_var in os.environ:
                    loaded_vars[key] = os.environ[ref_var]
                    del raw_vars[key]
                    resolved_any = True
                # Try to resolve from other raw vars
                elif ref_var in raw_vars and not raw_vars[ref_var].startswith('$'):
                    loaded_vars[key] = raw_vars[ref_var]
                    del raw_vars[key]
                    resolved_any = True
            else:
                # Direct value, no resolution needed
                loaded_vars[key] = value
                del raw_vars[key]
                resolved_any = True
        
        if not resolved_any:
            # Cannot resolve remaining variables, keep them as-is
            for key, value in raw_vars.items():
                loaded_vars[key] = value
            break
    
    # Update environment if requested
    if override or not any(key in os.environ for key in loaded_vars):
        for key, value in loaded_vars.items():
            if override or key not in os.environ:
                os.environ[key] = value
    
    return loaded_vars


def _find_project_root() -> Path:
    """Find the project root directory (contains .env file or pyproject.toml)."""
    current = Path.cwd()
    
    # Try to find project root by looking for marker files
    for parent in [current, *current.parents]:
        if (parent / ".env").exists() or (parent / "pyproject.toml").exists():
            return parent
    
    # If not found, return current directory
    return current


def _get_env_int(var_name: str, default: int) -> int:
    try:
        return int(os.environ.get(var_name, default))
    except Exception:
        return default


def _get_env_float(var_name: str, default: float) -> float:
    try:
        return float(os.environ.get(var_name, default))
    except Exception:
        return default
