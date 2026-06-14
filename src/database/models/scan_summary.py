"""Per-scan digest model for fast highlights/trend queries."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database.models.base import Base


class ScanSummary(Base):
    """One digest row per extraction run."""

    __tablename__ = "scan_summary"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extraction_runs.run_id", ondelete="CASCADE"),
        primary_key=True,
    )
    scan_completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    repos_scanned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    new_repos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retired_repos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_new_commits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    contributors: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    new_libraries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    new_vulnerabilities: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
