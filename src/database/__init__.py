"""
Database layer for the Repository Analysis System.

Provides SQLAlchemy ORM models and database connection management.
"""

from src.database.connection import (
    get_engine,
    get_session,
    SessionLocal,
)
from src.database.models import (
    Base,
    Organization,
    Project,
    Repository,
    Branch,
    RepositoryStack,
    Technology,
    Package,
    RepositoryDependency,
    Vulnerability,
    CodeQualityMetric,
    CodeIssue,
    RepositorySummary,
    ReadmeFile,
    Contributor,
    ContributorMetric,
    Commit,
    PullRequest,
    PRReview,
    PRComment,
    BranchMetric,
)

__all__ = [
    # Connection
    "get_engine",
    "get_session",
    "SessionLocal",
    # Base
    "Base",
    # Models
    "Organization",
    "Project",
    "Repository",
    "Branch",
    "RepositoryStack",
    "Technology",
    "Package",
    "RepositoryDependency",
    "Vulnerability",
    "CodeQualityMetric",
    "CodeIssue",
    "RepositorySummary",
    "ReadmeFile",
    "Contributor",
    "ContributorMetric",
    "Commit",
    "PullRequest",
    "PRReview",
    "PRComment",
    "BranchMetric",
]
