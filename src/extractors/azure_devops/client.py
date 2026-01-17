"""
Azure DevOps API client configuration and authentication.
"""

import os
from functools import lru_cache

from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication


@lru_cache(maxsize=1)
def get_connection() -> Connection:
    """
    Get authenticated Azure DevOps connection.

    Uses environment variables:
    - AZURE_DEVOPS_ORG_URL: Organization URL (e.g., https://dev.azure.com/myorg)
    - AZURE_DEVOPS_PAT: Personal Access Token

    Returns:
        Authenticated Connection object.

    Raises:
        ValueError: If required environment variables are not set.
    """
    org_url = os.environ.get("AZURE_DEVOPS_ORG_URL")
    pat = os.environ.get("AZURE_DEVOPS_PAT")

    if not org_url:
        raise ValueError("AZURE_DEVOPS_ORG_URL environment variable not set")
    if not pat:
        raise ValueError("AZURE_DEVOPS_PAT environment variable not set")

    credentials = BasicAuthentication("", pat)
    return Connection(base_url=org_url, creds=credentials)


def get_git_client():
    """Get the Git client for repository operations."""
    connection = get_connection()
    return connection.clients.get_git_client()


def get_core_client():
    """Get the Core client for project operations."""
    connection = get_connection()
    return connection.clients.get_core_client()
