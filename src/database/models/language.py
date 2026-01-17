"""
Repository language model (TimescaleDB hypertable).
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models.base import Base

if TYPE_CHECKING:
    from src.database.models.repository import Branch, Repository


class RepositoryLanguage(Base):
    """
    Programming language statistics for a repository.

    This is a TimescaleDB hypertable with 1-month chunks, partitioned by analyzed_at.
    """

    __tablename__ = "repository_languages"

    id: Mapped[int] = mapped_column(primary_key=True)
    repo_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("repositories.repo_id", ondelete="CASCADE")
    )
    branch_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("branches.branch_id", ondelete="CASCADE")
    )
    language: Mapped[str] = mapped_column(String(100), nullable=False)
    percentage: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    line_count: Mapped[Optional[int]] = mapped_column(Integer)
    byte_count: Mapped[Optional[int]] = mapped_column(BigInteger)
    analyzed_at: Mapped[datetime] = mapped_column(nullable=False)

    # Relationships
    repository: Mapped["Repository"] = relationship(back_populates="languages")
    branch: Mapped[Optional["Branch"]] = relationship(back_populates="languages")
