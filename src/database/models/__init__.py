"""
SQLAlchemy ORM models for the Repository Analysis System.

All models map to the schema defined in database/schema.sql.
"""

from src.database.models.base import Base, TimestampMixin
from src.database.models.branch_metric import BranchMetric
from src.database.models.commit import Commit
from src.database.models.contributor import Contributor, ContributorMetric
from src.database.models.dependency import RepositoryDependency, Vulnerability
from src.database.models.package import Package
from src.database.models.extraction_metric import ExtractionMetric, ExtractionRun
from src.database.models.repository_language import RepositoryLanguage
from src.database.models.organization import Organization, Project
from src.database.models.pull_request import PRComment, PRReview, PullRequest
from src.database.models.quality import CodeIssue, CodeQualityMetric
from src.database.models.repository import Branch, Repository
from src.database.models.service import RepositoryService, Service
from src.database.models.service_metric import ServiceMetric
from src.database.models.summary import ReadmeFile, RepositorySummary
from src.database.models.team import Team
from src.database.models.team_contributor import TeamContributor
from src.database.models.team_metric import TeamMetric

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    # Organization
    "Organization",
    "Project",
    "Team",
    "TeamContributor",
    "TeamMetric",
    # Repository
    "Repository",
    "Branch",
    # Language
    "RepositoryLanguage",
    # Dependency
    "Package",
    "RepositoryDependency",
    "Vulnerability",
    # Extraction Progress
    "ExtractionRun",
    "ExtractionMetric",
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
    # Service
    "Service",
    "RepositoryService",
    "ServiceMetric",
]
