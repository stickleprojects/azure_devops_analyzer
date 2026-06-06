# Investigation: Grafana UI Shortcomings — Navigation, Relational Drill-down, and Tool Fit

**Status**: RESOLVED 2026-05-03 — **Outcome 2 selected** (split admin from analytics; bespoke admin UI + tidied Grafana). Downstream [Plan 025](../plans/completed/025-bespoke-admin-and-navigation-ui.md) is now **fully delivered** (all phases merged by 2026-05-25; plan moved to `completed/`).
**Created**: 2026-05-01
**Related plans**: `.ai/plans/023-grafana-home-dashboard-links.md` (home nav links — closed), `.ai/plans/completed/025-bespoke-admin-and-navigation-ui.md` (bespoke React UI — complete)

---

## Why this exists

The user has identified two specific frustrations with the current Grafana setup:

1. **Cross-dashboard navigation is messy** — jumping back to root or sideways to a sibling dashboard requires either the static top-link bar (inconsistently populated per dashboard) or Grafana's general search.
2. **Relational drill-down is incomplete** — particularly on the security dashboard: a row that says "repository X has vulnerability Y" doesn't always let the user click through to the repository's deep-dive view. Vulnerability-centric tables (e.g. "Top Vulnerable Dependencies") are dead ends.

Plus a broader question about scope: Grafana is being asked to do **two different jobs** — analytics (the natural fit) and admin/operational control (rescan triggers, metric computes — currently embedded as HTML link buttons in `dashboards/admin-dashboard.json`). The hypothesis is that the second job is the wrong tool, and that explains a lot of the friction.

The goal of this investigation is to map the friction concretely before deciding how to spend effort: tidy what we have, rebuild some of it, or split the concerns.

---

## What we know already (from reading the dashboards)

- 12 dashboards in `dashboards/*.json`. Top-link bars are inconsistent: `admin-dashboard.json` has 1 link (Home), `security-dashboard.json` has 8, `dependency-vulnerability-portfolio.json` has 4.
- Drill-down via Grafana data links **does** exist on at least these tables:
  - `security-dashboard.json:658` → `Repository Security Overview` table → `repo-deep-dive`
  - `dependency-vulnerability-portfolio.json` → library detail (per Plan 021)
    Other tables (e.g. "Top Vulnerable Dependencies", severity breakdowns) have no row-level drill-down.
- The admin dashboard is unusual: extraction is triggered by a `text`/`stat` panel link that POSTs to `http://localhost:5000/api/rescan/github` (the Flask API). It works, but it's a UX of "click a Grafana stat tile and watch a browser tab open showing JSON".
- A rescan/health/packages/radar/stack Flask API is already exposed (~20 endpoints in [src/api/rescan.py](src/api/rescan.py) and [src/api/stack.py](src/api/stack.py)) — any new frontend has a server to talk to.
- Plan 023 just shipped to fix Home → child-dashboard discoverability. That's the _outbound_ nav from Home; the _inbound_ return-to-Home and _sideways_ sibling nav are still uneven.

---

## Themes to investigate

Each theme is a set of questions the user (or a contributor) should answer before committing to a direction. Keep answers short — one or two sentences each is usually enough.

### Theme A — Cross-dashboard navigation

_Goal: characterise where the navigation actually breaks down._

1. When you're on a non-Home dashboard and want to get back to Home, what do you currently do? (top-link, browser back, Grafana sidebar?)
2. When you're on Security and want to jump to Technology Landscape, how many clicks does it take? Where do you look first?
3. Is the inconsistency of top-link bars (1 vs 8 links per dashboard) the actual annoyance, or is it the absence of a consistent "you are here" hierarchy?
4. Would a uniform top-link bar (Home / Repos / Security / Tech / Admin) on every dashboard fix it, or does the issue remain even with that?
5. Is there a use-case for breadcrumb-style nav ("Home › Security › Repository X")? Grafana doesn't do this natively.

**Answers:**

1. I click the navigation top-link
2. It takes 2 clicks and some scrolling (1 click to home, scroll down the home page to find technology landscape, then have to scroll the panel to find the link, then click the link)
3. Missing "you are here" hierarchy and inconsistent navigation - ideally we would want to click on any category and "go there", if a data row has users, i should be able to click to that user's dashboard, if a datarow shows repositories i should be able to click and go to that repo dashboard
4. consistent top-link would help
5. dont need breadcrumb-style navigation

---

### Theme B — Relational drill-down

_Goal: list the missing edges in the data graph._

