#!/usr/bin/env python3
"""
Dashboard Screenshot Capture Script
-------------------------------------
Uses the Grafana Image Renderer API to capture a PNG screenshot of every
Grafana dashboard whose JSON source file has changed since the last commit
(or all dashboards when ``--all`` is passed).

Screenshots are written to ``docs/images/dashboards/``.

Usage
-----
  # Capture only changed dashboards (git-diff from HEAD~1)
  python scripts/capture_dashboard_screenshots.py

  # Capture all dashboards regardless of git changes
  python scripts/capture_dashboard_screenshots.py --all

  # Capture only specific dashboards by uid
  python scripts/capture_dashboard_screenshots.py --uid repo-overview security-dashboard

  # Override Grafana base URL (default: http://localhost:3000)
  python scripts/capture_dashboard_screenshots.py --grafana-url http://localhost:3000

  # Set image dimensions
  python scripts/capture_dashboard_screenshots.py --width 1600 --height 900

Exit codes
----------
  0  All requested screenshots captured successfully.
  1  One or more screenshots failed.
  2  No dashboards matched the selection criteria (treated as success).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import NamedTuple


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

class Dashboard(NamedTuple):
    uid: str
    title: str
    slug: str          # filesystem-safe title for filenames
    json_path: Path    # source JSON file


# ---------------------------------------------------------------------------
# Dashboard discovery
# ---------------------------------------------------------------------------

def _slugify(title: str) -> str:
    """Convert a dashboard title to a filename-safe slug."""
    import re
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def discover_dashboards(dashboards_dir: Path) -> list[Dashboard]:
    """Return all dashboards found in *dashboards_dir*."""
    boards: list[Dashboard] = []
    for path in sorted(dashboards_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"  ⚠️  Skipping {path.name}: {exc}", file=sys.stderr)
            continue

        uid = data.get("uid") or path.stem
        title = data.get("title") or path.stem
        boards.append(Dashboard(
            uid=uid,
            title=title,
            slug=_slugify(title),
            json_path=path,
        ))
    return boards


def changed_dashboard_paths(repo_root: Path, base_ref: str = "HEAD~1") -> set[Path]:
    """Return the set of dashboard JSON paths that changed since *base_ref*."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "diff", "--name-only", base_ref, "HEAD",
             "--", "dashboards/"],
            capture_output=True, text=True, check=True,
        )
        paths: set[Path] = set()
        for line in result.stdout.splitlines():
            p = repo_root / line.strip()
            if p.suffix == ".json" and p.exists():
                paths.add(p.resolve())
        return paths
    except subprocess.CalledProcessError as exc:
        print(f"  ⚠️  git diff failed ({exc}); treating all dashboards as changed",
              file=sys.stderr)
        return set()


# ---------------------------------------------------------------------------
# Grafana health check
# ---------------------------------------------------------------------------

def wait_for_grafana(base_url: str, timeout: int = 120) -> None:
    """Block until Grafana's /api/health endpoint reports OK, or raise."""
    health_url = f"{base_url.rstrip('/')}/api/health"
    deadline = time.time() + timeout
    last_exc: Exception | None = None

    print(f"⏳ Waiting for Grafana at {base_url} (timeout {timeout}s) …")
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(health_url, timeout=5) as resp:
                body = json.loads(resp.read())
                if body.get("database") == "ok":
                    print("  ✅ Grafana is healthy")
                    return
                print(f"  … database not ready yet: {body}")
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            last_exc = exc
        time.sleep(3)

    raise RuntimeError(
        f"Grafana did not become healthy within {timeout}s. "
        f"Last error: {last_exc}"
    )


# ---------------------------------------------------------------------------
# Screenshot capture
# ---------------------------------------------------------------------------

