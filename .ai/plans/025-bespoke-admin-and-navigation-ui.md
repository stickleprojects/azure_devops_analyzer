# Plan 025: Bespoke Web UI for Admin & Cross-Dashboard Navigation

> **Renumber note (2026-05-03)**: Originally drafted as Plan 024. Renumbered to 025 because PR #83 (open at drafting time) reserved Plan 024 for "auth error taxonomy and view consistency". Phase numbering inside this document is unchanged.

## Status: APPROVED 2026-05-03

**Implements**: A small React frontend that owns admin/operational workflows and coexists with Grafana — Grafana remains the home for analytics charts and the primary "Home" landing.

**Predicate met**: [Investigation grafana-ui-shortcomings](../investigations/grafana-ui-shortcomings.md) closed 2026-05-03 with Outcome 2 selected. The audits at the bottom of that document drive Phases 2 and 3 of this plan.

---

## Decisions (recorded 2026-05-03)

Answered open questions, locked in for execution:

1. **Outcome 2 confirmed** — investigation resolved; this plan is approved.
2. **Framework**: React + Vite + TypeScript.
3. **Auth**: ship without auth (matches the current Flask API). Auth is a future plan touching both layers.
4. **Location**: `web/admin-ui/`.
5. **Coexistence**: React UI **coexists** with `dashboards/dashboard-home.json` — neither replaces the other. The Grafana top-link bar's `Home` entry continues to point to the Grafana home dashboard. The React UI gets its own `Admin UI` top-link slot in the Grafana bar (option (a) — see Phase 2 below).

### Phase ordering (revised based on Theme E.2)

Theme E.2 of the investigation: tidying nav + adding missing data links solves "80% of the pain". So phases now run in this order to capture value fastest:

