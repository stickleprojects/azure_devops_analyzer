# Plan 020: Property-Based Identity Tests, Live-API Monitoring, Production Observability

_Last reviewed: 2026-04-30_

## Status: DRAFT

## Problem

Plans [018](018-contributor-pr-linking-regression-tests.md) and [019](019-production-data-bug-defence.md) build strong CI-side defences — regression tests, adversarial fixtures, DB invariants, idempotency, and snapshot tests. But those are all **snapshot-in-time** defences: they catch what we thought to check. Three gaps remain in the overall strategy:

**Gap 5 — Unknown-unknowns in normalisation logic.** The adversarial fixture corpus (Plan 019 Layer A) codifies the identity pathologies we *know about*. Nothing generates arbitrary inputs, which is where Hypothesis-style property-based testing shines: it finds the minimal failing case in shapes we didn't imagine.

**Gap 6 — Real-API shape drift.** Live-API tests exist but are excluded from CI by `-m "not live_api"`. When GitHub or Azure DevOps change a response shape, tweak a field, or push an API version bump, nothing in our pipeline notices until a production run breaks. Plan 019's recorded snapshots (Layer D) are a frozen point-in-time; they age.

**Gap 7 — Production anomalies only surface in production.** Even with a perfect test suite, real customer repos will contain shapes our corpora miss. Today, we learn about this when a dashboard looks wrong or a user reports it. We have no telemetry emitting "the invariants that hold in CI also hold after this production extraction."

## Decision

Add three components. Each delivers value independently — Components 1, 2, 3 can land in any order and are not architecturally coupled. They share one artefact with Plan 019: `tests/db_invariants.sql`. That file becomes the **single source of truth for "must always hold" truths**, consumed by:

- CI (Plan 019 Layer B — pytest fixture + tail script)
- Live-API nightly (Component 2 of this plan)
- Production extraction runs (Component 3 of this plan)

| Component | Addresses gap | Primary artefact |
|---|---|---|
| 1. Property-based identity tests | 5 | `tests/unit/test_contributor_identity_properties.py` |
| 2. Live-API nightly monitoring | 6 | `.github/workflows/live-api-nightly.yml` + canary test |
| 3. Production observability hook | 7 | `src/utils/extraction_health.py` + Grafana dashboard |

Cross-platform identity resolution (same human on GitHub + Azure DevOps → one `contributors` row) is explicitly out of scope — it is an architectural design problem, not a test/monitoring problem, and warrants its own design-spike plan.

## Architecture

```
          tests/db_invariants.sql  ←── single source of truth
                  │
        ┌─────────┼──────────────────┬────────────────────┐
        ▼         ▼                  ▼                    ▼
  pytest         run-tests-       nightly live-API    production
  fixture        docker.sh tail   workflow            extraction
  (CI)           (CI)             (CI-shape, real     (runtime,
                                   creds)              real data)
        │         │                  │                    │
        │         │                  ▼                    ▼
        │         │            opens GH Issue        Prometheus
        │         │            on violation          gauges + Grafana
        │         │                                  alerts
        └─────────┴── Plan 019 Layer B ─────────────┘
```

Property-based tests run at the unit layer and don't depend on the invariant SQL — they target the normalisation *function*, not the stored state.

### Reuse

- `get_or_create_contributor` in [src/database/storage.py](../../src/database/storage.py) — property-based target.
- `tests/db_invariants.sql` from Plan 019 — reused by Components 2 and 3.
- `scripts/run-tests-docker.sh` — reused by Component 2 with the `--live-api` flag.
- Existing Grafana provisioning in `dashboards/` — reused for Component 3's new dashboard.

## Implementation Steps

### Component 1 — Property-based identity tests

#### 1.1 Add dependency

Add `hypothesis` to `requirements-test.txt` (or the equivalent dev-dependencies file — verify before adding; it may already be present via another tool).

#### 1.2 Create strategies module

New file `tests/unit/strategies.py`:

```python
from hypothesis import strategies as st

# Valid email local-part characters — RFC 5322 subset
_local_char = st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="._+-")

def email_strategy() -> st.SearchStrategy[str]:
    """Plausible emails with mixed case and optional surrounding whitespace."""
    local = st.text(_local_char, min_size=1, max_size=20)
    domain = st.sampled_from(["example.com", "users.noreply.github.com", "corp.local"])
    leading_ws = st.sampled_from(["", " ", "  ", "\t"])
    trailing_ws = st.sampled_from(["", " ", "  ", "\t"])
    return st.builds(
        lambda l, d, lw, tw: f"{lw}{l}@{d}{tw}",
        local, domain, leading_ws, trailing_ws,
    )

def case_variants(email: str) -> st.SearchStrategy[str]:
    """Given an email, generate case-perturbed variants of it."""
    # Map each alpha char to random upper/lower via st.lists(st.booleans(), len=...)
    ...

def unicode_name_strategy() -> st.SearchStrategy[str]:
    """Display names with unicode pathologies."""
    return st.text(
        st.characters(min_codepoint=0x20, max_codepoint=0x10FFFF,
                       blacklist_categories=("Cs", "Cc")),
        min_size=1, max_size=50,
    )
```

