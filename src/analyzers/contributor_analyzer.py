"""
Contributor analytics module.

Calculates contributor metrics including commit counts, lines changed,
pull request activity, active days, and commit message quality.
"""

import re
from dataclasses import dataclass
from datetime import datetime, UTC
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, distinct, case
from sqlalchemy.orm import Session

from src.database.models import (
    ContributorMetric,
    Commit,
    PullRequest,
    PRReview,
    PRComment,
)


@dataclass
class CommitMessageQuality:
    """Results from commit message quality analysis."""

    score: Decimal  # 0.00 - 10.00
    has_subject: bool
    has_body: bool
    subject_length: int
    body_length: int
    has_issue_reference: bool
    has_imperative_mood: bool
    is_conventional: bool  # Follows conventional commits format


@dataclass
class ContributorStats:
    """Aggregated contributor statistics for a period."""

    contributor_id: int
    repo_id: str
    period_start: datetime
    period_end: datetime
    commit_count: int
    lines_added: int
    lines_removed: int
    files_modified: int
    pr_created: int
    pr_reviews: int
    pr_approvals: int
    active_days: int
    avg_commit_message_quality: Optional[Decimal]


class ContributorAnalyzer:
    """Analyzer for contributor activity and metrics."""

    # Conventional commit type prefixes
    CONVENTIONAL_TYPES = {
        "feat", "fix", "docs", "style", "refactor", "perf",
        "test", "build", "ci", "chore", "revert"
    }

    # Imperative mood verbs commonly used in commit messages
    IMPERATIVE_VERBS = {
        "add", "remove", "update", "fix", "change", "implement",
        "refactor", "improve", "create", "delete", "merge", "move",
        "rename", "revert", "bump", "release", "set", "enable",
        "disable", "configure", "handle", "support", "allow",
        "prevent", "use", "introduce", "optimize", "extract",
        "cleanup", "clean", "simplify", "reorganize", "restructure"
    }

    # Issue reference patterns
    ISSUE_PATTERNS = [
        r"#\d+",  # GitHub style: #123
        r"(?:fixes?|closes?|resolves?)\s+#?\d+",  # fixes #123, closes 123
        r"[A-Z]+-\d+",  # Jira style: PROJ-123
        r"(?:issue|bug|ticket)\s*[:#]?\s*\d+",  # issue: 123, bug #123
        r"AB#\d+",  # Azure Boards: AB#123
    ]

    def analyze_commit_message(self, message: str) -> CommitMessageQuality:
        """
        Analyze commit message quality.

        Args:
            message: The commit message to analyze.

        Returns:
            CommitMessageQuality with quality metrics.
        """
        if not message:
            return CommitMessageQuality(
                score=Decimal("0.00"),
                has_subject=False,
                has_body=False,
                subject_length=0,
                body_length=0,
                has_issue_reference=False,
                has_imperative_mood=False,
                is_conventional=False,
            )

        lines = message.strip().split("\n")
        subject = lines[0].strip() if lines else ""

        # Get body (skip blank line after subject)
        body_lines = []
        found_blank = False
        for line in lines[1:]:
            if not line.strip() and not found_blank:
                found_blank = True
                continue
            if found_blank:
                body_lines.append(line)
        body = "\n".join(body_lines).strip()

        # Analyze components
        has_subject = len(subject) > 0
        has_body = len(body) > 20  # Meaningful body has some content
        subject_length = len(subject)
        body_length = len(body)
        has_issue_reference = self._has_issue_reference(message)
        has_imperative_mood = self._has_imperative_mood(subject)
        is_conventional = self._is_conventional_commit(subject)

        # Calculate score (0-10)
        score = self._calculate_message_score(
            subject=subject,
            body=body,
            has_subject=has_subject,
            has_body=has_body,
            subject_length=subject_length,
            has_issue_reference=has_issue_reference,
            has_imperative_mood=has_imperative_mood,
            is_conventional=is_conventional,
        )

        return CommitMessageQuality(
            score=score,
            has_subject=has_subject,
            has_body=has_body,
            subject_length=subject_length,
            body_length=body_length,
            has_issue_reference=has_issue_reference,
            has_imperative_mood=has_imperative_mood,
            is_conventional=is_conventional,
        )

    def _has_issue_reference(self, message: str) -> bool:
        """Check if message contains an issue reference."""
        message_lower = message.lower()
        for pattern in self.ISSUE_PATTERNS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                return True
        return False

    def _has_imperative_mood(self, subject: str) -> bool:
        """Check if subject line starts with imperative mood verb."""
        if not subject:
            return False

        # Handle conventional commit format: type(scope): message
        # or type: message
        match = re.match(r"^(?:\w+(?:\([^)]+\))?:\s*)?(.+)", subject)
        if match:
            actual_message = match.group(1).strip()
        else:
            actual_message = subject

        # Get first word (lowercased)
        first_word = actual_message.split()[0].lower() if actual_message.split() else ""

        return first_word in self.IMPERATIVE_VERBS

    def _is_conventional_commit(self, subject: str) -> bool:
        """Check if subject follows conventional commits format."""
        if not subject:
            return False

        # Pattern: type(scope): description or type: description
        pattern = r"^(\w+)(?:\([^)]+\))?:\s+.+"
        match = re.match(pattern, subject)
        if not match:
            return False

        commit_type = match.group(1).lower()
        return commit_type in self.CONVENTIONAL_TYPES

    def _calculate_message_score(
        self,
        subject: str,
        body: str,
        has_subject: bool,
        has_body: bool,
        subject_length: int,
        has_issue_reference: bool,
        has_imperative_mood: bool,
        is_conventional: bool,
    ) -> Decimal:
        """
        Calculate commit message quality score (0-10).

        Scoring breakdown:
        - Subject presence and quality: up to 4 points
        - Body presence: up to 2 points
        - Issue reference: 1 point
        - Imperative mood: 1 point
        - Conventional format: 1 point
        - Subject length optimization: 1 point
        """
        score = Decimal("0.00")

        if not has_subject:
            return score

        # Subject presence (2 points base)
        score += Decimal("2.00")

        # Subject length optimization (1 point)
        # Ideal: 50-72 characters
        if 20 <= subject_length <= 72:
            score += Decimal("1.00")
        elif 10 <= subject_length <= 100:
            score += Decimal("0.50")

        # Subject content quality (1 point)
        # Not just a hash or trivial message
        trivial_patterns = [
            r"^[a-f0-9]{7,40}$",  # Just a commit hash
            r"^wip\b",  # WIP
            r"^merge\s+branch",  # Auto-generated merge
            r"^initial\s+commit$",  # Generic initial commit
            r"^\.$",  # Just a dot
            r"^-+$",  # Just dashes
            r"^\s*$",  # Empty
        ]
        is_trivial = any(
            re.match(p, subject.lower()) for p in trivial_patterns
        )
        if not is_trivial:
            score += Decimal("1.00")

        # Body presence (2 points)
        if has_body:
            score += Decimal("2.00")

        # Issue reference (1 point)
        if has_issue_reference:
            score += Decimal("1.00")

        # Imperative mood (1 point)
        if has_imperative_mood:
            score += Decimal("1.00")

        # Conventional commits format (1 point)
        if is_conventional:
            score += Decimal("1.00")

        return min(score, Decimal("10.00"))

    def calculate_contributor_metrics(
        self,
        session: Session,
        repo_id: str,
        period_start: datetime,
        period_end: datetime,
    ) -> list[ContributorStats]:
        """
        Calculate contributor metrics for a repository within a time period.

        Args:
            session: Database session.
            repo_id: Repository identifier.
            period_start: Start of the period (inclusive).
            period_end: End of the period (exclusive).

        Returns:
            List of ContributorStats for each contributor with activity.
        """
        # Get all contributors with commits in this period
        commit_stats = (
            session.query(
                Commit.author_id,
                func.count(Commit.commit_sha).label("commit_count"),
                func.coalesce(func.sum(Commit.lines_added), 0).label("lines_added"),
                func.coalesce(func.sum(Commit.lines_removed), 0).label("lines_removed"),
                func.coalesce(func.sum(Commit.files_changed), 0).label("files_modified"),
                func.count(distinct(func.date(Commit.commit_date))).label("commit_days"),
                func.avg(Commit.message_quality_score).label("avg_quality"),
            )
            .filter(
                Commit.repo_id == repo_id,
                Commit.commit_date >= period_start,
                Commit.commit_date < period_end,
                Commit.author_id.isnot(None),
            )
            .group_by(Commit.author_id)
            .all()
        )

        # Build a map of contributor stats from commits
        contributor_stats: dict[int, dict] = {}
        for row in commit_stats:
            contributor_stats[row.author_id] = {
                "commit_count": row.commit_count or 0,
                "lines_added": row.lines_added or 0,
                "lines_removed": row.lines_removed or 0,
                "files_modified": row.files_modified or 0,
                "commit_days": set(),  # Will be populated later
                "avg_quality": row.avg_quality,
            }

        # Get distinct commit dates for active days calculation
        commit_dates = (
            session.query(
                Commit.author_id,
                func.date(Commit.commit_date).label("activity_date"),
            )
            .filter(
                Commit.repo_id == repo_id,
                Commit.commit_date >= period_start,
                Commit.commit_date < period_end,
                Commit.author_id.isnot(None),
            )
            .distinct()
            .all()
        )

        # Track commit days
        for row in commit_dates:
            if row.author_id in contributor_stats:
                contributor_stats[row.author_id].setdefault("active_dates", set())
                contributor_stats[row.author_id]["active_dates"].add(row.activity_date)

        # Get PR creation stats
        pr_stats = (
            session.query(
                PullRequest.author_id,
                func.count(PullRequest.id).label("pr_created"),
                func.count(distinct(func.date(PullRequest.created_at))).label("pr_days"),
            )
            .filter(
                PullRequest.repo_id == repo_id,
                PullRequest.created_at >= period_start,
                PullRequest.created_at < period_end,
                PullRequest.author_id.isnot(None),
            )
            .group_by(PullRequest.author_id)
            .all()
        )

        for row in pr_stats:
            if row.author_id not in contributor_stats:
                contributor_stats[row.author_id] = {
                    "commit_count": 0,
                    "lines_added": 0,
                    "lines_removed": 0,
                    "files_modified": 0,
                    "active_dates": set(),
                    "avg_quality": None,
                }
            contributor_stats[row.author_id]["pr_created"] = row.pr_created or 0

        # Get PR creation dates for active days
        pr_dates = (
            session.query(
                PullRequest.author_id,
                func.date(PullRequest.created_at).label("activity_date"),
            )
            .filter(
                PullRequest.repo_id == repo_id,
                PullRequest.created_at >= period_start,
                PullRequest.created_at < period_end,
                PullRequest.author_id.isnot(None),
            )
            .distinct()
            .all()
        )

        for row in pr_dates:
            if row.author_id in contributor_stats:
                contributor_stats[row.author_id].setdefault("active_dates", set())
                contributor_stats[row.author_id]["active_dates"].add(row.activity_date)

        # Get review stats (need to join through PullRequest to filter by repo)
        review_stats = (
            session.query(
                PRReview.reviewer_id,
                func.count(PRReview.id).label("pr_reviews"),
                func.sum(
                    case((PRReview.vote == 10, 1), else_=0)
                ).label("pr_approvals"),
            )
            .join(PullRequest, PRReview.pr_id == PullRequest.id)
            .filter(
                PullRequest.repo_id == repo_id,
                PRReview.review_date >= period_start,
                PRReview.review_date < period_end,
                PRReview.reviewer_id.isnot(None),
            )
            .group_by(PRReview.reviewer_id)
            .all()
        )

        for row in review_stats:
            if row.reviewer_id not in contributor_stats:
                contributor_stats[row.reviewer_id] = {
                    "commit_count": 0,
                    "lines_added": 0,
                    "lines_removed": 0,
                    "files_modified": 0,
                    "active_dates": set(),
                    "avg_quality": None,
                }
            contributor_stats[row.reviewer_id]["pr_reviews"] = row.pr_reviews or 0
            contributor_stats[row.reviewer_id]["pr_approvals"] = row.pr_approvals or 0

        # Get review dates for active days
        review_dates = (
            session.query(
                PRReview.reviewer_id,
                func.date(PRReview.review_date).label("activity_date"),
            )
            .join(PullRequest, PRReview.pr_id == PullRequest.id)
            .filter(
                PullRequest.repo_id == repo_id,
                PRReview.review_date >= period_start,
                PRReview.review_date < period_end,
                PRReview.reviewer_id.isnot(None),
            )
            .distinct()
            .all()
        )

        for row in review_dates:
            if row.reviewer_id in contributor_stats:
                contributor_stats[row.reviewer_id].setdefault("active_dates", set())
                contributor_stats[row.reviewer_id]["active_dates"].add(row.activity_date)

        # Get comment dates for active days
        comment_dates = (
            session.query(
                PRComment.author_id,
                func.date(PRComment.published_date).label("activity_date"),
            )
            .join(PullRequest, PRComment.pr_id == PullRequest.id)
            .filter(
                PullRequest.repo_id == repo_id,
                PRComment.published_date >= period_start,
                PRComment.published_date < period_end,
                PRComment.author_id.isnot(None),
            )
            .distinct()
            .all()
        )

        for row in comment_dates:
            if row.author_id not in contributor_stats:
                contributor_stats[row.author_id] = {
                    "commit_count": 0,
                    "lines_added": 0,
                    "lines_removed": 0,
                    "files_modified": 0,
                    "active_dates": set(),
                    "avg_quality": None,
                }
            contributor_stats[row.author_id].setdefault("active_dates", set())
            contributor_stats[row.author_id]["active_dates"].add(row.activity_date)

        # Build result list
        results = []
        for contributor_id, stats in contributor_stats.items():
            active_dates = stats.get("active_dates", set())
            avg_quality = stats.get("avg_quality")

            results.append(
                ContributorStats(
                    contributor_id=contributor_id,
                    repo_id=repo_id,
                    period_start=period_start,
                    period_end=period_end,
                    commit_count=stats.get("commit_count", 0),
                    lines_added=stats.get("lines_added", 0),
                    lines_removed=stats.get("lines_removed", 0),
                    files_modified=stats.get("files_modified", 0),
                    pr_created=stats.get("pr_created", 0),
                    pr_reviews=stats.get("pr_reviews", 0),
                    pr_approvals=stats.get("pr_approvals", 0),
                    active_days=len(active_dates),
                    avg_commit_message_quality=(
                        Decimal(str(round(avg_quality, 2)))
                        if avg_quality is not None
                        else None
                    ),
                )
            )

        return results

    def update_commit_message_scores(
        self,
        session: Session,
        repo_id: Optional[str] = None,
        batch_size: int = 500,
    ) -> int:
        """
        Update commit message quality scores for commits that don't have them.

        Args:
            session: Database session.
            repo_id: Optional repository ID to limit scope.
            batch_size: Number of commits to process at once.

        Returns:
            Number of commits updated.
        """
        query = session.query(Commit).filter(
            Commit.message_quality_score.is_(None),
            Commit.message.isnot(None),
        )

        if repo_id:
            query = query.filter(Commit.repo_id == repo_id)

        commits = query.limit(batch_size).all()
        updated = 0

        for commit in commits:
            if commit.message:
                quality = self.analyze_commit_message(commit.message)
                commit.message_quality_score = quality.score
                updated += 1

        return updated


