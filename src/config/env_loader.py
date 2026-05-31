"""Shared environment loading helpers for extractor configuration."""

from __future__ import annotations

import os
from pathlib import Path


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

    if not os.access(env_path, os.R_OK):
        return {}

    loaded_vars = {}
    raw_vars = {}

    # First pass: load all raw values
    try:
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
    except OSError:
        return {}

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


def find_project_root() -> Path:
    """Find the project root directory (contains .env file or pyproject.toml)."""
    current = Path.cwd()

    # Try to find project root by looking for marker files
    for parent in [current, *current.parents]:
        if (parent / ".env").exists() or (parent / "pyproject.toml").exists():
            return parent

    # If not found, return current directory
    return current


def get_env_int(var_name: str, default: int) -> int:
    try:
        return int(os.environ.get(var_name, default))
    except Exception:
        return default


def get_env_float(var_name: str, default: float) -> float:
    try:
        return float(os.environ.get(var_name, default))
    except Exception:
        return default