#### 1.3 Property tests

New file `tests/unit/test_contributor_identity_properties.py`. Each test targets one invariant of `get_or_create_contributor`:

```python
from hypothesis import given, assume, settings
from .strategies import email_strategy, case_variants, unicode_name_strategy

class TestContributorIdentityProperties:

    @given(email=email_strategy(), name=unicode_name_strategy())
    def test_idempotent(self, db_session, email, name):
        """Calling get_or_create_contributor twice returns the same id."""
        c1 = get_or_create_contributor(db_session, email, name)
        c2 = get_or_create_contributor(db_session, email, name)
        assert c1.id == c2.id

    @given(email=email_strategy())
    def test_normalisation_stable(self, email):
        """Normalisation is a fixpoint: f(f(x)) == f(x)."""
        once = email.strip().lower()
        twice = once.strip().lower()
        assert once == twice

    @given(email=email_strategy(), data=st.data())
    def test_case_variants_collapse(self, db_session, email, data):
        """Any case-perturbation of a valid email returns the same contributor."""
        variant = data.draw(case_variants(email))
        c1 = get_or_create_contributor(db_session, email, "Alice")
        c2 = get_or_create_contributor(db_session, variant, "Alice")
        assert c1.id == c2.id

    @given(email=email_strategy())
    def test_whitespace_variants_collapse(self, db_session, email):
        """Leading/trailing/tab whitespace variants return same id."""
        c1 = get_or_create_contributor(db_session, email, "Alice")
        c2 = get_or_create_contributor(db_session, f"  {email.strip()}  ", "Alice")
        c3 = get_or_create_contributor(db_session, f"\t{email.strip()}\t", "Alice")
        assert c1.id == c2.id == c3.id

    @given(e1=email_strategy(), e2=email_strategy())
    def test_distinct_emails_do_not_collide(self, db_session, e1, e2):
        """Semantically-distinct emails return different contributor ids."""
        assume(e1.strip().lower() != e2.strip().lower())
        c1 = get_or_create_contributor(db_session, e1, "A")
        c2 = get_or_create_contributor(db_session, e2, "B")
        assert c1.id != c2.id

    @given(name=unicode_name_strategy())
    def test_unicode_names_round_trip(self, db_session, name):
        """Display names preserve unicode faithfully (not normalised)."""
        c = get_or_create_contributor(db_session, "alice@example.com", name)
        db_session.flush()
        reloaded = db_session.get(Contributor, c.id)
        assert reloaded.name == name
```

Each test runs Hypothesis's default 100 examples. Use `@settings(max_examples=...)` to tune if runtime is an issue. Mark the whole class `@pytest.mark.unit`; tests must complete under the existing unit-test timeout budget.

#### 1.4 CI wiring

No workflow change required — property tests live under `tests/unit/` and are picked up by the existing `pytest tests/unit/` step in [scripts/run-tests-docker.sh](../../scripts/run-tests-docker.sh) and [.github/workflows/tests.yml](../../.github/workflows/tests.yml).

### Component 2 — Live-API nightly monitoring

#### 2.1 Canary repositories

Designate a small number of known-good test repositories — one per platform, accessible via read-only creds. Examples: `stickleprojects/canary-repo` on GitHub, equivalent on the org's Azure DevOps instance. Criteria:

- Small (handful of PRs, handful of contributors).
- Stable (rarely changes, predictable counts).
- Contains at least one mixed-case email and one reviewer scenario.

Document the canaries in `tests/fixtures/canaries/README.md`.

#### 2.2 Canary test class

New file `tests/contract/integration/test_canary_live_api.py`. Marked `@pytest.mark.live_api` so it is excluded from normal CI.

```python
@pytest.mark.live_api
@pytest.mark.integration
class TestGitHubCanary:
    CANARY = "stickleprojects/canary-repo"
    EXPECTED_PR_COUNT = 5      # known-good baseline
    EXPECTED_CONTRIB_COUNT = 3

    def test_canary_extraction_and_invariants(
        self, db_session, github_extractor, db_invariants_check
    ):
        repo_data = github_extractor.extract_repository(self.CANARY)
        _store_repository_data(db_session, repo_data)
        db_session.commit()

        prs = db_session.query(PullRequest).filter(...).count()
        contribs = db_session.query(Contributor).count()
        assert prs >= self.EXPECTED_PR_COUNT
        assert contribs >= self.EXPECTED_CONTRIB_COUNT
        # db_invariants_check fixture runs on teardown
```

