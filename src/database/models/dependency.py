"""
RepositoryDependency and Vulnerability models.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.database.models.package import Package
    from src.database.models.repository import Branch, Repository


class RepositoryDependency(Base):
    """
    Per-repo usage of a package dependency.

    Upserted on (repo_id, package_name, ecosystem). Tracks first_seen_at and
    last_seen_at to infer when dependencies are added or removed.

    Version-agnostic metadata (EOL status, latest version) lives in the Package
    table. has_known_vulnerabilities is version-specific: a repo is flagged only
    if its pinned version is below the fixed_in_version of an active CVE.
    """

    __tablename__ = "repository_dependencies"

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
    is_dev_dependency: Mapped[bool] = mapped_column(Boolean, default=False)
    has_known_vulnerabilities: Mapped[bool] = mapped_column(Boolean, default=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    repository: Mapped["Repository"] = relationship(back_populates="repo_dependencies")
    branch: Mapped[Optional["Branch"]] = relationship(back_populates="repo_dependencies")


class Vulnerability(Base, TimestampMixin):
    """Security vulnerability for a package. Linked to packages, not per-repo dependencies."""

    __tablename__ = "vulnerabilities"

    id: Mapped[int] = mapped_column(primary_key=True)
    package_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("packages.id", ondelete="CASCADE")
    )
    cve_id: Mapped[Optional[str]] = mapped_column(String(50))
    vulnerability_id: Mapped[Optional[str]] = mapped_column(String(100))
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    published_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    modified_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    fixed_in_version: Mapped[Optional[str]] = mapped_column(String(100))
    references: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Relationships
    package: Mapped["Package"] = relationship(back_populates="vulnerabilities")
