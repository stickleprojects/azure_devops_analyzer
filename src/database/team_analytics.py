"""
Team analytics and aggregation queries.

Provides functions to compute team-level metrics from contributor data
and manage team membership relationships.

Implements FR-11.5 and FR-11.6: Team-level metric aggregation and queries.

IMPORTANT: This module manages team membership via the team_contributors junction table.
The legacy contributors.team_id field should NOT be used for new code.
See docs/04-implementation/contributor-team-migration.md for details.
"""

from datetime import datetime, UTC
from typing import Optional

from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session

from src.database.models import (
    Team,
    TeamContributor,
    TeamMetric,
    Contributor,
    ContributorMetric,
)


def add_contributor_to_team(
    session: Session,
    team_id: int,
    contributor_id: int,
    effective_start_date: Optional[datetime] = None,
) -> TeamContributor:
    """
    Add a contributor to a team.
    
    Uses the team_contributors junction table to support many-to-many relationships.
    The legacy contributors.team_id field is NOT used or modified.
    
    Args:
        session: Database session
        team_id: ID of the team
        contributor_id: ID of the contributor
        effective_start_date: When the contributor joined (default: now)
    
    Returns:
        TeamContributor: Created or existing relationship
        
    Raises:
        ValueError: If team or contributor doesn't exist
    """
    # Verify team exists
    team = session.query(Team).filter_by(team_id=team_id).first()
    if not team:
        raise ValueError(f"Team {team_id} not found")
    
    # Verify contributor exists
    contributor = session.query(Contributor).filter_by(id=contributor_id).first()
    if not contributor:
        raise ValueError(f"Contributor {contributor_id} not found")
    
    if effective_start_date is None:
        effective_start_date = datetime.now(UTC)
    
    # Check if already exists
    existing = session.query(TeamContributor).filter_by(
        team_id=team_id,
        contributor_id=contributor_id,
    ).first()
    
    if existing:
        return existing
    
    team_contributor = TeamContributor(
        team_id=team_id,
        contributor_id=contributor_id,
        effective_start_date=effective_start_date,
    )
    session.add(team_contributor)
    return team_contributor


def remove_contributor_from_team(
    session: Session,
    team_id: int,
    contributor_id: int,
    effective_end_date: Optional[datetime] = None,
) -> bool:
    """
    Remove a contributor from a team by setting effective_end_date.
    
    Args:
        session: Database session
        team_id: ID of the team
        contributor_id: ID of the contributor
        effective_end_date: When the contributor left (default: now)
    
    Returns:
        bool: True if updated, False if relationship not found
    """
    if effective_end_date is None:
        effective_end_date = datetime.now(UTC)
    
    team_contributor = session.query(TeamContributor).filter_by(
        team_id=team_id,
        contributor_id=contributor_id,
    ).first()
    
    if not team_contributor:
        return False
    
    team_contributor.effective_end_date = effective_end_date
    return True


def get_active_team_members(
    session: Session,
    team_id: int,
    as_of_date: Optional[datetime] = None,
) -> list[Contributor]:
    """
    Get all active members of a team.
    
    Args:
        session: Database session
        team_id: ID of the team
        as_of_date: Point in time to check membership (default: now)
    
    Returns:
        list[Contributor]: Active team members
    """
    if as_of_date is None:
        as_of_date = datetime.now(UTC)
    
    return session.query(Contributor).join(
        TeamContributor,
        Contributor.id == TeamContributor.contributor_id
    ).filter(
        and_(
            TeamContributor.team_id == team_id,
            TeamContributor.effective_start_date <= as_of_date,
            or_(
                TeamContributor.effective_end_date.is_(None),
                TeamContributor.effective_end_date > as_of_date
            )
        )
    ).all()


