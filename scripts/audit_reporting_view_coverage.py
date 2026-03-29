"""
Audit reporting-view coverage.

Parses database/views.sql to extract all defined view names, then parses
tests/contract/database/test_reporting_views.py to find which views are
referenced in SQL strings. Writes machine-readable artifacts to
artifacts/assessment/ and prints a concise summary to stdout.

No external dependencies – stdlib only.
"""

import json
import os
import re
import sys


# ---------------------------------------------------------------------------
# Paths (relative to repo root, resolved at runtime)
# ---------------------------------------------------------------------------
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
VIEWS_SQL = os.path.join(REPO_ROOT, "database", "views.sql")
TEST_FILE = os.path.join(
    REPO_ROOT, "tests", "contract", "database", "test_reporting_views.py"
)
ARTIFACTS_DIR = os.path.join(REPO_ROOT, "artifacts", "assessment")


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def extract_defined_views(views_sql_path: str) -> list[str]:
    """Return sorted list of view names from CREATE OR REPLACE VIEW statements."""
    pattern = re.compile(
        r"CREATE\s+OR\s+REPLACE\s+VIEW\s+([\w]+)", re.IGNORECASE
    )
    with open(views_sql_path, "r", encoding="utf-8") as fh:
        content = fh.read()
    return sorted(set(pattern.findall(content)))


def extract_referenced_views(test_file_path: str) -> list[str]:
    """Return sorted list of view names referenced in SQL strings inside the test file.

    Looks for the pattern ``FROM <view_name>`` or ``JOIN <view_name>`` where
    the name starts with v_ (case-insensitive).  Also catches bare view names
    that appear inside quoted strings regardless of context.
    """
    with open(test_file_path, "r", encoding="utf-8") as fh:
        content = fh.read()

    found: set[str] = set()

    # 1. FROM / JOIN references (most reliable)
    sql_ref = re.compile(
        r"(?:FROM|JOIN)\s+(v_\w+)", re.IGNORECASE
    )
    for m in sql_ref.finditer(content):
        found.add(m.group(1).lower())

    # 2. Quoted string literals that look like view names (e.g. "v_open_prs")
    quoted = re.compile(r"""["'](v_\w+)["']""")
    for m in quoted.finditer(content):
        found.add(m.group(1).lower())

    # 3. Bare identifiers assigned or passed as arguments  e.g. view_name="v_open_prs"
    #    This intentionally casts a wide net; false positives (Python variable names
    #    that start with v_) are acceptable here because we intersect with the
    #    *defined* views set before reporting anything as "tested".
    bare = re.compile(r"\b(v_\w+)\b")
    for m in bare.finditer(content):
        found.add(m.group(1).lower())

    return sorted(found)


# ---------------------------------------------------------------------------
# Rename-drift heuristics
# ---------------------------------------------------------------------------

_SUFFIX_VARIANTS = [
    ("_30d_total", "_30d"),
    ("_30d", "_30d_total"),
    ("_latest", ""),
    ("", "_latest"),
    ("_summary", ""),
    ("", "_summary"),
]


def detect_possible_renames(
    defined: list[str], tested: list[str]
) -> list[dict]:
    """Flag pairs where a tested name differs from a defined name by a known suffix swap."""
    defined_set = set(defined)
    tested_set = set(tested)
    renames = []
    for t in tested_set - defined_set:
        for old_sfx, new_sfx in _SUFFIX_VARIANTS:
            candidate = (
                t[: -len(old_sfx)] + new_sfx
                if old_sfx and t.endswith(old_sfx)
                else t + new_sfx
            )
            if candidate in defined_set:
                renames.append(
                    {
                        "tested_as": t,
                        "defined_as": candidate,
                        "note": f"suffix swap: '{old_sfx}' → '{new_sfx}'",
                    }
                )
                break
    return sorted(renames, key=lambda x: x["tested_as"])


# ---------------------------------------------------------------------------
# Artifact writers
# ---------------------------------------------------------------------------

def write_json(path: str, obj) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2)
    print(f"  wrote {os.path.relpath(path, REPO_ROOT)}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    if not os.path.isfile(VIEWS_SQL):
        print(f"ERROR: views.sql not found at {VIEWS_SQL}", file=sys.stderr)
        return 1
    if not os.path.isfile(TEST_FILE):
        print(f"ERROR: test file not found at {TEST_FILE}", file=sys.stderr)
        return 1

    defined = extract_defined_views(VIEWS_SQL)
    referenced = extract_referenced_views(TEST_FILE)

    # "Tested" = referenced in test file AND actually defined in views.sql
    defined_set = set(defined)
    referenced_set = set(referenced)

    tested = sorted(defined_set & referenced_set)
    untested = sorted(defined_set - referenced_set)
    possible_renames = detect_possible_renames(defined, referenced)

    total = len(defined)
    covered = len(tested)
    pct = round(100 * covered / total, 1) if total else 0.0

    summary = {
        "total_views": total,
        "tested_views": covered,
        "untested_views": len(untested),
        "coverage_pct": pct,
        "possible_renames": len(possible_renames),
        "views_sql": os.path.relpath(VIEWS_SQL, REPO_ROOT),
        "test_file": os.path.relpath(TEST_FILE, REPO_ROOT),
    }

    print("=== Reporting-View Coverage Audit ===")
    print(f"  Defined views  : {total}")
    print(f"  Tested views   : {covered}")
    print(f"  Untested views : {len(untested)}")
    print(f"  Coverage       : {pct}%")
    if possible_renames:
        print(f"  Possible renames detected: {len(possible_renames)}")
    print()

    if untested:
        print("Untested views:")
        for v in untested:
            print(f"  - {v}")
        print()

    print("Writing artifacts ...")
    write_json(os.path.join(ARTIFACTS_DIR, "reporting_views_all.json"), defined)
    write_json(os.path.join(ARTIFACTS_DIR, "reporting_views_tested.json"), tested)
    write_json(os.path.join(ARTIFACTS_DIR, "reporting_views_untested.json"), untested)
    write_json(os.path.join(ARTIFACTS_DIR, "reporting_views_summary.json"), summary)
    write_json(
        os.path.join(ARTIFACTS_DIR, "reporting_views_possible_renames.json"),
        possible_renames,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
