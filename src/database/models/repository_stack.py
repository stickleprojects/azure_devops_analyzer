"""
Repository technology stack model.

Unified table replacing repository_languages. Stores both platform API language
data (source='platform_api') and TechnologyDetector heuristic results
(source='heuristic') for all 8 technology categories.
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models.base import Base

if TYPE_CHECKING:
    from src.database.models.repository import Branch, Repository


class RepositoryStack(Base):
    """
    Technology stack entry for a repository.

    Upserted on (repo_id, category, name).
    - source='platform_api': language byte-count data from the VCS API.
    - source='heuristic': framework/DB/CI/CD detections from TechnologyDetector.

    first_seen_at is set on insert and never updated.
    last_seen_at is updated on every upsert.
    """

    __tablename__ = "repository_stack"

    id: Mapped[int] = mapped_column(primary_key=True)
    repo_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("repositories.repo_id", ondelete="CASCADE"),
        nullable=False,
    )
    branch_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("branches.branch_id", ondelete="CASCADE")
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="heuristic")

    # language-specific (non-null when category='language', source='platform_api')
    percentage: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    line_count: Mapped[Optional[int]] = mapped_column(Integer)
    byte_count: Mapped[Optional[int]] = mapped_column(BigInteger)

    # heuristic-specific (non-null when source='heuristic')
    confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 3))

    first_seen_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )

    # Relationships
    repository: Mapped["Repository"] = relationship(back_populates="stack")
    branch: Mapped[Optional["Branch"]] = relationship(back_populates="stack")