def capture_screenshot(
    base_url: str,
    dashboard: Dashboard,
    output_dir: Path,
    width: int,
    height: int,
) -> Path:
    """
    Call Grafana's image renderer endpoint and save the PNG.

    The render URL pattern is:
      GET /render/d/{uid}/{slug}?width=W&height=H&from=now-1h&to=now
    """
    url = (
        f"{base_url.rstrip('/')}/render/d/{dashboard.uid}/{dashboard.slug}"
        f"?width={width}&height={height}&from=now-1h&to=now&tz=UTC"
    )
    output_path = output_dir / f"{dashboard.slug}.png"

    print(f"  📸 Capturing '{dashboard.title}' ({dashboard.uid}) …")
    try:
        req = urllib.request.Request(url, headers={"Accept": "image/png"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            content_type = resp.headers.get("Content-Type", "")
            if "image" not in content_type:
                raise RuntimeError(
                    f"Unexpected Content-Type '{content_type}' – "
                    "is the Grafana Image Renderer plugin running?"
                )
            png_bytes = resp.read()

        output_path.write_bytes(png_bytes)
        size_kb = len(png_bytes) / 1024
        try:
            display_path = output_path.relative_to(output_dir.parent.parent)
        except ValueError:
            display_path = output_path
        print(f"     ✅ Saved {display_path} ({size_kb:.1f} KB)")
        return output_path

    except (urllib.error.HTTPError, urllib.error.URLError, OSError) as exc:
        raise RuntimeError(f"Failed to capture '{dashboard.title}': {exc}") from exc


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Capture Grafana dashboard screenshots via the render API."
    )
    parser.add_argument(
        "--grafana-url",
        default="http://localhost:3000",
        help="Base URL of the Grafana instance (default: http://localhost:3000)",
    )
    parser.add_argument(
        "--dashboards-dir",
        default=None,
        help="Directory containing dashboard JSON files "
             "(default: <repo-root>/dashboards)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory to write PNG screenshots "
             "(default: <repo-root>/docs/images/dashboards)",
    )
    parser.add_argument(
        "--all",
        dest="capture_all",
        action="store_true",
        help="Capture all dashboards, not just changed ones",
    )
    parser.add_argument(
        "--uid",
        nargs="+",
        metavar="UID",
        help="Capture only dashboards with these UIDs",
    )
    parser.add_argument(
        "--base-ref",
        default="HEAD~1",
        help="Git ref to compare against when detecting changes "
             "(default: HEAD~1)",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1280,
        help="Screenshot width in pixels (default: 1280)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=800,
        help="Screenshot height in pixels (default: 800)",
    )
    parser.add_argument(
        "--wait-timeout",
        type=int,
        default=120,
        help="Seconds to wait for Grafana to become healthy (default: 120)",
    )
    args = parser.parse_args(argv)

    # Resolve paths
    repo_root = Path(__file__).resolve().parent.parent
    dashboards_dir = Path(args.dashboards_dir) if args.dashboards_dir \
        else repo_root / "dashboards"
    output_dir = Path(args.output_dir) if args.output_dir \
        else repo_root / "docs" / "images" / "dashboards"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Discover all dashboards
    all_boards = discover_dashboards(dashboards_dir)
    if not all_boards:
        print("❌ No dashboard JSON files found in", dashboards_dir, file=sys.stderr)
        return 1

    # Filter to the dashboards we want to capture
    if args.uid:
        uid_set = set(args.uid)
        selected = [b for b in all_boards if b.uid in uid_set]
        missing = uid_set - {b.uid for b in selected}
        if missing:
            print(f"⚠️  UIDs not found in {dashboards_dir}: {', '.join(sorted(missing))}",
                  file=sys.stderr)
    elif args.capture_all:
        selected = all_boards
    else:
        changed = changed_dashboard_paths(repo_root, args.base_ref)
        if not changed:
            # Fall back to all dashboards when git diff returns nothing
            # (e.g. on a shallow clone or first commit)
            print("ℹ️  No changed dashboards detected via git diff – "
                  "capturing all dashboards as fallback")
            selected = all_boards
        else:
            selected = [b for b in all_boards
                        if b.json_path.resolve() in changed]

    if not selected:
        print("✅ No dashboards to capture (none changed).")
        return 0

    print(f"\n📊 Dashboards to capture ({len(selected)}):")
    for board in selected:
        print(f"   • {board.title} ({board.uid})")
    print()

    # Wait for Grafana to be ready
    try:
        wait_for_grafana(args.grafana_url, timeout=args.wait_timeout)
    except RuntimeError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1

    # Capture screenshots
    failures: list[str] = []
    captured: list[Path] = []

    for board in selected:
        try:
            path = capture_screenshot(
                args.grafana_url, board, output_dir, args.width, args.height
            )
            captured.append(path)
        except RuntimeError as exc:
            print(f"  ❌ {exc}", file=sys.stderr)
            failures.append(board.title)

    # Summary
    print(f"\n📈 Summary: {len(captured)} captured, {len(failures)} failed")
    if failures:
        print("Failed dashboards:", ", ".join(failures), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
