"""
Code quality models.
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models.base import Base

if TYPE_CHECKING:
    from src.database.models.repository import Branch, Repository


class CodeQualityMetric(Base):
    """
    Code quality metrics for a repository.

    This is a TimescaleDB hypertable with 1-week chunks, partitioned by timestamp.
    Uses composite primary key (id, timestamp) for hypertable compatibility.
    """

    __tablename__ = "code_quality_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    repo_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("repositories.repo_id", ondelete="CASCADE")
    )
    branch_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("branches.branch_id", ondelete="CASCADE")
    )
    timestamp: Mapped[datetime] = mapped_column(primary_key=True)
    total_issues: Mapped[int] = mapped_column(Integer, default=0)
    critical_issues: Mapped[int] = mapped_column(Integer, default=0)
    high_issues: Mapped[int] = mapped_column(Integer, default=0)
    medium_issues: Mapped[int] = mapped_column(Integer, default=0)
    low_issues: Mapped[int] = mapped_column(Integer, default=0)
    complexity_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    maintainability_index: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    test_coverage: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    code_smells: Mapped[int] = mapped_column(Integer, default=0)
    technical_debt_minutes: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    repository: Mapped["Repository"] = relationship(back_populates="quality_metrics")
    branch: Mapped[Optional["Branch"]] = relationship(back_populates="quality_metrics")


class CodeIssue(Base):
    """Individual code quality issue."""

    __tablename__ = "code_issues"

    id: Mapped[int] = mapped_column(primary_key=True)
    quality_metric_id: Mapped[int] = mapped_column(nullable=False)
    repo_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("repositories.repo_id", ondelete="CASCADE")
    )
    branch_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("branches.branch_id", ondelete="CASCADE")
    )
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    line_number: Mapped[Optional[int]] = mapped_column(Integer)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100))
    rule_id: Mapped[Optional[str]] = mapped_column(String(100))
    message: Mapped[Optional[str]] = mapped_column(Text)
    detected_at: Mapped[Optional[datetime]] = mapped_column()
    resolved_at: Mapped[Optional[datetime]] = mapped_column()

    # Relationships
    repository: Mapped["Repository"] = relationship(back_populates="code_issues")
    branch: Mapped[Optional["Branch"]] = relationship(back_populates="code_issues")
