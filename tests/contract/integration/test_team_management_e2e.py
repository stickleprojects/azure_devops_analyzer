"""
Integration tests for team management features (FR-11.2, FR-11.3, FR-11.5).

Tests many-to-many contributor-team relationships, metric aggregation,
and historical team membership tracking.
"""

import pytest
from datetime import datetime, timedelta, UTC
from decimal import Decimal

from src.database.models import Team, Contributor, TeamContributor, TeamMetric, ContributorMetric
from src.database.team_analytics import (
    add_contributor_to_team,
    remove_contributor_from_team,
    get_active_team_members,
    compute_team_metrics,
    get_team_metrics,
    get_team_contributors_count,
)


class TestTeamContributorRelationship:
    """Test basic team-contributor many-to-many relationships."""

    def test_add_contributor_to_team(self, test_session, organization, teams):
        """Test adding a contributor to a team."""
        contrib = Contributor(
            name="Alice",
            email="alice@example.com",
        )
        test_session.add(contrib)
        test_session.commit()

        team_contrib = add_contributor_to_team(
            test_session, teams[0].team_id, contrib.id
        )
        test_session.commit()

        assert team_contrib.team_id == teams[0].team_id
        assert team_contrib.contributor_id == contrib.id
        assert team_contrib.effective_start_date is not None
        assert team_contrib.effective_end_date is None

    def test_add_contributor_to_team_nonexistent_team(self, test_session, organization):
        """Test error when adding contributor to nonexistent team."""
        contrib = Contributor(
            name="Bob",
            email="bob@example.com",
        )
        test_session.add(contrib)
        test_session.commit()

        with pytest.raises(ValueError, match="Team.*not found"):
            add_contributor_to_team(test_session, 9999, contrib.id)

    def test_add_contributor_to_team_nonexistent_contributor(self, test_session, teams):
        """Test error when adding nonexistent contributor to team."""
        with pytest.raises(ValueError, match="Contributor.*not found"):
            add_contributor_to_team(test_session, teams[0].team_id, 9999)

    def test_add_contributor_duplicate(self, test_session, organization, teams):
        """Test adding same contributor twice returns existing relationship."""
        contrib = Contributor(
            name="Charlie",
            email="charlie@example.com",
        )
        test_session.add(contrib)
        test_session.commit()

        team_contrib1 = add_contributor_to_team(
            test_session, teams[0].team_id, contrib.id
        )
        test_session.commit()

        team_contrib2 = add_contributor_to_team(
            test_session, teams[0].team_id, contrib.id
        )
        test_session.commit()

        assert team_contrib1.id == team_contrib2.id


class TestTeamMembership:
    """Test team membership tracking and removal."""

    def test_remove_contributor_from_team(self, test_session, organization, teams):
        """Test removing contributor from team."""
        contrib = Contributor(
            name="Dave",
            email="dave@example.com",
        )
        test_session.add(contrib)
        test_session.commit()

        add_contributor_to_team(test_session, teams[0].team_id, contrib.id)
        test_session.commit()

        # Remove contributor
        removed = remove_contributor_from_team(
            test_session, teams[0].team_id, contrib.id
        )
        test_session.commit()

        assert removed is True

        # Verify effective_end_date is set
        team_contrib = test_session.query(TeamContributor).filter_by(
            team_id=teams[0].team_id, contributor_id=contrib.id
        ).first()
        assert team_contrib.effective_end_date is not None

    def test_remove_nonexistent_relationship(self, test_session, organization, teams):
        """Test removing relationship that doesn't exist."""
        contrib = Contributor(
            name="Eve",
            email="eve@example.com",
        )
        test_session.add(contrib)
        test_session.commit()

        # Try to remove without adding first
        removed = remove_contributor_from_team(
            test_session, teams[0].team_id, contrib.id
        )

        assert removed is False

    def test_get_active_team_members(self, test_session, organization, teams):
        """Test retrieving active team members."""
        contributors = []
        for i in range(3):
            contrib = Contributor(
                name=f"Member {i}",
                email=f"member{i}@example.com",
            )
            test_session.add(contrib)
            contributors.append(contrib)
        test_session.commit()

        # Add all to team
        for contrib in contributors:
            add_contributor_to_team(test_session, teams[0].team_id, contrib.id)
        test_session.commit()

        # Get active members
        active = get_active_team_members(test_session, teams[0].team_id)

        assert len(active) == 3
        assert all(c.id in [contrib.id for contrib in contributors] for c in active)

    def test_get_active_team_members_excludes_removed(self, test_session, organization, teams):
        """Test that removed members are not in active list."""
        contrib1 = Contributor(
            name="Kept",
            email="kept@example.com",
        )
        contrib2 = Contributor(
            name="Removed",
            email="removed@example.com",
        )
        test_session.add(contrib1)
        test_session.add(contrib2)
        test_session.commit()

        add_contributor_to_team(test_session, teams[0].team_id, contrib1.id)
        add_contributor_to_team(test_session, teams[0].team_id, contrib2.id)
        test_session.commit()

        # Remove contrib2
        remove_contributor_from_team(test_session, teams[0].team_id, contrib2.id)
        test_session.commit()

        # Get active members
        active = get_active_team_members(test_session, teams[0].team_id)

        assert len(active) == 1
        assert active[0].id == contrib1.id

    def test_get_active_team_members_as_of_date(self, test_session, organization, teams):
        """Test time-travel queries for team membership."""
        contrib = Contributor(
            name="Time Traveler",
            email="time_traveler@example.com",
        )
        test_session.add(contrib)
        test_session.commit()

        # Add with specific date
        past_date = datetime.now(UTC) - timedelta(days=30)
        team_contrib = add_contributor_to_team(
            test_session, teams[0].team_id, contrib.id, effective_start_date=past_date
        )
        future_removal = datetime.now(UTC) + timedelta(days=30)
        team_contrib.effective_end_date = future_removal
        test_session.commit()

        # Query at different points in time
        before_join = get_active_team_members(
            test_session, teams[0].team_id, as_of_date=past_date - timedelta(days=1)
        )
        during_membership = get_active_team_members(
            test_session, teams[0].team_id, as_of_date=datetime.now(UTC)
        )
        after_removal = get_active_team_members(
            test_session, teams[0].team_id, as_of_date=future_removal + timedelta(days=1)
        )

        assert len(before_join) == 0
        assert len(during_membership) == 1
        assert len(after_removal) == 0

    def test_get_team_contributors_count(self, test_session, organization, teams):
        """Test counting active team members."""
        contributors = []
        for i in range(5):
            contrib = Contributor(
                name=f"Counter {i}",
                email=f"counter{i}@example.com",
            )
            test_session.add(contrib)
            contributors.append(contrib)
        test_session.commit()

        # Add to team
        for contrib in contributors:
            add_contributor_to_team(test_session, teams[0].team_id, contrib.id)
        test_session.commit()

        count = get_team_contributors_count(test_session, teams[0].team_id)

        assert count == 5

        # Remove one
        remove_contributor_from_team(
            test_session, teams[0].team_id, contributors[0].id
        )
        test_session.commit()

        new_count = get_team_contributors_count(test_session, teams[0].team_id)
        assert new_count == 4


