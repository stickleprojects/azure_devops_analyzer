"""
Branch metrics model (TimescaleDB hypertable).
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models.base import Base

if TYPE_CHECKING:
    from src.database.models.repository import Branch


class BranchMetric(Base):
    """
    Time-series branch metrics.

    This is a TimescaleDB hypertable with 1-week chunks, partitioned by timestamp.
    Uses composite primary key (id, timestamp) for hypertable compatibility.
    """

    __tablename__ = "branch_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int] = mapped_column(
        ForeignKey("branches.branch_id", ondelete="CASCADE")
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    commit_count: Mapped[int] = mapped_column(Integer, default=0)
    unique_contributors: Mapped[int] = mapped_column(Integer, default=0)
    age_days: Mapped[int] = mapped_column(Integer, default=0)
    staleness_days: Mapped[int] = mapped_column(Integer, default=0)
    total_lines: Mapped[int] = mapped_column(Integer, default=0)
    divergence_from_main: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    branch: Mapped["Branch"] = relationship(back_populates="metrics")
