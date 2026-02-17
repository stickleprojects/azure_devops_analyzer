"""
Contributor and contributor metrics models.
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models.base import Base

if TYPE_CHECKING:
    from src.database.models.commit import Commit
    from src.database.models.pull_request import PRComment, PRReview, PullRequest
    from src.database.models.repository import Repository
    from src.database.models.team_contributor import TeamContributor


class Contributor(Base):
    """Contributor (developer) who has made commits or PRs."""

    __tablename__ = "contributors"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    first_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    metrics: Mapped[list["ContributorMetric"]] = relationship(
        back_populates="contributor", cascade="all, delete-orphan"
    )
    authored_commits: Mapped[list["Commit"]] = relationship(
        back_populates="author",
        foreign_keys="Commit.author_id",
        cascade="all, delete-orphan",
    )
    committed_commits: Mapped[list["Commit"]] = relationship(
        back_populates="committer",
        foreign_keys="Commit.committer_id",
        cascade="all, delete-orphan",
    )
    authored_prs: Mapped[list["PullRequest"]] = relationship(
        back_populates="author", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["PRReview"]] = relationship(
        back_populates="reviewer", cascade="all, delete-orphan"
    )
    comments: Mapped[list["PRComment"]] = relationship(
        back_populates="author", cascade="all, delete-orphan"
    )
    teams: Mapped[list["TeamContributor"]] = relationship(
        back_populates="contributor", cascade="all, delete-orphan"
    )


class ContributorMetric(Base):
    """
    Time-series contributor metrics for a repository.

    This is a TimescaleDB hypertable with 1-month chunks, partitioned by period_start.
    """

    __tablename__ = "contributor_metrics"

    repo_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("repositories.repo_id", ondelete="CASCADE"),
        primary_key=True,
    )
    contributor_id: Mapped[int] = mapped_column(
        ForeignKey("contributors.id", ondelete="CASCADE"),
        primary_key=True,
    )
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, primary_key=True,
    )
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    commit_count: Mapped[int] = mapped_column(Integer, default=0)
    lines_added: Mapped[int] = mapped_column(Integer, default=0)
    lines_removed: Mapped[int] = mapped_column(Integer, default=0)
    files_modified: Mapped[int] = mapped_column(Integer, default=0)
    pr_created: Mapped[int] = mapped_column(Integer, default=0)
    pr_reviews: Mapped[int] = mapped_column(Integer, default=0)
    pr_approvals: Mapped[int] = mapped_column(Integer, default=0)
    active_days: Mapped[int] = mapped_column(Integer, default=0)
    avg_commit_message_quality: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2)
    )

    # Relationships
    repository: Mapped["Repository"] = relationship(
        back_populates="contributor_metrics"
    )
    contributor: Mapped["Contributor"] = relationship(back_populates="metrics")
