"""
Service metrics model for aggregated service-level analytics.
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models.base import Base

if TYPE_CHECKING:
    from src.database.models.service import Service


class ServiceMetric(Base):
    """
    Time-series service metrics aggregated across all service repositories.
    
    This is a TimescaleDB hypertable with 1-month chunks, partitioned by period_start.
    Aggregates commits, PRs, quality, security, and dependency metrics across all
    repositories belonging to a service.
    """

    __tablename__ = "service_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.service_id", ondelete="CASCADE"), nullable=False
    )
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, nullable=False
    )
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Repository counts
    total_repositories: Mapped[int] = mapped_column(Integer, default=0)
    active_repositories: Mapped[int] = mapped_column(Integer, default=0)
    
    # Commit metrics (aggregated from contributor_metrics)
    total_commits: Mapped[int] = mapped_column(Integer, default=0)
    total_lines_added: Mapped[int] = mapped_column(Integer, default=0)
    total_lines_removed: Mapped[int] = mapped_column(Integer, default=0)
    total_files_modified: Mapped[int] = mapped_column(Integer, default=0)
    
    # Pull request metrics
    total_prs_created: Mapped[int] = mapped_column(Integer, default=0)
    total_prs_merged: Mapped[int] = mapped_column(Integer, default=0)
    avg_pr_review_time_hours: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    
    # Quality metrics (averaged across repos)
    avg_test_coverage: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    avg_maintainability_index: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    total_quality_issues: Mapped[int] = mapped_column(Integer, default=0)
    
    # Security metrics
    total_vulnerabilities: Mapped[int] = mapped_column(Integer, default=0)
    critical_vulnerabilities: Mapped[int] = mapped_column(Integer, default=0)
    high_vulnerabilities: Mapped[int] = mapped_column(Integer, default=0)
    
    # Dependency health
    total_dependencies: Mapped[int] = mapped_column(Integer, default=0)
    eol_dependencies: Mapped[int] = mapped_column(Integer, default=0)
    
    # Activity metrics
    unique_contributors: Mapped[int] = mapped_column(Integer, default=0)
    
    # Audit
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    
    # Relationships
    service: Mapped["Service"] = relationship("Service", back_populates="metrics")
