"""
Extractors package for fetching repository data from various platforms.

Supported platforms:
- Azure DevOps
- GitHub
"""

from src.extractors.base import (
    Platform,
    RepositoryExtractor,
    OrganizationData,
    ProjectData,
    RepositoryData,
    BranchData,
    LanguageData,
    CommitData,
    PullRequestData,
    PRReviewData,
    PRCommentData,
    ContributorData,
    FileTreeItem,
)
from src.extractors.factory import get_extractor

__all__ = [
    "Platform",
    "RepositoryExtractor",
    "OrganizationData",
    "ProjectData",
    "RepositoryData",
    "BranchData",
    "LanguageData",
    "CommitData",
    "PullRequestData",
    "PRReviewData",
    "PRCommentData",
    "ContributorData",
    "FileTreeItem",
    "get_extractor",
]
