import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def prepare_branch_scan(repo_id: str, branch_name: str) -> Dict[str, Any]:
    """
    Prepare context for a branch scan.
    """
    logger.info(f"Preparing scan for branch {branch_name} in repo {repo_id}")
    return {"repo_id": repo_id, "branch": branch_name}