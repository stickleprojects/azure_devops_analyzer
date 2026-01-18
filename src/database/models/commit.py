"""
Commit model.
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models.base import Base

if TYPE_CHECKING:
    from src.database.models.contributor import Contributor
    from src.database.models.repository import Repository


class Commit(Base):
    """Git commit in a repository."""

    __tablename__ = "commits"

    commit_sha: Mapped[str] = mapped_column(String(255), primary_key=True)
    repo_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("repositories.repo_id", ondelete="CASCADE")
    )
    branch_name: Mapped[Optional[str]] = mapped_column(String(255))
    author_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("contributors.id")
    )
    committer_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("contributors.id")
    )
    message: Mapped[Optional[str]] = mapped_column(Text)
    message_quality_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    commit_date: Mapped[datetime] = mapped_column(nullable=False)
    parent_shas: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text))
    files_changed: Mapped[Optional[int]] = mapped_column(Integer)
    lines_added: Mapped[Optional[int]] = mapped_column(Integer)
    lines_removed: Mapped[Optional[int]] = mapped_column(Integer)
    is_verified: Mapped[Optional[bool]] = mapped_column(Boolean)  # GPG signature verification
    verification_reason: Mapped[Optional[str]] = mapped_column(String(255))  # Reason if verification failed

    # Relationships
    repository: Mapped["Repository"] = relationship(back_populates="commits")
    author: Mapped[Optional["Contributor"]] = relationship(
        back_populates="authored_commits",
        foreign_keys=[author_id],
    )
    committer: Mapped[Optional["Contributor"]] = relationship(
        back_populates="committed_commits",
        foreign_keys=[committer_id],
    )
