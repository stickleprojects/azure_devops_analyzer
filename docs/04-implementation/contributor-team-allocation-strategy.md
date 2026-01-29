# Contributor-to-Team Allocation Strategy

## Overview

This document outlines the architecture for allocating contributors to teams during analysis scans (FR-13.2, FR-13.3). Contributors are discovered during extraction, and we need mechanisms to associate them with teams at that point in the workflow.

## Constraint Analysis

**Key Constraint**: Contributors are only discovered during analysis scans; we cannot pre-assign them to teams before extraction begins.

**Solution Approach**: Two-phase allocation

- **Phase 1 (Scan-time)**: Automatic allocation from `repository.json` or to fallback team
- **Phase 2 (Post-analysis)**: Manual reallocation using provided script

## Approved Technologies & Patterns

### Technology Stack (Already Approved)

| Layer                          | Technology                                        | Rationale                                    |
| ------------------------------ | ------------------------------------------------- | -------------------------------------------- |
| **Metadata Source**            | `repository.json` (existing Azure DevOps pattern) | Already in use for `teamname`, `servicename` |
| **Workflow Orchestration**     | Python workflows + Celery tasks                   | Existing architecture                        |
| **Database**                   | SQLAlchemy ORM + PostgreSQL (TimescaleDB)         | Existing stack                               |
| **Post-Analysis Reallocation** | Python script (standalone utility)                | Follows existing script patterns             |

### Architectural Boundaries (No Violations)

✅ **Extractors** remain platform-isolated (no cross-platform logic, no DB writes)  
✅ **Database layer** remains single point for DB operations  
✅ **Workflows** orchestrate the allocation process  
✅ **Team management** lives in new `team_allocation` service module

---

## Architecture Guardian Validation

### Guardian Checklist

✅ **Extractor Boundary**: No changes to extractor logic

- Extractors remain platform-isolated
- No analysis logic added to extractors
- Allocation happens in workflow layer (post-extraction)

✅ **Database Layer**: All DB operations centralized

- New tables defined in schema migrations
- All operations through SQLAlchemy ORM
- No direct SQL in business logic
- Service module abstracts complexity

✅ **Workflow Orchestration**: Workflows remain pure orchestration

- `team_allocation.py` is service module in `src/database/` (not a workflow)
- Workflows call service functions, don't implement logic
- No business logic in workflow files

✅ **Service Layer**: New module respects boundaries

- `team_allocation.py` belongs to database layer
- Provides abstractions for team operations (get_or_create, allocate, etc.)
- No platform-specific or analyzer logic

✅ **Cross-Cutting Concerns**: Audit trail is consistent

- Audit table follows existing temporal patterns (effective_date, UTC timestamps)
- Soft-delete pattern matches team_contributors design
- Maintains data consistency across related tables

**Guardian Status**: ✅ APPROVED - No architectural violations detected  
**Violation Count**: 0  
**Reference**: `agents/02a-architecture-guardian.md`

---

## Proposed Solution: Two-Stage Allocation Strategy

**During extraction workflow**:

```
For each repository:
  ├─ Extract repository.json (if exists)
  ├─ Extract teamname field
  └─ If teamname found:
       └─ Allocate all contributors to that team

For each contributor without team:
  └─ Allocate to "Unallocated" team (fallback)
        ↓
    [team_contributors table]
        ↓

Post-Analysis Phase (Manual Reallocation)
├─ Identify unallocated/misallocated contributors
├─ Run migration script to move to correct team
└─ Update all affected fields/tables
        ↓
    [team_contributors updated, metrics recalculated]
```

### Layer 1: Repository Metadata Discovery

**File**: `repository.json` (already supported by extractors)

**Standard Format**:

```json
{
  "teamname": "backend-platform",
  "servicename": "api-gateway"
}
```

**Behavior During Scan**:

- Extract `teamname` field from `repository.json` (if present)
- Look up or create team by name in database
- Allocate all contributors from this repository to that team
- If `repository.json` missing → proceed to Layer 2

**Approved Pattern**: Metadata-driven discovery (deterministic, no inference)

---

### Layer 2: Unallocated Team Fallback

**Purpose**: Provide safe landing zone for contributors when `repository.json` is absent

**Behavior**:

