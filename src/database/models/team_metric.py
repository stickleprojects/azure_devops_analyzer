"""
Team metrics model for aggregated team-level analytics.
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models.base import Base

if TYPE_CHECKING:
    from src.database.models.team import Team


class TeamMetric(Base):
    """
    Time-series team metrics aggregated across all team members.
    
    This is a TimescaleDB hypertable with 1-month chunks, partitioned by period_start.
    Aggregates commits, PRs, reviews, and contributor activity across team members.
    """

    __tablename__ = "team_metrics"

    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.team_id", ondelete="CASCADE"), nullable=False, primary_key=True
    )
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Aggregated metrics across all team members
    total_commits: Mapped[int] = mapped_column(Integer, default=0)
    total_lines_added: Mapped[int] = mapped_column(Integer, default=0)
    total_lines_removed: Mapped[int] = mapped_column(Integer, default=0)
    total_files_modified: Mapped[int] = mapped_column(Integer, default=0)
    
    # PR metrics
    total_prs_created: Mapped[int] = mapped_column(Integer, default=0)
    total_pr_reviews: Mapped[int] = mapped_column(Integer, default=0)
    total_pr_approvals: Mapped[int] = mapped_column(Integer, default=0)
    avg_pr_size_lines: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    
    # Team composition
    active_contributors: Mapped[int] = mapped_column(Integer, default=0)
    
    # Quality metrics
    avg_commit_message_quality: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    
    # Relationships
    team: Mapped["Team"] = relationship(back_populates="metrics")
