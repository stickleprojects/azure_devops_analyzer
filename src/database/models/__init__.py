"""
SQLAlchemy ORM models for the Repository Analysis System.

All models map to the schema defined in database/schema.sql.
"""

from src.database.models.base import Base, TimestampMixin
from src.database.models.branch_metric import BranchMetric
from src.database.models.commit import Commit
from src.database.models.contributor import Contributor, ContributorMetric
from src.database.models.dependency import Dependency, Vulnerability
from src.database.models.language import RepositoryLanguage
from src.database.models.organization import Organization, Project
from src.database.models.pull_request import PRComment, PRReview, PullRequest
from src.database.models.quality import CodeIssue, CodeQualityMetric
from src.database.models.repository import Branch, Repository
from src.database.models.summary import ReadmeFile, RepositorySummary

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    # Organization
    "Organization",
    "Project",
    # Repository
    "Repository",
    "Branch",
    # Language
    "RepositoryLanguage",
    # Dependency
    "Dependency",
    "Vulnerability",
    # Quality
    "CodeQualityMetric",
    "CodeIssue",
    # Summary
    "RepositorySummary",
    "ReadmeFile",
    # Contributor
    "Contributor",
    "ContributorMetric",
    # Commit
    "Commit",
    # Pull Request
    "PullRequest",
    "PRReview",
    "PRComment",
    # Branch Metric
    "BranchMetric",
]
