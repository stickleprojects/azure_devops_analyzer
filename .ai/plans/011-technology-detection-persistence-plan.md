# Plan: Technology Detection Persistence & Cross-Org Analysis

## Context

`TechnologyDetector` already identifies 8 categories of technology per repo (languages,
frameworks, databases, deployment platforms, build tools, testing frameworks, CI/CD,
documentation) but results are only logged — nothing is written to the DB. This means
we can't answer questions like "what frameworks are EOL across our org?" or "how many
services depend on .NET 6?".

Languages are currently stored in a separate `repository_languages` table populated from
the platform API. This plan **replaces that table with a unified `repository_stack`
table**, removing the split between "language stats" and "technology detections".

This plan covers:
1. **Unify** — replace `repository_languages` with `repository_stack`; persist all
   TechnologyDetector results into the same table
2. **Enrich** — query endoflife.date API and store EOL metadata in a separate
   `technologies` lookup table (EOL is a property of the technology, not of any
   specific repository's use of it)
3. **Surface** — new Grafana Technology Landscape dashboard + panels in existing
   dashboards + new API query endpoints

---

## Schema Design

### Two tables, clear responsibilities

```
technologies             — global facts about a technology (EOL, latest version)
repository_stack         — which repos use which technologies (and language stats)
```

**EOL data lives in `technologies`, not in `repository_stack`**, because "React 16 is EOL"
is true regardless of which repositories use it. Enrichment runs once per technology,
not once per repo.

**Query examples:**
```sql
-- which repos use C#?
SELECT DISTINCT rs.repo_id FROM repository_stack rs
WHERE rs.category = 'language' AND rs.name = 'C#';

-- which repos use React?
SELECT DISTINCT rs.repo_id FROM repository_stack rs
WHERE rs.category = 'framework' AND rs.name = 'React';

-- which repos are using EOL technologies?
SELECT rs.repo_id, rs.name, rs.category, t.eol_date
FROM repository_stack rs
JOIN technologies t ON t.name = rs.name AND t.category = rs.category
WHERE t.is_eol = true;

-- which technologies are EOL and how many repos are affected?
SELECT t.name, t.category, t.eol_date, COUNT(DISTINCT rs.repo_id) AS repo_count
FROM technologies t
JOIN repository_stack rs ON rs.name = t.name AND rs.category = t.category
WHERE t.is_eol = true
GROUP BY t.name, t.category, t.eol_date;
```

---

## Part 1 — Unify Storage

### Step 1: DB Migration `011_add_repository_stack.sql`

File: `database/migrations/011_add_repository_stack.sql`

```sql
-- ── technologies: global EOL metadata per technology ──────────────────────────
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'technologies'
    ) THEN
        CREATE TABLE technologies (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            category VARCHAR(50) NOT NULL,
                -- language | framework | database | deployment_platform
                -- build_tool | testing_framework | ci_cd | documentation
            is_eol BOOLEAN NOT NULL DEFAULT FALSE,
            eol_date DATE,
            latest_supported_version VARCHAR(100),
            eol_enriched_at TIMESTAMPTZ,
            CONSTRAINT uq_technology UNIQUE (name, category)
        );
        CREATE INDEX IF NOT EXISTS idx_tech_eol ON technologies(is_eol, eol_date);
        CREATE INDEX IF NOT EXISTS idx_tech_cat ON technologies(category);
    END IF;
END $$;

-- ── repository_stack: per-repo usage ──────────────────────────────────────────
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'repository_stack'
    ) THEN
        CREATE TABLE repository_stack (
            id SERIAL PRIMARY KEY,
            repo_id VARCHAR(255) NOT NULL,
            branch_id INTEGER,
            category VARCHAR(50) NOT NULL,
            name VARCHAR(200) NOT NULL,
            source VARCHAR(20) NOT NULL DEFAULT 'heuristic',
                -- 'platform_api' (from GitHub/ADO API)
                -- 'heuristic'    (from TechnologyDetector)

            -- language-specific (non-null when category='language', source='platform_api')
            percentage NUMERIC(5,2),
            line_count INTEGER,
            byte_count BIGINT,

            -- heuristic-specific (non-null when source='heuristic')
            confidence NUMERIC(4,3),            -- 0.000–1.000

            first_seen_at TIMESTAMPTZ NOT NULL,
            last_seen_at TIMESTAMPTZ NOT NULL,

            CONSTRAINT fk_stack_repo
                FOREIGN KEY (repo_id) REFERENCES repositories(repo_id) ON DELETE CASCADE,
            CONSTRAINT fk_stack_branch
                FOREIGN KEY (branch_id) REFERENCES branches(branch_id) ON DELETE CASCADE,
            CONSTRAINT uq_stack
                UNIQUE (repo_id, category, name)
        );
        CREATE INDEX IF NOT EXISTS idx_stack_repo_category ON repository_stack(repo_id, category);
        CREATE INDEX IF NOT EXISTS idx_stack_name ON repository_stack(name);
        CREATE INDEX IF NOT EXISTS idx_stack_cat_name ON repository_stack(category, name);
        CREATE INDEX IF NOT EXISTS idx_stack_source ON repository_stack(source, category);
    END IF;
END $$;

-- ── Migrate existing repository_languages data ────────────────────────────────
INSERT INTO repository_stack (
    repo_id, branch_id, category, name, source,
    percentage, line_count, byte_count,
    first_seen_at, last_seen_at
)
SELECT
    repo_id, branch_id, 'language', language, 'platform_api',
    percentage, line_count, byte_count,
    first_seen_at, last_seen_at
FROM repository_languages
ON CONFLICT (repo_id, category, name) DO NOTHING;

-- ── Drop old table ────────────────────────────────────────────────────────────
DO $$ BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'repository_languages'
    ) THEN
        DROP TABLE repository_languages CASCADE;
    END IF;
END $$;
```

---

### Step 2: ORM Models

**New file: `src/database/models/technology.py`**

```python
class Technology(Base):
    __tablename__ = "technologies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    is_eol: Mapped[bool] = mapped_column(Boolean, default=False)
    eol_date: Mapped[Optional[date]] = mapped_column(Date)
    latest_supported_version: Mapped[Optional[str]] = mapped_column(String(100))
    eol_enriched_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ)
```

**New file: `src/database/models/repository_stack.py`**

```python
class RepositoryStack(Base):
    __tablename__ = "repository_stack"

    id: Mapped[int] = mapped_column(primary_key=True)
    repo_id: Mapped[str] = mapped_column(String(255), ForeignKey(...))
    branch_id: Mapped[Optional[int]] = mapped_column(ForeignKey(...))
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="heuristic")

    # language-specific (nullable for non-language rows)
    percentage: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    line_count: Mapped[Optional[int]] = mapped_column(Integer)
    byte_count: Mapped[Optional[int]] = mapped_column(BigInteger)

    # heuristic-specific (nullable for platform_api rows)
    confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 3))

    first_seen_at: Mapped[datetime] = mapped_column(nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(nullable=False)

    repository: Mapped["Repository"] = relationship(back_populates="stack")
    branch: Mapped[Optional["Branch"]] = relationship(back_populates="stack")
```

In `src/database/models/repository.py`:
- Remove `languages: Mapped[list["RepositoryLanguage"]]` relationship
- Add `stack: Mapped[list["RepositoryStack"]]` relationship

Delete `src/database/models/repository_language.py`.

---

### Step 3: Storage Functions

In `src/database/storage.py`, replace `store_languages()` with two functions:

```python
def store_languages(
    session: Session,
    repo_id: str,
    languages: list[LanguageData],
    branch_id: Optional[int] = None,
) -> list[RepositoryStack]:
    """Upserts platform API language data into repository_stack.
    source='platform_api', category='language'.
    Updates: percentage, byte_count, line_count, last_seen_at.
    """
```

```python
def store_detections(
    session: Session,
    repo_id: str,
    detection: TechnologyDetection,
    branch_id: Optional[int] = None,
) -> list[RepositoryStack]:
    """Upserts TechnologyDetector results into repository_stack.
    source='heuristic'. Does not write category='language' rows.
    Updates: confidence, last_seen_at.
    """
```

**Category → field mapping for `store_detections`** (7 categories):

| category               | TechnologyDetection field  |
|------------------------|----------------------------|
| `framework`            | `frameworks`               |
| `database`             | `databases`                |
| `deployment_platform`  | `deployment_platforms`     |
| `build_tool`           | `build_tools`              |
| `testing_framework`    | `testing_frameworks`       |
| `ci_cd`                | `ci_cd_platforms`          |
| `documentation`        | `documentation_tools`      |

`programming_languages` from `TechnologyDetection` is **not stored** by `store_detections` —
language data comes from the platform API via `store_languages`.

**Add a third function for EOL upserts:**

```python
def store_technology_eol(
    session: Session,
    name: str,
    category: str,
    is_eol: bool,
    eol_date: Optional[date],
    latest_supported_version: Optional[str],
) -> Technology:
    """Upserts EOL metadata into the technologies table.
    Upsert on (name, category). Updates all EOL fields + eol_enriched_at.
    """
```

---

### Step 4: Workflow Integration

In `src/workflows/github_analysis.py`:

- Update `_process_languages()` to call the updated `store_languages()` (writes to
  `repository_stack` instead of `repository_languages`)
- Add `_process_detections()` method:

```python
def _process_detections(self, repo_data):
    file_names = [item["path"] for item in repo_data.file_tree]
    language_data = [{"language": e.name} for e in repo_data.stack
                     if e.category == "language"]
    detector = TechnologyDetector()
    detection = detector.detect(file_names, repo_data.file_tree, language_data)
    with session_scope() as session:
        store_detections(session, repo_data.repo_id, detection)
```

Call `_process_detections()` in `_process_repository()` after `_process_languages()`.

---

### Step 5: Unit Tests

New file: `tests/unit/test_stack_storage.py`

Test:
- `store_languages()` creates rows with `source='platform_api'`, `category='language'`
- `store_detections()` creates rows for all 7 non-language categories with `source='heuristic'`
- `store_detections()` does **not** create rows with `category='language'`
- Language upsert updates `percentage`, `byte_count`; detection upsert updates `confidence`
- `first_seen_at` is preserved on second upsert; `last_seen_at` is updated
- `store_technology_eol()` upserts into `technologies` table, not `repository_stack`
- Empty category lists produce no rows
- Both `store_languages` and `store_detections` write to the same `repository_stack` table

---

## Part 2 — EOL Enrichment

### Step 6: Technology Enricher

New file: `src/analyzers/technology_enricher.py`

```python
class TechnologyEnricher:
    """Queries endoflife.date and writes results to the technologies table.

    EOL data is stored once per technology (name + category), not per repository.
    Call this after store_detections() to ensure all detected technologies have
    a row in the technologies table before enriching.
    """

    EOL_SLUG_MAP = {
        "Python": "python",
        "Node.js": "nodejs",
        "Java": "java",
        "C#": "dotnet",
        "Go": "go",
        "Ruby": "ruby",
        "PHP": "php",
        "Spring": "spring-framework",
        "Django": "django",
        "Rails": "rails",
        "Laravel": "laravel",
        "Angular": "angular",
        "React": "react",        # no EOL data — skip gracefully
        "Vue": "vue",
        "ASP.NET": "dotnet",
        "Azure Pipelines": None, # no endoflife.date entry — skip
    }

    def enrich(self, session: Session, names: list[tuple[str, str]]) -> None:
        """
        Query endoflife.date for each (name, category) pair that has a slug mapping.
        Calls store_technology_eol() for each result.
        Skips entries with no slug mapping, 404s, or network errors (logs warning).

        names: list of (technology_name, category) pairs to enrich.
        """
```

**endoflife.date API call** (reuse `httpx` from `DependencyEnricher`):
`GET https://endoflife.date/api/{slug}.json` — returns list of release cycles.
If all cycles are past EOL → `is_eol = True`. Take the most recent active cycle
for `latest_supported_version`.

---

### Step 7: Integrate EOL Enrichment into Workflow

In `_process_detections()`, after `store_detections()`:

```python
enricher = TechnologyEnricher()
with session_scope() as session:
    # Collect distinct (name, category) pairs that were just stored
    pairs = [(e.name, e.category) for e in stored_entries]
    # Skip pairs already enriched recently (check eol_enriched_at)
    stale = [
        (name, cat) for name, cat in pairs
        if not session.query(Technology).filter_by(name=name, category=cat)
           .filter(Technology.eol_enriched_at > datetime.now() - timedelta(days=7))
           .first()
    ]
    enricher.enrich(session, stale)
```

The 7-day staleness check means EOL data is refreshed weekly without hitting the API
on every scan.

---

### Step 8: Contract Test

New file: `tests/contract/test_technology_enrichment.py`

Validate against mocked endoflife.date responses:
- Sets `is_eol=True` when all cycles are past EOL
- Sets `is_eol=False` and populates `latest_supported_version` when active cycle exists
- Skips technologies without slug mapping without raising
- Writes to `technologies` table (not `repository_stack`)
- Respects the 7-day staleness check (does not re-enrich recent entries)

---

## Part 3 — Analysis Surface

### Step 9: New API Endpoints

In `src/api/rescan.py` (or a new `src/api/stack.py` registered on the same app):

```
GET /api/stack/summary
  → org-wide: distinct name + category + source + repo_count + service_count + service_pct
  → optional ?category=language|framework|database|...
  → optional ?source=platform_api|heuristic
  → optional ?is_eol=true
  → optional ?group_by=service  (default: repo)
      when group_by=service: counts distinct services (not repos) that have ≥1 repo
      using the technology; service_pct = service_count / total_services * 100
      example response: [{ name: "C#", category: "language",
                           service_count: 12, service_pct: 48.0 }, ...]
  → JOINs technologies to include is_eol, eol_date per technology

GET /api/stack/by-service
  → per service: service_name + stack entries grouped by category + service-level counts
  → optional ?name=<technology_name>  filter to a specific technology
  → optional ?category=language|framework|...
  → joins repository_stack → repository_services → services
  → deduplicates: if a service has 10 C# repos it appears once under C#, not 10 times
  → includes EOL status via JOIN on technologies

GET /api/stack/eol
  → all technologies where is_eol=true or eol_date < now()+90days
  → JOINs repository_stack to list affected repos + services per technology

GET /api/stack/by-repo?repo_id=<id>
  → all stack entries for a specific repo, grouped by category
  → includes EOL status via LEFT JOIN on technologies
```

All endpoints return JSON following the existing pattern in `rescan.py`
(status, data, count).

---

### Step 10: Grafana — Technology Landscape Dashboard

New file: `dashboards/technology-landscape.json`

All repo-usage queries target `repository_stack`; EOL status comes from a JOIN
with `technologies`.

**Language & Framework Overview** (row)
- Pie chart: top languages by repo count — `WHERE rs.category = 'language'`
- Pie chart: top frameworks by repo count — `WHERE rs.category = 'framework'`
- Stat: total distinct non-language entries — `WHERE rs.category != 'language'`
- Stat: count of EOL technologies — `SELECT COUNT(*) FROM technologies WHERE is_eol = true`

**Technology by Service** (row)
- Table: service | languages | frameworks | databases | eol_count
  — languages/frameworks/databases via `repository_stack` joined through `repository_services`
  — eol_count via additional JOIN on `technologies WHERE is_eol = true`

**EOL & Risk** (row)
- Table: name | category | eol_date | affected_repos | affected_services
  — source: `technologies JOIN repository_stack JOIN repository_services`
  — colour-coded: red if `is_eol=true`, yellow if `eol_date < now()+90days`
- Stat: repos using ≥1 EOL technology
- Stat: services using ≥1 EOL technology

**Repository Stack Heatmap** (row)
- Table: repo | service | languages | frameworks | ci_cd | eol_affected
  — all from `repository_stack` with category filters
  — `eol_affected`: EXISTS subquery joining `technologies WHERE is_eol=true`
  — sortable, filtered by `$service` variable

Dashboard variable: `$service` (same query as service-overview)
Dashboard uid: `technology-landscape`

---

### Step 11: Extend Existing Dashboards

**Service Overview** (`dashboards/service-overview.json`):
- Add new row "Technology Stack" (after Security row)
- Panel 1: Table — service + languages + frameworks + eol_count
  (all from `repository_stack` + `technologies` JOIN for EOL)
- Panel 2: Bar chart — top 10 non-language entries across selected services

**Repository Deep-Dive** (`dashboards/repository-deep-dive.json`):
- Replace panels querying `repository_languages` with `repository_stack WHERE category='language'`
- Add "Technologies" section showing stack entries grouped by category + EOL status
  (EOL status via JOIN on `technologies`)

---

## Critical Files

| Action | File |
|--------|------|
| Create | `database/migrations/011_add_repository_stack.sql` |
| Create | `src/database/models/technology.py` |
| Create | `src/database/models/repository_stack.py` |
| Delete | `src/database/models/repository_language.py` |
| Modify | `src/database/models/repository.py` (replace `languages` rel → `stack`) |
| Modify | `src/database/storage.py` (update `store_languages`, add `store_detections`, add `store_technology_eol`) |
| Modify | `src/workflows/github_analysis.py` (update `_process_languages`, add `_process_detections`) |
| Create | `src/analyzers/technology_enricher.py` |
| Modify | `src/api/rescan.py` (or create `src/api/stack.py` with 4 endpoints) |
| Create | `dashboards/technology-landscape.json` |
| Modify | `dashboards/service-overview.json` (update queries + add Technology Stack row) |
| Modify | `dashboards/repository-deep-dive.json` (update queries + add Technologies section) |
| Create | `tests/unit/test_stack_storage.py` |
| Create | `tests/contract/test_technology_enrichment.py` |

## Reuse

- `src/analyzers/dependency_enricher.py` — copy `httpx` + endoflife.date call pattern
- `src/database/storage.py` `store_languages()` — upsert pattern to copy for `store_detections`
- `database/migrations/010_add_service_metrics.sql` — copy DO-block + idempotency pattern
- `src/api/rescan.py` — copy Flask route + error handling pattern

## Data Source Boundaries

| Data | Table | category | source | Notes |
|------|-------|----------|--------|-------|
| Programming languages | `repository_stack` | `language` | `platform_api` | Authoritative; byte counts + percentages |
| Frameworks, DBs, CI/CD, etc. | `repository_stack` | various | `heuristic` | 7 categories; confidence score |
| EOL metadata | `technologies` | — | endoflife.date | Global fact; not per-repo |
| AI-summarised tech keywords | `repository_summaries.key_technologies` | — | Claude AI | Unstructured TEXT[]; different purpose |
| Package-level dependencies | `dependencies` | — | Package file parsing | Per-package with version + ecosystem |

> **Note:** The same EOL-normalisation principle applies to `dependencies.is_eol` /
> `dependencies.eol_date` — those columns are also per-repo copies of a global fact.
> Normalising them into a `packages` lookup table is out of scope for this plan but
> follows the same pattern established here.

## Suggested Implementation Order

1. Migration (creates `technologies` + `repository_stack`, migrates language data, drops `repository_languages`)
2. Models (`technology.py`, `repository_stack.py`) + update `repository.py` + delete old model
3. Storage functions (`store_languages`, `store_detections`, `store_technology_eol`) — testable in isolation
4. Workflow integration
5. Unit tests
6. EOL enricher + contract test
7. API endpoints
8. Technology Landscape dashboard
9. Update existing dashboards

## Verification

- Run migration: `psql $DB_URL -f database/migrations/011_add_repository_stack.sql`
- Confirm language data migrated: `SELECT category, source, name FROM repository_stack WHERE category = 'language' LIMIT 10;`
- Confirm old table gone: `\dt repository_languages` (should return nothing)
- Run a single-repo scan and query:
  ```sql
  SELECT rs.category, rs.source, rs.name, t.is_eol, t.eol_date
  FROM repository_stack rs
  LEFT JOIN technologies t ON t.name = rs.name AND t.category = rs.category
  WHERE rs.repo_id = '<id>';
  ```
- Unit tests: `pytest tests/unit/test_stack_storage.py -v`
- Contract tests: `pytest tests/contract/test_technology_enrichment.py -v`
- API: `curl http://localhost:5000/api/stack/summary`
- Grafana: import `dashboards/technology-landscape.json`, verify all panels populate
