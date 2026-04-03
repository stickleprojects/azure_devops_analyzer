"""
Package model — version-agnostic metadata for a dependency package.
"""

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Date, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models.base import Base

if TYPE_CHECKING:
    from src.database.models.dependency import Vulnerability


class Package(Base):
    """
    Version-agnostic global metadata for a package (EOL status, latest version).

    One row per (package_name, ecosystem). Vulnerabilities link here rather than
    to per-repo dependency rows, so each CVE is stored once regardless of how many
    repos use the package.
    """

    __tablename__ = "packages"

    id: Mapped[int] = mapped_column(primary_key=True)
    package_name: Mapped[str] = mapped_column(String(500), nullable=False)
    ecosystem: Mapped[str] = mapped_column(String(100), nullable=False)
    latest_version: Mapped[Optional[str]] = mapped_column(String(100))
    is_eol: Mapped[bool] = mapped_column(Boolean, default=False)
    eol_date: Mapped[Optional[date]] = mapped_column(Date)
    enriched_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    vulnerabilities: Mapped[list["Vulnerability"]] = relationship(
        back_populates="package", cascade="all, delete-orphan"
    )
