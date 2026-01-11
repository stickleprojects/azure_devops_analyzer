import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def fetch_repositories() -> List[Dict[str, Any]]:
    """
    Fetch list of all repositories to scan.
    """
    logger.info("Fetching repositories for full scan")
    # Placeholder for actual API call
    # In real implementation: client.get_repositories()
    return [
        {"id": "repo-1", "name": "demo-repo-1"},
        {"id": "repo-2", "name": "demo-repo-2"}
    ]