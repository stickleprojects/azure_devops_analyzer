"""
Service and Repository-Service mapping models.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models.base import Base

if TYPE_CHECKING:
    from src.database.models.repository import Repository


class Service(Base):
    """Service representing a logical grouping of repositories."""

    __tablename__ = "services"

    service_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    purpose: Mapped[Optional[str]] = mapped_column(Text)
    cmdb_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    created_at: Mapped[Optional[datetime]] = mapped_column()
    updated_at: Mapped[Optional[datetime]] = mapped_column()

    # Relationships
    repository_services: Mapped[list["RepositoryService"]] = relationship(
        back_populates="service", cascade="all, delete-orphan"
    )

    @property
    def repositories(self) -> list["Repository"]:
        """Get all repositories belonging to this service."""
        return [rs.repository for rs in self.repository_services]


class RepositoryService(Base):
    """Junction table for many-to-many relationship between repositories and services."""

    __tablename__ = "repository_services"
    __table_args__ = (
        UniqueConstraint("repo_id", "service_id", name="uq_repo_service"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    repo_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("repositories.repo_id", ondelete="CASCADE")
    )
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.service_id", ondelete="CASCADE")
    )
    linked_at: Mapped[Optional[datetime]] = mapped_column()

    # Relationships
    repository: Mapped["Repository"] = relationship(back_populates="repository_services")
    service: Mapped["Service"] = relationship(back_populates="repository_services")