1. On the security dashboard, list every panel where you've wished you could click a row and weren't able to. (e.g. "Top Vulnerable Dependencies → which repos use this?", "EOL Status → which repos?")
2. Are these missing because the data is there but the data link wasn't configured, or because the underlying SQL doesn't expose the join key?
3. For each missing edge, what is the natural drill-down target? (a repo deep-dive, a library deep-dive, a service overview, a team page?)
4. Is the friction "I can't get there at all" or "I can get there but it's two manual steps via a search box"?
5. Are there panels you'd actively _prevent_ drill-down from? (e.g. aggregate trend lines that would make no sense as link targets)

**Answers:**

1. "top vulnerable dependencies" should allow me to view the associated repos and then navigate into them, "EOL status" should also support this. Although note the lack of data makes this difficult to test
2. I believe the data is there, just not configured
3. top vulnerable, go to library deep-dive and then the repos that use it
4. the friction is no navigation at all
5. no panels should prevent drilldown as long as there is a dashboard to navigate to that shows that unique item
   Example missing use-case, in the organizaiton security summary, we have 10 total vulnerabilities and 4 repositories but no way to get to them, the repository security overview shows all repos and zeros for every column

---

### Theme C — Admin / operational workflows in Grafana

_Goal: confirm whether admin belongs in Grafana at all._

1. Today, what are the admin actions you actually perform from `admin-dashboard.json`? (Trigger rescan, recompute service metrics, check API health, see Flower, look at stale repos…)
2. Which of those feel comfortable in Grafana, and which feel like fighting the tool?
3. When you trigger a rescan, what feedback do you get? (the API returns JSON in a new tab — is that acceptable, or do you want the running job's progress in-place?)
4. Is there a workflow you've avoided implementing because it would be too painful to express as a Grafana panel? (e.g. "exclude this repo from scans", "tag this team as inactive", "edit a service-to-repo mapping")
5. If admin moved to a separate web UI tomorrow, what would you keep in Grafana? (probably: Active Runs, Recent Runs, Auth Failures, Repository Staleness — i.e. the read-only operational _observability_ panels)

**Answers:**

1. I use it to start analysis
2. Starting the analysis does not feel right
3. when you trigger a rescan, you are taken to a new window with the queue/job information, there is no nice popup to say "your scan request has been logged and will start soon" from within grafana
4. i havent excluded a particular workflow for that reason
5. i would keep the observability panels as you suggest

---

### Theme D — Analytics tool fit

_Goal: separate "Grafana is wrong" from "this Grafana isn't great"._

1. For the analytics dashboards specifically (security, technology landscape, dependency portfolio, library detail, repo overview, team, service, contributors, PRs) — is the issue ever Grafana's data model (can't express the chart you want), or is it always navigation/drill-down?
2. Have you hit a query you couldn't write in Grafana's SQL editor? (suggests a tool ceiling)
3. Have you wanted a custom interaction Grafana can't render? (e.g. a faceted search, a sortable table with multi-column filters, a timeline scrubber, a graph visualisation of dependencies between packages)
4. If we kept Grafana for charts and put navigation/drill-down on top of it, would that solve it? Or do specific dashboards need to leave Grafana entirely?

**Answers:**

1. Navigation is somewhat painful, and the panels can feel cluttered and have scrollbars to find links/etc
2. no
3. no. But the visualisation between packages seems like a cool idea and i believe there is a visualisation for that
4. grafana for charts and analysis and alerts is great, perhaps the diagnostics (did the scan work?) and details are the problem

---

### Theme E — Effort and audience

_Goal: anchor the decision in real cost and real users._

1. Who uses these dashboards? (you alone, a small team, leadership, external stakeholders?) Different audiences justify different investments.
2. What does "good enough" look like — would tidying the top-link bar across all 12 dashboards and adding the missing data links satisfy 80% of the pain?
3. How much time per week is currently lost to nav/drill-down friction? (rough estimate)
4. Are you willing to maintain a small bespoke React app long-term (deps, builds, security patches), or is that a cost you'd regret in six months?

**Answers:**

1. these will be used by team and leadership, as there will be many teams
2. yes
3. 20% of my time is one-hit debugging, so i think this is an unfair question at current usage
4. yes im happy to maintain the app

---

## Synthesis — decision matrix

Once Themes A–E have answers, map them to one of three outcomes. The investigation isn't done until this table is filled.

| Outcome                                                    | Justified when…                                                                                                                                        | Effort                                                    | Reversibility                                       |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------- | --------------------------------------------------- |
| **(1) Tidy Grafana only**                                  | Theme A is the dominant pain, Themes C/D answers don't surface tool-fit problems, Theme E says "no budget for bespoke"                                 | ~1–2 days (uniform top-link bar + add missing data links) | Trivial                                             |
| **(2) Split: bespoke admin UI + tidied Grafana analytics** | Theme C surfaces real tool-fit pain (admin in Grafana feels wrong), Theme D says analytics is mostly fine, Theme E supports modest ongoing maintenance | ~1–2 weeks for admin MVP + the Outcome 1 work             | Reversible — admin UI can be deleted, Grafana stays |
| **(3) Replace analytics tool too**                         | Theme D surfaces ceiling problems (queries Grafana can't express, interactions it can't render)                                                        | Multi-week migration to Metabase/Superset/bespoke         | Hard — dashboards are real assets                   |

