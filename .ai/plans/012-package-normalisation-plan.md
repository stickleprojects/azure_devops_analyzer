# Plan: Package Normalisation — `packages` + `repository_dependencies`

## Context

The existing `dependencies` table mixes per-repo usage facts with global facts about
packages:

| Column | Actually belongs to | Reason |
|--------|---------------------|--------|
| `repo_id`, `branch_id`, `package_name`, `version`, `ecosystem`, `is_dev_dependency` | per-repo usage | different per repo |
| `latest_version`, `is_eol`, `eol_date` | the package itself | true regardless of which repo uses it |
| `has_vulnerabilities` | per-repo usage | **version-specific** — a repo on `lodash@4.17.21` is not vulnerable even if older versions are |

The `vulnerabilities` table is linked to `dependencies.id` — meaning if 50 repos use
`lodash@3.10.0`, the same CVE is stored 50 times. A vulnerability is a fact about a
package, not about a specific repository's use of it.

`has_vulnerabilities` is intentionally kept per-repo (renamed to `has_known_vulnerabilities`)
because it must be computed against the specific version in use: a repo is exposed only
if its pinned version is below the `fixed_in_version` of an active CVE. This is determined
at enrichment time and stored as a pre-computed flag to avoid expensive version-comparison
joins on every dashboard query.

This plan:
1. **Renames** `dependencies` → `repository_dependencies` (per-repo usage only)
2. **Creates** a `packages` lookup table for version-agnostic package metadata (EOL, latest version)
3. **Re-links** `vulnerabilities` from `dependencies.id` → `packages.id`
4. **Retains** `has_known_vulnerabilities` on `repository_dependencies`, computed per scan
   by comparing the repo's pinned version against `fixed_in_version`
5. **Updates** all models, storage functions, enricher, and workflows accordingly

---

## Schema Design

```
packages                     — version-agnostic global facts (EOL, latest version)
  (package_name, ecosystem)  — unique key; one row per package
  latest_version             — from OSV.dev
  is_eol, eol_date           — from endoflife.date
  enriched_at                — last time external APIs were queried

vulnerabilities              — one row per CVE; linked to packages, not repos
  package_id FK → packages
  cve_id, severity, fixed_in_version, affected_versions, ...

repository_dependencies      — renamed from 'dependencies'; per-repo usage + version-specific flags
  repo_id, branch_id
  package_name, ecosystem, version
  is_dev_dependency
  has_known_vulnerabilities  — computed at scan: repo's version < fixed_in_version of any active CVE
  first_seen_at, last_seen_at
```

**Why `has_known_vulnerabilities` stays per-repo:**
```
packages row: lodash / npm                     → is_eol=false
vulnerabilities row: CVE-2021-23337 (lodash)   → fixed_in_version='4.17.21'

repo A uses lodash@3.10.0  → has_known_vulnerabilities = TRUE  (3.10.0 < 4.17.21)
repo B uses lodash@4.17.21 → has_known_vulnerabilities = FALSE (at or above fix)
```

**Query examples:**
```sql
-- which repos use xunit@2.6.1?
SELECT repo_id FROM repository_dependencies
WHERE package_name = 'xunit' AND version = '2.6.1';

-- which repos use any version of lodash, and what version?
SELECT repo_id, version FROM repository_dependencies
WHERE package_name = 'lodash' AND ecosystem = 'npm';

-- which repos are exposed to known vulnerabilities? (fast — uses pre-computed flag)
SELECT repo_id, package_name, version
FROM repository_dependencies
WHERE has_known_vulnerabilities = true;

-- which CVEs affect a specific repo? (for detail view)
SELECT rd.repo_id, rd.package_name, rd.version, v.cve_id, v.severity, v.fixed_in_version
FROM repository_dependencies rd
JOIN packages p ON p.package_name = rd.package_name AND p.ecosystem = rd.ecosystem
JOIN vulnerabilities v ON v.package_id = p.id
WHERE rd.repo_id = '<id>'
  AND rd.has_known_vulnerabilities = true;

-- which repos use an EOL package?
SELECT rd.repo_id, rd.package_name, rd.version, p.eol_date
FROM repository_dependencies rd
JOIN packages p ON p.package_name = rd.package_name AND p.ecosystem = rd.ecosystem
WHERE p.is_eol = true;
```

