#!/usr/bin/env python3
"""
Screenshot Database Seeder
---------------------------
Populates the screenshot database with realistic data by running every
non-empty fixture scenario through the same extraction and storage pipeline
that the e2e tests use.

Because the data comes from the tested fixture infrastructure, every
Grafana dashboard view is guaranteed to receive data in the same format
that the application produces in production.

Usage
-----
  python scripts/seed_screenshot_db.py [--db-url <url>]

  --db-url   SQLAlchemy database URL.
             Default: $DATABASE_URL env var, or
             postgresql://postgres:postgres@localhost:5432/devops_screenshots

Environment variables
---------------------
  DATABASE_URL          Override the default database URL.
  PYTHONPATH            Must include the repo root so that src/ and tests/ are
                        importable (the workflow sets this automatically).

What this script does
---------------------
1. Connects to the target database (schema + views already applied by the
   db-migrations container).
2. Iterates over every non-empty scenario in
   tests/fixtures/scenarios/generated/.
3. For each scenario it calls the same store_* functions as the e2e tests:
     store_organization → store_project → store_repository →
     store_branch → store_commit → store_pull_request →
     store_languages → store_dependencies (if manifests present)
4. For scenarios that carry vulnerability_data it calls
   store_package_metadata + store_repo_dependencies to populate the
   security / dependency views.
5. Commits all data — no rollback, so Grafana can read it immediately.

Exit codes
----------
  0  All scenarios seeded successfully.
  1  Fatal error (e.g. cannot connect to database).
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime
from pathlib import Path

# ── ensure repo root is on sys.path ──────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# ── third-party / application imports (available after pip install -r requirements.txt)
try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session

    from src.database.storage import (
        store_organization,
        store_project,
        store_repository,
        store_branch,
        store_commit,
        store_pull_request,
        store_languages,
        store_dependencies,
        store_package_metadata,
        store_repo_dependencies,
    )
    from src.analyzers.dependency_analyzer import DependencyAnalyzer
    from src.analyzers.dependency_enricher import EnrichedDependency
    from src.extractors.base import Platform
    from tests.fixtures.fixture_extractor import FixtureExtractor
    from tests.fixtures.sample_data import sample_organization_data, sample_repository_data
except ImportError as exc:
    print(
        f"❌ Import error: {exc}\n"
        "   Make sure you have run `pip install -r requirements.txt` and that\n"
        "   PYTHONPATH includes the repository root.",
        file=sys.stderr,
    )
    sys.exit(1)


# ── scenarios to load ────────────────────────────────────────────────────────

# All non-empty generated scenarios.  Empty stubs are excluded because they
# contribute no commits/PRs and would clutter the repository table without
# adding useful chart data.
SCENARIOS_DIR = REPO_ROOT / "tests" / "fixtures" / "scenarios" / "generated"

SKIP_SCENARIOS = {"empty-stub", "empty-archive", "empty-handoff"}


def _discover_scenarios() -> list[str]:
    """Return scenario names from the generated directory, excluding empty ones."""
    return sorted(
        p.stem
        for p in SCENARIOS_DIR.glob("*.json")
        if p.stem not in SKIP_SCENARIOS
    )


# ── per-scenario loading ──────────────────────────────────────────────────────

def _load_scenario(session: Session, scenario_name: str) -> object:
    """
    Load one fixture scenario into the database.

    Mirrors the _load_scenario helper in test_full_pipeline_e2e.py but
    operates on a plain (non-rollback) session so data persists for Grafana.
    """
    extractor = FixtureExtractor(scenario_name)

    org_data = sample_organization_data(
        name=f"fixture-org-{scenario_name}",
        platform=Platform.GITHUB,
    )
    org = store_organization(session, org_data)

    project = store_project(session, org, name=f"project-{scenario_name}")

    repo_data = sample_repository_data(
        repo_id=f"fixture/{scenario_name}",
        name=scenario_name,
        url=f"https://github.com/fixture/{scenario_name}",
    )
    repo = store_repository(session, project, repo_data)
    session.flush()

    # Branches
    for branch in extractor.get_branches(repo.repo_id):
        store_branch(session, repo.repo_id, branch)
    session.flush()

    # Commits (use the first declared branch as the target)
    branches = extractor.get_branches(repo.repo_id)
    default_branch = branches[0].name if branches else "main"
    for commit in extractor.get_commits(repo.repo_id):
        store_commit(session, repo.repo_id, default_branch, commit)
    session.flush()

    # Pull requests
    for pr in extractor.get_pull_requests(repo.repo_id):
        store_pull_request(session, repo.repo_id, pr)
    session.flush()

    # Languages
    languages = extractor.get_languages(repo.repo_id)
    if languages:
        store_languages(session, repo.repo_id, languages)
        session.flush()

    # Manifest-based dependencies (no live API enrichment)
    analyzer = DependencyAnalyzer(enrich=False)
    dep_result = analyzer.analyze(extractor, repo.repo_id)
    if dep_result.total_dependencies > 0:
        store_dependencies(session, repo.repo_id, dep_result.dependencies)
        session.flush()

    session.commit()
    return repo


def _enrich_scenario(session: Session, repo_id: str, scenario_name: str) -> int:
    """
    Store package metadata and per-repo enriched dependencies from the
    scenario's vulnerability_data field.

    Mirrors _enrich_from_fixture in test_full_pipeline_e2e.py.
    Returns the number of packages processed.
    """
    packages = FixtureExtractor(scenario_name).get_vulnerability_data()
    if not packages:
        return 0

    enriched_deps: list[EnrichedDependency] = []
    for pkg_data in packages:
        raw_eol_date = pkg_data.get("eol_date")
        eol_date = date.fromisoformat(raw_eol_date) if raw_eol_date else None

        store_package_metadata(
            session,
            package_name=pkg_data["package_name"],
            ecosystem=pkg_data["ecosystem"],
            latest_version=pkg_data["latest_version"],
            is_eol=pkg_data["is_eol"],
            eol_date=eol_date,
            vulnerabilities=pkg_data["vulnerabilities"],
        )
        enriched_deps.append(
            EnrichedDependency(
                package_name=pkg_data["package_name"],
                version=pkg_data["pinned_version"],
                ecosystem=pkg_data["ecosystem"],
                is_dev_dependency=False,
                source_file="requirements.txt",
                version_constraint=None,
                has_known_vulnerabilities=len(pkg_data["vulnerabilities"]) > 0,
            )
        )

    store_repo_dependencies(session, repo_id, enriched_deps)
    session.commit()
    return len(packages)


# ── quick view sanity-check ───────────────────────────────────────────────────

def _print_view_counts(session: Session) -> None:
    """Print a quick summary of key view row-counts to confirm data is visible."""
    checks = [
        ("v_commits_total",              "SELECT total FROM v_commits_total"),
        ("v_pull_requests_total",        "SELECT total FROM v_pull_requests_total"),
        ("v_active_repositories_total",  "SELECT total FROM v_active_repositories_total"),
        ("v_contributors_total",         "SELECT total FROM v_contributors_total"),
        ("v_security_overview_latest",
         "SELECT total_vulnerabilities FROM v_security_overview_latest"),
    ]
    print("\n📊 View sanity-check:")
    for label, sql in checks:
        try:
            val = session.execute(text(sql)).scalar()
            print(f"   {label}: {val}")
        except Exception as exc:
            print(f"   {label}: ERROR – {exc}")


# ── entry point ───────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Seed the screenshot database with fixture data."
    )
    parser.add_argument(
        "--db-url",
        default=None,
        help="SQLAlchemy database URL (overrides $DATABASE_URL)",
    )
    args = parser.parse_args(argv)

    db_url = (
        args.db_url
        or os.environ.get("DATABASE_URL")
        or "postgresql://postgres:postgres@localhost:5432/devops_screenshots"
    )

    print(f"🔌 Connecting to {db_url.split('@')[-1]} …")
    try:
        engine = create_engine(db_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        print(f"❌ Cannot connect to database: {exc}", file=sys.stderr)
        return 1

    scenarios = _discover_scenarios()
    print(f"📋 Found {len(scenarios)} scenarios to load: {', '.join(scenarios)}\n")

    loaded = 0
    enriched = 0
    errors: list[str] = []

    with Session(engine) as session:
        for scenario_name in scenarios:
            print(f"  ▶ Loading {scenario_name} …", end=" ", flush=True)
            try:
                repo = _load_scenario(session, scenario_name)
                pkg_count = _enrich_scenario(session, repo.repo_id, scenario_name)
                loaded += 1
                if pkg_count:
                    enriched += 1
                    print(f"✅  (+{pkg_count} packages/vulns)")
                else:
                    print("✅")
            except Exception as exc:
                print(f"❌  {exc}", file=sys.stderr)
                errors.append(f"{scenario_name}: {exc}")
                try:
                    session.rollback()
                except Exception:
                    pass

        _print_view_counts(session)

    print(f"\n🎉 Seeding complete: {loaded}/{len(scenarios)} scenarios loaded, "
          f"{enriched} with vulnerability data.")

    if errors:
        print(f"\n⚠️  {len(errors)} scenario(s) failed:", file=sys.stderr)
        for err in errors:
            print(f"   • {err}", file=sys.stderr)
        # Non-fatal: Grafana will show data from the scenarios that did load.

    return 0


if __name__ == "__main__":
    sys.exit(main())
