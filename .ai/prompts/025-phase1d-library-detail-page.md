# Copilot Agent Prompt — Plan 025 Phase 1d: Library Detail Page

> **Usage**: Paste the contents of the **Prompt** section below into GitHub
> Copilot agent. Everything above the horizontal rule is meta-context for the
> human; everything below it is the agent instruction.
>
> **Runs in parallel with** [025-phase1c-tech-radar-viewer.md](025-phase1c-tech-radar-viewer.md).
> The only file both tasks edit is `web/admin-ui/src/App.tsx`. See the
> **Parallel execution** section — keep to the assigned insertion anchors and the
> two PRs will auto-merge.

**Branch to create**: `feature/025-phase1d-library-detail-page`
**PR target**: `main`
**PR title**: `Plan 025 Phase 1d: Library detail page`

---

## Prompt

You are implementing **Phase 1d of Plan 025** for the `azure_devops_analyzer`
repository. The plan is at `.ai/plans/025-bespoke-admin-and-navigation-ui.md`
("Task D" under *What's next*) — read it first.

You are adding **one route** to the **existing** React admin UI at
`web/admin-ui/`:

- `/library/:ecosystem/:name` — a detail page for a single library/package:
  metadata + CVE list + adoption-by-team + per-repo usage.

This is **frontend-only**. Do **NOT** touch anything under `src/`, `tests/`,
`dashboards/`, or `database/`. The backend endpoint already exists and is
unchanged. It coexists with the Grafana `library-detail-deep-dive.json` dashboard
— both stay; Phase 3's data links still point at the Grafana version.

---

### Backend endpoint (already exists — read-only contract)

**`GET /api/packages/library/<name>/<ecosystem>`** — note the path order is
**name first, then ecosystem**. Returns:

```jsonc
{
  "metadata": { "package_name": "react", "ecosystem": "npm",
                "latest_version": "18.3.1", "is_eol": false, "eol_date": null },
  "cves": [
    { "cve_id": "CVE-2024-1234", "severity": "HIGH", "summary": "...",
      "fixed_in_version": "18.3.0", "published_date": "2024-03-01",
      "exposed_repo_count": 4 }
  ],
  "usage": [
    { "repo_id": "...", "team_name": "Payments", "version": "18.2.0",
      "has_known_vulnerabilities": true }
  ],
  "by_team": [
    { "team_name": "Payments", "repo_count": 6, "exposed_repos": 2,
      "versions_in_use": ["18.2.0", "18.3.1"] }
  ]
}
```

If the package does not exist, the endpoint returns **HTTP 404** with
`{"status": "error", "message": "Package not found"}`. Handle this with a clean
"Package not found" message, not a crash.

> **Route vs endpoint param order — do not get this wrong.** The React route is
> `/library/:ecosystem/:name` (ecosystem first in the URL), but the API path is
> `/api/packages/library/<name>/<ecosystem>` (name first). Read both
> `useParams()` values and pass them to the client in the **API's** order.

---

### Files to create

```
web/admin-ui/
  src/
    api/
      library.ts                  ← typed client + response types (THIS feature only)
      library.test.ts
    pages/
      LibraryDetailPage.tsx
      LibraryDetailPage.test.tsx
  e2e/
    library.spec.ts
```

> **Note**: put the library API client + its types in a **new** `src/api/library.ts`
> file. Do **not** append to the shared `src/api/client.ts` / `src/api/types.ts`
> — that keeps this PR conflict-free against the parallel Phase 1c PR.

### Files to modify (minimal, additive)

- `web/admin-ui/src/App.tsx` — add **one** route. See **Parallel execution** for
  the exact anchor. This is the only shared file.

You do **not** need to modify `Layout.tsx`, `HomePage.tsx`, or `package.json`.
(`/library/:ecosystem/:name` is a parametric leaf route reached by direct URL or a
future drill-down link — a nav link/tile would need params it doesn't have. A
dedicated entry point is explicitly a future enhancement; see Out of scope.)

---

### Page (`LibraryDetailPage.tsx`)

- Read `ecosystem` and `name` from `useParams()`.
- `useQuery` against `getLibraryDetail(name, ecosystem)` from `api/library.ts`.
- States: loading, error (generic 5xx), **not-found** (404 → "Package not found"),
  and success.
- On success render four sections:
  1. **Header / metadata** — package name, ecosystem, latest version, and an
     EOL badge when `is_eol` is true (show `eol_date` if present).
  2. **CVEs** — table of `cves` (cve_id, severity, summary, fixed_in_version,
     published_date, exposed_repo_count). Empty → "No known CVEs".
  3. **Adoption by team** — table of `by_team` (team_name, repo_count,
     exposed_repos, versions_in_use joined as a comma list).
  4. **Per-repo usage** — table of `usage` (repo_id, team_name, version, a
     "vulnerable" indicator when `has_known_vulnerabilities`).

Use Tailwind utility classes; match the visual style of the existing
`RepositoriesPage.tsx` (tables, badges, spacing).

### Tech stack (locked — match the existing app)

React 18 + Vite 5 + TS (strict) · Tailwind v3 (utility classes only) · TanStack
Query v5 · React Router v6 · Vitest + `@testing-library/react` · Playwright (e2e).
**No new runtime dependencies.**

---

### API client (`src/api/library.ts`)

Export one typed function plus its response types:

```typescript
// GET /api/packages/library/<name>/<ecosystem>
export async function getLibraryDetail(name: string, ecosystem: string): Promise<LibraryDetail>
```

`encodeURIComponent` both path segments. Throw an `Error` with the response body
text on non-2xx (mirror the `request()` helper in `src/api/client.ts`), but the
page must be able to distinguish a 404 from other errors (e.g. check the thrown
message or expose the status) so it can show "Package not found".

---

### Tests

- **`api/library.test.ts`**: mock `fetch`; assert the request URL is
  `/api/packages/library/<name>/<ecosystem>` in the **correct order**; assert the
  parsed body returns; assert non-2xx throws; assert 404 is distinguishable.
- **`pages/LibraryDetailPage.test.tsx`**: mock `api/library.ts`. Cover loading,
  the populated happy path (all four sections render with sample data), the empty
  `cves` case ("No known CVEs"), the 404 → "Package not found" path, and a generic
  error path. Assert the EOL badge appears when `is_eol` is true.
- **`e2e/library.spec.ts`**: follow the pattern in the existing `e2e/*.spec.ts`
  files (mock the API the same way they do). Navigate to a
  `/library/npm/some-package` URL and assert the metadata header renders.

---

### Parallel execution — `App.tsx` is the only shared file

This task runs **at the same time** as Phase 1c. Both add a route to
`web/admin-ui/src/App.tsx`. To let git auto-merge, use these **exact anchors**:

- **Import**: add your import immediately **after** the existing
  `import RepositoriesPage from './pages/RepositoriesPage'` line:
  ```tsx
  import LibraryDetailPage from './pages/LibraryDetailPage'
  ```
- **Route**: add yours immediately **after** the existing
  `<Route path="/repositories" element={<RepositoriesPage />} />` line:
  ```tsx
  <Route path="/library/:ecosystem/:name" element={<LibraryDetailPage />} />
  ```

Phase 1c uses different anchors (after `HealthPage` / `/health`), so the two diffs
do not overlap. If your PR merges second and git still flags a conflict in
`App.tsx`, it is a trivial resolve — keep both sets of routes.

Do **not** edit `src/api/client.ts`, `src/api/types.ts`, `src/api/client.test.ts`,
`src/components/Layout.tsx`, `src/pages/HomePage.tsx`, `package.json`, or any
Phase 1c file.

---

### Architecture constraint

`web/admin-ui` code must **never** import from `src/`, `tests/`, or
`dashboards/`. It talks to the Flask API over HTTP only. If you reach outside
`web/admin-ui/`, stop — that's wrong.

---

### Out of scope

- Phase 1c (Tech Radar viewer) — separate parallel PR.
- An entry point for the page (nav link, HomePage tile, or a `/library` search
  index). The page is reached by direct URL / future drill-down for this PR;
  a "Library Browser" entry is a later enhancement per the plan.
- Any backend change. The endpoint exists and is correct.
- Editing the Grafana `library-detail-deep-dive.json` dashboard (it stays).
- Auth, dark mode, i18n, mobile-first layout.

---

### Acceptance checklist (reviewer will verify)

- [ ] `/library/:ecosystem/:name` renders metadata, CVEs, adoption-by-team, and per-repo usage
- [ ] URL params (`ecosystem`, `name`) are passed to the API in the correct order (name, ecosystem)
- [ ] EOL badge shows when `is_eol` is true; "No known CVEs" shows when `cves` is empty
- [ ] 404 from the API renders a clean "Package not found", not a crash
- [ ] New API client lives in `src/api/library.ts` (shared `client.ts`/`types.ts` untouched)
- [ ] `App.tsx` edits use the assigned anchors (after `/repositories`)
- [ ] No new runtime dependencies added
- [ ] No files changed under `src/`, `tests/`, `dashboards/`, or `database/`
- [ ] `npm run typecheck`, `npm run test -- --run`, `npm run build`, and `npm run e2e` all exit 0 in `web/admin-ui/`

---

## ACCEPTANCE — DO NOT STOP UNTIL CI IS GREEN

This is non-negotiable. Previous Copilot agents on this project have declared work
done while CI was red, costing the maintainer 2+ feedback rounds per task.

1. **Before pushing**, from `web/admin-ui/` run locally and get all four green:
   `npm run typecheck` · `npm run test -- --run` · `npm run build` · `npm run e2e`
   (run `npx playwright install chromium` first if needed).
2. After pushing and opening the PR, run: `gh pr checks <PR#> --watch`.
3. If any required check fails:
   1. `gh run view <run-id> --log-failed` to read the failure.
   2. Fix the **root cause**. Do **NOT** `--no-verify`, skip/weaken tests, or
      delete assertions to make CI pass.
   3. Commit, push, repeat from step 2.
4. Required check: the **Frontend CI** workflow (`.github/workflows/frontend.yml`),
   which runs typecheck + test + build + Playwright e2e on `web/admin-ui/**`.
5. Only declare done when: all required checks are green, the PR has no merge
   conflicts, and the final PR comment links to the green check run.

If you cannot get CI green after 3 attempts, stop and post a comment explaining
what you tried and what's blocking.

---

### Estimated size

~2–3 days. Mostly a data-rendering page over one endpoint. The two things to get
right: the **name/ecosystem param order** and the **404 → "Package not found"**
distinction.
