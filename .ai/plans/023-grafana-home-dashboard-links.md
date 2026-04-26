# Plan 023: Add Missing Dashboards to Grafana Home Navigation

## Status: DESIGN (Ready for Implementation)

**Implements**: Navigation gaps on the Grafana Home dashboard. No new functional requirement; pure UX/discoverability fix.

---

## Problem

Four existing Grafana dashboards are not linked from the home dashboard's "Dashboard Navigation" section:

- `security-dashboard` (UID `security-dashboard`) — pre-existing, never linked
- `technology-landscape` (UID `technology-landscape`) — pre-existing, never linked
- `dependency-vulnerability-portfolio` (UID `dep-vuln-portfolio`) — added by Plan 021 (PR #73, merged 2026-04-26)
- `library-detail-deep-dive` (UID `library-detail-deep-dive`) — added by Plan 021 (PR #73, merged 2026-04-26)

The home dashboard ([dashboards/dashboard-home.json](../../dashboards/dashboard-home.json)) currently shows tiles for: Repository Overview, Repository Deep-Dive, Pull Requests, Contributors, Team Overview, Service Overview, and Administration. Users hitting Home today have no route to the four dashboards above except Grafana's general search or a known URL.

---

## Scope

### In scope

Add four text-panel navigation tiles to `dashboards/dashboard-home.json`:

1. **Security Dashboard** → `/d/security-dashboard`
2. **Technology Landscape** → `/d/technology-landscape`
3. **Dependency Vulnerability Portfolio** → `/d/dep-vuln-portfolio`
4. **Library Detail Deep-Dive** → `/d/library-detail-deep-dive`

### Out of scope (possible follow-ups)

- **Plan 022 Tech Radar** ships as API endpoints only (`/api/radar`, `/api/radar/history`, `/api/radar/export`) — there is no Grafana dashboard for it yet. A future plan could either (a) build a Grafana radar panel using the existing `radar_blips` table, or (b) link to an external Thoughtworks-format viewer. Not in this plan.

---

## Current home layout

The home dashboard uses a 24-column Grafana grid. Existing layout:

```
y=0..2   [ Welcome banner (id=1, w=24, h=3) ]
y=3..6   [ Total Repos | Active Contribs | Commits | PRs | Teams | Open PRs ]   (6 stat cards, w=4, h=4)
y=7      [ "Dashboard Navigation" row separator (id=8, w=24, h=1) ]
y=8..13  [ Repository Overview (id=9, x=0)  | Repository Deep-Dive (id=10, x=8)  | Pull Requests (id=11, x=16) ]   (each w=8, h=6)
y=14..19 [ Contributors (id=12, x=0)        | Team Overview (id=13, x=8)         | Service Overview (id=14, x=16) ]
y=20..25 [ Administration (id=15, x=0)      | (empty)                            | (empty) ]
```

Row 3 of the navigation has two empty slots, and we need four new tiles — so one new row is required. **No existing panel moves**; Administration stays at `(y=20, x=0)`.

### Target layout

Group strategically: Security and Technology Landscape sit alongside Administration on the existing row (all "operational/strategic" views). The two dependency tiles share a new row directly below.

```
y=20..25 [ Administration (id=15, x=0)               | Security Dashboard (id=16, x=8)         | Technology Landscape (id=17, x=16) ]
y=26..31 [ Dependency Vulnerability Portfolio (id=18, x=0) | Library Detail Deep-Dive (id=19, x=8) | (empty) ]
```

Rationale for ordering:

- Security & Tech Landscape are top-level portfolio views → natural fit next to Administration.
- Dependency Portfolio is the entry point; Library Detail Deep-Dive is its drill-down companion → kept adjacent.
- The trailing empty cell at `(y=26, x=16)` leaves room for one future tile (e.g. a Tech Radar dashboard) without further reflow.

---

## Implementation

### File: `dashboards/dashboard-home.json`

Append four new text panels to the `panels` array, after the existing Administration panel (id=15). Use ids `16`, `17`, `18`, `19` (next available — confirmed unique by grepping the file). Order panels in the JSON in the same order they read visually (left-to-right, top-to-bottom): Security → Technology Landscape → Dependency Portfolio → Library Detail.

#### Panel 16 — Security Dashboard

```json
{
  "datasource": {
    "type": "postgres",
    "uid": "TimescaleDB"
  },
  "fieldConfig": {
    "defaults": {
      "color": { "mode": "thresholds" },
      "mappings": [],
      "thresholds": {
        "mode": "absolute",
        "steps": [{ "color": "green", "value": null }]
      }
    },
    "overrides": []
  },
  "gridPos": { "h": 6, "w": 8, "x": 8, "y": 20 },
  "id": 16,
  "options": {
    "content": "# Security Dashboard\n\n**Org-wide vulnerability and EOL exposure**\n\n- Total vulnerabilities and EOL dependencies\n- Severity distribution and top vulnerable repos\n- Vulnerability trends over time\n- Repository security overview with drilldown\n\n[View Security Dashboard →](/d/security-dashboard)",
    "mode": "markdown"
  },
  "pluginVersion": "11.0.0",
  "title": "Security Dashboard",
  "type": "text"
}
```

#### Panel 17 — Technology Landscape

```json
{
  "datasource": {
    "type": "postgres",
    "uid": "TimescaleDB"
  },
  "fieldConfig": {
    "defaults": {
      "color": { "mode": "thresholds" },
      "mappings": [],
      "thresholds": {
        "mode": "absolute",
        "steps": [{ "color": "green", "value": null }]
      }
    },
    "overrides": []
  },
  "gridPos": { "h": 6, "w": 8, "x": 16, "y": 20 },
  "id": 17,
  "options": {
    "content": "# Technology Landscape\n\n**Languages, frameworks, and EOL technology footprint**\n\n- Top languages and frameworks by repo count\n- Distinct technologies in use across the portfolio\n- EOL technologies with affected-repo counts\n- Repository stack heatmap by source\n\n[View Technology Landscape →](/d/technology-landscape)",
    "mode": "markdown"
  },
  "pluginVersion": "11.0.0",
  "title": "Technology Landscape",
  "type": "text"
}
```

#### Panel 18 — Dependency Vulnerability Portfolio

```json
{
  "datasource": {
    "type": "postgres",
    "uid": "TimescaleDB"
  },
  "fieldConfig": {
    "defaults": {
      "color": { "mode": "thresholds" },
      "mappings": [],
      "thresholds": {
        "mode": "absolute",
        "steps": [{ "color": "green", "value": null }]
      }
    },
    "overrides": []
  },
  "gridPos": { "h": 6, "w": 8, "x": 0, "y": 26 },
  "id": 18,
  "options": {
    "content": "# Dependency Vulnerability Portfolio\n\n**Org-wide dependency health and CVE exposure**\n\n- Health buckets: healthy / high-exposed / critical-exposed / EOL / approaching-EOL\n- Top vulnerable packages by repo count\n- Adoption timelines (90-day trend)\n- Filter by team, service, or severity\n\n[View Dependency Portfolio →](/d/dep-vuln-portfolio)",
    "mode": "markdown"
  },
  "pluginVersion": "11.0.0",
  "title": "Dependency Vulnerability Portfolio",
  "type": "text"
}
```

#### Panel 19 — Library Detail Deep-Dive

```json
{
  "datasource": {
    "type": "postgres",
    "uid": "TimescaleDB"
  },
  "fieldConfig": {
    "defaults": {
      "color": { "mode": "thresholds" },
      "mappings": [],
      "thresholds": {
        "mode": "absolute",
        "steps": [{ "color": "green", "value": null }]
      }
    },
    "overrides": []
  },
  "gridPos": { "h": 6, "w": 8, "x": 8, "y": 26 },
  "id": 19,
  "options": {
    "content": "# Library Detail Deep-Dive\n\n**Per-package CVE, version, and team usage view**\n\n- CVE list with severity and fixed-in version\n- Repos using the package, grouped by team\n- Versions in use across the portfolio\n- Drilldown target from the portfolio dashboard\n\n[View Library Detail →](/d/library-detail-deep-dive)",
    "mode": "markdown"
  },
  "pluginVersion": "11.0.0",
  "title": "Library Detail Deep-Dive",
  "type": "text"
}
```

### Style notes for the agent

- Match the structure of existing nav panels (id 9–15) exactly — same field defaults, same threshold colour, same `pluginVersion`, same markdown content shape (`# Title`, bold tagline, bullet list, action link).
- Use single threshold colour `green` on both new panels (matches all existing nav tiles except `Total Repositories` which uses `blue`).
- The `datasource` block on text panels is unused but every existing nav panel includes it — keep it for consistency.
- Do **not** bump the dashboard `version` field — Grafana provisioning manages that.
- Do **not** touch `schemaVersion`, `uid`, or `title` of the home dashboard.

---

## Acceptance criteria

- [ ] Four new tiles render on the home dashboard's "Dashboard Navigation" section, in the layout shown above.
- [ ] Tile **Security Dashboard** links to `/d/security-dashboard` and lands on the Security Dashboard.
- [ ] Tile **Technology Landscape** links to `/d/technology-landscape` and lands on the Technology Landscape dashboard.
- [ ] Tile **Dependency Vulnerability Portfolio** links to `/d/dep-vuln-portfolio` and lands on the Dependency Vulnerability Portfolio dashboard.
- [ ] Tile **Library Detail Deep-Dive** links to `/d/library-detail-deep-dive` and lands on the Library Detail Deep-Dive dashboard.
- [ ] No `gridPos` collision with existing panels (visually verify nothing overlaps).
- [ ] `dashboards/dashboard-home.json` is valid JSON (`python -c "import json; json.load(open('dashboards/dashboard-home.json'))"` exits 0).
- [ ] Panel ids remain unique: `jq '.panels[].id' dashboards/dashboard-home.json | sort | uniq -d` prints nothing.
- [ ] Grafana provisions the dashboard cleanly on container startup (no errors in `docker compose logs grafana`).

---

## Test plan

1. **JSON sanity** (no Docker needed):
   ```bash
   python -c "import json; json.load(open('dashboards/dashboard-home.json'))" && echo OK
   jq '.panels | length' dashboards/dashboard-home.json   # was 15, should now be 19
   jq '[.panels[].id] | length == ([.panels[].id] | unique | length)' dashboards/dashboard-home.json   # true
   ```

2. **Visual check** (requires the stack):
   ```bash
   docker compose --env-file .env.resolved up -d grafana
   ```
   - Open `http://localhost:3000` (admin/admin).
   - Navigate to **Home** → confirm all four new tiles appear (Security & Tech Landscape next to Administration; Dependency Portfolio & Library Detail on the new row below).
   - Click each tile → confirm correct destination loads.

3. **Provisioning check**:
   - `docker compose logs grafana | grep -i "dashboard-home"` should show the dashboard loaded without parse errors.

No automated tests are needed — this is JSON-only, the only failure mode is malformed JSON or wrong link URL, both caught by the steps above.

---

## Risk

| Risk | Probability | Mitigation |
|------|-------------|-----------|
| Wrong UID in link URL | Low | UIDs verified before plan written: `security-dashboard`, `technology-landscape`, `dep-vuln-portfolio`, `library-detail-deep-dive` |
| `gridPos` collision | Low | Free 8-wide slots at `(y=20, x=8)`, `(y=20, x=16)`, `(y=26, x=0)`, `(y=26, x=8)` confirmed by reading current home JSON |
| Layout looks asymmetric on narrow screens | Low | Same w=8/h=6 cell size as every other nav tile — Grafana handles responsive reflow consistently |

---

## File manifest

```
dashboards/dashboard-home.json   (modified — add 2 panels)
```

**Total new files**: 0
**Total modified**: 1
**Estimated effort**: 20–40 min (one PR, no review cycles needed beyond a quick visual confirmation)

---

## PR template

**Branch**: `feat/home-dashboard-nav-links` (or similar)

**Title**: `feat(dashboards): link Security, Technology Landscape, and Plan-021 dashboards from Grafana Home`

**Body**:

```
## Summary

Add four navigation tiles to dashboards/dashboard-home.json so the
following dashboards are reachable from Home:

- Security Dashboard → /d/security-dashboard
- Technology Landscape → /d/technology-landscape
- Dependency Vulnerability Portfolio → /d/dep-vuln-portfolio
- Library Detail Deep-Dive → /d/library-detail-deep-dive

Layout: Security and Technology Landscape fill the two empty cells
next to Administration (y=20). Dependency Portfolio and Library
Detail share a new row below at y=26. No existing panels moved.

## Test plan

- [ ] python -c "import json; json.load(open('dashboards/dashboard-home.json'))"
- [ ] jq '.panels | length' confirms 19 (was 15)
- [ ] jq '[.panels[].id] | length == ([.panels[].id] | unique | length)' is true
- [ ] Visual: `docker compose up grafana`, open Home, click each new tile
```
