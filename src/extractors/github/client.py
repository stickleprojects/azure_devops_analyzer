"""
GitHub API client configuration and authentication.
"""

import os
from functools import lru_cache

from github import Github, Auth


@lru_cache(maxsize=1)
def get_github_client() -> Github:
    """
    Get authenticated GitHub client.

    Uses environment variables:
    - GITHUB_TOKEN: Personal Access Token or GitHub App token

    Returns:
        Authenticated Github object.

    Raises:
        ValueError: If required environment variables are not set.
    """
    token = os.environ.get("GITHUB_TOKEN")

    if not token:
        raise ValueError("GITHUB_TOKEN environment variable not set")

    auth = Auth.Token(token)
    return Github(auth=auth)


def get_organization_name() -> str | None:
    """Get the configured GitHub organization name."""
    return os.environ.get("GITHUB_ORG")


def get_user_name() -> str | None:
    """Get the configured GitHub username (for personal repos)."""
    return os.environ.get("GITHUB_USER")