def store_contributor_metrics(
    session: Session,
    stats: ContributorStats,
) -> ContributorMetric:
    """
    Store or update contributor metrics for a period.

    Args:
        session: Database session.
        stats: Contributor statistics to store.

    Returns:
        ContributorMetric instance.
    """
    # Check for existing metric in this period
    existing = (
        session.query(ContributorMetric)
        .filter(
            ContributorMetric.repo_id == stats.repo_id,
            ContributorMetric.contributor_id == stats.contributor_id,
            ContributorMetric.period_start == stats.period_start,
        )
        .first()
    )

    if existing:
        # Update existing
        existing.period_end = stats.period_end
        existing.commit_count = stats.commit_count
        existing.lines_added = stats.lines_added
        existing.lines_removed = stats.lines_removed
        existing.files_modified = stats.files_modified
        existing.pr_created = stats.pr_created
        existing.pr_reviews = stats.pr_reviews
        existing.pr_approvals = stats.pr_approvals
        existing.active_days = stats.active_days
        existing.avg_commit_message_quality = stats.avg_commit_message_quality
        return existing
    else:
        # Create new
        metric = ContributorMetric(
            repo_id=stats.repo_id,
            contributor_id=stats.contributor_id,
            period_start=stats.period_start,
            period_end=stats.period_end,
            commit_count=stats.commit_count,
            lines_added=stats.lines_added,
            lines_removed=stats.lines_removed,
            files_modified=stats.files_modified,
            pr_created=stats.pr_created,
            pr_reviews=stats.pr_reviews,
            pr_approvals=stats.pr_approvals,
            active_days=stats.active_days,
            avg_commit_message_quality=stats.avg_commit_message_quality,
        )
        session.add(metric)
        return metric


