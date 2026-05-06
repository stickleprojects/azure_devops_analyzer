"""
Pull request, review, and comment models.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models.base import Base

if TYPE_CHECKING:
    from src.database.models.contributor import Contributor
    from src.database.models.repository import Repository


class PullRequest(Base):
    """Pull request in a repository."""

    __tablename__ = "pull_requests"
    __table_args__ = (
        UniqueConstraint("repo_id", "pr_number", name="uq_pr_repo_number"),
        UniqueConstraint("repo_id", "platform_pr_id", name="uq_pr_repo_platform_pr_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    repo_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("repositories.repo_id", ondelete="CASCADE")
    )
    pr_number: Mapped[int] = mapped_column(Integer, nullable=False)
    platform_pr_id: Mapped[Optional[str]] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    source_branch: Mapped[Optional[str]] = mapped_column(String(255))
    target_branch: Mapped[Optional[str]] = mapped_column(String(255))
    author_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("contributors.id")
    )
    status: Mapped[Optional[str]] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    merged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    files_changed: Mapped[int] = mapped_column(Integer, default=0)
    lines_added: Mapped[int] = mapped_column(Integer, default=0)
    lines_removed: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)
    approval_count: Mapped[int] = mapped_column(Integer, default=0)
    size_category: Mapped[Optional[str]] = mapped_column(String(20))
    has_issues: Mapped[bool] = mapped_column(Boolean, default=False)
    issue_flags: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text))

    # Relationships
    repository: Mapped["Repository"] = relationship(back_populates="pull_requests")
    author: Mapped[Optional["Contributor"]] = relationship(back_populates="authored_prs")
    reviews: Mapped[list["PRReview"]] = relationship(
        back_populates="pull_request", cascade="all, delete-orphan"
    )
    comments: Mapped[list["PRComment"]] = relationship(
        back_populates="pull_request", cascade="all, delete-orphan"
    )


class PRReview(Base):
    """Review on a pull request."""

    __tablename__ = "pr_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    pr_id: Mapped[int] = mapped_column(
        ForeignKey("pull_requests.id", ondelete="CASCADE")
    )
    reviewer_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("contributors.id")
    )
    review_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    vote: Mapped[Optional[int]] = mapped_column(Integer)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    pull_request: Mapped["PullRequest"] = relationship(back_populates="reviews")
    reviewer: Mapped[Optional["Contributor"]] = relationship(back_populates="reviews")


class PRComment(Base):
    """Comment or thread on a pull request."""

    __tablename__ = "pr_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    pr_id: Mapped[int] = mapped_column(
        ForeignKey("pull_requests.id", ondelete="CASCADE")
    )
    thread_id: Mapped[Optional[str]] = mapped_column(String(255))
    author_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("contributors.id")
    )
    content: Mapped[Optional[str]] = mapped_column(Text)
    comment_type: Mapped[Optional[str]] = mapped_column(String(50))
    published_date: Mapped[datetime] = mapped_column(nullable=False)
    file_path: Mapped[Optional[str]] = mapped_column(Text)
    line_number: Mapped[Optional[int]] = mapped_column(Integer)

    # Relationships
    pull_request: Mapped["PullRequest"] = relationship(back_populates="comments")
    author: Mapped[Optional["Contributor"]] = relationship(back_populates="comments")
