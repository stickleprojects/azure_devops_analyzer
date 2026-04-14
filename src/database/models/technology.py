"""
Technology global metadata model.

Stores EOL and version information for technologies — one row per (name, category).
This is a global lookup table; EOL data is not per-repository.
"""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, String
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from src.database.models.base import Base


class Technology(Base):
    """
    Global facts about a technology (EOL, latest version).

    Upserted on (name, category). EOL enrichment runs once per technology,
    not once per repository — EOL is a global fact, not a per-repo fact.
    """

    __tablename__ = "technologies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    is_eol: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    eol_date: Mapped[Optional[date]] = mapped_column(Date)
    latest_supported_version: Mapped[Optional[str]] = mapped_column(String(100))
    eol_enriched_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True)
    )