- Create system-wide "Unallocated" team (one-time setup)
- Any contributor from a repository without `teamname` gets assigned here
- Clear audit trail: operators know exactly which contributors need reassignment
- No data loss, no silent failures

**Setup** (one-time initialization):

```sql
-- Create unallocated team if it doesn't exist
INSERT INTO teams (name, description, organization_id, created_at)
SELECT 'Unallocated', 'Contributors awaiting manual team assignment', NULL, NOW()
WHERE NOT EXISTS (SELECT 1 FROM teams WHERE name = 'Unallocated');
```

**Advantages**:

- ✅ Simple, deterministic behavior (no guessing)
- ✅ Complete contributor discovery (nothing gets lost)
- ✅ Explicit workflow for operators
- ✅ Auditability: clear which contributors need attention
- ✅ No configuration needed

**Approved Pattern**: Explicit fallback team (no code changes between organizations)

---

### Layer 3: Workflow Integration

**Location**: Enhanced extraction workflow

**Workflow step** (insert after `store_repository`):

```python
# Get teamname from repository.json (already extracted by extractor)
repo_team_name = repository_metadata.get('teamname')

# Determine target team
if repo_team_name:
    # Explicit team from repository.json
    target_team = get_or_create_team_by_name(session, repo_team_name)
else:
    # Fallback to unallocated team
    target_team = get_unallocated_team(session)

# For each contributor discovered in this repository
for contributor_data in contributors:
    contributor = store_contributor(session, contributor_data)
    allocate_contributor_to_team(
        session,
        team_id=target_team.team_id,
        contributor_id=contributor.id,
        source="scan",
        is_unallocated=(not repo_team_name)
    )
```

**Data captured**:

```python
class TeamContributor(Base):
    # ... existing fields ...
    source: str  # "scan", "api", "manual"
    is_unallocated: bool = False  # True if assigned to unallocated team
    allocated_at: datetime  # When assignment happened
```

---

### Layer 4: Post-Analysis Reallocation

### Layer 4: Post-Analysis Reallocation

**After extraction completes**, operators can reassign contributors to correct teams using a script.

#### Layer 4.1: Contributor Migration Script

**Location**: `scripts/migrate_contributor_to_team.py`

**Purpose**: Comprehensive script for managing teams and contributor allocations post-analysis, supporting:

1. **Create new teams manually** - Add teams without running a full scan
2. **Create teams on-the-fly** - Create target team during migration if it doesn't exist
3. **Migrate contributors by name** - Friendly names instead of numeric IDs
4. **Migrate contributors by ID** - Fast direct migration when IDs known
5. **Update affected data** - Automatically recalculates metrics and maintains audit trail

**Affected Tables & Fields**:

1. `teams` - Create new teams (when needed)
2. `team_contributors` - Update team_id, effective_end_date on old, create new record
3. `team_metrics` - Recalculate metrics for affected teams/periods
4. `contributor_migration_audit` - Log all migrations with reason and timestamp

**Usage**:

```bash
# Move single contributor
python scripts/migrate_contributor_to_team.py \
  --contributor-id 42 \
  --from-team-id 1 \
  --to-team-id 5 \
  --effective-date 2026-01-29

# Bulk move (all unallocated contributors from a repo to a team)
python scripts/migrate_contributor_to_team.py \
  --from-team-name "Unallocated" \
  --to-team-name "backend-platform" \
  --repository-id 10 \
  --dry-run  # Preview changes first

# Move all contributors from old team to new team
python scripts/migrate_contributor_to_team.py \
  --from-team-id 1 \
  --to-team-id 5 \
  --reason "Team restructuring - legacy team dissolved"
```

#### Layer 4.2: Script Location & Core Functions

**Location**: `scripts/migrate_contributor_to_team.py`

**Core Capabilities** (see script file for complete implementations):

1. **`create_team(session, team_name, description, organization_id)`**
   - Creates new team or raises ValueError if already exists
   - Called before migrations if auto-create needed

2. **`get_contributor_by_name(session, contributor_name)`**
   - Flexible lookup: exact name → email → partial match (case-insensitive)
   - Raises ValueError if multiple partial matches found
   - Returns Contributor object or None

3. **`migrate_contributor(...)`**
   - Supports flexible parameters: ID or name lookups for contributor/teams
   - Creates target team on-the-fly if `create_team_if_missing=True`
   - Performs soft-delete on old relationship, creates new one
   - Recalculates team metrics for ±30 days around migration
   - Creates audit log entry with reason