Parallel `TestAzureDevOpsCanary` for the other platform. Baselines (`EXPECTED_PR_COUNT`, etc.) are lower bounds; inequality prevents flaky failures from legitimate canary growth. If numbers drift far from expected, the canary is probably stale — open an issue to refresh the baseline.

#### 2.3 Nightly workflow

New file `.github/workflows/live-api-nightly.yml`:

```yaml
name: live-api-nightly
on:
  schedule:
    - cron: "0 2 * * *"   # 02:00 UTC daily
  workflow_dispatch:       # manual trigger for ad-hoc checks

jobs:
  live-api:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run live-API tests
        env:
          GITHUB_TOKEN: ${{ secrets.CANARY_GITHUB_TOKEN }}
          AZURE_DEVOPS_PAT: ${{ secrets.CANARY_AZURE_DEVOPS_PAT }}
        run: bash scripts/run-tests-docker.sh --live-api
      - name: Open issue on failure
        if: failure()
        uses: actions/github-script@v7
        with:
          script: |
            // Find/create issue titled "Live-API regression detected"
            // Append run URL and failing-test names
            ...
```

**Secrets setup** (manual, one-time):

- Create `CANARY_GITHUB_TOKEN` — a GitHub PAT with `repo:read` scope on the canary repo only.
- Create `CANARY_AZURE_DEVOPS_PAT` — equivalent, read-only, scoped to the canary project.
- Confirm both are classic-scoped tokens with minimal surface.

Not a required PR check. Failures never block merges — the signal is the opened issue.

### Component 3 — Production observability hook

#### 3.1 Health module

New file `src/utils/extraction_health.py`. Lives in `utils/` per the architecture rule that cross-cutting concerns belong there.

```python
@dataclass
class InvariantResult:
    name: str
    violations: int
    sample_rows: list[dict]   # capped at 5

@dataclass
class HealthReport:
    platform: str
    repo_id: str | None       # None = whole-DB check
    timestamp: datetime
    invariants: list[InvariantResult]

    @property
    def is_healthy(self) -> bool:
        return all(r.violations == 0 for r in self.invariants)

def compute_extraction_health(
    session, platform: str, repo_id: str | None = None
) -> HealthReport:
    """Run every named invariant from tests/db_invariants.sql against the DB."""
    invariants = _parse_invariants_sql(Path("tests/db_invariants.sql"))
    # If invariant scope is repo-specific, substitute :repo_id into the query
    results = [...]
    return HealthReport(platform, repo_id, datetime.utcnow(), results)
```

The module parses the SAME `tests/db_invariants.sql` file used by pytest — invariants are defined once, checked everywhere. If the file is not packaged with the runtime image, copy it under `src/data/db_invariants.sql` during Docker build and have the module resolve either location.

#### 3.2 Wire into extraction workflows

At the tail of each extraction workflow (after final commit), call `compute_extraction_health` and emit the report. In [src/workflows/github_analysis.py](../../src/workflows/github_analysis.py) and [src/workflows/azure_devops_analysis.py](../../src/workflows/azure_devops_analysis.py), after the storage step:

```python
from src.utils.extraction_health import compute_extraction_health
from src.utils.metrics import emit_health_report

report = compute_extraction_health(session, platform="github", repo_id=repo_id)
emit_health_report(report)
if not report.is_healthy:
    logger.warning("extraction-health violations", extra={"report": asdict(report)})
```

#### 3.3 Metric emission

New file `src/utils/metrics.py` (or extend existing metrics module — check first). Emit one Prometheus gauge per invariant:

- `extraction_invariant_violations{platform, repo_id, invariant_name}`
- Plus a structured log line at `warning` level when any violation is non-zero

Use the existing Prometheus client library (check `requirements.txt` for `prometheus_client`). If not present, add it as a dependency — but only if the wider project already has Prometheus wiring. If not, fall back to structured logs only and mark the dashboard step as "pending Prometheus infrastructure."

#### 3.4 Grafana dashboard

New file `dashboards/extraction-health.json`. Panels:

- One gauge per named invariant showing current value across platforms.
- One time-series showing `extraction_invariant_violations` over the last 7 days, legend per invariant.
- Provisioning entry in Grafana config so the dashboard auto-loads.

Alert rule: fire if any invariant gauge is non-zero for more than 1 hour. Route to the same channel as existing extraction alerts.

**Top-link bar (when Plan 025 has landed)**: copy the canonical 6-entry `links[]` array from any other `dashboards/*.json` (e.g. `security-dashboard.json`) so the new dashboard inherits the uniform top-link bar from Plan 025 Phase 2. Do not invent a new bar shape. If Plan 025 has not yet shipped, omit `links[]` and Phase 2 will add it during the sweep.

