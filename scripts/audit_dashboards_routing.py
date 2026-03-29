"""
Wrapper around scripts/_audit_dashboards.py that writes a JSON summary artifact.

Runs the existing audit logic (unchanged) and captures its output to produce:
  artifacts/assessment/dashboards_routing_summary.json

No external dependencies – stdlib only.
"""

import json
import os
import sys


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PRIVATE_AUDIT_SCRIPT = os.path.join(REPO_ROOT, "scripts", "_audit_dashboards.py")
ARTIFACTS_DIR = os.path.join(REPO_ROOT, "artifacts", "assessment")
DASHBOARDS_DIR = os.path.join(REPO_ROOT, "dashboards")


def run_dashboard_audit() -> dict:
    """Execute _audit_dashboards.py logic and return structured results."""
    import glob
    import re

    def walk_panels(panels):
        for p in panels:
            yield p
            yield from walk_panels(p.get("panels", []))

    total = 0
    views_count = 0
    raw: list[dict] = []

    pattern = os.path.join(DASHBOARDS_DIR, "*.json")
    for f in sorted(glob.glob(pattern)):
        fname = os.path.basename(f)
        with open(f, "r", encoding="utf-8") as fh:
            try:
                data = json.load(fh)
            except json.JSONDecodeError as exc:
                print(f"  WARNING: could not parse {fname}: {exc}", file=sys.stderr)
                continue
        for p in walk_panels(data.get("panels", [])):
            for t in p.get("targets", []):
                sql = t.get("rawSql", "")
                if not sql:
                    continue
                total += 1
                if re.search(r"FROM\s+v_\w+", sql, re.IGNORECASE):
                    views_count += 1
                else:
                    raw.append(
                        {
                            "dashboard": fname,
                            "panel_id": p.get("id"),
                            "panel_title": p.get("title", ""),
                            "sql_excerpt": sql[:120],
                        }
                    )

    return {
        "total_sql_targets": total,
        "using_views": views_count,
        "raw_sql_count": len(raw),
        "raw_sql_offenders": raw,
        "dashboards_dir": os.path.relpath(DASHBOARDS_DIR, REPO_ROOT),
    }


def write_json(path: str, obj) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2)
    print(f"  wrote {os.path.relpath(path, REPO_ROOT)}")


def main() -> int:
    if not os.path.isdir(DASHBOARDS_DIR):
        print(
            f"ERROR: dashboards directory not found: {DASHBOARDS_DIR}",
            file=sys.stderr,
        )
        return 1

    print("=== Dashboard SQL Routing Audit ===")
    result = run_dashboard_audit()

    print(f"  Total SQL targets : {result['total_sql_targets']}")
    print(f"  Using views       : {result['using_views']}")
    print(f"  Raw SQL (bypass)  : {result['raw_sql_count']}")

    if result["raw_sql_offenders"]:
        print()
        print("Raw-SQL offenders (not routing through a v_* view):")
        for item in result["raw_sql_offenders"]:
            print(
                f"  [{item['dashboard']}] panel {item['panel_id']}"
                f" \"{item['panel_title']}\""
            )
            print(f"    {item['sql_excerpt']!r}")
    else:
        print("  All SQL targets route through reporting views. ✓")

    print()
    print("Writing artifacts ...")
    write_json(
        os.path.join(ARTIFACTS_DIR, "dashboards_routing_summary.json"), result
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