---

## Part 1 — DB Migration `012_normalise_packages.sql`

File: `database/migrations/012_normalise_packages.sql`

Runs in phases; each phase is idempotent (DO-block guarded).

```sql
-- ── Phase 1: Create packages table ───────────────────────────────────────────
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'packages'
    ) THEN
        CREATE TABLE packages (
            id SERIAL PRIMARY KEY,
            package_name VARCHAR(500) NOT NULL,
            ecosystem VARCHAR(100) NOT NULL,
            latest_version VARCHAR(100),
            is_eol BOOLEAN NOT NULL DEFAULT FALSE,
            eol_date DATE,
            enriched_at TIMESTAMPTZ,
            CONSTRAINT uq_package UNIQUE (package_name, ecosystem)
        );
        CREATE INDEX IF NOT EXISTS idx_pkg_eol ON packages(is_eol, eol_date);
        CREATE INDEX IF NOT EXISTS idx_pkg_eco ON packages(ecosystem);
    END IF;
END $$;

-- ── Phase 2: Populate packages from existing dependencies ─────────────────────
-- NOTE: has_vulnerabilities is intentionally NOT migrated — it is version-specific
-- and will be recomputed per-repo on the next scan.
INSERT INTO packages (package_name, ecosystem, latest_version, is_eol, eol_date, enriched_at)
SELECT DISTINCT ON (package_name, ecosystem)
    package_name,
    ecosystem,
    latest_version,
    is_eol,
    eol_date,
    NOW()
FROM dependencies
ORDER BY package_name, ecosystem, last_seen_at DESC
ON CONFLICT (package_name, ecosystem) DO NOTHING;

-- ── Phase 3: Re-link vulnerabilities to packages ─────────────────────────────
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'vulnerabilities' AND column_name = 'package_id'
    ) THEN
        ALTER TABLE vulnerabilities ADD COLUMN package_id INTEGER;
    END IF;
END $$;

UPDATE vulnerabilities v
SET package_id = p.id
FROM dependencies d
JOIN packages p ON p.package_name = d.package_name AND p.ecosystem = d.ecosystem
WHERE v.dependency_id = d.id
  AND v.package_id IS NULL;

DO $$ BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'vulnerabilities'
          AND column_name = 'package_id'
          AND is_nullable = 'YES'
    ) THEN
        IF NOT EXISTS (SELECT 1 FROM vulnerabilities WHERE package_id IS NULL) THEN
            ALTER TABLE vulnerabilities ALTER COLUMN package_id SET NOT NULL;
            ALTER TABLE vulnerabilities
                ADD CONSTRAINT fk_vuln_package
                FOREIGN KEY (package_id) REFERENCES packages(id) ON DELETE CASCADE;
        END IF;
    END IF;
END $$;

DO $$ BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'vulnerabilities' AND column_name = 'dependency_id'
    ) THEN
        ALTER TABLE vulnerabilities DROP COLUMN dependency_id;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_vuln_package ON vulnerabilities(package_id);

-- ── Phase 4: Rename dependencies → repository_dependencies ───────────────────
DO $$ BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'dependencies'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'repository_dependencies'
    ) THEN
        ALTER TABLE dependencies RENAME TO repository_dependencies;
    END IF;
END $$;

-- ── Phase 5: Clean up columns on repository_dependencies ─────────────────────
-- Drop version-agnostic columns (now in packages).
-- Rename has_vulnerabilities → has_known_vulnerabilities for clarity.
DO $$ BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'repository_dependencies' AND column_name = 'is_eol'
    ) THEN
        ALTER TABLE repository_dependencies
            DROP COLUMN IF EXISTS is_eol,
            DROP COLUMN IF EXISTS eol_date,
            DROP COLUMN IF EXISTS latest_version;
    END IF;
END $$;

DO $$ BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'repository_dependencies' AND column_name = 'has_vulnerabilities'
    ) THEN
        ALTER TABLE repository_dependencies
            RENAME COLUMN has_vulnerabilities TO has_known_vulnerabilities;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_repodep_vuln
    ON repository_dependencies(has_known_vulnerabilities)
    WHERE has_known_vulnerabilities = true;
```

---

## Part 2 — ORM Models

### New file: `src/database/models/package.py`