#### 3.5 Documentation

Short note in `docs/03-operations/extraction-health-monitoring.md`:

- What each invariant means.
- What to do when one fires (likely: open a bug + inspect sample rows from the log line).
- How to add a new invariant (edit `tests/db_invariants.sql` — it propagates to CI, live-API nightly, and production automatically).

## Compatibility Notes

- Component 1 adds `hypothesis` if not already in dev deps. Verify before adding.
- Component 2 requires secrets with read-only canary scope — must be provisioned by someone with org admin access. Do not add workflow without confirming secrets exist, otherwise it will fail every night on missing-creds.
- Component 3 introduces a production code path in the workflow tail. The call must never crash an extraction — wrap in try/except that logs and swallows, so a bug in health-checking can never break extraction itself.
- `tests/db_invariants.sql` must be readable by both pytest and the production runtime. If Docker multi-stage builds skip `tests/`, copy the file into a runtime-accessible location during image build.
- Components are independent — landing them one at a time is fine. Suggested order: 1 (pure unit, lowest risk), 3 (observability, read-only from prod), 2 (requires secrets setup).

## Scope Boundary

In scope:

- Components 1, 2, 3 as described.
- Reuse of `tests/db_invariants.sql` from Plan 019 across CI, live-API, and production.

Out of scope:

- Cross-platform identity resolution (GitHub user ↔ Azure DevOps user). Architectural design problem; separate plan.
- Changing Prometheus or Grafana infrastructure. Component 3 assumes they exist; if not, it degrades to structured logs.
- Fault injection / chaos testing (timeout mid-extraction, rate-limit mid-page). Separate plan candidate.
- Scale/pagination testing (repos with 1000+ PRs). Separate plan candidate.
- Retiring `-m "not live_api"` from the default CI run. Keep live_api tests off the hot PR path; only Component 2 executes them.

## Success Criteria

- [ ] `hypothesis` added to dev dependencies (if not already present).
- [ ] `tests/unit/test_contributor_identity_properties.py` contains at least 6 property tests and runs under the existing unit-test timeout.
- [ ] All property tests pass; removing `.strip().lower()` from `get_or_create_contributor` causes at least `test_idempotent`, `test_case_variants_collapse`, and `test_whitespace_variants_collapse` to fail (manually verified once).
- [ ] `.github/workflows/live-api-nightly.yml` exists, runs on cron, uses canary secrets, and is not a required PR check.
- [ ] `CANARY_GITHUB_TOKEN` and `CANARY_AZURE_DEVOPS_PAT` secrets provisioned with read-only scope on canary repos only.
- [ ] Manual workflow dispatch of the nightly succeeds end-to-end at least once before merging.
- [ ] Canary test baselines documented in `tests/fixtures/canaries/README.md`.
- [ ] `src/utils/extraction_health.py` parses the same `tests/db_invariants.sql` used by CI; unit test proves identical invariant set.
- [ ] Health report emitted at tail of each extraction workflow; wrapped so failures never break the workflow.
- [ ] Prometheus gauges visible in `dashboards/extraction-health.json`; dashboard auto-provisions.
- [ ] Alert rule fires on sustained invariant violation (verified by injecting a synthetic orphan in a staging DB).
- [ ] `docs/03-operations/extraction-health-monitoring.md` explains the signal and the remediation path.

## Verification

1. `bash scripts/run-tests-docker.sh` — full suite green, includes property tests.
2. Temporarily revert `.strip().lower()` in `get_or_create_contributor`. Run `pytest tests/unit/test_contributor_identity_properties.py`. Confirm Hypothesis shrinks the input to a minimal failing case (likely two-character case-variant email). Restore the line.
3. Manually dispatch the nightly workflow via the GitHub UI. Confirm it runs live-API tests against the canary, passes, and does not open an issue. Break the canary baseline (lower the expected count) locally, dispatch again, confirm an issue is opened with the failure details. Revert the baseline.
4. Run a production-like extraction against a staging DB. Query `extraction_invariant_violations` in Prometheus and confirm gauges exist with value 0 for all invariants.
5. Inject a synthetic violation in the staging DB (e.g. INSERT a `pull_requests` row with `author_id = 999999`). Trigger an extraction. Confirm the gauge goes non-zero and the Grafana alert fires after the cool-down window.
6. Add a new invariant to `tests/db_invariants.sql` (e.g. `no_null_commit_author_email`). Confirm without any other code change that: (a) the pytest fixture picks it up, (b) the `verify-extraction.sh` tail picks it up, (c) `compute_extraction_health` exposes a new gauge. This proves the single-source-of-truth property.
