"""
TeamContributor model for many-to-many contributor-team relationships.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models.base import Base

if TYPE_CHECKING:
    from src.database.models.contributor import Contributor
    from src.database.models.team import Team


class TeamContributor(Base):
    """
    Many-to-many relationship between teams and contributors.
    
    Tracks when a contributor is a member of a team with effective date ranges
    to support historical team membership analysis.
    """

    __tablename__ = "team_contributors"
    __table_args__ = (
        UniqueConstraint("team_id", "contributor_id", name="uq_team_contributor"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.team_id", ondelete="CASCADE"), nullable=False
    )
    contributor_id: Mapped[int] = mapped_column(
        ForeignKey("contributors.id", ondelete="CASCADE"), nullable=False
    )
    
    # Effective date range for team membership
    # If effective_end_date is NULL, the contributor is currently an active team member
    effective_start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    effective_end_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    # Relationships
    team: Mapped["Team"] = relationship(back_populates="contributors")
    contributor: Mapped["Contributor"] = relationship(back_populates="teams")