```python
class Package(Base):
    __tablename__ = "packages"

    id: Mapped[int] = mapped_column(primary_key=True)
    package_name: Mapped[str] = mapped_column(String(500), nullable=False)
    ecosystem: Mapped[str] = mapped_column(String(100), nullable=False)
    latest_version: Mapped[Optional[str]] = mapped_column(String(100))
    is_eol: Mapped[bool] = mapped_column(Boolean, default=False)
    eol_date: Mapped[Optional[date]] = mapped_column(Date)
    enriched_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ)

    vulnerabilities: Mapped[list["Vulnerability"]] = relationship(
        back_populates="package", cascade="all, delete-orphan"
    )
```

### Modify: `src/database/models/dependency.py`

- Rename class `Dependency` → `RepositoryDependency`
- Rename `__tablename__` → `"repository_dependencies"`
- Remove columns: `latest_version`, `is_eol`, `eol_date`
- Rename column: `has_vulnerabilities` → `has_known_vulnerabilities`
- Remove `vulnerabilities` relationship (now on `Package`)
- Update `back_populates` targets: `"repo_dependencies"` on both `repository` and `branch`

Update `Vulnerability` in the same file:
- Replace `dependency_id` FK and column → `package_id` FK referencing `packages.id`
- Replace `dependency` relationship → `package: Mapped["Package"]`

### Modify: `src/database/models/repository.py`

- Update import: `RepositoryDependency` (was `Dependency`)
- Rename relationship attribute `dependencies` → `repo_dependencies` on both `Repository`
  and `Branch`

---

## Part 3 — Storage Functions

In `src/database/storage.py`:

### Update `store_dependencies()`

- Update type references: `Dependency` → `RepositoryDependency`
- Remove writes to `latest_version`, `is_eol`, `eol_date`
- `has_known_vulnerabilities` is not set here — it requires enriched data; defaults to
  existing DB value or `False` on first insert

### Replace `store_enriched_dependencies()` with two functions

```python
def store_package_metadata(
    session: Session,
    package_name: str,
    ecosystem: str,
    latest_version: Optional[str],
    is_eol: bool,
    eol_date: Optional[date],
    vulnerabilities: list[dict],
) -> Package:
    """
    Upsert version-agnostic package metadata and its vulnerability records.
    Upsert on (package_name, ecosystem). Updates enriched_at to now().
    Replaces all vulnerability records for this package (OSV returns full current list).
    Does NOT store has_known_vulnerabilities — that is version-specific and computed
    per-repo in store_repo_dependencies().
    """
```

```python
def store_repo_dependencies(
    session: Session,
    repo_id: str,
    enriched_dependencies: list[EnrichedDependency],
    branch_name: Optional[str] = None,
) -> list[RepositoryDependency]:
    """
    Upsert per-repo dependency usage.
    Writes: package_name, ecosystem, version, is_dev_dependency,
            has_known_vulnerabilities, first_seen_at, last_seen_at.
    has_known_vulnerabilities is taken from EnrichedDependency.has_known_vulnerabilities,
    which the enricher computes by comparing version against fixed_in_version.
    """
```

### Update `get_extraction_summary()`

```python
# before
"dependencies": session.query(Dependency).count(),
# after
"repository_dependencies": session.query(RepositoryDependency).count(),
"packages": session.query(Package).count(),
```

---

## Part 4 — Update `DependencyEnricher`

In `src/analyzers/dependency_enricher.py`:

Split the current single `EnrichedDependency` into two dataclasses routed to different
tables:

```python
@dataclass
class PackageMetadata:
    """Version-agnostic facts — written to the packages table."""
    package_name: str
    ecosystem: str
    latest_version: Optional[str]
    is_eol: bool
    eol_date: Optional[date]
    vulnerabilities: list[dict]  # full CVE list from OSV, includes fixed_in_version

@dataclass
class EnrichedDependency:
    """Per-repo usage — written to repository_dependencies."""
    package_name: str
    ecosystem: str
    version: Optional[str]
    is_dev_dependency: bool
    source_file: str
    version_constraint: Optional[str]
    has_known_vulnerabilities: bool = False  # computed: version < fixed_in_version of any CVE
    package_metadata: Optional[PackageMetadata] = None
```

In `_enrich_single()`, after fetching vulnerability data from OSV:

