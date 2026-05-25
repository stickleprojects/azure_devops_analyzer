# Copilot Agent Prompt — Plan 025 Phase 1c: Tech Radar Viewer (visual radar)

> **Usage**: Paste the contents of the **Prompt** section below into GitHub
> Copilot agent. Everything above the horizontal rule is meta-context for the
> human; everything below it is the agent instruction.
>
> **Runs in parallel with** [025-phase1d-library-detail-page.md](025-phase1d-library-detail-page.md).
> The only file both tasks edit is `web/admin-ui/src/App.tsx`. See the
> **Parallel execution** section — keep to the assigned insertion anchors and the
> two PRs will auto-merge.

**Branch to create**: `feature/025-phase1c-tech-radar-viewer`
**PR target**: `main`
**PR title**: `Plan 025 Phase 1c: Tech Radar viewer (visual Zalando radar)`

---

## Prompt

You are implementing **Phase 1c of Plan 025** for the `azure_devops_analyzer`
repository. The plan is at `.ai/plans/025-bespoke-admin-and-navigation-ui.md`
("Task C" under *What's next*) — read it first.

You are adding two routes to the **existing** React admin UI at `web/admin-ui/`:

- `/radar` — renders an **actual visual radar** (the circular blip diagram).
- `/radar/history` — renders the ring-movement timeline as a sortable table.

This is **frontend-only**. Do **NOT** touch anything under `src/`, `tests/`,
`dashboards/`, or `database/`. The backend endpoints already exist and are
unchanged.

---

### Renderer: vendored Zalando tech-radar (MIT) — NOT Thoughtworks BYOR

Render the radar with the **MIT-licensed** D3 renderer from
<https://github.com/zalando/tech-radar> (single file `radar.js`, exposes
`radar_visualization()`, uses D3 v7).

> **Why Zalando and not Thoughtworks build-your-own-radar:** BYOR is AGPL-3.0,
> which would copyleft this frontend bundle. The maintainer rejected that.
> Zalando's radar is the same Thoughtworks-derived visual but MIT — no copyleft.
> **Do not** substitute BYOR, an iframe to thoughtworks.com, or a plain list.

**Vendoring steps:**

1. Download `radar.js` from a pinned Zalando release (e.g. `release/radar-0.12.js`)
   into `web/admin-ui/src/vendor/zalando-radar/radar.js`. **Record the exact
   release/commit** in a comment at the top of the file and **keep its MIT
   copyright header** intact.
2. The file is written as a browser global, not an ES module. Lightly adapt it to
   `export function radar_visualization(config) { ... }` (MIT permits
   modification). Do not rewrite its drawing logic — only the export seam.
3. Add `d3` (v7) to `dependencies` and `@types/d3` to `devDependencies` in
   `web/admin-ui/package.json`. Run `npm install` so `package-lock.json` updates.
4. Add a `web/admin-ui/THIRD_PARTY_NOTICES.md` (or append if it exists) crediting
   Zalando tech-radar under MIT with the pinned version.

---

### Backend endpoints (already exist — read-only contract)

**`GET /api/radar`** returns Thoughtworks-format JSON:

```jsonc
{
  "documentTitle": "Organization Tech Radar",
  "quadrants": [ {"name": "Infrastructure"}, {"name": "Platforms"},
                 {"name": "Tools"}, {"name": "Languages & Frameworks"} ],
  "rings": [ {"name": "Adopt",  "color": "#00AA00"},
             {"name": "Trial",  "color": "#00FFFF"},
             {"name": "Assess", "color": "#FFFF00"},
             {"name": "Hold",   "color": "#FF0000"} ],
  "entries": [
    { "id": 1, "label": "react", "description": "...",
      "quadrant": "Languages & Frameworks", "ring": "Trial",
      "isNew": false, "isMoved": true }
  ],
  "publication": { "id": 1, "version": "...", "date": "2026-05-25", "published_by": "..." }
}
```

When no radar has been published yet, `entries` is `[]` (and there is no
`publication` key). Handle this — show a "No radar published yet" placeholder,
**not** a broken/empty chart.