4. **`get_or_create_team(session, team_name)`**
   - Helper: returns existing team or creates if missing

**Data Handled**:

- Updates `team_contributors`: sets `effective_end_date` on old record, creates new
- Updates `team_metrics`: recalculates for affected teams/periods
- Creates `contributor_migration_audit`: logs migration with reason

**See implementation**: [scripts/migrate_contributor_to_team.py](../../../scripts/migrate_contributor_to_team.py)

````

#### Layer 4.3: Bulk Migration for Unallocated Contributors

**Script: `scripts/process_unallocated_contributors.py`**

```python
def bulk_move_unallocated_to_team(
    session: Session,
    from_repository_id: int,
    to_team_name: str,
    dry_run: bool = True,
) -> dict:
    """
    Move all unallocated contributors from a repository to a team.

    Use case: After analyzing which repo belongs to which team,
    move all contributors in batch rather than one-by-one.

    Returns:
        Summary of moved contributors and metrics recalculated
    """
````

---

## Data Model Extensions

### New Table: `contributor_migration_audit`

Tracks who moved which contributor, when, and why.

```sql
CREATE TABLE contributor_migration_audit (
    id SERIAL PRIMARY KEY,
    contributor_id INT NOT NULL REFERENCES contributors(id),
    from_team_id INT NOT NULL REFERENCES teams(team_id),
    to_team_id INT NOT NULL REFERENCES teams(team_id),
    effective_date TIMESTAMPTZ NOT NULL,
    reason TEXT,  -- Why the migration happened
    migrated_by VARCHAR(255),  -- Script, API, or user
    migrated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),

    FOREIGN KEY (contributor_id) REFERENCES contributors(id) ON DELETE CASCADE,
    FOREIGN KEY (from_team_id) REFERENCES teams(team_id) ON DELETE RESTRICT,
    FOREIGN KEY (to_team_id) REFERENCES teams(team_id) ON DELETE RESTRICT,

    CONSTRAINT audit_valid_teams CHECK (from_team_id != to_team_id)
);

CREATE INDEX idx_contributor_migration_contributor
    ON contributor_migration_audit(contributor_id);
CREATE INDEX idx_contributor_migration_teams
    ON contributor_migration_audit(from_team_id, to_team_id);
CREATE INDEX idx_contributor_migration_date
    ON contributor_migration_audit(migrated_at DESC);
```

### Enhanced: `team_contributors` Table

Add metadata fields:

```sql
ALTER TABLE team_contributors ADD COLUMN IF NOT EXISTS
    source VARCHAR(50) DEFAULT 'scan',  -- "scan", "api", "manual"
    is_unallocated BOOLEAN DEFAULT FALSE,
    allocated_at TIMESTAMPTZ DEFAULT NOW();
```

---

## Service Module: `src/database/team_allocation.py`

Centralized functions for team allocation (already created in PR #15, extended here):

```python
def get_unallocated_team(session: Session) -> Team:
    """Get or create the system-wide unallocated team."""

def allocate_contributor_to_team(
    session: Session,
    team_id: int,
    contributor_id: int,
    source: str = "scan",
    is_unallocated: bool = False,
) -> TeamContributor:
    """Allocate contributor to team with metadata."""

def get_team_by_name(session: Session, team_name: str) -> Optional[Team]:
    """Look up team by name."""

def get_or_create_team_by_name(
    session: Session,
    team_name: str,
) -> Team:
    """Create team if doesn't exist, return team."""

def recalculate_team_metrics(
    session: Session,
    team_id: int,
    period_start: datetime,
) -> TeamMetric:
    """Recalculate aggregated metrics for a team for a specific period."""