**Pre-investigation lean** (to be confirmed by answers): Outcome 2. Plan 025 is drafted on that assumption.

**Resolution (2026-05-03): Outcome 2 confirmed.**

| Theme | Signal | Mapped to outcome |
| --- | --- | --- |
| A — Navigation | Wants consistent top-link bar; wants click-through from any data row to its target dashboard. No breadcrumbs needed. | Tidy Grafana (Phase 2/3 of Plan 025) |
| B — Drill-down | Friction is "no navigation at all" rather than slow nav. Data is there, just unconfigured. All panels with a unique target should drill down. | Tidy Grafana (Phase 3 of Plan 025) |
| C — Admin | Only "start analysis" is used today. Does NOT feel right in Grafana. New-tab JSON feedback is bad UX. | Out of Grafana (Phase 1 of Plan 025) |
| D — Tool fit | Grafana fine for charts/alerts. No query ceiling. Diagnostics/details and panel clutter are the actual issues. | Keep Grafana for analytics |
| E — Effort | Team + leadership audience. Tidy nav + missing data links would solve ~80% of pain. Happy to maintain a small React app. | Outcome 2 viable |

**80/20 implication**: Phases 2 + 3 of Plan 025 (Grafana tidy, ~2–3 days) capture most of the value. Phase 1 (React MVP, ~1–2 weeks) addresses the remaining admin pain. Plan 025 has been re-sequenced accordingly. RESOLVED

---

## Concrete artefacts to produce alongside the answers

1. **Top-link audit** — a table listing each dashboard and its current top-link entries, so the inconsistency is visible at a glance.
   ```bash
   for f in dashboards/*.json; do
     echo "=== $f ==="
     jq -r '.links[] | "  \(.title) -> \(.url)"' "$f"
   done
   ```
2. **Drill-down audit** — for each table panel in security, dependency-vulnerability-portfolio, library-detail-deep-dive, technology-landscape: does the row have a data link? Where does it go?
   ```bash
   jq '[.panels[] | select(.type=="table") | {title, has_link: (.fieldConfig.overrides // [] | any(.properties[]?.id == "links"))}]' dashboards/security-dashboard.json
   ```
3. **Admin action inventory** — list every action panel in `admin-dashboard.json` with the API endpoint it calls and the user feedback it gives today.

These three artefacts make Themes A, B, and C answerable from data instead of memory.

---

## Next step

When the synthesis table is at least half filled in, decide between Outcomes 1, 2, 3. If Outcome 2 (the current lean), proceed with [Plan 025](../plans/025-bespoke-admin-and-navigation-ui.md). If Outcome 1, scope a smaller "Grafana navigation hardening" plan instead. If Outcome 3, this becomes a much larger conversation.

---

## Risks of skipping this investigation

- Building Plan 025's React UI without confirming Theme C means we might over-build (rebuilding things Grafana actually does well) or under-build (missing the actual workflows that motivate the rebuild).
- Tidying Grafana without confirming Theme D means we may sink time into a tool that has a ceiling we haven't acknowledged.
- 30–60 min of structured Q&A here probably saves a week of misdirected work.

---

## Audit findings (2026-05-03)

These three audits make Phases 2 and 3 of Plan 025 mechanical to execute. Snapshot from `main` at the time of investigation closure.

### 1. Top-link audit

7 distinct shapes across 12 dashboards. Inconsistent ordering, inconsistent membership.

| Dashboard | Top-link entries |
| --- | --- |
| `admin-dashboard.json` | Home |
| `contributor-analytics.json` | Home, Team Overview, Repository Overview, Repository Deep-Dive, Pull Requests |
| `dashboard-home.json` | (none — it IS Home) |
| `dependency-vulnerability-portfolio.json` | Home, Security, Library Deep-Dive |
| `library-detail-deep-dive.json` | Home, Package Portfolio, Security |
| `pull-requests.json` | Home, Team Overview, Repository Overview, Repository Deep-Dive, Contributors |
| `repository-deep-dive.json` | Home, Team Overview, Repository Overview, Pull Requests, Contributors |
| `repository-overview.json` | Home, Team Overview, Repository Deep-Dive, Pull Requests, Contributors |
| `security-dashboard.json` | Home, Team Overview, Repository Overview, Repository Deep-Dive, Pull Requests, Contributors |
| `service-overview.json` | Home, Repository Overview, Team Overview, Security |
| `team-overview.json` | Home, Repository Overview, Repository Deep-Dive, Pull Requests, Contributors |
| `technology-landscape.json` | (none — regression) |

