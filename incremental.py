import logging
from datetime import datetime
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

def detect_changes(last_run: datetime) -> Dict[str, List[Dict[str, Any]]]:
    """
    Detect changes in repositories since the last run.
    """
    logger.info(f"Detecting changes since {last_run}")
    # Placeholder logic
    return {
        "repos_with_new_commits": [],
        "repos_with_pr_changes": []
    }