```

---

## Workflow Integration Details

### Updated Workflow: `src/workflows/github_analysis.py`

**Add this after `store_repository()` call**:

```python
def _allocate_contributors_to_team(
    self,
    session: Session,
    org_data,
    repo_data,
    repository_record,
    contributors: List[ContributorData],
):
    """
    Allocate contributors to team based on repository metadata.

    Strategy:
    1. Get teamname from repository.json (if present)
    2. Look up or create team in database
    3. Allocate all contributors to that team
    4. If no teamname, allocate to "Unallocated" team
    """

    # Get teamname from repository metadata (extracted by extractor)
    repo_team_name = repository_record.get_metadata('teamname')

    if repo_team_name:
        # Explicit team assignment
        target_team = get_or_create_team_by_name(session, repo_team_name)
        is_unallocated = False
        logger.info(f"  Contributors → team: {repo_team_name}")
    else:
        # Fallback to unallocated
        target_team = get_unallocated_team(session)
        is_unallocated = True
        logger.info(f"  Contributors → team: Unallocated")

    # Allocate all contributors in batch
    for contributor_data in contributors:
        allocate_contributor_to_team(
            session,
            team_id=target_team.team_id,
            contributor_id=contributor_data.id,
            source="scan",
            is_unallocated=is_unallocated,
        )
```

---

## Script CLI Reference

**File**: `scripts/migrate_contributor_to_team.py`

See the script file for complete CLI documentation and all supported options. Key workflows:

**Workflow 1: Migrate single contributor** (using friendly names):

```bash
python scripts/migrate_contributor_to_team.py \
  --contributor-name "John Smith" \
  --from-team-name "Unallocated" \
  --to-team-name "backend-platform" \
  --reason "Assigned to backend team"
```

**Workflow 2: Create team and migrate (auto-create if missing)**:

```bash
python scripts/migrate_contributor_to_team.py \
  --contributor-name "Jane Doe" \
  --from-team-name "Unallocated" \
  --to-team-name "new-platform-team" \
  --create-team-if-missing \
  --reason "New team created"
```

**Workflow 3: Preview before executing (dry-run)**:

```bash
python scripts/migrate_contributor_to_team.py \
  --contributor-name "John Smith" \
  --from-team-name "Unallocated" \
  --to-team-name "backend-platform" \
  --dry-run
```

For programmatic usage and full documentation, see [scripts/migrate_contributor_to_team.py](../../../scripts/migrate_contributor_to_team.py).

---

## Implementation Phases

| Phase | Component                                  | Status               | Notes                                         |
| ----- | ------------------------------------------ | -------------------- | --------------------------------------------- |
| **1** | Create "Unallocated" team                  | ✅ Done (manual SQL) | One-time setup                                |
| **2** | Extend `team_allocation.py` service        | ⏳ Implement         | Add `get_unallocated_team()`                  |
| **3** | Update workflow integration                | ⏳ Implement         | Add allocation step after repo store          |
| **4** | Create `contributor_migration_audit` table | ⏳ Implement         | New migration file                            |
| **5** | Implement migration script                 | ⏳ Implement         | `scripts/migrate_contributor_to_team.py`      |
| **6** | Add bulk migration utility                 | ⏳ Implement         | `scripts/process_unallocated_contributors.py` |
| **7** | Write tests                                | ⏳ Implement         | Unit + integration tests                      |
| **8** | Update requirements-status.md              | ⏳ Implement         | Mark FR-13.2, FR-13.3 complete                |

---

## Testing Strategy

### Unit Tests

**File**: `tests/unit/database/test_team_allocation.py`

```python
def test_get_unallocated_team_creates_if_missing():
    """Unallocated team auto-created on first call."""

def test_allocate_contributor_to_team():
    """Contributor successfully allocated."""

def test_get_or_create_team_by_name():
    """Team created if doesn't exist."""

def test_recalculate_team_metrics():
    """Metrics recalculated after allocation change."""
```

### Integration Tests

**File**: `tests/contract/integration/test_contributor_team_allocation.py`

```python
def test_scan_with_repository_json_allocates_to_named_team():
    """Contributors from repo with teamname allocated to that team."""

def test_scan_without_repository_json_allocates_to_unallocated():
    """Contributors from repo without teamname go to Unallocated."""

def test_migrate_contributor_between_teams():
    """migrate_contributor() correctly updates all affected records."""

def test_bulk_migrate_unallocated_contributors():
    """Bulk move of unallocated contributors to team."""

def test_team_metrics_recalculated_after_migration():
    """TeamMetric records updated after contributor moves."""

def test_audit_log_tracks_migrations():
    """Migration audit trail created with reason."""