**Phase 2 implication**: a uniform 5-entry bar (Home / Repos / Security / Technology / Admin) replaces all of the above. `dashboard-home.json` keeps no bar; everything else gets the same bar.

### 2. Drill-down audit

Most table panels have NO row-level data link. `[LINK]` = has data link configured; `[----]` = missing.

| Dashboard | Panel | Status | Natural target |
| --- | --- | --- | --- |
| security-dashboard | Repository Security Overview | [LINK] | (already drills to repo-deep-dive) |
| security-dashboard | Top Vulnerable Dependencies | [----] | library-detail-deep-dive |
| dependency-vulnerability-portfolio | Top 20 Vulnerable Packages | [----] | library-detail-deep-dive |
| dependency-vulnerability-portfolio | Packages Reaching EOL Within 90 Days | [----] | library-detail-deep-dive |
| dependency-vulnerability-portfolio | Package Usage by Team | [----] | team-overview / library-detail-deep-dive |
| library-detail-deep-dive | Health Status | [----] | (review — may not need drill-down) |
| library-detail-deep-dive | CVE Details | [----] | (external — CVE link) |
| library-detail-deep-dive | Repositories Using $package_name | [----] | repo-deep-dive **(highest-value gap)** |
| technology-landscape | EOL Technologies with Affected Repo Count | [----] | repo-deep-dive (filtered) |
| technology-landscape | Repository Stack (by source) | [----] | repo-deep-dive |
| repository-deep-dive | Vulnerability Details | [----] | library-detail-deep-dive |
| repository-deep-dive | Branch Details | [----] | (no obvious target — skip) |
| repository-deep-dive | Repository Summary | [----] | (no obvious target — skip) |
| repository-deep-dive | Technologies (Detected Stack) | [----] | technology-landscape (filtered) |
| repository-deep-dive | Recent Commits | [----] | (external — git host) |
| repository-deep-dive | Open Pull Requests | [----] | pull-requests |
| repository-overview | Top 10 Active Repositories | [LINK] | (already drills) |
| repository-overview | All Repositories | [LINK] | (already drills) |
| team-overview | Repository Health Matrix | [LINK] | (already drills) |
| team-overview | Team Performance Summary | [----] | repo-overview (filtered by team) |
| team-overview | Recent Pull Requests (7 Days) | [LINK] | (already drills) |
| service-overview | Services at a Glance | [----] | service-overview detail (same dashboard, drilled) |
| service-overview | Technology Stack by Service | [----] | technology-landscape (filtered) |
| service-overview | Repository Breakdown | [LINK] | (already drills) |

**Phase 3 implication**: ~10 high-value gaps to close. Each is a small `fieldConfig.overrides[]` JSON edit. The user's specific complaint (org security summary → underlying repos) is the "Top Vulnerable Dependencies" + "Repositories Using $package_name" chain, both flagged.

### 3. Admin action inventory

| Panel | Type | Endpoint | Current feedback |
| --- | --- | --- | --- |
| Force Rescan — GitHub | stat | `POST http://localhost:5000/api/rescan/github` | Opens new tab with raw JSON |
| Force Rescan — Azure DevOps | stat | `POST http://localhost:5000/api/rescan/azure-devops` | Opens new tab with raw JSON |
| Compute Service Metrics | stat | `POST http://localhost:5000/api/compute/service-metrics` | Opens new tab with raw JSON |
| API Health Check | stat | `GET http://localhost:5000/health` | Opens new tab with raw JSON |
| Celery Monitor (Flower) | stat | `http://localhost:5555` | External link — fine as-is |
| Active Runs | stat | (read-only metric) | Observability — keep in Grafana |
| Latest Run Progress | stat | (read-only metric) | Observability — keep in Grafana |
| Auth Failures (24h) | stat | (read-only metric) | Observability — keep in Grafana |
| Recent Runs | table | (read-only) | Observability — keep in Grafana |
| Stale Repositories (7+ days) | table | (read-only) | Observability — keep in Grafana |
| Never Scanned | table | (read-only) | Observability — keep in Grafana |
| Recent Repository Activity (with Errors) | table | (read-only) | Observability — keep in Grafana |
| Auth Errors by Platform (24h) | table | (read-only) | Observability — keep in Grafana |

**Phase 1 implication**: 4 action panels move to React (rescan ×2, compute metrics, health check). 9 observability panels stay in Grafana. Theme C.1 says only "start analysis" is actively used today, so React MVP could ship with just the two rescan triggers + health check, deferring Compute Service Metrics and Repository List to a Phase 1b.
