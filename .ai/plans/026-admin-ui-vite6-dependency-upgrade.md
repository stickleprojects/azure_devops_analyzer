# Plan 026: Admin UI vite 6 Upgrade (clear remaining MEDIUM Dependabot alerts)

## Status: READY — pick up next session (2026-05-29+)

**Implements**: Phase 2 of the `web/admin-ui` Dependabot remediation — upgrade
`vite` 5 → 6 so the two remaining **MEDIUM** alerts close. Phase 1 (the HIGH
`@playwright/test` bump) shipped separately in **PR #113**.

**Why this is its own plan**: the fix is a *breaking* major upgrade (`vite` 5 → 6,
which forces `vitest` 1 → 3) and needs the full frontend suite re-run, so it was
deliberately split from the trivial, in-range playwright bump.

---

## Background — the two alerts

Both are in `web/admin-ui/package-lock.json` (npm), all dev/build/test-time deps.
The admin UI is the internal, localhost-only, no-auth React app (Plan 025), so
real-world exploitability is low — this is hygiene + clearing the alert list.

| Alert | Sev | Package | Installed | Fixed in | Notes |
| ----- | --- | ------- | --------- | -------- | ----- |
| GHSA-4w7w-66w2-5vf9 (#3) | MED | `vite` | 5.4.21 | **6.4.2** (also 7.3.2 / 8.0.5) | Path traversal in optimized-deps `.map` handling. **No 5.x patch exists** — must go to 6.x. Only reachable via the dev server (`vite` / `vite preview`); prod is a static `vite build`. |
| GHSA-67mh-4wv8-2f99 (#1) | MED | `esbuild` | 0.21.5 | **0.25.0** | esbuild's own `serve` CORS bug. **Vite never uses esbuild serve**, so effectively non-exploitable here. Pulled in transitively by vite. |

**Key lever**: `vite@6.4.2` depends on `esbuild ^0.25.0`, so upgrading vite to
6.4.2 **also clears the esbuild alert for free** — no manual `overrides` needed.

---

## What's next (agent entry point)

All work is inside `web/admin-ui/`. Start from a fresh branch off `main`
(suggested `fix/admin-ui-vite6-upgrade`).

### Step 1 — Bump the manifest

In `web/admin-ui/package.json` `devDependencies`:

- `"vite": "^5.3.1"` → `"^6.4.2"`
- `"vitest": "^1.6.0"` → `"^3.2.4"` (vite 6 needs vitest ≥ 2; go to latest 3.x)
- **Keep** `"@vitejs/plugin-react": "^4.3.1"` — its 4.x peer range is
  `vite ^4.2.0 || ^5.0.0 || ^6.0.0`, so 4.x is correct for vite 6. **Do NOT**
  bump it to 5.x: plugin-react 5.x peers `vite ^8.0.0` and would force a much
  bigger jump.

Leave `@vitejs/plugin-react` on 4.x; let `npm install` pull the latest 4.x.

### Step 2 — Reinstall and confirm the tree

```bash
cd web/admin-ui
npm install
npm audit            # expect: 0 vulnerabilities
npm ls vite esbuild vitest   # vite ≥6.4.2, esbuild ≥0.25.0, vitest ≥3.2.4
```

### Step 3 — Fix breakage, then validate

```bash
npm run typecheck    # tsc --noEmit
npm run test         # vitest unit suite
npm run build        # vite build
npm run e2e          # Playwright (needs browsers + preview server)
```

---

## Breaking-change watch list

**vite 5 → 6** (most config is forward-compatible, but check):
- Default browser build target changed to `'baseline-widely-available'`
  (Chrome 107 / Firefox 104 / Safari 16). Fine for an internal tool; only matters
  if a specific older-browser target was relied on (it isn't here).
- `vite.config.ts` API mostly stable. `@vitejs/plugin-react` 4.x stays compatible.
- Tailwind/PostCSS path (`tailwindcss@3.4`, `postcss@8.4`, `autoprefixer@10.4`)
  is unaffected by the vite major.
- Node: vite 6 needs Node 18+; the dev machine is on Node 20.12.2 — OK. (Do **not**
  drift to vite 7 — it requires Node 20.19+/22.12+.)

**vitest 1 → 3** (two majors — the riskier half):
- Re-check `vite.config.ts` / any `vitest` config block: `test.environment`
  (`jsdom`), `globals`, `setupFiles` are still supported but defaults shifted
  between majors. The jsdom env + `@testing-library/jest-dom` setup must still load.
- Some matchers / mock APIs changed across v2/v3; if unit tests fail, they're the
  likely cause — adjust per the vitest migration notes, don't downgrade.
- `jsdom@24` is compatible with vitest 3.

---

## Acceptance criteria

- [ ] `npm audit` in `web/admin-ui/` reports **0 vulnerabilities**.
- [ ] `vite ≥ 6.4.2`, `esbuild ≥ 0.25.0`, `vitest ≥ 3.2.4` resolved in the lockfile.
- [ ] `@vitejs/plugin-react` still on 4.x.
- [ ] `npm run typecheck`, `npm run test`, `npm run build` all pass.
- [ ] `npm run e2e` passes (or is explicitly noted as verified in CI).
- [ ] Dependabot alerts **#1 (esbuild)** and **#3 (vite)** auto-close once merged to `main`.

## Risks

| Risk | Likelihood | Mitigation |
| ---- | ---------- | ---------- |
| vitest 1→3 test API churn breaks the unit suite | Medium | Fix forward per migration notes; the suite is small (admin-ui only). Don't pin vitest to 2.x as a half-measure — go to 3.x. |
| `npm audit fix --force` over-bumps (e.g. plugin-react → 5.x → wants vite 8) | Medium | Do the **controlled** bumps in Step 1 by hand; avoid `--force`. |
| A new vite 6 transitive dep introduces its own advisory | Low | Re-run `npm audit` after install; address before opening the PR. |
| Playwright e2e can't run locally (no browsers) | Low | Run `npx playwright install` first, or rely on CI's Frontend job. |

## Notes

- Phase 1 (PR #113) bumped `@playwright/test` → 1.60.0 and cleared the HIGH; this
  plan covers only the two MEDIUMs.
- Dependabot has not opened its own PRs (alerts-only), so there's no bot PR to
  reconcile against — this is a hand-rolled upgrade.

---

## Agent execution guards (Copilot)

This plan is suitable for autonomous execution by Copilot, with the following
non-negotiable guards. They are listed because previous Copilot runs in this
repo have hit each failure mode at least once.

1. **CI green is the done condition, not "tests pass locally".** After opening
   the PR, poll `gh pr checks <pr-number>` until every required check returns
   `SUCCESS`. Do **not** post a "ready for review" comment, mark the task
   complete, or declare done while any check is still `IN_PROGRESS`, `QUEUED`,
   or `FAILURE`. If a check fails, push fixes on the same branch and re-poll.

2. **Do not silence failing tests.** The vitest 1 → 3 jump will surface real
   migration breakage in the unit suite. Fix forward per the vitest migration
   notes. Do **not**:
   - comment out or `.skip` failing tests,
   - mark them `xfail` / `it.todo`,
   - delete assertions to make the build green,
   - downgrade `vitest` to 2.x as a half-measure.

   If a test legitimately no longer applies after a vitest API change, delete
   it with a one-line justification in the PR description — never silently.

3. **Stay within the controlled bumps in Step 1.** Do **not** run
   `npm audit fix --force`. Do **not** bump `@vitejs/plugin-react` beyond 4.x,
   `vite` beyond 6.x, or `vitest` beyond 3.x. If `npm install` resolves a
   surprise major upgrade (e.g. jsdom 25, node-fetch), stop and surface it in
   the PR description rather than accepting it.

### Required PR shape

- **Branch**: `fix/admin-ui-vite6-upgrade` (off latest `main`).
- **Title**: `fix(admin-ui): upgrade vite to 6.x to close GHSA-4w7w-66w2-5vf9 and GHSA-67mh-4wv8-2f99`
- **Body must include**:
  - Resolved versions of `vite`, `esbuild`, `vitest` from `npm ls`.
  - Output line from `npm audit` showing `0 vulnerabilities`.
  - Any tests deleted/rewritten because of vitest API changes, with reason.
  - Confirmation that `npm run typecheck`, `npm run test`, `npm run build`
    were each run and exit 0 locally.
