"""
SQLAlchemy ORM models for Tech Radar tables (Plan 022).

Three tables:
  RadarPublication   — a versioned radar snapshot
  RadarBlip          — an individual technology entry within a publication
  RadarBlipHistory   — ring-movement history for timeline view
"""

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models.base import Base

if TYPE_CHECKING:
    pass  # no cross-model relationships needed outside this file


class RadarPublication(Base):
    """A single published Tech Radar snapshot."""

    __tablename__ = "radar_publications"

    id: Mapped[int] = mapped_column(primary_key=True)
    publication_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    publication_version: Mapped[Optional[str]] = mapped_column(String(50))
    description: Mapped[Optional[str]] = mapped_column(Text)
    published_by: Mapped[Optional[str]] = mapped_column(String(255))
    is_latest: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    blips: Mapped[list["RadarBlip"]] = relationship(
        back_populates="publication", cascade="all, delete-orphan"
    )


class RadarBlip(Base):
    """A technology entry (blip) within a RadarPublication."""

    __tablename__ = "radar_blips"

    id: Mapped[int] = mapped_column(primary_key=True)
    publication_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("radar_publications.id", ondelete="CASCADE"), nullable=False
    )
    package_name: Mapped[str] = mapped_column(String(500), nullable=False)
    ecosystem: Mapped[str] = mapped_column(String(100), nullable=False)
    ring: Mapped[str] = mapped_column(String(50), nullable=False)
    quadrant: Mapped[str] = mapped_column(String(50), nullable=False)
    label: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_new: Mapped[bool] = mapped_column(Boolean, default=False)
    is_moved: Mapped[bool] = mapped_column(Boolean, default=False)
    adopted_date: Mapped[Optional[date]] = mapped_column(Date)
    repo_count: Mapped[Optional[int]] = mapped_column(Integer)
    exposed_to_cves: Mapped[int] = mapped_column(Integer, default=0)
    is_eol: Mapped[bool] = mapped_column(Boolean, default=False)
    eol_date: Mapped[Optional[date]] = mapped_column(Date)
    latest_version: Mapped[Optional[str]] = mapped_column(String(100))
    flags: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    publication: Mapped["RadarPublication"] = relationship(back_populates="blips")


class RadarBlipHistory(Base):
    """Ring-movement record for a (package, ecosystem) across publications."""

    __tablename__ = "radar_blip_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    package_name: Mapped[str] = mapped_column(String(500), nullable=False)
    ecosystem: Mapped[str] = mapped_column(String(100), nullable=False)
    publication_date: Mapped[date] = mapped_column(Date, nullable=False)
    prior_ring: Mapped[Optional[str]] = mapped_column(String(50))
    current_ring: Mapped[str] = mapped_column(String(50), nullable=False)
    repo_count_delta: Mapped[Optional[int]] = mapped_column(Integer)
    vulnerability_change: Mapped[Optional[str]] = mapped_column(
        Text
    )  # now_exposed | fixed | unchanged
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
