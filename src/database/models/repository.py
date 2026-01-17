"""
Repository and Branch models.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models.base import Base

if TYPE_CHECKING:
    from src.database.models.branch_metric import BranchMetric
    from src.database.models.commit import Commit
    from src.database.models.contributor import ContributorMetric
    from src.database.models.dependency import Dependency
    from src.database.models.language import RepositoryLanguage
    from src.database.models.organization import Project
    from src.database.models.pull_request import PullRequest
    from src.database.models.quality import CodeIssue, CodeQualityMetric
    from src.database.models.summary import ReadmeFile, RepositorySummary


class Repository(Base):
    """Repository from a source control platform."""

    __tablename__ = "repositories"

    repo_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.project_id")
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    default_branch: Mapped[Optional[str]] = mapped_column(String(255))
    platform_repo_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    created_at: Mapped[Optional[datetime]] = mapped_column()
    last_analyzed_at: Mapped[Optional[datetime]] = mapped_column()
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    project: Mapped[Optional["Project"]] = relationship(back_populates="repositories")
    branches: Mapped[list["Branch"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )
    languages: Mapped[list["RepositoryLanguage"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )
    dependencies: Mapped[list["Dependency"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )
    quality_metrics: Mapped[list["CodeQualityMetric"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )
    code_issues: Mapped[list["CodeIssue"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )
    summaries: Mapped[list["RepositorySummary"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )
    readme_files: Mapped[list["ReadmeFile"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )
    contributor_metrics: Mapped[list["ContributorMetric"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )
    commits: Mapped[list["Commit"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )
    pull_requests: Mapped[list["PullRequest"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )


class Branch(Base):
    """Branch within a repository."""

    __tablename__ = "branches"
    __table_args__ = (
        UniqueConstraint("repo_id", "branch_name", name="uq_branch_repo_name"),
    )

    branch_id: Mapped[int] = mapped_column(primary_key=True)
    repo_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("repositories.repo_id", ondelete="CASCADE")
    )
    branch_name: Mapped[str] = mapped_column(String(255), nullable=False)
    latest_commit_sha: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[Optional[datetime]] = mapped_column()
    last_analyzed_at: Mapped[Optional[datetime]] = mapped_column()
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    repository: Mapped["Repository"] = relationship(back_populates="branches")
    languages: Mapped[list["RepositoryLanguage"]] = relationship(
        back_populates="branch", cascade="all, delete-orphan"
    )
    dependencies: Mapped[list["Dependency"]] = relationship(
        back_populates="branch", cascade="all, delete-orphan"
    )
    quality_metrics: Mapped[list["CodeQualityMetric"]] = relationship(
        back_populates="branch", cascade="all, delete-orphan"
    )
    code_issues: Mapped[list["CodeIssue"]] = relationship(
        back_populates="branch", cascade="all, delete-orphan"
    )
    summaries: Mapped[list["RepositorySummary"]] = relationship(
        back_populates="branch", cascade="all, delete-orphan"
    )
    readme_files: Mapped[list["ReadmeFile"]] = relationship(
        back_populates="branch", cascade="all, delete-orphan"
    )
    metrics: Mapped[list["BranchMetric"]] = relationship(
        back_populates="branch", cascade="all, delete-orphan"
    )
