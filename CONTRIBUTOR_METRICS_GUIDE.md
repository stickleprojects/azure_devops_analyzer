# Contributor Metrics Process - Architecture & Implementation Guide

## Overview

The contributor metrics system calculates and stores metrics about contributor activity for a given time period. It tracks commits, pull requests, reviews, and code quality across all contributors in a repository.

---

## Data Flow Diagram

```
Extraction Workflow (GitHub/Azure DevOps)
    ↓
_process_repository()
    ├─ _process_commits()          [Stores commits with author_id FK]
    ├─ _process_pull_requests()    [Stores PRs with author_id FK]
    ├─ _process_dependencies()
    └─ _process_contributor_metrics()  ← STARTS HERE
         ↓
    calculate_and_store_contributor_metrics(repo_id, period_start, period_end)
         ↓
    [1] ContributorAnalyzer.update_commit_message_scores()
         └─ Scores all commits without message_quality_score
         ↓
    [2] ContributorAnalyzer.calculate_contributor_metrics()
         ├─ Query: Commits by repo/period
         ├─ Query: Pull Requests by repo/period
         ├─ Query: PR Reviews by repo/period
         ├─ Query: PR Comments by repo/period
         └─ Return: List[ContributorStats]
         ↓
    [3] store_contributor_metrics(stats)
         └─ For each ContributorStats → Insert ContributorMetric record
         ↓
    Database: contributor_metrics table updated
```

---

## Key Files & Locations

### 1. **Main Analyzer: [src/analyzers/contributor_analyzer.py](src/analyzers/contributor_analyzer.py)**

**Class: `ContributorAnalyzer`**

- **Line 268**: `calculate_contributor_metrics()` - Main calculation engine
- **Line 507**: `update_commit_message_scores()` - Quality scoring
- **Line 100**: `analyze_commit_message()` - Message quality algorithm

**Function: `calculate_and_store_contributor_metrics()` (Line 603)**

- Entry point called by workflows
- Orchestrates: scoring → calculation → storage

### 2. **Workflow Integration**