```

### Docker-Based Contract Tests

Use existing test infrastructure with mocked data.

---

## Configuration

No configuration file needed! The system uses:

- ✅ `repository.json` for metadata (already present in repos)
- ✅ "Unallocated" team (created once at setup)
- ✅ Migration scripts (run on-demand by operators)

---

## Usage Examples

### During Scan (Automatic)

```bash
# Scan runs normally
python scripts/run_extraction.py --org "myorg" --platform github

# Contributions allocated:
# - Repos WITH repository.json → named team
# - Repos WITHOUT repository.json → Unallocated team
```

---

## Usage Examples

### During Scan (Automatic)

Contributors are allocated automatically based on `repository.json`:

- Repos **with** `teamname` field → contributors assigned to that team
- Repos **without** `teamname` field → contributors assigned to "Unallocated" team

```bash
python scripts/run_extraction.py --org "myorg" --platform github
# Automatically allocates all discovered contributors
```

### Post-Scan (Manual Reallocation)

See [Script CLI Reference](#script-cli-reference) above for common workflows.

For complete programmatic usage, see test files: [tests/contract/integration/test_contributor_team_allocation.py](../../../tests/contract/integration/test_contributor_team_allocation.py)

---

## Script Capabilities Summary

The migration script supports comprehensive operations for managing teams and contributors:

| Capability               | Operation                         | Details                                               |
| ------------------------ | --------------------------------- | ----------------------------------------------------- |
| **Create Team Manually** | Create new teams before migration | Supports team metadata (name, description)            |
| **Migrate by IDs**       | Fast lookup using numeric IDs     | Use when IDs are known                                |
| **Migrate by Names**     | Human-friendly name-based lookup  | Recommended for operators (auto-resolves names)       |
| **Auto-Create Team**     | Create target team if missing     | Creates team on-the-fly during migration              |
| **Name Lookup**          | Flexible name matching            | Exact name → email → partial match (case-insensitive) |
| **Dry-Run Preview**      | Preview changes before executing  | Validates migration path without making changes       |
| **Audit Trail**          | Complete migration history        | Logs contributor, teams, timestamp, reason            |
| **Metric Recalculation** | Auto-update affected team metrics | Automatic for ±30 days around migration date          |

---

## Benefits of This Approach

### 1. **Simple and Deterministic**

- No inference, no guessing
- Clear rules: teamname → named team, no teamname → Unallocated
- Same behavior across all organizations

### 2. **Audit Trail**

- Track where each allocation came from (scan vs. script)
- Audit log shows who moved contributor and why
- Complete migration history

### 3. **Respects Boundaries**

- Extractors remain isolated
- Database layer handles all storage
- Workflows orchestrate allocation step
- Scripts are standalone utilities

### 4. **Backward Compatible**

- New tables/fields are additive
- Existing contributor data unchanged
- Gradual adoption: scan, then reallocate as needed

### 5. **Flexible**

- Scan completes without manual intervention
- Reallocation happens post-analysis via script
- Operators control the pace and timing
- Bulk operations supported

### 6. **No Configuration Needed**

- Uses existing `repository.json` format
- Unallocated team is implicit fallback
- Script has built-in help and dry-run

---

## Risks & Mitigation

| Risk                                          | Impact                                 | Mitigation                                          |
| --------------------------------------------- | -------------------------------------- | --------------------------------------------------- |
| **Slow growth of Unallocated team**           | Eventually hard to track               | Quarterly review; dashboard shows unallocated count |
| **Wrong metadata in repository.json**         | Misallocation                          | Validate teamname against known teams; log warnings |
| **Performance of metric recalc**              | Migration script slow for many changes | Batch recalculation; run during off-hours           |
| **Contributor in multiple teams temporarily** | Confusing metrics                      | Soft-delete old record with effective_end_date      |

---

## Next Steps (If Approved)

1. ✅ Approve this simplified approach
2. Create "Unallocated" team via SQL
3. Extend `team_allocation.py` with new functions
4. Add allocation step to workflow
5. Create migration script and audit table
6. Write comprehensive tests
7. Update requirements-status.md
8. Commit to feat/team-management branch

---

## References

- **FR-13.2**: Many-to-many contributor-team relationships
- **FR-13.3**: Effective date tracking for team membership
- **Existing Pattern**: `src/database/team_analytics.py`
- **Architecture Boundaries**: `agents/02a-architecture-guardian.md`
- **Approved Stack**: Python 3.12, SQLAlchemy, PostgreSQL
