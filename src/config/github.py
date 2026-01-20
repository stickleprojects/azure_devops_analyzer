"""Configuration helpers for GitHub extraction."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class GitHubExtractorConfig:
    """Configuration for GitHubExtractor pagination and backoff."""

    page_size: int = 100
    max_items_per_list: int = 5000
    max_retries: int = 3
    backoff_seconds: float = 2.0
    max_backoff_seconds: float = 60.0

    @classmethod
    def from_env(cls) -> "GitHubExtractorConfig":
        """Build config using environment overrides when present."""
        return cls(
            page_size=_get_env_int("GITHUB_PAGE_SIZE", cls.page_size),
            max_items_per_list=_get_env_int("GITHUB_MAX_ITEMS_PER_LIST", cls.max_items_per_list),
            max_retries=_get_env_int("GITHUB_MAX_RETRIES", cls.max_retries),
            backoff_seconds=_get_env_float("GITHUB_BACKOFF_SECONDS", cls.backoff_seconds),
            max_backoff_seconds=_get_env_float("GITHUB_MAX_BACKOFF_SECONDS", cls.max_backoff_seconds),
        )


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