class TestTeamMetrics:
    """Test team metrics computation and retrieval."""

    def test_compute_team_metrics(self, test_session, organization, teams, contributors):
        """Test computing aggregated team metrics."""
        # Add contributors to team
        for contrib in contributors:
            add_contributor_to_team(test_session, teams[0].team_id, contrib.id)
        test_session.commit()

        # Create contributor metrics for the period
        period_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = period_start + timedelta(days=1)

        for i, contrib in enumerate(contributors):
            metric = ContributorMetric(
                contributor_id=contrib.id,
                period_start=period_start,
                period_end=period_end,
                commit_count=10 + i,
                pr_created=2 + i,
                pr_reviews=3 + i,
                pr_approvals=1 + i,
                lines_added=100 * (i + 1),
                lines_removed=50 * (i + 1),
                files_modified=5 + i,
                avg_commit_message_quality=Decimal("4.5"),
            )
            test_session.add(metric)
        test_session.commit()

        # Compute team metrics
        team_metric = compute_team_metrics(
            test_session, teams[0].team_id, period_start, period_end
        )

        # Verify aggregations
        assert team_metric.total_commits > 0
        assert team_metric.total_prs_created > 0
        assert team_metric.active_contributors > 0

    def test_get_team_metrics(self, test_session, organization, teams, contributors):
        """Test retrieving stored team metrics."""
        # Add contributors to team
        for contrib in contributors:
            add_contributor_to_team(test_session, teams[0].team_id, contrib.id)
        test_session.commit()

        # Create and store team metrics
        period_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = period_start + timedelta(days=1)

        team_metric = TeamMetric(
            team_id=teams[0].team_id,
            period_start=period_start,
            period_end=period_end,
            total_commits=100,
            total_lines_added=1000,
            total_lines_removed=500,
            active_contributors=len(contributors),
        )
        test_session.add(team_metric)
        test_session.commit()

        # Retrieve metrics
        retrieved = get_team_metrics(
            test_session,
            teams[0].team_id,
            period_start - timedelta(days=1),
            period_end + timedelta(days=1),
        )

        assert len(retrieved) >= 1
        assert retrieved[0].team_id == teams[0].team_id
        assert retrieved[0].total_commits == 100


class TestTeamContributorCascade:
    """Test foreign key cascading behavior."""

    def test_contributor_deletion_cascades(self, test_session, organization, teams):
        """Test that deleting a contributor removes their team relationships."""
        contrib = Contributor(
            name="Cascade Test",
            email="cascade_test@example.com",
        )
        test_session.add(contrib)
        test_session.commit()

        add_contributor_to_team(test_session, teams[0].team_id, contrib.id)
        test_session.commit()

        # Verify relationship exists
        tc = test_session.query(TeamContributor).filter_by(
            contributor_id=contrib.id
        ).first()
        assert tc is not None

        # Delete contributor
        test_session.delete(contrib)
        test_session.commit()

        # Verify relationship is gone
        tc = test_session.query(TeamContributor).filter_by(
            contributor_id=contrib.id
        ).first()
        assert tc is None

    def test_team_deletion_cascades(self, test_session, organization, teams, contributors):
        """Test that deleting a team removes team relationships."""
        # Add contributors to team
        for contrib in contributors:
            add_contributor_to_team(test_session, teams[0].team_id, contrib.id)
        test_session.commit()

        # Verify relationships exist
        tc_count = test_session.query(TeamContributor).filter_by(
            team_id=teams[0].team_id
        ).count()
        assert tc_count > 0

        # Delete team
        test_session.delete(teams[0])
        test_session.commit()

        # Verify relationships are gone
        tc_count = test_session.query(TeamContributor).filter_by(
            team_id=teams[0].team_id
        ).count()
        assert tc_count == 0
