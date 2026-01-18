"""
Organization and Project models.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.database.models.repository import Repository
    from src.database.models.team import Team


class Organization(Base, TimestampMixin):
    """Organization or account from a source control platform."""

    __tablename__ = "organizations"
    __table_args__ = (
        UniqueConstraint("platform", "name", name="uq_org_platform_name"),
    )

    organization_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    platform: Mapped[str] = mapped_column(
        String(20), nullable=False, default="azure_devops"
    )

    # Relationships
    projects: Mapped[list["Project"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    teams: Mapped[list["Team"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )


class Project(Base, TimestampMixin):
    """Project within an organization (Azure DevOps concept)."""

    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_project_org_name"),
    )

    project_id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("organizations.organization_id")
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    organization: Mapped[Optional["Organization"]] = relationship(
        back_populates="projects"
    )
    repositories: Mapped[list["Repository"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
