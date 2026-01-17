"""
Repository summary and README models.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models.base import Base

if TYPE_CHECKING:
    from src.database.models.repository import Branch, Repository


class RepositorySummary(Base):
    """AI-generated repository summary."""

    __tablename__ = "repository_summaries"

    id: Mapped[int] = mapped_column(primary_key=True)
    repo_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("repositories.repo_id", ondelete="CASCADE")
    )
    branch_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("branches.branch_id", ondelete="CASCADE")
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    purpose: Mapped[Optional[str]] = mapped_column(Text)
    key_technologies: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text))
    target_audience: Mapped[Optional[str]] = mapped_column(Text)
    generated_at: Mapped[datetime] = mapped_column(nullable=False)
    generated_by: Mapped[Optional[str]] = mapped_column(String(100))

    # Relationships
    repository: Mapped["Repository"] = relationship(back_populates="summaries")
    branch: Mapped[Optional["Branch"]] = relationship(back_populates="summaries")


class ReadmeFile(Base):
    """README file content and analysis."""

    __tablename__ = "readme_files"
    __table_args__ = (
        UniqueConstraint(
            "repo_id", "branch_id", "file_path", name="uq_readme_repo_branch_path"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    repo_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("repositories.repo_id", ondelete="CASCADE")
    )
    branch_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("branches.branch_id", ondelete="CASCADE")
    )
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    word_count: Mapped[Optional[int]] = mapped_column(Integer)
    analyzed_at: Mapped[Optional[datetime]] = mapped_column()

    # Relationships
    repository: Mapped["Repository"] = relationship(back_populates="readme_files")
    branch: Mapped[Optional["Branch"]] = relationship(back_populates="readme_files")