def compute_team_metrics(
    session: Session,
    team_id: int,
    period_start: datetime,
    period_end: datetime,
) -> TeamMetric:
    """
    Compute aggregated team metrics for a time period.
    
    Aggregates all contributor metrics for active team members during
    the specified period.
    
    Args:
        session: Database session
        team_id: ID of the team
        period_start: Start of period
        period_end: End of period
    
    Returns:
        TeamMetric: Computed team metrics (not yet saved)
    """
    # Get all contributors who were active in the team during this period
    active_members = session.query(Contributor.id).join(
        TeamContributor,
        Contributor.id == TeamContributor.contributor_id
    ).filter(
        and_(
            TeamContributor.team_id == team_id,
            TeamContributor.effective_start_date < period_end,
            or_(
                TeamContributor.effective_end_date.is_(None),
                TeamContributor.effective_end_date > period_start
            )
        )
    ).subquery()
    
    # Aggregate contributor metrics for the period
    metrics_query = session.query(
        func.sum(ContributorMetric.commit_count).label("total_commits"),
        func.sum(ContributorMetric.lines_added).label("total_lines_added"),
        func.sum(ContributorMetric.lines_removed).label("total_lines_removed"),
        func.sum(ContributorMetric.files_modified).label("total_files_modified"),
        func.sum(ContributorMetric.pr_created).label("total_prs_created"),
        func.sum(ContributorMetric.pr_reviews).label("total_pr_reviews"),
        func.sum(ContributorMetric.pr_approvals).label("total_pr_approvals"),
        func.avg(ContributorMetric.avg_commit_message_quality).label("avg_commit_message_quality"),
        func.count(func.distinct(ContributorMetric.contributor_id)).label("active_contributors"),
    ).filter(
        and_(
            ContributorMetric.contributor_id.in_(session.query(active_members)),
            ContributorMetric.period_start >= period_start,
            ContributorMetric.period_end <= period_end,
        )
    )
    
    result = metrics_query.first()
    
    # Create TeamMetric object with aggregated values
    team_metric = TeamMetric(
        team_id=team_id,
        period_start=period_start,
        period_end=period_end,
        total_commits=result.total_commits or 0,
        total_lines_added=result.total_lines_added or 0,
        total_lines_removed=result.total_lines_removed or 0,
        total_files_modified=result.total_files_modified or 0,
        total_prs_created=result.total_prs_created or 0,
        total_pr_reviews=result.total_pr_reviews or 0,
        total_pr_approvals=result.total_pr_approvals or 0,
        avg_commit_message_quality=result.avg_commit_message_quality,
        active_contributors=result.active_contributors or 0,
    )
    
    return team_metric


def get_team_metrics(
    session: Session,
    team_id: int,
    period_start: datetime,
    period_end: datetime,
) -> list[TeamMetric]:
    """
    Retrieve team metrics for a time range.
    
    Args:
        session: Database session
        team_id: ID of the team
        period_start: Start of time range
        period_end: End of time range
    
    Returns:
        list[TeamMetric]: Team metrics ordered by period_start descending
    """
    return session.query(TeamMetric).filter(
        and_(
            TeamMetric.team_id == team_id,
            TeamMetric.period_start >= period_start,
            TeamMetric.period_start <= period_end,
        )
    ).order_by(TeamMetric.period_start.desc()).all()


def get_team_contributors_count(
    session: Session,
    team_id: int,
    as_of_date: Optional[datetime] = None,
) -> int:
    """
    Get the count of active team members.
    
    Args:
        session: Database session
        team_id: ID of the team
        as_of_date: Point in time to check (default: now)
    
    Returns:
        int: Count of active members
    """
    if as_of_date is None:
        as_of_date = datetime.now(UTC)
    
    return session.query(func.count(TeamContributor.id)).filter(
        and_(
            TeamContributor.team_id == team_id,
            TeamContributor.effective_start_date <= as_of_date,
            or_(
                TeamContributor.effective_end_date.is_(None),
                TeamContributor.effective_end_date > as_of_date
            )
        )
    ).scalar() or 0
