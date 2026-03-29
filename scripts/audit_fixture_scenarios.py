"""
Audit fixture-scenario coverage.

Counts and lists JSON files under tests/fixtures/scenarios/generated/ then
extracts the exercised SCENARIOS list from
tests/contract/integration/test_fixture_scenarios.py.

Writes machine-readable artifacts to artifacts/assessment/ and prints a
concise summary to stdout.

No external dependencies – stdlib only.
"""

import ast
import json
import os
import re
import sys


# ---------------------------------------------------------------------------
# Paths (relative to repo root)
# ---------------------------------------------------------------------------
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GENERATED_DIR = os.path.join(
    REPO_ROOT, "tests", "fixtures", "scenarios", "generated"
)
TEST_FILE = os.path.join(
    REPO_ROOT,
    "tests",
    "contract",
    "integration",
    "test_fixture_scenarios.py",
)
ARTIFACTS_DIR = os.path.join(REPO_ROOT, "artifacts", "assessment")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def list_generated_scenarios(generated_dir: str) -> list[str]:
    """Return sorted list of base names (without .json) of generated fixture files."""
    if not os.path.isdir(generated_dir):
        return []
    names = []
    for fname in os.listdir(generated_dir):
        if fname.endswith(".json"):
            names.append(fname[:-5])  # strip .json
    return sorted(names)


def extract_exercised_scenarios(test_file_path: str) -> list[str]:
    """Parse the SCENARIOS list from the test file using AST, with regex fallback."""
    with open(test_file_path, "r", encoding="utf-8") as fh:
        source = fh.read()

    # --- AST approach (precise) ---
    try:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "SCENARIOS":
                        if isinstance(node.value, ast.List):
                            return sorted(
                                elt.value
                                for elt in node.value.elts
                                if isinstance(elt, ast.Constant)
                                and isinstance(elt.value, str)
                            )
    except SyntaxError:
        pass

    # --- Regex fallback ---
    pattern = re.compile(
        r'SCENARIOS\s*=\s*\[([^\]]+)\]', re.DOTALL
    )
    m = pattern.search(source)
    if m:
        items = re.findall(r'["\']([^"\']+)["\']', m.group(1))
        return sorted(items)

    return []


def write_json(path: str, obj) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2)
    print(f"  wrote {os.path.relpath(path, REPO_ROOT)}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    if not os.path.isdir(GENERATED_DIR):
        print(
            f"ERROR: generated scenarios directory not found: {GENERATED_DIR}",
            file=sys.stderr,
        )
        return 1
    if not os.path.isfile(TEST_FILE):
        print(f"ERROR: test file not found: {TEST_FILE}", file=sys.stderr)
        return 1

    all_scenarios = list_generated_scenarios(GENERATED_DIR)
    exercised = extract_exercised_scenarios(TEST_FILE)

    exercised_set = set(exercised)
    all_set = set(all_scenarios)

    unexercised = sorted(all_set - exercised_set)
    # Exercised but not generated (stale references)
    orphan = sorted(exercised_set - all_set)

    total = len(all_scenarios)
    n_exercised = len(exercised_set & all_set)
    ratio = round(n_exercised / total, 4) if total else 0.0

    summary = {
        "total_generated": total,
        "exercised": n_exercised,
        "unexercised": len(unexercised),
        "orphan_references": len(orphan),
        "coverage_ratio": ratio,          # 4 dp – for programmatic comparisons
        "coverage_pct": round(ratio * 100, 1),  # 1 dp – for display
        "generated_dir": os.path.relpath(GENERATED_DIR, REPO_ROOT),
        "test_file": os.path.relpath(TEST_FILE, REPO_ROOT),
    }

    print("=== Fixture-Scenario Coverage Audit ===")
    print(f"  Generated scenarios : {total}")
    print(f"  Exercised by tests  : {n_exercised}")
    print(f"  Unexercised         : {len(unexercised)}")
    print(f"  Coverage            : {summary['coverage_pct']}%")
    if orphan:
        print(
            f"  Orphan references (exercised but file missing): {len(orphan)}"
        )
    print()

    if unexercised:
        print("Unexercised scenarios:")
        for s in unexercised:
            print(f"  - {s}")
        print()

    if orphan:
        print("Orphan test references (no matching file):")
        for s in orphan:
            print(f"  - {s}")
        print()

    print("Writing artifacts ...")
    write_json(
        os.path.join(ARTIFACTS_DIR, "fixture_generated_all.json"), all_scenarios
    )
    write_json(
        os.path.join(ARTIFACTS_DIR, "fixture_exercised.json"),
        sorted(exercised_set & all_set),
    )
    write_json(
        os.path.join(ARTIFACTS_DIR, "fixture_unexercised.json"), unexercised
    )
    write_json(os.path.join(ARTIFACTS_DIR, "fixture_summary.json"), summary)

    return 0


if __name__ == "__main__":
    sys.exit(main())