**GitHub Workflow: [src/workflows/github_analysis.py](src/workflows/github_analysis.py#L381-L433)**

- **Line 188**: Calls `_process_contributor_metrics(repo_data)`
- **Line 381-433**: `_process_contributor_metrics()` implementation
  - Checks if commits exist in current period (early exit)
  - Calls `calculate_and_store_contributor_metrics()`

**Azure DevOps Workflow: [src/workflows/azure_devops_analysis.py](src/workflows/azure_devops_analysis.py#L379-L431)**

- **Line 199**: Calls `_process_contributor_metrics(repo_data)`
- **Line 379-431**: `_process_contributor_metrics()` implementation (same logic)

### 3. **Data Models**

**Database Tables: [database/schema.sql](database/schema.sql)**

| Table                 | Primary Key          | Foreign Keys                                          | Purpose                                                 |
| --------------------- | -------------------- | ----------------------------------------------------- | ------------------------------------------------------- |
| `contributors`        | `id`                 | `team_id` (FK)                                        | Stores contributor info (email, name)                   |
| `contributor_metrics` | `(id, period_start)` | `repo_id` (FK), `contributor_id` (FK)                 | **Time-series metrics** for each contributor per period |
| `commits`             | `commit_sha`         | `repo_id` (FK), `author_id` (FK), `committer_id` (FK) | Commit data                                             |
| `pull_requests`       | `id`                 | `repo_id` (FK), `author_id` (FK)                      | PR data                                                 |
| `pr_reviews`          | `id`                 | `pr_id` (FK), `reviewer_id` (FK)                      | Review data                                             |
| `pr_comments`         | `id`                 | `pr_id` (FK), `author_id` (FK)                        | Comment data                                            |

### 4. **Test: [tests/contract/integration/test_contributor_metrics_e2e.py](tests/contract/integration/test_contributor_metrics_e2e.py)**

- **Line 27-102**: GitHub contributor metrics test
- **Line 105-155**: Azure DevOps contributor metrics test

---

## Detailed Process: Step-by-Step

### Step 1: Workflow calls `_process_contributor_metrics(repo_data)`

**Location**: `github_analysis.py:381` | `azure_devops_analysis.py:379`

```python
def _process_contributor_metrics(self, repo_data):
    """Calculate and store contributor metrics for the repository."""
    try:
        from datetime import datetime, UTC

        logger.info("      Calculating contributor metrics...")

        now = datetime.now(UTC)
        period_start = datetime(now.year, now.month, 1, tzinfo=UTC)

        # Calculate end of current month
        if now.month == 12:
            period_end = datetime(now.year + 1, 1, 1, tzinfo=UTC)
        else:
            period_end = datetime(now.year, now.month + 1, 1, tzinfo=UTC)

        with session_scope() as session:
            # **KEY OPTIMIZATION**: Early exit if no commits in period
            from src.database.models import Commit
            has_commits = (
                session.query(Commit)
                .filter(
                    Commit.repo_id == repo_data.repo_id,
                    Commit.commit_date >= period_start,
                    Commit.commit_date < period_end,
                )
                .limit(1)
                .first()
            )

            if not has_commits:
                logger.info("      No commits in current period - skipping metrics calculation")
                return  # ← EARLY EXIT (prevents unnecessary processing)

            # Call the main calculation function
            metrics = calculate_and_store_contributor_metrics(
                session,
                repo_data.repo_id,
                period_start,
                period_end,
            )

            if metrics:
                logger.info(
                    "      Calculated metrics for %d contributors",
                    len(metrics),
                )
```

**Key Points**:

- ✅ Period is always "current month" (1st to 1st)
- ✅ **Early exit optimization**: If no commits exist in period, skip entire calculation
- ✅ Uses `session_scope()` context manager (auto-commit)

### Step 2: `calculate_and_store_contributor_metrics()` Orchestration

**Location**: `src/analyzers/contributor_analyzer.py:603`

```python
def calculate_and_store_contributor_metrics(
    session: Session,
    repo_id: str,
    period_start: datetime,
    period_end: datetime,
) -> list[ContributorMetric]:
    """
    Calculate and store contributor metrics for a repository.
    """
    analyzer = ContributorAnalyzer()

    # **PHASE 1**: Score all unscored commits
    analyzer.update_commit_message_scores(session, repo_id)

    # **PHASE 2**: Calculate metrics
    stats_list = analyzer.calculate_contributor_metrics(
        session, repo_id, period_start, period_end
    )

    # **PHASE 3**: Store metrics
    metrics = []
    for stats in stats_list:
        metric = store_contributor_metrics(session, stats)
        metrics.append(metric)

    return metrics
```

**Three Phases**:

1. **Scoring** - Calculate `message_quality_score` for commits
2. **Calculation** - Aggregate activity data
3. **Storage** - Persist `ContributorMetric` records

---

### Step 3a: Phase 1 - Update Commit Message Scores

**Location**: `src/analyzers/contributor_analyzer.py:507`

```python
def update_commit_message_scores(
    self,
    session: Session,
    repo_id: Optional[str] = None,
    batch_size: int = 500,
) -> int:
    """
    Update commit message quality scores for commits that don't have them.

    Only processes commits WHERE message_quality_score IS NULL
    """
    query = session.query(Commit).filter(
        Commit.message_quality_score.is_(None),  # ← Only unscored commits
        Commit.message.isnot(None),
    )

    if repo_id:
        query = query.filter(Commit.repo_id == repo_id)  # ← Scoped to repository

    commits = query.limit(batch_size).all()  # ← Batch processing
    updated = 0

    for commit in commits:
        if commit.message:
            quality = self.analyze_commit_message(commit.message)  # ← Score it
            commit.message_quality_score = quality.score
            updated += 1

    return updated
```

**Quality Score Calculation** (`analyze_commit_message()`):

- **Subject presence**: 2 points (base)
- **Subject length**: 1 point (optimal: 50-72 chars)
- **Subject content**: 1 point (not trivial/hash)
- **Body presence**: 2 points
- **Issue reference**: 1 point
- **Imperative mood**: 1 point
- **Conventional format**: 1 point
- **Total**: 0.00 - 10.00 scale

---

### Step 3b: Phase 2 - Calculate Contributor Metrics

**Location**: `src/analyzers/contributor_analyzer.py:268`

This is the **core calculation engine**. It performs **7 SQL queries**:

```python
def calculate_contributor_metrics(
    self,
    session: Session,
    repo_id: str,
    period_start: datetime,
    period_end: datetime,
) -> list[ContributorStats]:
    """
    Calculate contributor metrics for a repository within a time period.
    """
    # QUERY 1: Get commit stats (count, lines, files)
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

    # QUERY 2: Get commit dates (for active days calculation)
    commit_dates = (
        session.query(
            Commit.author_id,
            func.date(Commit.commit_date).label("activity_date"),
        )
        .filter(...)
        .distinct()
        .all()
    )

    # QUERY 3: Get PR creation stats
    pr_stats = (
        session.query(
            PullRequest.author_id,
            func.count(PullRequest.id).label("pr_created"),
        )
        .filter(...)
        .group_by(PullRequest.author_id)
        .all()
    )

    # QUERY 4: Get PR creation dates
    pr_dates = (...)

    # QUERY 5: Get review stats (approvals, rejections)
    review_stats = (
        session.query(
            PRReview.reviewer_id,
            func.count(PRReview.id).label("pr_reviews"),
            func.sum(case((PRReview.vote == 10, 1))).label("pr_approvals"),
        )
        .join(PullRequest, ...)
        .filter(...)
        .group_by(PRReview.reviewer_id)
        .all()
    )

    # QUERY 6: Get review dates
    review_dates = (...)

    # QUERY 7: Get PR comment dates
    comment_dates = (...)

    # Aggregate results into ContributorStats objects
    results = []
    for contributor_id, stats in contributor_stats.items():
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
                active_days=len(active_dates),  # Count distinct dates
                avg_commit_message_quality=avg_quality,
            )
        )

    return results
```

**Metrics Calculated**:
| Metric | Source | Calculation |
|--------|--------|-------------|
| `commit_count` | Commits | COUNT(commits) per author |
| `lines_added` | Commits | SUM(lines_added) |
| `lines_removed` | Commits | SUM(lines_removed) |
| `files_modified` | Commits | SUM(files_changed) |
| `pr_created` | PullRequests | COUNT(prs) where author_id |
| `pr_reviews` | PRReviews | COUNT(reviews) where reviewer_id |
| `pr_approvals` | PRReviews | COUNT(reviews where vote=10) |
| `active_days` | All activity | COUNT(DISTINCT dates with commits/PRs/reviews/comments) |
| `avg_commit_message_quality` | Commits | AVG(message_quality_score) |

---

### Step 3c: Phase 3 - Store Metrics

**Location**: `src/analyzers/contributor_analyzer.py:544`

```python
def store_contributor_metrics(
    session: Session,
    stats: ContributorStats,
) -> ContributorMetric:
    """
    Store or update contributor metrics for a period.
    """
    # Check for existing metric in this period
    existing = (
        session.query(ContributorMetric)
        .filter_by(
            repo_id=stats.repo_id,
            contributor_id=stats.contributor_id,
            period_start=stats.period_start,
        )
        .first()
    )

    if existing:
        # UPDATE existing
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
        # INSERT new
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
```

---

## Data Relationships

```
Repository
    ↓ (repo_id)
Contributor  ← Email uniqueness ensures no duplicates
    ↓ (contributor_id)
├─ Commits (author_id)
├─ PullRequests (author_id)
├─ PRReviews (reviewer_id)
└─ PRComments (author_id)
    ↓
ContributorMetric (aggregation point)
    ├─ Period: [period_start, period_end)
    ├─ Metrics: counts, lines, quality
    └─ Time-series: Multiple records per contributor (one per month)
```

---

## Test Failure Analysis

### What the Test Expects

**File**: [tests/contract/integration/test_contributor_metrics_e2e.py](tests/contract/integration/test_contributor_metrics_e2e.py)

1. **Extract a repository** using `GitHubAnalysisWorkflow`
2. **Automatically calculates metrics** during extraction (called in `_process_repository()`)
3. **Verify**:
   - Contributors exist in database
   - ContributorMetric records exist (if commits in current month)
   - Metrics have correct structure (period_start, repo_id, contributor_id, counts)

### Common Failure Modes

| Failure                     | Cause                                  | Fix                                                            |
| --------------------------- | -------------------------------------- | -------------------------------------------------------------- |
| **No metrics found**        | No commits in current month (Jan 2026) | ✅ Already handled - test accepts empty metrics                |
| **FK constraint error**     | Contributor not found                  | Check: `get_or_create_contributor()` called with correct email |
| **Session not committed**   | Changes not persisted                  | Ensure `session_scope()` used or `.commit()` called            |
| **Query returns None**      | Filter conditions wrong                | Check period_start/period_end boundaries                       |
| **Score calculation hangs** | Large batch of unscored commits        | Already optimized - only processes 500 at a time               |

---

## Summary: The Complete Flow

```
User calls: workflow.run()
    ↓
For each repository:
    ├─ Extract commits → store_commit() → creates Contributor
    ├─ Extract PRs → store_pull_request() → references Contributor
    ├─ Extract PR reviews
    └─ _process_contributor_metrics()
         ↓
         Has commits in current month?
         ├─ NO  → Skip (log message)
         └─ YES → Calculate & Store
              ├─ update_commit_message_scores()
              ├─ calculate_contributor_metrics() → List[ContributorStats]
              └─ store_contributor_metrics() → ContributorMetric records
                    ↓
                    Database updated ✓
```

---

## Files to Read (In Order)

1. **Start here**: `tests/contract/integration/test_contributor_metrics_e2e.py` (test expectations)
2. **Then**: `src/workflows/github_analysis.py:381-433` (workflow integration)
3. **Then**: `src/analyzers/contributor_analyzer.py:603-650` (orchestration)
4. **Deep dive**: `src/analyzers/contributor_analyzer.py:268-510` (calculation engine)
5. **Reference**: `database/schema.sql` (data model)