**`GET /api/radar/history`** returns:

```jsonc
{ "timeline": [
  { "publication_date": "2026-05-25", "package_name": "react", "ecosystem": "npm",
    "prior_ring": "Assess", "current_ring": "Trial",
    "repo_count_delta": 3, "vulnerability_change": 0 }
] }
```

---

### Files to create

```
web/admin-ui/
  THIRD_PARTY_NOTICES.md                    ← Zalando MIT credit (create or append)
  src/
    vendor/zalando-radar/radar.js           ← vendored MIT renderer (ESM-adapted)
    api/
      radar.ts                              ← typed client + response types (THIS feature only)
      radar.test.ts
    lib/
      radarMapping.ts                       ← pure: /api/radar response → Zalando config
      radarMapping.test.ts
    components/
      RadarChart.tsx                        ← React wrapper around radar_visualization()
      RadarChart.test.tsx
    pages/
      RadarPage.tsx
      RadarPage.test.tsx
      RadarHistoryPage.tsx
      RadarHistoryPage.test.tsx
  e2e/
    radar.spec.ts
```

> **Note**: put the radar API client + its types in a **new** `src/api/radar.ts`
> file. Do **not** append to the shared `src/api/client.ts` / `src/api/types.ts`
> — that keeps this PR conflict-free against the parallel Phase 1d PR.

### Files to modify (minimal, additive)

- `web/admin-ui/package.json` — add `d3` + `@types/d3` (only this task touches it).
- `web/admin-ui/src/components/Layout.tsx` — add **one** nav link
  `{ to: '/radar', label: 'Tech Radar' }` to the `navLinks` array (only this task
  touches it).
- `web/admin-ui/src/App.tsx` — see **Parallel execution** for the exact anchor.

---

### Data mapping (`src/lib/radarMapping.ts`)

Zalando's `radar_visualization()` uses **numeric** quadrant/ring indices; the API
uses **names**. Write a pure function `toRadarConfig(api)` that converts:

- `quadrants`: pass through `[{name}]` (4). Placement order is cosmetic.
- `rings`: pass through `[{name, color}]` indexed 0→3 inner→outer. The API order
  Adopt / Trial / Assess / Hold already matches (Adopt = innermost = index 0).
  Pass each ring's `color` through.
- `entries`: map each blip to
  `{ label: e.label, quadrant: <index of e.quadrant in quadrants>, ring: <index of e.ring in rings>, moved: e.isNew ? 2 : (e.isMoved ? 1 : 0), active: true }`.
  (Zalando `moved`: `2` = new, `1` = moved in, `0` = no change, `-1` = moved out.
  The API gives no moved-out signal, so `-1` is unused.)
- If a blip's `quadrant`/`ring` name is not found in the arrays, drop it and
  `console.warn` — never produce `quadrant: -1`.

`RadarChart.tsx` takes the API response (or the mapped config) as a prop, and in a
`useEffect` calls `radar_visualization()` against a ref'd `<svg id="radar">`.
Clear the SVG's children on unmount / before re-render so it doesn't double-draw.

---

### Pages

- **`RadarPage.tsx`** — `useQuery` against `getRadar()` (from `api/radar.ts`).
  Loading + error states. If `entries.length === 0`, render the placeholder.
  Otherwise render `<RadarChart>`. Show the publication date/version if present.
- **`RadarHistoryPage.tsx`** — `useQuery` against `getRadarHistory()`. Render a
  table of the `timeline` rows. Make at least the `publication_date` and
  `package_name` columns **sortable** (click header toggles asc/desc). Loading +
  error + empty states.

### Tech stack (locked — match the existing app)

React 18 + Vite 5 + TS (strict) · Tailwind v3 (utility classes only) · TanStack
Query v5 · React Router v6 · Vitest + `@testing-library/react` · Playwright (e2e).
Plus `d3` v7 for the radar. No other new runtime deps.

---

### Tests

- **`lib/radarMapping.test.ts`** (the important one): quadrant→index and
  ring→index conversion; `moved` derivation for new / moved / unchanged blips;
  colour pass-through; empty `entries`; unknown quadrant/ring name dropped.
