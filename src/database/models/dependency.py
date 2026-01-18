"""
Dependency and Vulnerability models.
"""

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.database.models.repository import Branch, Repository


class Dependency(Base):
    """
    Package dependency for a repository.

    This is a TimescaleDB hypertable with 1-month chunks, partitioned by analyzed_at.
    """

    __tablename__ = "dependencies"

    id: Mapped[int] = mapped_column(primary_key=True)
    repo_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("repositories.repo_id", ondelete="CASCADE")
    )
    branch_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("branches.branch_id", ondelete="CASCADE")
    )
    package_name: Mapped[str] = mapped_column(String(500), nullable=False)
    version: Mapped[Optional[str]] = mapped_column(String(100))
    ecosystem: Mapped[str] = mapped_column(String(100), nullable=False)
    latest_version: Mapped[Optional[str]] = mapped_column(String(100))
    is_dev_dependency: Mapped[bool] = mapped_column(Boolean, default=False)
    has_vulnerabilities: Mapped[bool] = mapped_column(Boolean, default=False)
    is_eol: Mapped[bool] = mapped_column(Boolean, default=False)
    eol_date: Mapped[Optional[date]] = mapped_column(Date)
    analyzed_at: Mapped[datetime] = mapped_column(nullable=False)

    # Relationships
    repository: Mapped["Repository"] = relationship(back_populates="dependencies")
    branch: Mapped[Optional["Branch"]] = relationship(back_populates="dependencies")
    vulnerabilities: Mapped[list["Vulnerability"]] = relationship(
        back_populates="dependency", cascade="all, delete-orphan"
    )


class Vulnerability(Base, TimestampMixin):
    """Security vulnerability associated with a dependency."""

    __tablename__ = "vulnerabilities"

    id: Mapped[int] = mapped_column(primary_key=True)
    dependency_id: Mapped[int] = mapped_column(
        ForeignKey("dependencies.id", ondelete="CASCADE")
    )
    cve_id: Mapped[Optional[str]] = mapped_column(String(50))
    vulnerability_id: Mapped[Optional[str]] = mapped_column(String(100))
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    published_date: Mapped[Optional[datetime]] = mapped_column()
    modified_date: Mapped[Optional[datetime]] = mapped_column()
    fixed_in_version: Mapped[Optional[str]] = mapped_column(String(100))
    references: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Relationships
    dependency: Mapped["Dependency"] = relationship(back_populates="vulnerabilities")
