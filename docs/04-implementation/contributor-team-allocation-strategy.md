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

**Location**: Enhanced extraction workflow (`src/workflows/github_analysis.py`)

**Workflow step** (insert after `store_repository`):

1. Extract `teamname` from `repository_metadata` 
2. If `teamname` exists → lookup or create that team; set `is_unallocated=False`
3. If no `teamname` → use "Unallocated" fallback team; set `is_unallocated=True`
4. For each contributor discovered → call `allocate_contributor_to_team()` with team ID, source="scan", and unallocated flag

See workflow source file for complete implementation details and error handling.

---

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

Supports batch operations for moving multiple contributors in one command. Use when reassigning entire repository's contributors to a newly identified team.

See script implementation for full function signatures and examples.

---

## Data Model Extensions

### New Table: `contributor_migration_audit`

Tracks migration history: who moved which contributor, when, and why. Used to maintain complete audit trail of team assignments.

Key fields: contributor_id, from_team_id, to_team_id, reason, migrated_at. Full schema in database migration files.

### Enhanced: `team_contributors` Table

Add metadata fields: `source` (scan/api/manual), `is_unallocated` (bool), `allocated_at` (timestamp).

---

## Service Module: `src/database/team_allocation.py`

Centralized functions for team allocation operations:
- `get_unallocated_team()` - Returns/creates system-wide unallocated team
- `allocate_contributor_to_team()` - Allocates contributor with metadata
- `get_team_by_name()` - Team lookup by name
- `get_or_create_team_by_name()` - Creates team if needed
- `recalculate_team_metrics()` - Updates aggregated metrics after allocation change

All functions already created in PR #15; see source file for signatures.

---

## Workflow Integration Details

### Updated Workflow: `src/workflows/github_analysis.py`

**Add allocation step after `store_repository()`**: Extract teamname from repository metadata, look up/create team, then allocate all contributors to that team. If no teamname, use fallback "Unallocated" team.

**Helper function added to workflow**: `_allocate_contributors_to_team()` handles the logic. See workflow source file for complete implementation.

---

## Script Capabilities Summary

The migration script supports comprehensive operations:

| Capability               | Operation                         |
| ------------------------ | --------------------------------- |
| **Create Team Manually** | Add new teams before migration    |
| **Migrate by IDs**       | Fast lookup using numeric IDs     |
| **Migrate by Names**     | Human-friendly name-based lookup  |
| **Auto-Create Team**     | Create target team if missing     |
| **Name Lookup**          | Flexible matching (exact/email/partial) |
| **Dry-Run Preview**      | Validate before executing         |
| **Audit Trail**          | Complete migration history        |
| **Metric Recalculation** | Auto-update team metrics          |

---

## Testing Strategy

**Unit Tests** (`tests/unit/database/test_team_allocation.py`):
- `test_get_unallocated_team_creates_if_missing()`
- `test_allocate_contributor_to_team()`
- `test_get_or_create_team_by_name()`
- `test_recalculate_team_metrics()`

**Integration Tests** (`tests/contract/integration/test_contributor_team_allocation.py`):
- `test_scan_with_repository_json_allocates_to_named_team()`
- `test_scan_without_repository_json_allocates_to_unallocated()`
- `test_migrate_contributor_between_teams()`
- `test_bulk_migrate_unallocated_contributors()`
- `test_team_metrics_recalculated_after_migration()`
- `test_audit_log_tracks_migrations()`

---

## Implementation Phases

| Phase | Component                                  | Status               |
| ----- | ------------------------------------------ | -------------------- |
| **1** | Create "Unallocated" team                  | ✅ Done (manual SQL) |
| **2** | Extend `team_allocation.py` service        | ⏳ Implement         |
| **3** | Update workflow integration                | ⏳ Implement         |
| **4** | Create `contributor_migration_audit` table | ⏳ Implement         |
| **5** | Implement migration script                 | ⏳ Implement         |
| **6** | Add bulk migration utility                 | ⏳ Implement         |
| **7** | Write tests                                | ⏳ Implement         |
| **8** | Update requirements-status.md              | ⏳ Implement         |

---

## Benefits of This Approach

**Simple & Deterministic**: No inference, clear rules (teamname → team, no teamname → Unallocated)

**Complete Audit Trail**: Track where each allocation came from, who moved contributors, when, and why

**Respects Boundaries**: Extractors isolated, database layer centralized, workflows orchestrate, scripts are utilities

**Backward Compatible**: All changes are additive, existing data unaffected, gradual adoption

**Flexible & Operator-Driven**: Scan completes automatically, operators control reallocation timing

**No Configuration**: Uses existing `repository.json`, implicit fallback team

---

## Risks & Mitigation

| Risk                                | Mitigation                                        |
| ----------------------------------- | ------------------------------------------------- |
| Unallocated team grows slowly       | Quarterly review; dashboard shows unallocated count |
| Wrong metadata in repository.json   | Validate against known teams; log warnings       |
| Slow metric recalculation          | Batch recalculation; run during off-hours        |
| Contributor in multiple teams      | Soft-delete with effective_end_date              |

---

## References

- **FR-13.2**: Many-to-many contributor-team relationships
- **FR-13.3**: Effective date tracking for team membership
- **Existing Pattern**: `src/database/team_analytics.py`
- **Architecture Boundaries**: `agents/02a-architecture-guardian.md`
- **Approved Stack**: Python 3.12, SQLAlchemy, PostgreSQL