- **`api/radar.test.ts`**: mock `fetch`; assert correct URL + that a non-2xx
  throws an `Error` with the body text (mirror `src/api/client.ts`'s `request()`).
- **`pages/RadarPage.test.tsx`**: mock `api/radar.ts`. Assert the empty-state
  placeholder renders when `entries: []`; assert a populated response mounts the
  chart (an `<svg>` appears). Assert the error path shows an error message.
- **`pages/RadarHistoryPage.test.tsx`**: mock the client; assert rows render and
  that clicking a sortable header reorders them.
- **`components/RadarChart.test.tsx`**: smoke test — mounts without throwing and
  emits an `<svg>`. **Do not** assert on D3-computed geometry (jsdom doesn't lay
  out SVG).
- **`e2e/radar.spec.ts`**: follow the pattern in the existing `e2e/*.spec.ts`
  files (mock the API the same way they do). Verify `/radar` shows a radar (or the
  empty placeholder) and `/radar/history` shows the table.

---

### Parallel execution — `App.tsx` is the only shared file

This task runs **at the same time** as Phase 1d. Both add a route to
`web/admin-ui/src/App.tsx`. To let git auto-merge, use these **exact anchors**:

- **Import**: add your imports immediately **after** the existing
  `import HealthPage from './pages/HealthPage'` line:
  ```tsx
  import RadarPage from './pages/RadarPage'
  import RadarHistoryPage from './pages/RadarHistoryPage'
  ```
- **Routes**: add yours immediately **after** the existing
  `<Route path="/health" element={<HealthPage />} />` line:
  ```tsx
  <Route path="/radar" element={<RadarPage />} />
  <Route path="/radar/history" element={<RadarHistoryPage />} />
  ```

Phase 1d uses different anchors (after `RepositoriesPage` / `/repositories`), so
the two diffs do not overlap. If your PR merges second and git still flags a
conflict in `App.tsx`, it is a trivial 2-line resolve — keep both sets of routes.

Do **not** edit `src/api/client.ts`, `src/api/types.ts`, `src/api/client.test.ts`,
`src/pages/HomePage.tsx`, or any Phase 1d file.

---

### Architecture constraint

`web/admin-ui` code must **never** import from `src/`, `tests/`, or
`dashboards/`. It talks to the Flask API over HTTP only. If you reach outside
`web/admin-ui/`, stop — that's wrong.

---

### Out of scope

- Phase 1d (Library detail page) — separate parallel PR.
- The radar **export** endpoint (`/api/radar/export`) — not part of this phase.
- Any backend change. The endpoints exist and are correct.
- Auth, dark mode, i18n, mobile-first layout.
- A HomePage tile for the radar — the Layout nav link is the entry point.

---

### Acceptance checklist (reviewer will verify)

- [ ] `/radar` renders the **visual** Zalando radar (circular blip diagram), not a list/iframe
- [ ] Empty publication (`entries: []`) shows a placeholder, not a broken chart
- [ ] `/radar/history` renders a sortable timeline table
- [ ] "Tech Radar" nav link appears in `Layout.tsx`
- [ ] `radar.js` is vendored with its MIT header + pinned version; `THIRD_PARTY_NOTICES.md` credits it
- [ ] `radarMapping.ts` is a pure, unit-tested function (name→index, `moved` derivation, empty/unknown handling)
- [ ] `d3` added to `package.json`; `package-lock.json` regenerated
- [ ] New API client lives in `src/api/radar.ts` (shared `client.ts`/`types.ts` untouched)
- [ ] `App.tsx` edits use the assigned anchors (after `/health`)
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
what you tried and what's blocking. If the Zalando `radar.js` proves hard to
adapt to ESM, **stop and ask** before substituting a different renderer — the MIT
licensing is the whole reason it was chosen.

---

### Estimated size

~3–4 days. The vendored-renderer ESM seam and the name→index mapping are the
two fiddly parts — get `radarMapping.test.ts` green first, then wire the chart.