```python
# Compute version-specific exposure
has_known_vulnerabilities = any(
    self._version_is_affected(enriched.version, v.get("fixed_in_version"))
    for v in package_metadata.vulnerabilities
)
enriched.has_known_vulnerabilities = has_known_vulnerabilities
```

Add a `_version_is_affected(current: str, fixed_in: str) -> bool` helper using
`packaging.version` (already available in the Python ecosystem) for semver comparison.
Return `False` if either version string is unparseable — fail safe over false positive.

---

## Part 5 — Workflow Integration

In `src/workflows/github_analysis.py`, update `_process_dependencies()`:

```python
def _process_dependencies(self, repo_data):
    ...
    enriched = enricher.enrich(raw_deps)

    with session_scope() as session:
        # 1. Write version-agnostic package metadata + vulnerabilities (once per package)
        for e in enriched:
            if e.package_metadata:
                store_package_metadata(session, **e.package_metadata.__dict__)

        # 2. Write per-repo usage including version-specific has_known_vulnerabilities
        store_repo_dependencies(session, repo_data.repo_id, enriched)
```

---

## Part 6 — Tests

### Update existing tests

- `Dependency` → `RepositoryDependency`; `"dependencies"` table → `"repository_dependencies"`
- `store_enriched_dependencies()` → two function calls
- Assertions on `is_eol`/`eol_date`/`latest_version` on `Dependency` rows → move to `Package`
- `has_vulnerabilities` field → `has_known_vulnerabilities` on `RepositoryDependency`

### New file: `tests/unit/test_package_storage.py`

Test:
- `store_package_metadata()` writes to `packages`, not `repository_dependencies`
- `store_package_metadata()` does **not** store `has_known_vulnerabilities`
- `store_repo_dependencies()` writes `has_known_vulnerabilities` to `repository_dependencies`
- Upsert: `store_package_metadata()` second call updates `enriched_at`; preserves `id`
- Vulnerability replace: second `store_package_metadata()` call with updated CVE list
  replaces old vulnerability rows, not appends
- Two repos using the same package → one `packages` row, two `repository_dependencies` rows
  with independent `has_known_vulnerabilities` values

### New file: `tests/unit/test_version_comparison.py`

Test `_version_is_affected()` helper:
- `"3.10.0"` vs `fixed_in="4.17.21"` → `True`
- `"4.17.21"` vs `fixed_in="4.17.21"` → `False` (at the fix boundary = not affected)
- `"4.18.0"` vs `fixed_in="4.17.21"` → `False`
- Unparseable version string → `False` (fail safe)
- `fixed_in=None` → `False`

---

## Part 7 — API & Dashboard Updates

### API endpoints

```
GET /api/packages/search?name=<name>&ecosystem=<ecosystem>&version=<version>
  → optional ?name=        partial match on package_name
  → optional ?ecosystem=   exact match (npm | nuget | pypi | maven | ...)
  → optional ?version=     when provided: filters to repos using exactly this version
                            and returns repo list + service list instead of aggregate counts
      without ?version:  { package_name, ecosystem, latest_version, is_eol,
                           eol_date, repo_count, service_count }
      with    ?version:  { package_name, version, repos: [...], services: [...] }
  → example: /api/packages/search?name=xunit&version=2.6.1
      → "which repos and services use xunit@2.6.1"
  → example: /api/packages/search?name=lodash&ecosystem=npm
      → "how many repos/services use any version of lodash"

GET /api/packages/by-service?name=<name>&ecosystem=<ecosystem>&version=<version>
  → which services have ≥1 repo using the specified package
  → optional ?version=  when provided, filters to that exact version
  → deduplicates: a service with 3 repos using lodash appears once
  → returns: [{ service_name, repo_count, versions_in_use: ["1.2.3", "4.17.21"] }]
  → example: /api/packages/by-service?name=lodash&version=1.2.3
      → "what services are using lodash@1.2.3"

GET /api/packages/by-repo?repo_id=<id>
  → all packages used by a specific repo
  → JOIN repository_dependencies → packages for EOL status
  → includes has_known_vulnerabilities from repository_dependencies (version-specific)

GET /api/packages/vulnerable
  → repos where has_known_vulnerabilities=true in repository_dependencies
  → grouped by package_name, includes repo_count and CVE summary via packages→vulnerabilities

GET /api/packages/eol
  → packages where is_eol=true or eol_date < now()+90days
  → JOIN repository_dependencies for repo_count
```