1. **Phase 2 first** — uniform Grafana top-link bar (~1 day, mechanical, coding-agent ready).
2. **Phase 3 second** — missing data links (~1–2 days, ~10 specific edits enumerated in the investigation's drill-down audit).
3. **Phase 1 third** — React admin UI (~1–2 weeks). Scope tightened: Theme C.1 says "start analysis" is the only admin action used today, so Phase 1a ships with rescan triggers + health, deferring Repository List and Compute Service Metrics to Phase 1b.

---

## Problem

Two pains drove this plan (full breakdown in the investigation):

1. **Grafana is the wrong tool for admin/CRUD.** `admin-dashboard.json` triggers rescans by rendering a Grafana stat panel whose `links[]` entry POSTs to `http://localhost:5000/api/rescan/github` — clicking it opens a new browser tab showing JSON. There's no in-place feedback, no progress, no per-repo controls, no service/team mapping editor.
2. **Cross-dashboard navigation is uneven.** Top-link bars are inconsistently populated (1–8 entries per dashboard). There's no breadcrumb. Returning Home, jumping to a sibling, or following a relational link from "repo X has vulnerability Y" to the repo deep-dive only sometimes works.

This plan splits the concerns:

- **Admin workflows leave Grafana** and live in a small React UI that calls the existing Flask API.
- **Analytics stays in Grafana** (those dashboards are good at what they do); this plan only adds the missing data links and a uniform top-link bar so cross-dashboard nav stops being a paper cut.
- The new React UI doubles as the **navigation hub**: a single landing page that links into Grafana dashboards by topic and exposes admin actions from one place.

---

## Scope

### In scope

**Phase 2 — Cross-dashboard nav tidy (Grafana-side, no React) — RUN FIRST:**

- Uniform top-link bar across 11 of 12 dashboards in `dashboards/*.json` (`dashboard-home.json` keeps no bar — it IS Home). Six entries in this fixed order: **Home, Repos, Security, Technology, Admin, Admin UI**.
  - `Home` → `/d/dashboard-home` (type: `dashboards` or `link` with relative URL — see canonical example below)
  - `Repos` → `/d/repo-overview`
  - `Security` → `/d/security-dashboard`
  - `Technology` → `/d/technology-landscape`
  - `Admin` → `/d/admin-dashboard` (Grafana admin observability)
  - `Admin UI` → `http://localhost:8080/` with `targetBlank: true` (new React UI — Phase 1 will serve it on `:8080`. Until Phase 1 ships, this link 404s; opening in a new tab keeps the dead-link impact minimal. **All other entries use `targetBlank: false`.**)
- The links array **fully replaces** any existing `links[]` in each dashboard JSON — do not append.
- Canonical existing example: `security-dashboard.json` already has 6 working internal links — copy that link object shape (`type`, `icon`, `tags`, `targetBlank`, `url`, `title`) and just swap the entry list.
- Replaces the 7 distinct shapes catalogued in the top-link audit (investigation, audit #1).

**Phase 3 — Relational drill-down completeness (Grafana-side, no React) — RUN SECOND:**

For each gap in the investigation's drill-down audit (audit #2), add a `fieldConfig.overrides[]` entry pointing to the natural target dashboard. The high-value gaps:

- `security-dashboard.json` "Top Vulnerable Dependencies" → `library-detail-deep-dive` by package name
- `dependency-vulnerability-portfolio.json` "Top 20 Vulnerable Packages" → `library-detail-deep-dive`
- `dependency-vulnerability-portfolio.json` "Packages Reaching EOL Within 90 Days" → `library-detail-deep-dive`
- `dependency-vulnerability-portfolio.json` "Package Usage by Team" → `library-detail-deep-dive` (and `team-overview` if a team column exists)
- `library-detail-deep-dive.json` "Repositories Using $package_name" → `repo-deep-dive` **(highest-value gap — closes the user's main complaint)**
- `technology-landscape.json` "EOL Technologies with Affected Repo Count" → `repo-deep-dive` (filtered)
- `technology-landscape.json` "Repository Stack (by source)" → `repo-deep-dive`
- `repository-deep-dive.json` "Vulnerability Details" → `library-detail-deep-dive`
- `repository-deep-dive.json` "Technologies (Detected Stack)" → `technology-landscape` (filtered)
- `repository-deep-dive.json` "Open Pull Requests" → `pull-requests`
- `team-overview.json` "Team Performance Summary" → `repo-overview` (filtered by team)
- `service-overview.json` "Technology Stack by Service" → `technology-landscape` (filtered)

Skipped (no obvious target or external link): `repository-deep-dive` Branch Details / Repository Summary / Recent Commits, `library-detail-deep-dive` Health Status / CVE Details.

**Phase 1 — Admin UI MVP (~1–2 weeks) — RUN THIRD:**

- New React + Vite + TypeScript app in `web/admin-ui/`.
- Talks to existing Flask API at `http://localhost:5000`. **No new backend endpoints required.**
- Auth: none (matches the current Flask API).

**Phase 1a (must-ship, narrowed to Theme C.1 actual usage):**

- **Home** — landing page with tiles linking out to each Grafana dashboard.
- **Extraction Control** — trigger GitHub rescan and Azure DevOps rescan. In-page success/failure feedback (toast) replacing the current "open JSON in a new tab" UX.
- **System Health** — render `/health` output; link out to Flower (`http://localhost:5555`) and to the Grafana admin observability dashboard.

**Phase 1b (deferred — only if Phase 1a's value is confirmed):**

- **Compute Service Metrics** trigger on the Extraction Control page.
- **Repository List** — paginated/filterable view of `/api/repositories` with per-row Rescan/Remove buttons.

**Phase 1c (deferred — Tech Radar viewer, depends on Plan 022 shipping):**

- React route at `/radar` rendering the Thoughtworks-format JSON returned by `GET /api/radar` (Plan 022 Part C).
- React route at `/radar/history` rendering the timeline from `GET /api/radar/history` as a sortable table.
- Replaces the now-removed `src/api/radar_viewer.html` from Plan 022. Plan 022's backend is unchanged and ships independently of this phase.
- Rationale: Tech Radar is a leadership-facing artifact (Theme E.1 audience). A React route is much cleaner than an iframe to thoughtworks.com or a static HTML wrapper, and is exactly the kind of high-visibility surface that justifies the React investment beyond admin chores.

**Phase 1d (deferred — Library detail page, depends on Plan 021 endpoints):**

- React route at `/library/:ecosystem/:name` consuming `GET /api/packages/library/<name>/<ecosystem>` (Plan 021 Part C).
- Renders metadata + CVE list + adoption timeline + per-repo usage in a layout the Grafana `library-detail-deep-dive.json` dashboard struggles with (Theme D.1: "panels can feel cluttered and have scrollbars to find links").
- Coexists with the Grafana dashboard — both stay; data links from Phase 3 still point to the Grafana version. The Grafana home dashboard could optionally add a "Library Browser" tile pointing to the React route once shipped.

### Out of scope

- Rebuilding any analytics dashboard in React. Charts stay in Grafana. If the investigation surfaces queries Grafana can't express, that's a separate plan.
- Authentication/authorisation. The current API is unauthenticated; the UI will be too. Adding auth is a future plan touching both layers.
- Editing service ↔ repository mappings. Tempting, but adds a write-path that doesn't exist on the API today. Punt to a follow-up plan if Theme C surfaces it as a real need.
- Server-side rendering, mobile-first design, i18n, dark/light themes beyond defaults.
- Deploying behind a real domain or TLS — for MVP, the UI is served on `localhost` like everything else.

---

## API surface used (read-only confirmation)

All endpoints already exist; this is a contract list, not new work.

| Endpoint                                  | Used by            |
| ----------------------------------------- | ------------------ |
| `POST /api/rescan/github`                 | Extraction Control |
| `POST /api/rescan/azure-devops`           | Extraction Control |
| `POST /api/rescan/repository/<repo_id>`   | Repository List    |
| `DELETE /api/rescan/repository/<repo_id>` | Repository List    |
| `GET /api/repositories`                   | Repository List    |
| `POST /api/compute/service-metrics`       | Extraction Control |
| `GET /health`                             | System Health      |

If any of these grow query parameters to support the UI better (e.g. `/api/repositories?stale=true`), that's a small follow-up addition, not blocking.

---

## Architecture

### Where it lives

```
web/
  admin-ui/
    src/
      pages/        ← Home, Extraction, Repos, Health
      components/   ← Shared UI primitives
      api/          ← Typed wrappers around the Flask endpoints
    public/
    package.json
    vite.config.ts
    tsconfig.json
    Dockerfile      ← multi-stage: Node build → nginx static serve
```

### How it talks to the backend

- Dev: Vite dev server on `:5173`, proxies `/api` and `/health` to `http://localhost:5000`. CORS not needed because of the proxy.
- Prod (in-stack): nginx serving the static build on `:8080`, with `/api` and `/health` reverse-proxied to the Flask container. Added as a new service `admin-ui` to `docker-compose.yml`.

### Architecture-Guardian alignment

- The new code is a frontend. It does not import from `src/extractors/`, `src/analyzers/`, `src/database/`, or `src/workflows/`. It only consumes HTTP endpoints exposed by `src/api/`.
- No changes to extractor/analyzer/database/workflow boundaries. (Principle 2 satisfied — boundaries unchanged.)
- No changes to the test architecture in `tests/contract/` or `tests/implementation/`. New frontend tests live alongside the frontend code (`web/admin-ui/src/**/*.test.tsx`) and run independently of the Python suite. (Principle 1 satisfied — Python contract tests untouched.)

### Tech-stack rationale

| Choice                           | Why                                                                                               | What we considered and rejected                                                               |
| -------------------------------- | ------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| React + Vite + TypeScript        | Standard, fast dev loop, large hire-pool, types catch most refactor regressions                   | Next.js (overkill — no SSR needed); Svelte (smaller community for a long-lived internal tool) |
| TanStack Query for data fetching | Built-in caching, refetch-on-focus, mutation feedback — good fit for "trigger rescan, show toast" | Plain `fetch` (would re-implement caching by hand); Redux Toolkit Query (heavier than needed) |
| Tailwind for styling             | Lets us ship fast without a design system                                                         | A real component library (MUI, Chakra) — too heavyweight for a small internal tool            |
| Vitest + React Testing Library   | Standard for Vite projects                                                                        | Jest (works fine but Vitest integrates with Vite config natively)                             |

If the user has a strong preference for Vue/Svelte/HTMX, swap before implementation — none of the structural decisions in this plan depend on React specifically.

---

## Phased delivery

Phases ship in order — Phase 2 first (highest value-per-day), then 3, then 1. Phases 2 and 3 are coding-agent ready.

### Phase 2 — Uniform Grafana top-link bar (~1 day) — FIRST

Edit each `dashboards/*.json` (except `dashboard-home.json`) to have the same 6-entry `links[]` array as specified in the Scope section. Mechanical change.

### Phase 3 — Missing drill-downs (~1–2 days) — SECOND

For each gap enumerated in the Scope section, add a `fieldConfig.overrides[]` entry on the relevant table panel. Each gap is a small isolated JSON edit. Use the Plan 021 pattern (existing data link on `security-dashboard.json` "Repository Security Overview") as the canonical example.

### Phase 1 — Admin UI MVP (~1–2 weeks) — THIRD

1. Scaffold `web/admin-ui/` with Vite + React + TS + Tailwind + TanStack Query + Vitest.
2. Implement the API client wrappers (typed) for the Phase 1a endpoints (3 endpoints: github rescan, azure-devops rescan, health).
3. Implement Home, Extraction Control, System Health pages.
4. Add `Dockerfile`, `nginx.conf`, and `admin-ui` service to `docker-compose.yml`.
5. Add a job to `.github/workflows/` (or extend existing) to: install, build, type-check, run unit tests on PRs touching `web/admin-ui/**`.
6. Phase 1b (Compute Metrics trigger + Repository List page) added in a follow-up PR if Phase 1a's value is confirmed.

---

## Acceptance criteria

### Phase 2

- [ ] Every `dashboards/*.json` except `dashboard-home.json` has identical 6-entry `links[]` array (Home / Repos / Security / Technology / Admin / Admin UI) in that order.
- [ ] `dashboard-home.json` retains no top-link bar.
- [ ] All entries use `targetBlank=false`.
- [ ] Manual click-through: from each dashboard, each top-link entry lands on the right destination (Admin UI link 404s until Phase 1 ships — acceptable).
- [ ] JSON sanity per Plan 023 pattern: `python -c "import json; json.load(open('dashboards/<file>.json'))"` exits 0 for each file.

### Phase 3

- [ ] Every gap listed in the Scope section's Phase 3 list has a working data link.
- [ ] Skipped panels (Branch Details, Repository Summary, Recent Commits, Health Status, CVE Details) are documented inline as deliberate skips.
- [ ] Manual click-through: pick one gap-fix per dashboard, confirm the data link opens the right target with the right filter applied.

### Phase 1a (must-ship MVP)

- [ ] `docker compose up admin-ui` serves the UI at a known port (e.g. `:8080`).
- [ ] Home page renders tiles linking to each existing Grafana dashboard.
- [ ] Clicking "Trigger GitHub rescan" calls `POST /api/rescan/github`, shows an in-page success toast with the returned `task_id`, and does **not** open a new browser tab.
- [ ] Same for Azure DevOps rescan.
- [ ] System Health page shows `/health` output and a working "Open Flower" link.
- [ ] `npm run typecheck` and `npm run test` exit 0 in `web/admin-ui/`.
- [ ] CI runs frontend lint/typecheck/test on PRs touching `web/admin-ui/**`.
- [ ] No changes to `src/extractors/**`, `src/analyzers/**`, `src/database/**`, `src/workflows/**`. (Architecture boundary check.)
- [ ] Python test suite (`bash scripts/run-tests-docker.sh`) still passes — this plan adds no Python code, but verify nothing was broken by Docker Compose changes.

### Phase 1b (follow-up, optional)

- [ ] Compute Service Metrics trigger added to Extraction Control with toast feedback.
- [ ] Repository List page renders rows from `/api/repositories`, supports filter-by-name, and per-row Rescan/Remove buttons work and show feedback.

---

## Test plan

### Frontend (Phase 1)

- Unit-test each API client wrapper against a mocked `fetch` — covers shape of request and parsing of response.
- Component-test each page with TanStack Query in test mode and the API client mocked — covers happy path + error path (e.g. rescan API returns 500).
- Manual smoke-test in the browser: every button performs the right network call (verified via DevTools), every dashboard tile lands on the right `/d/...`.

### Grafana (Phases 2–3)

- JSON sanity per Plan 023's pattern: `python -c "import json; json.load(open('dashboards/<file>.json'))"`.
- `jq` checks that all `links[]` arrays match the canonical 5-entry shape.
- Visual check: stack up, click every link from every dashboard.

### Cross-cutting

- `bash scripts/run-tests-docker.sh` still green (no Python changes expected; this is a regression check on the Compose changes).

---

## Risks

| Risk                                                                                     | Probability | Mitigation                                                                                                                                                                      |
| ---------------------------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Phase 2 dead-link `Admin UI` 404s confuse users between Phase 2 ship and Phase 1 ship    | Low         | Internal-only tool, small audience. If Phase 1 slips, change `Admin UI` link target to `/d/admin-dashboard` as a placeholder.                                                   |
| API endpoints prove insufficient (e.g. `/api/repositories` doesn't expose enough fields) | Medium      | Each gap is a small additive endpoint change in `src/api/rescan.py`. Defer until Phase 1b surfaces the specific need.                                                           |
| Maintenance burden of a second codebase outweighs benefit                                | Medium      | Phase 1a is deliberately tiny (3 pages, no auth, no fancy state). Phase 1b only ships if 1a's value is real.                                                                    |
| Auth becomes urgent later                                                                | Medium      | Plan now: when the Flask API gets auth, add a login page and an `Authorization` header to the API client. Both are well-trodden patterns; not a blocker today.                  |
| nginx + reverse proxy complexity in Compose                                              | Low         | Pattern is standard; many examples online. Worst case, serve via Vite preview in dev and skip nginx until prod really matters.                                                  |

---

## File manifest (Phase 1)

```
web/admin-ui/
  Dockerfile                         (new)
  nginx.conf                         (new)
  package.json                       (new)
  tsconfig.json                      (new)
  vite.config.ts                     (new)
  tailwind.config.ts                 (new)
  index.html                         (new)
  src/
    main.tsx                         (new)
    App.tsx                          (new)
    pages/
      HomePage.tsx                   (new)
      ExtractionPage.tsx             (new)
      RepositoriesPage.tsx           (new)
      HealthPage.tsx                 (new)
    components/
      Layout.tsx                     (new)
      Toast.tsx                      (new)
      ApiButton.tsx                  (new)
    api/
      client.ts                      (new)
      types.ts                       (new)
docker-compose.yml                   (modified — add admin-ui service)
.github/workflows/frontend.yml       (new — or extend tests.yml)
```

**Estimated effort**: Phase 1 ~5–10 working days for one developer; Phases 2–3 ~2–3 days combined and parallelisable.

---

## Open questions

All previously open questions resolved 2026-05-03 — see the **Decisions** section near the top of this document.