def calculate_and_store_contributor_metrics(
    session: Session,
    repo_id: str,
    period_start: datetime,
    period_end: datetime,
) -> list[ContributorMetric]:
    """
    Calculate and store contributor metrics for a repository.

    This is a convenience function that combines calculation and storage.

    Args:
        session: Database session.
        repo_id: Repository identifier.
        period_start: Start of the period (inclusive).
        period_end: End of the period (exclusive).

    Returns:
        List of stored ContributorMetric instances.
    """
    analyzer = ContributorAnalyzer()

    # First, ensure commit message scores are calculated
    analyzer.update_commit_message_scores(session, repo_id)

    # Calculate metrics
    stats_list = analyzer.calculate_contributor_metrics(
        session, repo_id, period_start, period_end
    )

    # Store each contributor's metrics
    metrics = []
    for stats in stats_list:
        metric = store_contributor_metrics(session, stats)
        metrics.append(metric)

    return metrics


def get_monthly_periods(
    start_date: datetime,
    end_date: datetime,
) -> list[tuple[datetime, datetime]]:
    """
    Generate monthly period boundaries between two dates.

    Args:
        start_date: Start date.
        end_date: End date.

    Returns:
        List of (period_start, period_end) tuples.
    """
    periods = []
    current = datetime(start_date.year, start_date.month, 1, tzinfo=UTC)

    while current < end_date:
        # Calculate end of month
        if current.month == 12:
            next_month = datetime(current.year + 1, 1, 1, tzinfo=UTC)
        else:
            next_month = datetime(current.year, current.month + 1, 1, tzinfo=UTC)

        periods.append((current, next_month))
        current = next_month

    return periods
