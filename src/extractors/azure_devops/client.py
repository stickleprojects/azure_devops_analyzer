"""
Azure DevOps API client configuration and authentication.
"""

from functools import lru_cache
from typing import Any, Optional

from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication

from src.config.azure_devops import AzureDevOpsExtractorConfig


@lru_cache(maxsize=1)
def get_connection(config: Optional[AzureDevOpsExtractorConfig] = None) -> Connection:
    """
    Get authenticated Azure DevOps connection.

    Args:
        config: Optional AzureDevOpsExtractorConfig. If not provided, loads from environment.

    Uses environment variables (if config not provided):
    - AZURE_DEVOPS_ORG_URL: Organization URL (e.g., https://dev.azure.com/myorg)
    - AZURE_DEVOPS_PAT: Personal Access Token

    Returns:
        Authenticated Connection object.

    Raises:
        ValueError: If required configuration is not set.
    """
    if config is None:
        config = AzureDevOpsExtractorConfig.from_env()
    
    org_url = config.org_url
    pat = config.pat

    if not org_url:
        raise ValueError("AZURE_DEVOPS_ORG_URL not configured")
    if not pat:
        raise ValueError("AZURE_DEVOPS_PAT not configured")

    credentials = BasicAuthentication("", pat)
    return Connection(base_url=org_url, creds=credentials)


def get_git_client(config: Optional[AzureDevOpsExtractorConfig] = None) -> Any:
    """Get the Git client for repository operations."""
    connection = get_connection(config)
    return connection.clients.get_git_client()


def get_core_client(config: Optional[AzureDevOpsExtractorConfig] = None) -> Any:
    """Get the Core client for project operations."""
    connection = get_connection(config)
    return connection.clients.get_core_client()