### Dashboards

**Repository Deep-Dive** (`dashboards/repository-deep-dive.json`):
- Vulnerability flag: `repository_dependencies.has_known_vulnerabilities` (no JOIN needed)
- EOL flag: JOIN `repository_dependencies → packages WHERE p.is_eol = true`
- CVE detail panel: JOIN `→ packages → vulnerabilities`

**Service Overview** (`dashboards/service-overview.json`):
- `total_vulnerabilities` count: `COUNT(*) WHERE has_known_vulnerabilities = true` on
  `repository_dependencies` (fast, no JOIN)
- `eol_dependencies` count: JOIN through `packages WHERE is_eol = true`

---

## Critical Files

| Action | File |
|--------|------|
| Create | `database/migrations/012_normalise_packages.sql` |
| Create | `src/database/models/package.py` |
| Modify | `src/database/models/dependency.py` (rename class + table, drop EOL cols, rename has_vulnerabilities, re-link Vulnerability) |
| Modify | `src/database/models/repository.py` (rename `dependencies` rel → `repo_dependencies`) |
| Modify | `src/database/storage.py` (update `store_dependencies`, split `store_enriched_dependencies`, update `get_extraction_summary`) |
| Modify | `src/analyzers/dependency_enricher.py` (add `PackageMetadata`, compute `has_known_vulnerabilities` in `_enrich_single`, add `_version_is_affected` helper) |
| Modify | `src/workflows/github_analysis.py` (update `_process_dependencies`) |
| Modify | `src/api/rescan.py` (add 4 package endpoints) |
| Modify | `dashboards/repository-deep-dive.json` |
| Modify | `dashboards/service-overview.json` |
| Create | `tests/unit/test_package_storage.py` |
| Create | `tests/unit/test_version_comparison.py` |
| Modify | `tests/unit/test_dependency_storage.py` (if it exists) |

---

## Reuse

- `src/database/storage.py` `store_technology_eol()` (plan 011) — upsert pattern for
  `store_package_metadata()`
- `src/database/models/package.py` mirrors `src/database/models/technology.py` (plan 011)
- Migration phase structure mirrors `011_add_repository_stack.sql`

## Relationship to Plan 011

| Plan 011 | Plan 012 |
|----------|----------|
| `technologies` | `packages` |
| `repository_stack` | `repository_dependencies` |
| EOL at global level | EOL at global level; **vulnerability exposure at repo level** |

Implement plan 011 first.

---

## Suggested Implementation Order

1. Migration — run against a dev DB snapshot first to verify data integrity before prod
2. ORM models (`package.py`, update `dependency.py`, `repository.py`)
3. Storage functions (`store_package_metadata`, `store_repo_dependencies`, update `store_dependencies`)
4. `DependencyEnricher` — add `PackageMetadata`, `_version_is_affected`, compute `has_known_vulnerabilities`
5. Workflow (`_process_dependencies`)
6. Tests (storage + version comparison)
7. API endpoints
8. Dashboards

---

## Verification

```sql
-- packages populated (no has_known_vulnerabilities column)
SELECT column_name FROM information_schema.columns WHERE table_name = 'packages';
-- → should NOT include has_known_vulnerabilities

-- version-agnostic columns gone from repository_dependencies
SELECT column_name FROM information_schema.columns
WHERE table_name = 'repository_dependencies'
  AND column_name IN ('is_eol', 'eol_date', 'latest_version', 'has_vulnerabilities');
-- → should return 0 rows

-- has_known_vulnerabilities present on repository_dependencies
SELECT column_name FROM information_schema.columns
WHERE table_name = 'repository_dependencies' AND column_name = 'has_known_vulnerabilities';
-- → should return 1 row

-- vulnerabilities linked to packages, not dependencies
SELECT COUNT(*) FROM vulnerabilities WHERE package_id IS NULL;
-- → 0

-- two repos using same package, different vulnerability status
SELECT repo_id, package_name, version, has_known_vulnerabilities
FROM repository_dependencies WHERE package_name = 'lodash';
```

- Unit tests: `pytest tests/unit/test_package_storage.py tests/unit/test_version_comparison.py -v`
- API: `curl "http://localhost:5000/api/packages/search?name=lodash"`
