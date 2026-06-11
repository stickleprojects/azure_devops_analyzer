# Plan 029: Scan Highlights & Trends ("What changed since last scan")

## Status: DRAFT 📝 (not started — issue #147)

Tracks GitHub issue
[#147](https://github.com/stickleprojects/azure_devops_analyzer/issues/147):
"when we rescan it's difficult to see updates and highlights, add a feature to
show interesting information from each scan."

## Motivation

Each rescan rewrites the same tables in place, so there is no surface that
answers *"what actually changed since last time?"*. Operators want a digest
after every scan plus longer-term (month-over-month) trends. From the issue and
follow-up discussion, the requested highlights are:

- **New repos** / **retired repos**
- **Top commit improvers** (repos with the biggest activity jump since last scan)
- **Most active contributors** this scan vs last
- **New libraries added** — at **repo / team / org** level, to spot tech-radar
  changes and assess **blast radius** when a library is introduced
- **New security vulnerabilities found** — at repo / team / org level, with
  drill-down (security dashboards already exist — link, don't rebuild)
- All of the above viewable as **trends over the past months**
- A **daily news bulletin** that collates the interesting changes into a
  human-readable digest, published automatically on a cron, with an **archive
  the user can browse** (old bulletins).

## Data foundation — verified against the schema and code

This was checked against the live schema/code before drafting, so the plan
states facts, not assumptions.

### What already exists (strong reuse)

| Need | Backing data | Notes |
| --- | --- | --- |
| Discrete scan events | [`extraction_runs`](../../database/schema.sql) (`run_id`, `started_at`, `completed_at`) | The anchor for "since last scan". |
| Per-repo activity per run | [`extraction_metrics`](../../database/schema.sql) hypertable (`commits_extracted`, `pull_requests_extracted`, `contributors_extracted`, keyed by `run_id`+`repository_id`) | Retains history per run. |
| **Top commit improvers** | `extraction_metrics.commits_extracted` | **Verified**: this is `stored_count` of *newly-stored, de-duplicated* commits this run ([`github_analysis.py:438-453`](../../src/workflows/github_analysis.py)) — a per-run "new this scan" value. No run-diff needed; just rank the latest run. ⚠️ Capped by `max_commits` and limited to "recent commits". |
| New / retired repos | run membership in `extraction_metrics` (repos in run N but not N-1, and vice-versa) + `repositories.is_active` / `last_analyzed_at` | `is_active` column exists; confirm extractor flips it rather than hard-deleting. |
| **New libraries added** | [`repository_dependencies`](../../database/schema.sql) `first_seen_at` / `last_seen_at`, `UNIQUE(repo_id, package_name, ecosystem)` | **No schema change needed.** New-to-repo = `first_seen_at` in window; new-to-org = `MIN(first_seen_at)` per `(package, ecosystem)` in window. |
| Team / org rollups | `repository_dependencies.repo_id` → `repositories.team_id` / `project_id` (FKs exist) | Single-repo / team / org = a `GROUP BY`. |
| **Blast radius** of a library | `radar_blips.repo_count`; vuln exposure = `radar_blips.exposed_to_cves` | Already precomputed by the radar workflow. |
| **Tech-radar changes** | `radar_blips.is_new` / `is_moved`; [`radar_blip_history`](../../database/migrations/018_tech_radar_schema.sql) (`prior_ring → current_ring`, `repo_count_delta`, `vulnerability_change`) | The diff engine already exists — this is a *surfacing* job, not a build. |

### Gaps that need real work

1. **Radar publication has no automated trigger.** **Verified**:
   `RadarPublicationWorkflow` is invoked only from tests — there is no publish
   API route (only `GET /api/radar*` in
   [`rescan.py`](../../src/api/rescan.py)) and no CI workflow references radar.
   So "radar changes since last scan" requires *adding* a trigger. **Decided:
   publish at the end of each completed full scan** (see Phase 0). This is a
   prerequisite, not just a cadence-alignment decision.

   *Radar UI/back-end already exist and are tested end-to-end* — schema
   (`radar_*` tables), `RadarPublicationWorkflow`, `GET /api/radar` +
   `/api/radar/history` + `/api/radar/export`, and the admin-ui
   `/radar` + `/radar/history` pages (`RadarPage`, `RadarHistoryPage`,
   `RadarChart`) all ship with tests (33 categorizer unit, 8 API contract, 3
   workflow e2e, plus DB-schema and frontend suites). **The only missing piece
   is the production trigger**: `GET /api/radar` returns `200` with
   `entries: []` until something is published, so today the radar renders empty
   in a real deployment. Wiring the post-scan trigger (Phase 0/Phase 4)
   populates it for the first time — no new UI work is needed for the radar
   itself.

2. **Vulnerabilities are stored once per package, not per scan.** After
   migration 014, `vulnerabilities` is keyed by `package_id` with only
   `created_at` / `published_date`. "New vuln this scan" therefore splits into
   two *distinct* events that need different queries and labels:
   - a **newly-published CVE** affecting a library already in use
     (`vulnerabilities.created_at` in window);
   - an **existing CVE that now hits us because a newly-added library
     introduced it** (joins new-library detection to existing vuln rows — this
     is the "blast radius when a library is introduced" case).

3. **No digest/snapshot table.** Diffing raw `extraction_metrics` answers "last
   scan" but month-over-month trends across many runs gets expensive and
   fragile. A small `scan_summary` table written once per run makes trends a
   trivial time-series query.

4. **Contributor metrics are paused.** `_process_contributor_metrics` is
   disabled for performance ([`github_analysis.py:293-298`](../../src/workflows/github_analysis.py)).
   "Most active contributors" must derive from `contributors_extracted` +
   per-author commit counts from the `commits` table, not the paused pipeline.

## Scope

### In scope

- A `scan_summary` digest table + a writer hook at extraction-run completion.
- A read API + view exposing "what changed since last scan" and month trends.
- New-library detection (repo/team/org) from `first_seen_at`.
- New-vulnerability highlights (both event types above) with drill-down links
  to the existing Plan 021 security dashboards.
- Surfacing existing radar change signals (`is_new`/`is_moved`/`radar_blip_history`).
- A UI surface: an admin-ui `/highlights` page and/or a Grafana "Scan Highlights"
  dashboard for the trend panels.
- A **daily news bulletin**: a `news_bulletins` table, a Celery Beat task that
  generates one bulletin per day from the highlights data, a read API, and an
  admin-ui archive/reader page. Opt-in email delivery with per-subscriber scope
  (all / team / specific repos), team inferred from `repository.json`.

### Out of scope

- Rebuilding security drill-downs (Plan 021 owns those — link to them).
- Re-enabling the paused contributor-metrics pipeline (separate concern).
- Changing extraction/caching behaviour.

## Phases

### Phase 0 — Decisions & confirmations (no code)
- Confirm `is_active` is set (not hard-delete) on disappearance, so retired-repo
  detection is reliable.
- **Radar trigger — DECIDED: publish `RadarPublicationWorkflow` at the end of
  each completed full scan.** This makes `radar_blip_history.publication_date`
  track scan completion, so "radar changes since last scan" aligns naturally.
  Guard it to run once per scan (after all repos processed), not per-repo.
- Confirm the `max_commits` cap is acceptable for "top improvers" (or note the
  caveat in the UI).

### Phase 1 — `scan_summary` digest table + writer
- Migration `021_scan_summary.sql`: one row per `extraction_run` with headline
  totals (repos scanned, new/retired counts, total new commits, contributors,
  new libraries, new vulns).
- Writer hook on run completion; forward-only, with a one-time backfill from
  `extraction_metrics` where derivable.

### Phase 2 — "What changed since last scan" view + API
- View/endpoint returning, for the two latest runs: new/retired repos, top
  commit improvers (rank latest `commits_extracted`), most active contributors,
  and **new libraries** (`first_seen_at`) at repo/team/org.

### Phase 3 — Trends over months
- Time-series view/endpoint over `scan_summary`.

### Phase 4 — Vulnerability + radar highlights
- New-vuln highlights (both event types), blast-radius via
  `radar_blips.repo_count` / `exposed_to_cves`, drill-down links to Plan 021
  dashboards.
- Surface `radar_blip_history` / `is_new` / `is_moved`. Requires the Phase 0
  trigger so radar history is produced per scan.

### Phase 5 — UI surface
- admin-ui `/highlights` (or `/whats-new`) React route (pattern in
  [`web/admin-ui/src/App.tsx`](../../web/admin-ui/src/App.tsx)).
- Grafana "Scan Highlights" dashboard for the month-trend panels.

### Phase 6 — Daily news bulletin + archive
- **Storage**: migration adds a `news_bulletins` table — one row per published
  bulletin: `bulletin_date` (UNIQUE), `published_at`, a structured `payload`
  (JSONB — the collated highlight sections) and a rendered `body` (Markdown/HTML
  for display). Keeping both lets the archive re-render without recomputing.
- **Generation**: a Celery task `tasks.generate_daily_bulletin` that collates
  everything interesting **since the previous bulletin** (not "since last scan"
  — see note) into the payload, renders the body, and upserts the row. Idempotent
  per `bulletin_date` so re-runs don't duplicate.
- **Schedule**: add the **project's first `beat_schedule` entry** to
  [`celery_app.py`](../../src/scheduler/celery_app.py) (a daily `crontab`, e.g.
  06:00 UTC). The `celery-beat` service already exists in
  [`docker-compose.yml`](../../docker-compose.yml) — no new infra. Provide a
  manual trigger (API or management task) for backfill/testing.
- **Read API**: `GET /api/bulletins` (paginated list, newest first),
  `GET /api/bulletins/latest`, and `GET /api/bulletins/<date>` (or `/<id>`).
- **UI**: admin-ui `/bulletins` archive list + `/bulletins/:date` reader route,
  following the existing page/routing pattern. The archive and reader support a
  **team/repo filter** (same scope vocabulary as subscriptions: all / team /
  repo) so browsing can be narrowed to match what a user cares about; the filter
  is applied client-side over the full stored bulletin, or passed to the read
  API as query params (`?team=` / `?repo=`) which filter the returned highlight
  sections server-side. Default view is the full (org-wide) bulletin.
- **Quiet-day behaviour — DECIDED: always publish.** On a day with nothing
  notable, generate a short **"No notable changes"** bulletin (flagged
  `is_quiet_day = true` on the row) so the daily archive has no gaps. The
  collator decides "quiet" when every highlight section is empty.
- **Email distribution — opt-in model.** After a bulletin is published, the
  task emails it only to people who have **explicitly subscribed**. Design:
  - **Subscription store**: a `bulletin_subscriptions` table keyed by lowercased
    `email`, with `subscribed_at`, `confirmed_at` (nullable), and an
    `unsubscribe_token`. **No one receives email until they subscribe** — empty
    by default.
  - **Scoped subscriptions** — a subscriber chooses *what* they hear about, via a
    `bulletin_subscription_scopes` child table (`subscription_id`, `scope_type`,
    `scope_value`) so one email can hold several scopes (e.g. "team Payments
    **plus** repo X"):
    - `all` — org-wide (everything; `scope_value` unused).
    - `team` — every repository belonging to a team. **Team is inferred from each
      repo's `repository.json` `teamname`** ([`base.py:760-769`](../../src/extractors/base.py)),
      which `store_repository` resolves into `teams` and sets as
      `repositories.team_id` ([`storage.py:455-468`](../../src/database/storage.py)).
      `scope_value` = team name/id. (Repos with no `repository.json` have a NULL
      team — surfaced as an "unassigned" pseudo-team, not silently dropped.)
    - `repo` — one named repository; `scope_value` = `repo_id`.
  - **Per-subscriber filtering**: generation still builds one **global** highlights
    dataset (and the in-app archive shows the full bulletin). The *email* task
    then, per subscriber, filters that dataset to the union of their scopes,
    renders a personalised body, and skips the send if nothing in-scope changed
    (subject to the quiet-day toggle). Highlights carry `repo_id` / `team_id`
    already, so filtering is a straightforward membership test.
  - **Subscribe from the UI while browsing the news**: the admin-ui `/bulletins`
    archive carries a "Get this by email" control where a user enters their
    address **and picks a scope** — all news, one or more teams (list sourced
    from distinct `repositories.team_id`/name), or specific repositories; the
    reader page has the same affordance. Backed by
    `POST /api/bulletins/subscribe` (email + scopes) and
    `POST /api/bulletins/unsubscribe`, plus a manage endpoint so a returning user
    can edit their scopes. Each sent email also carries a one-click unsubscribe
    link (signed token), so users can leave without logging in.
  - **Email-domain allowlist**: subscriptions and sends are restricted to a
    configured set of allowed domains (`BULLETIN_ALLOWED_EMAIL_DOMAINS`, e.g.
    the org's internal domains). An address outside the allowlist is **rejected
    at subscribe time** (clear UI error) and defensively re-checked at send time,
    so notifications can never go to an unapproved domain even if a row predates
    a config change.
  - **SMTP is a new dependency** (no email code exists today): add a small
    sender abstraction + env config (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`,
    `SMTP_PASSWORD`, `SMTP_FROM`, `BULLETIN_EMAIL_ENABLED`,
    `BULLETIN_ALLOWED_EMAIL_DOMAINS`). Email sending is a **separate Celery
    task** from generation so a mail failure never blocks the bulletin row from
    being written, and it can be retried independently.
  - Respect the quiet-day case per a config toggle (`BULLETIN_EMAIL_ON_QUIET_DAY`,
    default **off** — don't email "nothing happened" daily; still archived in-app).
  - *Optional hardening (note for implementation):* a double-opt-in confirmation
    email (`confirmed_at`) prevents someone subscribing a colleague's address.
    Worth doing if addresses aren't otherwise verified.

**Cadence note** — the bulletin window is *"since the previous bulletin"*, not
*"since the last scan"*: scans may not run daily, or may run several times a
day. The collator aggregates everything in that window; the quiet-day path
above handles windows with no notable changes.

## Reuse

- `extraction_runs` / `extraction_metrics` (extraction pipeline).
- `repository_dependencies.first_seen_at` (Plan 012).
- `radar_blips` / `radar_blip_history` / `RadarPublicationWorkflow` (Plan 022).
- Plan 021 security dashboards + views (drill-down target).
- admin-ui routing/page patterns (Plan 025); Grafana panel patterns (Plan 011/021/023).
- Celery + `celery-beat` service and named-task pattern in
  [`src/scheduler/tasks.py`](../../src/scheduler/tasks.py) (bulletin generation
  task + first `beat_schedule` entry).

## Open questions

- Should "top improvers" use raw `commits_extracted` (simple, cap-limited) or a
  true run-N vs run-(N-1) delta? Raw is cheaper and already "new this scan".
- One unified `/highlights` page, or fold each highlight into its existing home
  (radar page, security dashboard) plus a digest landing page?
- Retention/aggregation policy for `scan_summary` (keep all runs vs. roll up).
- Bulletin retention (keep forever vs. prune old rows).
- The exact allowed email domains (`BULLETIN_ALLOWED_EMAIL_DOMAINS` value).
- Double-opt-in confirmation — required, or is a plain subscribe enough given
  the domain allowlist already limits exposure?
- Slack/Teams distribution later, or is email + in-app archive enough?

## Acceptance criteria

- [ ] `scan_summary` populated automatically on each completed scan; backfill runs once.
- [ ] "Since last scan" API returns new/retired repos, top commit improvers,
      active contributors, and new libraries (repo/team/org) with correct aggregations.
- [ ] New-library and new-vuln highlights resolve to a blast-radius repo count and
      link to the Plan 021 security dashboard.
- [ ] Radar changes (`is_new`/`is_moved`/ring movements) surfaced for the latest scan.
- [ ] Month-over-month trend endpoint/panel renders.
- [ ] Daily `tasks.generate_daily_bulletin` runs on the Celery Beat schedule,
      upserts one idempotent row per `bulletin_date`, and collates highlights
      since the previous bulletin.
- [ ] On a window with no notable changes, a "No notable changes" bulletin is
      published (`is_quiet_day = true`) so the archive has no gaps.
- [ ] Bulletin read API lists/serves bulletins; admin-ui `/bulletins` archive
      lets the user browse and read old bulletins, and filter the view by
      team/repo (matching the subscription scope vocabulary).
- [ ] Published bulletins are emailed only to explicitly subscribed addresses
      (opt-in); no email is sent to anyone who hasn't subscribed.
- [ ] A user can subscribe from the `/bulletins` UI while browsing, choosing a
      scope (all / one-or-more teams / specific repos), and unsubscribe via the
      link in any email; both update `bulletin_subscriptions`(+ scopes).
- [ ] Each subscriber's email contains only highlights matching their scopes;
      team scope resolves via `repository.json`-derived `team_id`, and repos with
      no team appear under an "unassigned" pseudo-team rather than vanishing.
- [ ] Subscriptions and sends are restricted to the configured email-domain
      allowlist — an out-of-allowlist address is rejected at subscribe time and
      never emailed even if it somehow exists in the table.
- [ ] Email sending is a separate task from generation; a mail failure never
      blocks the bulletin row from being written.
- [ ] Contract tests: digest writer, since-last-scan view, trend view, new-library
      detection at all three rollup levels, bulletin generation (incl. quiet-day
      behaviour and idempotent re-run), bulletin API, subscribe/unsubscribe,
      scoped delivery (all/team/repo filtering, incl. unassigned-team repos),
      domain-allowlist enforcement, and the quiet-day email toggle.
- [ ] Docs + plan status flipped to IN REVIEW in the implementation PR.
