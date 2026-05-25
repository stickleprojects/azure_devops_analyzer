"""Extraction progress tracking models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models.base import Base


class ExtractionRun(Base):
    """Top-level extraction run tracking."""

    __tablename__ = "extraction_runs"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    organization_name: Mapped[Optional[str]] = mapped_column(String(255))
    project_name: Mapped[Optional[str]] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    total_repositories: Mapped[int] = mapped_column(Integer, default=0)
    processed_repositories: Mapped[int] = mapped_column(Integer, default=0)
    current_repository_id: Mapped[Optional[str]] = mapped_column(String(255))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    metrics: Mapped[list["ExtractionMetric"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class ExtractionMetric(Base):
    """Per-repository extraction metrics for monitoring."""

    __tablename__ = "extraction_metrics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extraction_runs.run_id", ondelete="CASCADE"),
        nullable=False,
    )
    repository_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    extraction_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, primary_key=True
    )
    extraction_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    extraction_duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    commits_extracted: Mapped[int] = mapped_column(Integer, default=0)
    pull_requests_extracted: Mapped[int] = mapped_column(Integer, default=0)
    branches_extracted: Mapped[int] = mapped_column(Integer, default=0)
    contributors_extracted: Mapped[int] = mapped_column(Integer, default=0)
    cache_hits: Mapped[int] = mapped_column(Integer, default=0)
    cache_misses: Mapped[int] = mapped_column(Integer, default=0)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255))
    worker_hostname: Mapped[Optional[str]] = mapped_column(String(255))
    correlation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid.uuid4, nullable=False
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp()
    )

    run: Mapped["ExtractionRun"] = relationship(back_populates="metrics")
