"""
Base classes and mixins for SQLAlchemy models.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class TimestampMixin:
    """Mixin that adds created_at timestamp column."""
    created_at: Mapped[Optional[datetime]] = mapped_column(
        default=func.current_timestamp()
    )
