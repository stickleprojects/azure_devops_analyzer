# Plans 021 & 022: Parallel Implementation Strategy for Copilot Delegation

## Status: COMPLETE — both plans merged 2026-04-26

| Plan | Implementation PR | Status |
|------|------------------|--------|
| 021 — Dependency Vulnerability & EOL Dashboard (FR-5) | [#73](https://github.com/stickleprojects/azure_devops_analyzer/pull/73) (`c4346ad`) | ✅ Merged 2026-04-26 |
| 022 — Thoughtworks Tech Radar Publication (FR-6) | [#74](https://github.com/stickleprojects/azure_devops_analyzer/pull/74) (`db5ffd6`) | ✅ Merged 2026-04-26 |

### Post-merge documentation follow-ups

| PR | Date | What it changed |
|----|------|-----------------|
| [#75](https://github.com/stickleprojects/azure_devops_analyzer/pull/75) (`efe30d1`) | 2026-04-26 | Recorded both plans complete; added `.claude/settings.json` |
| [#86](https://github.com/stickleprojects/azure_devops_analyzer/pull/86) (`a206801`) | 2026-05-03 | Wave 1B: PROGRESS.md note describing tech radar schema/categorizer (titled as a feat, but the implementation already shipped in #74 — diff is docs-only, 44 lines in `PROGRESS.md`) |
| [#89](https://github.com/stickleprojects/azure_devops_analyzer/pull/89) (`7e581ad`) | 2026-05-03 | Plan 021 docs/visualization/requirements alignment (docs-only, 72 lines) |

### Outcome vs. plan

- **Parallelism worked**: Copilot implemented both plans concurrently, no blocking between them. Both landed on the same day (2026-04-26).
- **PR strategy diverged**: Each plan landed as a **single PR** rather than the three-tracks-three-PRs split originally proposed below. In practice the per-track decomposition was unnecessary — review burden was manageable as one PR per plan.
- **Conflict point**: Both PRs added endpoints to `src/api/rescan.py`. PR #74 picked up the conflict when #73 merged first; resolved by keeping all 6 endpoints (3 dashboard + 3 radar). No semantic overlap.

### What shipped (Plan 021, merged in #73)

- `database/migrations/017_dependency_dashboard_views.sql` + 5 views in `database/views.sql`
- `dashboards/dependency-vulnerability-portfolio.json`
- `dashboards/library-detail-deep-dive.json`
- 3 endpoints in `src/api/rescan.py`: `/api/packages/health`, `/api/packages/adoption`, `/api/packages/library/<name>/<ecosystem>`
- Contract tests: `tests/contract/database/test_dependency_dashboard_views.py`, `tests/contract/api/test_dependency_dashboard_api.py`

### What shipped (Plan 022, merged in #74)

- `database/migrations/018_tech_radar_schema.sql` — 3 tables (`radar_publications`, `radar_blips`, `radar_blip_history`)
- `src/database/models/radar.py`, `src/analyzers/radar_categorization.py` (+ `radar_categorization_config.json`), `src/workflows/radar_publication.py`
- 3 endpoints in `src/api/rescan.py`: `/api/radar`, `/api/radar/history`, `/api/radar/export`
- Tests: 33 unit (incl. 4 hypothesis property-based) + 19 contract — schema (S1–S5), categorization (C1–C6), API (A1–A8)
- Movement detection records `repo_count_delta`, `vulnerability_change` (`now_exposed` / `fixed` / `unchanged`), and `"Removed"` history rows when packages disappear from the snapshot
- `is_new` only set when a prior publication exists (avoids first-publication false positives)

---

## Original Plan (Historical — superseded by actual execution)

> **This section is preserved for archaeology only.** Everything below was the pre-implementation delegation strategy — three tracks per plan, multiple parallel Copilot agents, six PRs total. Actual execution was simpler: one PR per plan, both implemented by Copilot concurrently. Track-level effort estimates and PR sequencing below did not match reality and should not be used as a template for future plans.

## Overview

Two major feature plans are ready for GitHub Copilot implementation:

- **Plan 021**: Dependency Vulnerability & EOL Dashboard (FR-5) — 6 requirements
- **Plan 022**: Thoughtworks Tech Radar Publication (FR-6) — 7 requirements

Both can be developed **in full parallel**. No architectural dependencies exist between them; they operate independently and share only the Plan 012 dependency schema.

---

## Dependency Map

```
Plan 012 (Completed)
├── packages, repository_dependencies, vulnerabilities tables
├── has_known_vulnerabilities flag
└─ Used by both Plan 021 and Plan 022

        ├─→ Plan 021 (Dashboard)              ├─→ Plan 022 (Tech Radar)
        │   └─ 5 new views                    │   └─ 3 new tables
        │   └─ 2 new dashboards               │   └─ Categorization engine
        │   └─ 3 new API endpoints            │   └─ 3 new API endpoints
        │   └─ 11 contract tests              │   └─ 13 contract tests
        │                                     │
        └─────────────────┬─────────────────┘
                          │
                    (Independent,
                     no blocking)
```

**Implication**: Plan 021 and Plan 022 can be developed in **separate PRs** and merged in **any order**. No sequencing required.

---

## Parallel Work Breakdown

### Plan 021: Three Tracks (Can Proceed in Parallel)

**Track A — Backend Views (2–3 hours)**
- File: `database/migrations/017_dependency_dashboard_views.sql`
- File: `tests/contract/database/test_dependency_dashboard_views.py`
- Dependency: None (only Plan 012 schema)
- Blocker: None
- **Status**: Ready to start immediately

**Track B — Dashboard JSON (2–3 hours)**
- Files: `dashboards/dependency-vulnerability-portfolio.json`, `dashboards/library-detail-deep-dive.json`
- Dependency: TRACK A views (but can mock/stub them)
- Blocker: None
- **Status**: Can start immediately; panels will fail gracefully until views exist

**Track C — API Endpoints (2–4 hours)**
- File: `src/api/rescan.py` (add 3 endpoints)
- File: `tests/contract/api/test_dependency_dashboard_api.py`
- Dependency: TRACK A views
- Blocker: None
- **Status**: Can start once TRACK A is drafted (even before merge)

**Recommendation**: 
- **Copilot Worker 1**: TRACK A (views + DB tests)
- **Copilot Worker 2**: TRACK B (dashboard JSON) — start in parallel
- **Copilot Worker 3** (or sequential): TRACK C (API endpoints) — start once A is drafted

**PR Strategy**:
1. PR-021-A: Views + database tests (independent, lands first)
2. PR-021-B: Dashboard JSON (can land independently)
3. PR-021-C: API endpoints (depends on PR-021-A merged)

All three can be opened simultaneously; review in parallel.

---

### Plan 022: Three Tracks (Sequential Dependency but Mostly Parallelizable)

**Track A — Schema + Categorization (2–3 hours)**
- Files: `database/migrations/018_tech_radar_schema.sql`, `src/analyzers/radar_categorization.py`, `src/analyzers/radar_categorization_config.json`
- Files: `tests/unit/test_radar_categorizer.py`, `tests/contract/database/test_radar_schema.py`
- Dependency: None
- Blocker: None
- **Status**: Ready to start immediately

**Track B — Workflow (1–2 hours)**
- File: `src/workflows/radar_publication.py`
- Dependency: TRACK A (RadarCategorizer, schema)
- Blocker: TRACK A must be at least drafted
- **Status**: Can start once A is drafted; no blocking

**Track C — API Endpoints (2–3 hours)**
- Files: `src/api/rescan.py` (add 3 endpoints), `tests/contract/api/test_radar_endpoints.py`
- Dependency: TRACK A (schema) + TRACK B (workflow logic)
- Blocker: TRACK A must be merged or nearly complete
- **Status**: Can start in parallel with TRACK B; just assumes schema exists

**Recommendation**:
- **Copilot Worker 1**: TRACK A (schema + categorizer, fully unblocked)
- **Copilot Worker 2** (after A is drafted): TRACK B (workflow)
- **Copilot Worker 3** (parallel with B): TRACK C (API) — assumes schema available

**PR Strategy**:
1. PR-022-A: Schema + Categorization (lands first, unblocked)
2. PR-022-B: Workflow (depends on PR-022-A merged)
3. PR-022-C: API endpoints (can start in parallel with B; needs A merged)

**Timeline**:
- t=0: Start PR-022-A
- t=1–2h: PR-022-A lands
- t=2h: Start PR-022-B and PR-022-C (in parallel)
- t=4–6h: Both B and C land

---

## Optimal Parallel Execution (Copilot)

If **two Copilot agents work in parallel**:

**Agent 1 Timeline (Plan 021):**
```
t=0h   → Start 021-TRACK-A (views + DB tests)
t=2h   → PR-021-A ready for review
t=2h   → Simultaneously start 021-TRACK-B (dashboard)
t=2.5h → Start 021-TRACK-C (API endpoints, assuming A is drafted)
t=4h   → PR-021-B ready
t=6h   → PR-021-C ready (after A merged)
```

**Agent 2 Timeline (Plan 022):**
```
t=0h   → Start 022-TRACK-A (schema + categorizer)
t=2h   → PR-022-A ready for review
t=2h   → Start 022-TRACK-B (workflow)
t=3h   → Start 022-TRACK-C (API, in parallel with B)
t=3.5h → PR-022-B ready (after A merged)
t=5.5h → PR-022-C ready (after A merged)
```

**Total Clock Time**: ~6 hours (if work starts immediately and is well-coordinated)
**Total Copilot Hours**: ~12 hours (6h × 2 agents)

---

## Cross-Cutting Concerns (Shared)

### Test Command

Both plans should validate via Docker:

```bash
# Plan 021 tests
bash scripts/run-tests-docker.sh \
  tests/contract/database/test_dependency_dashboard_views.py \
  tests/contract/api/test_dependency_dashboard_api.py

# Plan 022 tests
bash scripts/run-tests-docker.sh \
  tests/unit/test_radar_categorizer.py \
  tests/contract/database/test_radar_schema.py \
  tests/contract/database/test_radar_categorization.py \
  tests/contract/api/test_radar_endpoints.py

# Full suite (after PRs land)
bash scripts/run-tests-docker.sh
```

### Pre-Commit Validation

Both should follow `.ai/principles.md` Principle 1 (Tests Define Truth):
- Write contract tests **first** (before implementation)
- Run Docker tests **before committing**
- All tests must pass; no partial implementations

### Commit Message Style

Example (from Plan 012):
```
feat: implement Plan 021 Track A — dependency dashboard views

Add five new views for portfolio-level dependency queries:
- v_package_portfolio_latest: aggregate repo/service/CVE counts
- v_package_health_latest: health status classification
- v_package_adoption_timeline: 90-day adoption trends
- v_package_by_team_latest: usage aggregated by team
- v_package_vulnerabilities_detail: per-package CVE details

Add contract tests (T1–T6) validating view semantics and aggregations.

All Docker tests pass. Views consume Plan 012 schema (no breaking changes).
```

---

## Risk Mitigation

### Plan 021 Risks

| Risk | Probability | Mitigation |
|------|-------------|-----------|
| View performance on large dataset | Medium | Add indexes upfront; test with production-like data |
| Dashboard panel layout issues | Low | Test grid positioning before merge |
| API endpoint response size | Low | Paginate large result sets if needed |

**Mitigation**: TRACK A should include performance testing (EXPLAIN ANALYZE on views).

### Plan 022 Risks

| Risk | Probability | Mitigation |
|------|-------------|-----------|
| Categorization rules not flexible enough | Medium | Config-driven via JSON; easy to tweak without code |
| Thoughtworks schema validation | Medium | Test export against actual schema early |
| Time-in-use calculation edge cases | Low | Test with fixture data covering various timezones and scan patterns |

**Mitigation**: TRACK A unit tests should be property-based to catch categorization edge cases.

---

## Checklist for Copilot Delegation

### Before Starting

- [ ] Both Plan 021 and Plan 022 docs read and understood
- [ ] Plan 012 (packages schema) verified to be merged and deployed
- [ ] `.ai/principles.md` reviewed (especially Principle 1: Tests Define Truth)
- [ ] Docker test runner working locally or in CI
- [ ] Two agents assigned (or sequential phases clear)

### Plan 021 Execution

**TRACK A**:
- [ ] Migration file created with 5 views
- [ ] Views tested with fixture data
- [ ] Database contract tests written and passing
- [ ] PR-021-A created, reviewed, merged

**TRACK B** (can start in parallel with A review):
- [ ] Dashboard JSON files created
- [ ] Panels configured with correct query targets
- [ ] Grid layout validated (visual check optional)
- [ ] PR-021-B created, reviewed, merged

**TRACK C** (after A merged):
- [ ] 3 endpoints implemented in `src/api/rescan.py`
- [ ] API contract tests written and passing
- [ ] All Docker tests pass
- [ ] PR-021-C created, reviewed, merged

### Plan 022 Execution

**TRACK A**:
- [ ] Migration file created with 3 tables
- [ ] RadarCategorizer implemented
- [ ] Config file created with default rules
- [ ] Unit tests written (property-based + deterministic)
- [ ] Database contract tests written and passing
- [ ] PR-022-A created, reviewed, merged

**TRACK B** (can start once A is drafted):
- [ ] RadarPublicationWorkflow implemented
- [ ] Integration with categorizer verified
- [ ] Movement detection logic tested
- [ ] PR-022-B created, reviewed, merged

**TRACK C** (can start in parallel with B; needs A merged):
- [ ] 3 endpoints implemented in `src/api/rescan.py`
- [ ] API contract tests written and passing
- [ ] Thoughtworks schema validation tested
- [ ] All Docker tests pass
- [ ] PR-022-C created, reviewed, merged

### After Both Plans

- [ ] Full Docker test suite passes
- [ ] PROGRESS.md updated with session notes
- [ ] Both plan docs updated with final status
- [ ] Architecture docs (if needed) updated
- [ ] All PRs merged to `main`

---

## Communication Points

### Key Decisions During Implementation

1. **Plan 021**: If adoption timeline view becomes slow, consider:
   - Materialized view + scheduled refresh
   - or incremental update (not full rescan each time)
   - Document trade-off in migration comment

2. **Plan 022**: If categorization rules too complex:
   - Start with simple heuristics (repo_count + time_in_use)
   - Config-driven; rules can evolve post-launch
   - Document rationale in config comments

### Testing Coordination

- Both PRs should validate with full Docker suite
- If tests fail cross-plan (e.g., API endpoint conflicts), coordinate resolution
- Contract tests should be independent; no sequencing assumptions

### Documentation

- PROGRESS.md: Add session entry summarizing both plans upon completion
- Plan 021 and 022 docs: Update status to ✅ Complete
- README: Consider adding "Tech Radar" and "Dependency Dashboard" to feature list

---

## Alternative: Sequential if Resource-Constrained

If only **one Copilot agent** available:

**Sequence**:
1. Plan 022 TRACK A (schema + categorizer) — ~2–3h
2. Plan 021 TRACK A (views) — ~2–3h
3. Plan 022 TRACK B (workflow) — ~1–2h
4. Plan 021 TRACK B (dashboard) — ~2–3h
5. Plan 022 TRACK C (API) — ~2–3h
6. Plan 021 TRACK C (API) — ~2–4h

**Total**: ~12–18h sequential
**Per-PR time**: Each PR takes 2–4h (including tests, review cycles)

**Advantage**: Simpler coordination; no race conditions.
**Disadvantage**: Takes 8–12h wall-clock time vs ~6h with parallel double-team.

---

## Success Criteria (Final)

- ✅ Plan 021: All 11 contract tests passing
- ✅ Plan 022: All 13 contract tests passing
- ✅ Full Docker test suite passes
- ✅ Both feature sets deployable independently
- ✅ Both plans marked ✅ Complete in documentation
- ✅ PROGRESS.md includes completion notes for both
- ✅ No regressions in existing tests

---

## Quick Reference: File Manifest

### Plan 021 (Dashboard)
```
database/migrations/017_dependency_dashboard_views.sql
dashboards/dependency-vulnerability-portfolio.json
dashboards/library-detail-deep-dive.json
src/api/rescan.py (add 3 endpoints)
tests/contract/database/test_dependency_dashboard_views.py (6 tests)
tests/contract/api/test_dependency_dashboard_api.py (5 tests)
```

### Plan 022 (Tech Radar)
```
database/migrations/018_tech_radar_schema.sql
src/analyzers/radar_categorization.py
src/analyzers/radar_categorization_config.json
src/workflows/radar_publication.py
src/api/rescan.py (add 3 endpoints)
tests/unit/test_radar_categorizer.py
tests/contract/database/test_radar_schema.py (5 tests)
tests/contract/database/test_radar_categorization.py (6 tests)
tests/contract/api/test_radar_endpoints.py (6 tests)
```

**Total new files**: 17
**Total test cases**: 24 (11 Plan 021 + 13 Plan 022)
**Estimated effort**: 12–18 hours (parallel = ~6h wall-clock)

