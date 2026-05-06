"""Configuration helpers for Azure DevOps extraction."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.config.github import load_env_file, _find_project_root, _get_env_int, _get_env_float


@dataclass(frozen=True)
class AzureDevOpsExtractorConfig:
    """Configuration for AzureDevOpsExtractor pagination and backoff."""

    page_size: int = 100
    max_items_per_list: int = 5000
    max_retries: int = 3
    backoff_seconds: float = 2.0
    max_backoff_seconds: float = 60.0
    # Feature flags
    fetch_pr_file_metrics: bool = True  # Extra API calls per PR for file count
    # Credentials
    pat: Optional[str] = None
    org_url: Optional[str] = None
    organization: Optional[str] = None
    project: Optional[str] = None

    @classmethod
    def from_env(cls, env_file: Optional[str | Path] = None) -> "AzureDevOpsExtractorConfig":
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
            page_size=_get_env_int("AZURE_PAGE_SIZE", cls.page_size),
            max_items_per_list=_get_env_int("AZURE_MAX_ITEMS_PER_LIST", cls.max_items_per_list),
            max_retries=_get_env_int("AZURE_MAX_RETRIES", cls.max_retries),
            backoff_seconds=_get_env_float("AZURE_BACKOFF_SECONDS", cls.backoff_seconds),
            max_backoff_seconds=_get_env_float("AZURE_MAX_BACKOFF_SECONDS", cls.max_backoff_seconds),
            fetch_pr_file_metrics=os.environ.get(
                "AZURE_FETCH_PR_FILE_METRICS", "true"
            ).lower() == "true",
            pat=os.environ.get("AZURE_DEVOPS_PAT"),
            org_url=os.environ.get("AZURE_DEVOPS_ORG_URL"),
            organization=os.environ.get("AZURE_DEVOPS_ORG"),
            project=os.environ.get("AZURE_DEVOPS_PROJECT"),
        )
