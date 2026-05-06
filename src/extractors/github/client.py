"""
GitHub API client configuration and authentication.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from github import Github, Auth

from src.config.github import GitHubExtractorConfig


def get_github_client(
    config: Optional[GitHubExtractorConfig] = None,
    env_file: Optional[str | Path] = None
) -> Github:
    """
    Get authenticated GitHub client.

    Args:
        config: Optional GitHubExtractorConfig instance. If not provided,
                will be loaded from environment.
        env_file: Optional path to .env file to load. If not provided,
                 will use .env.resolved or .env from project root.

    Returns:
        Authenticated Github object.

    Raises:
        ValueError: If required environment variables are not set.
    """
    # Load config if not provided
    if config is None:
        config = GitHubExtractorConfig.from_env(env_file=env_file)
    
    token = config.token

    if not token:
        raise ValueError("GITHUB_TOKEN environment variable not set or not provided in config")

    auth = Auth.Token(token)
    return Github(auth=auth)


def get_organization_name(config: Optional[GitHubExtractorConfig] = None) -> str | None:
    """
    Get the configured GitHub organization name.
    
    Args:
        config: Optional GitHubExtractorConfig instance. If not provided,
                will read from environment.
    """
    if config is not None:
        return config.organization
    return os.environ.get("GITHUB_ORG")


def get_user_name(config: Optional[GitHubExtractorConfig] = None) -> str | None:
    """
    Get the configured GitHub username (for personal repos).
    
    Args:
        config: Optional GitHubExtractorConfig instance. If not provided,
                will read from environment.
    """
    if config is not None:
        return config.user
    return os.environ.get("GITHUB_USER")
