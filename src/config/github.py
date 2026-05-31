"""Configuration helpers for GitHub extraction."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.config.env_loader import find_project_root, get_env_float, get_env_int, load_env_file


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
            project_root = find_project_root()
            resolved_env = project_root / ".env.resolved"
            regular_env = project_root / ".env"
            
            if resolved_env.exists():
                load_env_file(resolved_env)
            elif regular_env.exists():
                load_env_file(regular_env, override = True)
        
        return cls(
            page_size=get_env_int("GITHUB_PAGE_SIZE", cls.page_size),
            max_items_per_list=get_env_int("GITHUB_MAX_ITEMS_PER_LIST", cls.max_items_per_list),
            max_retries=get_env_int("GITHUB_MAX_RETRIES", cls.max_retries),
            backoff_seconds=get_env_float("GITHUB_BACKOFF_SECONDS", cls.backoff_seconds),
            max_backoff_seconds=get_env_float("GITHUB_MAX_BACKOFF_SECONDS", cls.max_backoff_seconds),
            token=os.environ.get("GITHUB_TOKEN"),
            organization=os.environ.get("GITHUB_ORG"),
            user=os.environ.get("GITHUB_USER"),
            private_repo=os.environ.get("GITHUB_PRIVATE_REPO"),
        )
