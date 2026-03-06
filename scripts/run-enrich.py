#!/usr/bin/env python3
"""Orchestrate fixture seed enrichment for all repos defined in config.json.

Reads config.json to determine expected seed names, then calls enrich-repo.py
for each seed file found in tests/fixtures/scenarios/generated/.

Usage:
    python run-enrich.py [config.json]

config.json defaults to tests/fixtures/scenarios/config.json relative to the
project root (the script's parent directory).
"""

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_CONFIG = PROJECT_ROOT / "tests/fixtures/scenarios/config.json"
GENERATED_DIR = PROJECT_ROOT / "tests/fixtures/scenarios/generated"
ENRICH_SCRIPT = Path(__file__).parent / "enrich-repo.py"


def expand_seed_names(config: dict) -> list[str]:
    names = []
    for repo_set in config["repo_sets"]:
        if "names" in repo_set:
            names.extend(repo_set["names"])
        elif "name_template" in repo_set:
            tmpl = repo_set["name_template"]
            names.extend(tmpl.replace("{service}", s) for s in repo_set.get("services", []))
    return names


def main() -> None:
    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CONFIG

    config = json.loads(config_path.read_text())
    seed_names = expand_seed_names(config)

    found = 0
    for name in seed_names:
        seed_path = GENERATED_DIR / f"{name}.json"
        if not seed_path.exists():
            print(f"  [skip] {name}.json not found — run --step seeds first")
            continue

        print(f"\n==> Running enrichment for {name}")
        result = subprocess.run(
            ["python", str(ENRICH_SCRIPT), str(seed_path), str(config_path)],
            check=False,
        )
        if result.returncode != 0:
            print(f"ERROR: Enrichment failed for {name} (exit {result.returncode})", file=sys.stderr)
            sys.exit(result.returncode)
        found += 1

    if found == 0:
        print("ERROR: No seed JSON files found. Run --step seeds first.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
