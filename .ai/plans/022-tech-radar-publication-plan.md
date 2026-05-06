# Plan 022: Thoughtworks Tech Radar Publication (FR-6)

## Status: IMPLEMENTED ✅

Merged in [PR #74](https://github.com/stickleprojects/azure_devops_analyzer/pull/74) (`db5ffd6`, 2026-04-26). Verified 2026-05-03: all contract/unit tests pass (53 passed; 4 hypothesis property-based tests skipped because `hypothesis` is not installed in the test image — see `tests/unit/test_radar_categorizer.py::TestCategorizationPropertyBased`).

**Implements**: FR-6.1, FR-6.2, FR-6.3, FR-6.4, FR-6.5, FR-6.6, FR-6.7

## Problem

Tech Radar is a high-visibility artifact for communicating technology strategy. Today:
- No radar generation exists
- No categorization logic (Adopt/Trial/Assess/Hold)
- No history of technology movement/changes
- No export/sharing API
- No metadata context (why did a tech move rings? when did exposure occur?)

FR-6.1–6.7 require: schema for radar state + history, categorization engine, API endpoint, and optional UI viewer.

---

## Design Principles

1. **Thought Works Spec**: JSON format must validate against [TW Radar schema](https://github.com/thoughtworks/build-your-own-radar)
2. **Versioned History**: Each publication is a snapshot; history tracked for timeline view
3. **Metadata Rich**: Each blip includes adoption date, CVE status, EOL impact
4. **Decoupled from Dashboards**: Radar is independent from Plan 021; can be implemented in parallel
5. **Flexible Categorization**: Rules can be customized; default rules provided

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Input: packages + repository_dependencies (Plan 012 schema) │
└────────────────────────┬────────────────────────────────────┘
                         │
                    (daily job)
                         │
        ┌────────────────┴────────────────┐
        │                                 │
    TRACK A                           TRACK B
    ────────                           ──────────
    Schema +                           Categorization
    Storage                            Engine
    (DB)                               (Python)
    │                                 │
    │ radar_publications              categorize_tech()
    │ radar_blips                     ranking_rules.json
    │ radar_blip_history              adoption_metrics.py
    │                                 │
    └────────────────┬────────────────┘
                     │
                  TRACK C
                  ───────────
                  API + Export
                  /api/radar
                  /api/radar/history
                  /api/radar/export
                  │
                  └─→ Optional UI (link to viewer)
```

---

## Part A — Schema and Storage

### File: `database/migrations/018_tech_radar_schema.sql`

Three new tables:

#### `radar_publications`

Published radar snapshots:

```sql
CREATE TABLE radar_publications (
    id SERIAL PRIMARY KEY,
    publication_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    publication_version VARCHAR(50),  -- e.g., "v1.2", "2026-04-26"
    description TEXT,
    published_by VARCHAR(255),  -- user/CI system that published
    is_latest BOOLEAN DEFAULT TRUE,  -- flag for "current" radar
    metadata JSONB,  -- arbitrary context
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_radar_pub_latest ON radar_publications(is_latest) WHERE is_latest = TRUE;
CREATE INDEX idx_radar_pub_date ON radar_publications(publication_date DESC);
```

#### `radar_blips`

Individual technology entries (linked to publication):

```sql
CREATE TABLE radar_blips (
    id SERIAL PRIMARY KEY,
    publication_id INTEGER NOT NULL REFERENCES radar_publications(id) ON DELETE CASCADE,
    package_name VARCHAR(500) NOT NULL,
    ecosystem VARCHAR(100) NOT NULL,
    ring VARCHAR(50) NOT NULL,  -- 'Adopt', 'Trial', 'Assess', 'Hold'
    quadrant VARCHAR(50) NOT NULL,  -- 'Infrastructure', 'Platforms', 'Tools', 'Languages & Frameworks'
    label TEXT,  -- friendly name
    description TEXT,  -- TW rationale
    is_new BOOLEAN DEFAULT FALSE,  -- first appearance
    is_moved BOOLEAN DEFAULT FALSE,  -- moved rings this cycle
    adopted_date DATE,  -- when we first started using
    repo_count INTEGER,  -- repos using
    exposed_to_cves INTEGER DEFAULT 0,  -- repos with known vulnerable versions
    is_eol BOOLEAN DEFAULT FALSE,
    eol_date DATE,
    latest_version VARCHAR(100),
    flags JSONB,  -- custom metadata (rationale, risk level, etc.)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_blip_pub ON radar_blips(publication_id);
CREATE INDEX idx_blip_name_eco ON radar_blips(package_name, ecosystem);
CREATE INDEX idx_blip_ring ON radar_blips(ring);
```

#### `radar_blip_history`

Movement history (timeline view):

```sql
CREATE TABLE radar_blip_history (
    id SERIAL PRIMARY KEY,
    package_name VARCHAR(500) NOT NULL,
    ecosystem VARCHAR(100) NOT NULL,
    publication_date DATE NOT NULL,
    prior_ring VARCHAR(50),  -- where it was before
    current_ring VARCHAR(50) NOT NULL,  -- where it is now
    repo_count_delta INTEGER,  -- +3 repos started using, -1 stopped
    vulnerability_change TEXT,  -- "now_exposed" | "fixed" | "unchanged"
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_blip_hist_name ON radar_blip_history(package_name, ecosystem);
CREATE INDEX idx_blip_hist_date ON radar_blip_history(publication_date DESC);
```

---

## Part B — Categorization Engine

### File: `src/analyzers/radar_categorization.py` (new)

Engine to categorize packages into rings:

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional

class Ring(Enum):
    ADOPT = "Adopt"
    TRIAL = "Trial"
    ASSESS = "Assess"
    HOLD = "Hold"

class Quadrant(Enum):
    INFRASTRUCTURE = "Infrastructure"
    PLATFORMS = "Platforms"
    TOOLS = "Tools"
    LANGUAGES = "Languages & Frameworks"

@dataclass
class RadarBlip:
    package_name: str
    ecosystem: str
    ring: Ring
    quadrant: Quadrant
    label: str
    description: str
    repo_count: int
    is_new: bool
    is_moved: bool
    adopted_date: Optional[date]
    exposed_to_cves: int
    is_eol: bool
    eol_date: Optional[date]
    flags: dict

class RadarCategorizer:
    """
    Categorizes packages into Adopt/Trial/Assess/Hold rings based on:
    1. Adoption metrics (repo_count, time_in_use)
    2. Health metrics (CVE exposure, EOL status)
    3. Category mapping (language → Languages, docker → Infrastructure)
    4. Custom rules (loaded from JSON config)
    """
    
    def categorize(self, package_name: str, ecosystem: str, metrics: dict) -> RadarBlip:
        """
        Given package metrics, return categorization.
        
        Metrics dict includes:
          - repo_count: usage breadth
          - time_in_use: adoption duration
          - exposed_cves: vulnerability exposure
          - is_eol: end-of-life status
          - category: detected category (language, framework, tool, db)
        """
        
    def _ring_from_adoption(self, repo_count: int, time_in_use_days: int) -> Ring:
        """
        Default logic: Adopt (25+ repos, 6+ months), Trial (5-25 repos, 3+ months),
        Assess (2-5 repos), Hold (1 repo or deprecated).
        """
```

### File: `src/analyzers/radar_categorization_config.json` (new)

Customizable rules for ring classification:

```json
{
  "ring_rules": {
    "adopt": {
      "min_repo_count": 25,
      "min_time_in_use_days": 180,
      "conditions": "all"
    },
    "trial": {
      "min_repo_count": 5,
      "min_time_in_use_days": 90,
      "conditions": "all"
    },
    "assess": {
      "min_repo_count": 2,
      "conditions": "all"
    },
    "hold": {
      "description": "Single-use, deprecated, or high-risk"
    }
  },
  "quadrant_mapping": {
    "language": "Languages & Frameworks",
    "framework": "Languages & Frameworks",
    "database": "Platforms",
    "infrastructure": "Infrastructure",
    "docker": "Infrastructure",
    "ci_cd": "Tools",
    "build_tool": "Tools"
  },
  "exclusions": [
    "test-package-*",
    "internal-*"
  ]
}
```

### File: `src/workflows/radar_publication.py` (new)

Orchestration to generate and publish radar:

```python
class RadarPublicationWorkflow:
    def run(self, description: str = None, published_by: str = "automated"):
        """
        1. Query packages + repository_dependencies + vulnerabilities
        2. Categorize each package (via RadarCategorizer)
        3. Detect movements (compare to prior publication)
        4. Store blips + history
        5. Mark new publication as latest
        """
        
    def _load_prior_blips(self) -> dict:
        """Latest radar blips, keyed by (package_name, ecosystem)."""
        
    def _detect_movements(self, prior: dict, current: dict) -> dict:
        """Compare prior and current rings, repo deltas."""
        
    def _store_publication(self, blips: list[RadarBlip], history: list[dict]):
        """Insert radar_publications + radar_blips + radar_blip_history."""
```

---

## Part C — API and Export

### File: `src/api/rescan.py` (additions)

#### `GET /api/radar`

Current radar in Thoughtworks format:

```python
@app.route("/api/radar", methods=["GET"])
def get_radar():
    """
    Returns latest publication in TW Radar schema.
    https://github.com/thoughtworks/build-your-own-radar/blob/master/doc/data_format.md
    
    JSON structure:
    {
      "documentTitle": "Organization Tech Radar",
      "quadrants": [
        { "name": "Infrastructure", ... },
        { "name": "Platforms", ... },
        { "name": "Tools", ... },
        { "name": "Languages & Frameworks", ... }
      ],
      "rings": [
        { "name": "Adopt", "color": "#00AA00" },
        { "name": "Trial", "color": "#00FFFF" },
        { "name": "Assess", "color": "#FFFF00" },
        { "name": "Hold", "color": "#FF0000" }
      ],
      "entries": [
        {
          "id": 1,
          "label": "lodash",
          "description": "Used in 45 repos; stable and well-maintained.",
          "quadrant": "Languages & Frameworks",
          "ring": "Adopt",
          "isNew": false,
          "isMoved": false
        },
        ...
      ]
    }
    """
```

#### `GET /api/radar/history`

Timeline of technology movements:

```python
@app.route("/api/radar/history", methods=["GET"])
def radar_history():
    """
    ?package_name=lodash → movement history for one package
    ?limit=100 → last N publication dates
    
    Returns:
    {
      "timeline": [
        {
          "publication_date": "2026-04-26",
          "package_name": "lodash",
          "prior_ring": "Trial",
          "current_ring": "Adopt",
          "repo_count_delta": 5,
          "vulnerability_change": "unchanged"
        },
        ...
      ]
    }
    """
```

#### `GET /api/radar/export`

Export formats for external sharing:

```python
@app.route("/api/radar/export", methods=["GET"])
def export_radar():
    """
    ?format=json (TW format, default)
    ?format=csv (tabular download)
    ?format=html (static viewer HTML)
    ?date=2026-04-26 (historical snapshot)
    
    Content-Disposition: attachment; filename=radar-2026-04-26.json
    """
```

### Viewer UI — superseded by Plan 025

A standalone `src/api/radar_viewer.html` is **no longer planned**. With Plan 025 introducing a React app at `web/admin-ui/`, the radar viewer becomes a route in that app (Plan 025 Phase 1c, deferred). It consumes the `/api/radar`, `/api/radar/history`, and `/api/radar/export` endpoints defined above — all backend work in this plan is unchanged.

If Plan 025's React app is dropped or the radar must ship before Phase 1c, fall back to: external viewer (`https://radar.thoughtworks.com`) consuming `/api/radar` JSON.

---

## Part D — Tests

### File: `tests/contract/database/test_radar_schema.py` (new)

Schema and storage tests:

| Test | Scenario | Expected |
|------|----------|----------|
| S1 | Insert publication with 3 blips | all rows stored correctly |
| S2 | Blip moved from Trial → Adopt | `is_moved=true`, history row created |
| S3 | New package added to radar | `is_new=true` |
| S4 | Mark publication as latest | only one `is_latest=true` at a time |
| S5 | Query radar_blip_history for one package | correct movement timeline |

### File: `tests/contract/database/test_radar_categorization.py` (new)

Categorization engine tests:

| Test | Scenario | Expected |
|------|----------|----------|
| C1 | Package with 30 repos, 200 days old | ring='Adopt' |
| C2 | Package with 3 repos, 60 days old | ring='Assess' |
| C3 | Package with 1 repo, EOL | ring='Hold' |
| C4 | Package with high CVE exposure, low adoption | ring='Hold' or 'Assess' depending on priority |
| C5 | Language package → Quadrant='Languages & Frameworks' | correct quadrant |
| C6 | Custom rule: min_adopt_repos=20 | categorization respects config |

### File: `tests/contract/api/test_radar_endpoints.py` (new)

API contract tests:

| Test | Endpoint | Expected |
|------|----------|----------|
| A1 | `GET /api/radar` | 200, valid TW schema, all quadrants present |
| A2 | Radar has entries | entry count > 0, each has ring/quadrant/label |
| A3 | `GET /api/radar/history?package_name=lodash` | 200, timeline sorted by date |
| A4 | `GET /api/radar/export?format=csv` | 200, CSV with entries, correct headers |
| A5 | `GET /api/radar/export?date=invalid` | 404 or reasonable error |
| A6 | New publication published | `/api/radar` returns updated entries |

### File: `tests/unit/test_radar_categorizer.py`

Unit tests for categorization logic (property-based + deterministic):

```python
@given(repo_count=st.integers(min_value=1, max_value=100),
       time_in_use_days=st.integers(min_value=0, max_value=1000))
def test_categorization_monotonic(repo_count, time_in_use_days):
    """More repos/time → same or higher ring."""

def test_eol_never_adopt():
    """EOL packages never in Adopt ring."""
    
def test_high_cve_exposure_not_adopt():
    """Packages with critical exposed CVEs not in Adopt."""
```

---

## Critical Files

| Status | Action | File |
|--------|--------|------|
| ❌ TODO | Create | `database/migrations/018_tech_radar_schema.sql` |
| ❌ TODO | Create | `src/analyzers/radar_categorization.py` |
| ❌ TODO | Create | `src/analyzers/radar_categorization_config.json` |
| ❌ TODO | Create | `src/workflows/radar_publication.py` |
| ❌ TODO | Modify | `src/api/rescan.py` (add 3 endpoints) |
| ❌ TODO | Create | `tests/contract/database/test_radar_schema.py` |
| ❌ TODO | Create | `tests/contract/database/test_radar_categorization.py` |
| ❌ TODO | Create | `tests/contract/api/test_radar_endpoints.py` |
| ❌ TODO | Create | `tests/unit/test_radar_categorizer.py` |
| ❌ Removed | — | ~~`src/api/radar_viewer.html`~~ — replaced by Plan 025 Phase 1c (React route) |
| ⚠️ Optional | Create | `.github/workflows/publish-radar.yml` (scheduled publication) |

---

## Parallel Implementation Strategy

**TRACK A (Schema + Categorization — 2–3 hours):**
1. Write migration (3 new tables)
2. Write categorization engine (RadarCategorizer)
3. Load categorization config
4. Write unit tests for categorization (property-based)
5. Write database contract tests (S1–S5)
6. All independent; no blocking

**TRACK B (Workflow — 1–2 hours):**
- Depends on TRACK A (uses RadarCategorizer)
- Write radar publication workflow (query → categorize → store)
- Can proceed in parallel; just assumes categorizer exists

**TRACK C (API + Export — 2–3 hours):**
- Depends on TRACK A (schema) + TRACK B (workflow logic)
- Write 3 endpoints (radar, history, export)
- Write API contract tests (A1–A6)
- Can proceed in parallel with TRACK B

**Recommended parallel workflow for Copilot:**

1. **PR #1 (TRACK A)**: Schema + Categorization engine + config + unit tests
   - Independent, can land immediately

2. **PR #2 (TRACK B)**: Workflow + database contract tests (depends on PR #1)
   - Can start once PR #1 is drafted but not merged

3. **PR #3 (TRACK C)**: API endpoints + API contract tests (depends on PR #1 merged)
   - Can proceed in parallel with PR #2 tests
   - Assume schema + categorizer are available

**Optional follow-up:**
- Schedule job to auto-publish radar (`.github/workflows/publish-radar.yml`)
- Add radar viewer UI page linking to external radar or embedding HTML

---

## Reuse

- `packages`, `repository_dependencies`, `vulnerabilities` schema (Plan 012)
- `has_known_vulnerabilities` flag (Plan 012 R-B)
- `TechnologyDetector` for quadrant categorization (Plan 011)
- Test patterns from Plan 011/012 contract tests
- API endpoint patterns from Plan 021 endpoints

---

## Acceptance Criteria

- ✅ Three tables created; migration idempotent
- ✅ RadarCategorizer correctly assigns rings based on metrics
- ✅ Config file loaded and customizable rules applied
- ✅ RadarPublicationWorkflow executes end-to-end without error
- ✅ Blip movements detected and history recorded
- ✅ `/api/radar` returns valid Thoughtworks Radar JSON
- ✅ `/api/radar/history` shows movement timeline
- ✅ `/api/radar/export` exports CSV/JSON correctly
- ✅ All contract tests pass (schema, categorization, API)
- ✅ Unit tests (property-based + deterministic) pass
- ✅ Radar snapshot exportable and importable to thoughtworks.com/radar

---

## Implementation Notes

1. **Thoughtworks Schema**: JSON must match https://github.com/thoughtworks/build-your-own-radar/blob/master/doc/data_format.md
   - Quadrants ordered as: Infrastructure, Platforms, Tools, Languages & Frameworks
   - Rings ordered as: Adopt (green), Trial (cyan), Assess (yellow), Hold (red)

2. **Categorization Priority**: If conflicting rules apply, use: EOL > CVE Exposure > Adoption Metrics

3. **is_new / is_moved flags**: 
   - `is_new=true` if package not in prior publication
   - `is_moved=true` if ring changed from prior publication
   - Reset both flags on each publication (snapshot semantics)

4. **Time-in-use calculation**: `adopted_date` taken from `repository_dependencies.first_seen_at` (when first scan detected it)

5. **Quadrant mapping**: Uses technology category detected (Plan 011); can fall back to ecosystem if needed

6. **Config versioning**: Consider tracking `radar_categorization_config.json` version in each publication for auditability

---

## Optional Enhancements (Future)

- Blip comments/justification field (editable, timestamped)
- Threshold alerts (e.g., "Package X moved to Hold due to EOL")
- Team-specific radar variants (e.g., "Platform team radar")
- Visual comparison view (prior vs current radar diff)
- Integration with Jira/Linear to tag related issues

---

## Deployment Notes

- No external dependencies (Thoughtworks radar is client-side viewer)
- Requires Plan 012 (packages schema) deployed first
- Can publish radar manually via `/api/radar/export` or schedule via CI
- Archive previous publications for history queries
- Optional: set up scheduled job to auto-publish radar daily or weekly

---

## Success Metrics

- Radar generated successfully from 2+ month usage data
- Blips categorized into all four rings
- Movement history shows meaningful transitions (e.g., adoption growth → Adopt)
- Exported radar renders correctly in Thoughtworks radar viewer
- Teams use radar for technology strategy discussions
