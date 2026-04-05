#!/usr/bin/env python3
"""
Documentation Audit Script
----------------------------
Audits project documentation and produces a structured Markdown report covering:

1. README freshness  – detects references to files/sections that no longer exist
2. PROGRESS.md drift – checks whether recent commits have a matching session entry
3. Requirements status – flags requirements still marked Draft or Not Started
4. Plan staleness     – highlights implementation plans that appear complete but
                        are not explicitly closed
5. Readability hints  – flags oversized sections and missing headings

Usage
-----
  python scripts/doc_audit.py [--repo-root <path>] [--output <file>]

  --repo-root  Root of the repository (default: directory two levels above this
               script, i.e. the project root).
  --output     Write the Markdown report to this file instead of stdout.

Exit codes
----------
  0  Audit ran to completion (report may still contain warnings/suggestions).
  1  Unexpected error.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import NamedTuple


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class Finding(NamedTuple):
    severity: str   # "error" | "warning" | "info"
    category: str
    file: str
    message: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _git_log(repo_root: Path, max_count: int = 30) -> list[str]:
    """Return recent commit subject lines (newest first)."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "log", f"--max-count={max_count}",
             "--pretty=format:%s"],
            capture_output=True, text=True, check=True,
        )
        return result.stdout.splitlines()
    except subprocess.CalledProcessError:
        return []


def _git_recent_touched_docs(repo_root: Path, days: int = 30) -> list[str]:
    """Return doc files modified in the last *days* days (relative paths)."""
    since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "log", f"--since={since}",
             "--name-only", "--pretty=format:", "--diff-filter=ACMR"],
            capture_output=True, text=True, check=True,
        )
        paths = [p for p in result.stdout.splitlines()
                 if p.endswith(".md")]
        return list(dict.fromkeys(paths))   # deduplicate, preserve order
    except subprocess.CalledProcessError:
        return []


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _internal_links(content: str) -> list[str]:
    """Extract all markdown link targets that look like local paths."""
    return re.findall(r'\]\(([^)#]+?)(?:#[^)]*)?\)', content)


# ---------------------------------------------------------------------------
# Audit checks
# ---------------------------------------------------------------------------

def audit_readme(repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    readme = repo_root / "README.md"
    if not readme.exists():
        return [Finding("error", "README", "README.md", "README.md is missing")]

    content = _read(readme)
    lines = content.splitlines()

    # 1. Look for internal links that point to non-existent targets
    for target in _internal_links(content):
        if target.startswith("http"):
            continue
        target_path = (repo_root / target).resolve()
        if not target_path.exists():
            findings.append(Finding(
                "warning", "README", "README.md",
                f"Broken internal link: `{target}` (file not found)"
            ))

    # 2. Flag sections with unusually long prose blocks (readability)
    in_code = False
    para_lines = 0
    for line in lines:
        if line.startswith("```"):
            in_code = not in_code
        if in_code:
            continue
        if line.strip() == "":
            if para_lines > 15:
                findings.append(Finding(
                    "info", "README", "README.md",
                    f"Long paragraph (~{para_lines} lines) detected – "
                    "consider breaking it up with sub-headings or a table"
                ))
            para_lines = 0
        else:
            para_lines += 1

    # 3. Check for a "Last Updated" marker that is more than 90 days old
    match = re.search(r"\*\*Last Updated\*\*.*?(\d{4}-\d{2}-\d{2})", content)
    if match:
        try:
            last_updated = date.fromisoformat(match.group(1))
            age = (date.today() - last_updated).days
            if age > 90:
                findings.append(Finding(
                    "warning", "README", "README.md",
                    f"Last Updated marker is {age} days old ({last_updated}) – "
                    "verify that the README reflects the current state of the project"
                ))
        except ValueError:
            pass

    return findings


def audit_progress_md(repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    progress = repo_root / "PROGRESS.md"
    if not progress.exists():
        return [Finding("warning", "PROGRESS", "PROGRESS.md",
                        "PROGRESS.md not found")]

    content = _read(progress)

    # 1. Look for the most recent session date in PROGRESS.md
    session_dates = re.findall(r"## Session: (\d{4}-\d{2}-\d{2})", content)
    if not session_dates:
        findings.append(Finding(
            "warning", "PROGRESS", "PROGRESS.md",
            "No session entries (## Session: YYYY-MM-DD) found"
        ))
        return findings

    latest_session = max(date.fromisoformat(d) for d in session_dates)
    age = (date.today() - latest_session).days

    if age > 30:
        findings.append(Finding(
            "warning", "PROGRESS", "PROGRESS.md",
            f"Latest session entry is {age} days old ({latest_session}). "
            "Consider adding a new session entry to reflect recent activity."
        ))

    # 2. Cross-check: get commit subjects from the last 30 days and see if any
    #    look like major feature work without a matching session entry
    recent_commits = _git_log(repo_root, max_count=50)
    feature_keywords = ["feat:", "fix:", "refactor:", "add ", "implement"]
    content_lower = content.lower()
    undocumented: list[str] = []
    for subject in recent_commits[:20]:
        lower = subject.lower()
        if any(k in lower for k in feature_keywords):
            # Rough heuristic: check if any word from the commit appears in PROGRESS
            first_word = subject.split()[0] if subject.split() else ""
            # Only flag if a significant commit keyword isn't mentioned at all
            if first_word.lower() not in content_lower and len(subject) > 10:
                undocumented.append(subject)

    if undocumented:
        sample = undocumented[:3]
        findings.append(Finding(
            "info", "PROGRESS", "PROGRESS.md",
            "Some recent commits may not be captured in PROGRESS.md: "
            + "; ".join(f"`{s}`" for s in sample)
        ))

    return findings


def audit_requirements_status(repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    status_file = repo_root / "docs" / "01-strategy" / "requirements-status.md"
    if not status_file.exists():
        return [Finding("info", "Requirements",
                        "docs/01-strategy/requirements-status.md",
                        "requirements-status.md not found – create one to track "
                        "feature completion against business requirements")]

    content = _read(status_file)

    # Detect rows marked as Not Started / Draft
    not_started = re.findall(r"\|\s*[^|]+\|\s*[^|]*(?:Not Started|:x:)[^|]*\|",
                             content)
    draft_items = re.findall(r"\|\s*[^|]+\|\s*[^|]*(?:Draft|:construction:)[^|]*\|",
                             content)

    rel_path = status_file.relative_to(repo_root)
    if not_started:
        findings.append(Finding(
            "info", "Requirements", str(rel_path),
            f"{len(not_started)} requirement(s) still marked **Not Started** – "
            "confirm these are genuinely out-of-scope or update their status"
        ))

    if draft_items:
        findings.append(Finding(
            "info", "Requirements", str(rel_path),
            f"{len(draft_items)} requirement(s) still at **Draft** status – "
            "review and promote to a definitive status"
        ))

    # Check last-updated header
    match = re.search(r"Last Updated\s*\|?\s*(\d{4}-\d{2}-\d{2})", content)
    if match:
        try:
            last_updated = date.fromisoformat(match.group(1))
            age = (date.today() - last_updated).days
            if age > 60:
                findings.append(Finding(
                    "warning", "Requirements", str(rel_path),
                    f"requirements-status.md was last updated {age} days ago "
                    f"({last_updated}) – consider reviewing completion status"
                ))
        except ValueError:
            pass

    return findings


def audit_plans(repo_root: Path) -> list[Finding]:
    """Scan docs/04-implementation/ for plans that look complete but aren't closed."""
    findings: list[Finding] = []
    plans_dir = repo_root / "docs" / "04-implementation"
    if not plans_dir.exists():
        return findings

    completion_patterns = [
        r"- \[x\]",           # completed checklist item
        r"(?i)status.*complete",
        r"(?i)✅.*complete",
    ]
    incomplete_patterns = [
        r"- \[ \]",           # open checklist item
        r"(?i)status.*pending",
        r"(?i)status.*draft",
        r"(?i)not started",
    ]

    for plan_file in plans_dir.glob("*.md"):
        content = _read(plan_file)
        rel = plan_file.relative_to(repo_root)

        completed_count = sum(
            len(re.findall(p, content)) for p in completion_patterns
        )
        incomplete_count = sum(
            len(re.findall(p, content)) for p in incomplete_patterns
        )

        if completed_count > 0 and incomplete_count == 0:
            findings.append(Finding(
                "info", "Plans", str(rel),
                "All checklist items appear complete – consider marking this plan "
                "as **Closed** in its status header"
            ))
        elif completed_count > 0 and incomplete_count > 0:
            ratio = completed_count / (completed_count + incomplete_count)
            if ratio >= 0.80:
                findings.append(Finding(
                    "info", "Plans", str(rel),
                    f"Plan is ~{int(ratio * 100)}% complete "
                    f"({completed_count} done, {incomplete_count} remaining) – "
                    "review and update its status header"
                ))

    return findings


def audit_readability(repo_root: Path) -> list[Finding]:
    """Broad readability sweep across all docs."""
    findings: list[Finding] = []
    docs_dir = repo_root / "docs"
    if not docs_dir.exists():
        return findings

    for md_file in docs_dir.rglob("*.md"):
        content = _read(md_file)
        lines = content.splitlines()
        rel = md_file.relative_to(repo_root)

        # Check: very long file with no TOC
        if len(lines) > 150 and "- [" not in content and "Contents" not in content:
            findings.append(Finding(
                "info", "Readability", str(rel),
                f"File has {len(lines)} lines but no table of contents – "
                "add a TOC or split into smaller documents"
            ))

        # Check: document has no level-2 headings at all
        if not re.search(r"^## ", content, re.MULTILINE):
            findings.append(Finding(
                "info", "Readability", str(rel),
                "No level-2 section headings (##) found – "
                "add headings to improve navigation"
            ))

        # Check: stale date markers older than 180 days
        for m in re.finditer(r"\*\*Last Updated\*\*[^\d]*(\d{4}-\d{2}-\d{2})",
                              content):
            try:
                updated = date.fromisoformat(m.group(1))
                age = (date.today() - updated).days
                if age > 180:
                    findings.append(Finding(
                        "warning", "Readability", str(rel),
                        f"Last Updated is {age} days old ({updated}) – "
                        "verify the document is still accurate"
                    ))
            except ValueError:
                pass

    return findings


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

def _severity_icon(severity: str) -> str:
    return {"error": "❌", "warning": "⚠️", "info": "💡"}.get(severity, "ℹ️")


def render_report(findings: list[Finding], repo_root: Path) -> str:
    today = date.today().isoformat()
    lines: list[str] = [
        "# Documentation Audit Report",
        "",
        f"**Generated**: {today}  ",
        f"**Repository root**: `{repo_root}`",
        "",
        "---",
        "",
    ]

    if not findings:
        lines += [
            "## ✅ No Issues Found",
            "",
            "All documentation checks passed. Nothing to action.",
        ]
        return "\n".join(lines)

    # Group by category
    by_category: dict[str, list[Finding]] = {}
    for f in findings:
        by_category.setdefault(f.category, []).append(f)

    # Summary table
    errors = sum(1 for f in findings if f.severity == "error")
    warnings = sum(1 for f in findings if f.severity == "warning")
    infos = sum(1 for f in findings if f.severity == "info")

    lines += [
        "## Summary",
        "",
        "| Severity | Count |",
        "|----------|-------|",
        f"| ❌ Error   | {errors} |",
        f"| ⚠️ Warning  | {warnings} |",
        f"| 💡 Info     | {infos} |",
        f"| **Total**  | **{len(findings)}** |",
        "",
        "---",
        "",
    ]

    for category, items in sorted(by_category.items()):
        lines.append(f"## {category}")
        lines.append("")
        for item in items:
            icon = _severity_icon(item.severity)
            lines.append(f"- {icon} **`{item.file}`** – {item.message}")
        lines.append("")

    lines += [
        "---",
        "",
        "## Recommended Actions",
        "",
        "1. **Errors** – fix immediately; they indicate broken references or "
        "missing required files.",
        "2. **Warnings** – address before the next release; stale dates and "
        "broken links erode trust in documentation.",
        "3. **Info / Suggestions** – tackle in the next documentation sprint; "
        "they improve readability and completeness.",
        "",
        "_This report was generated by `scripts/doc_audit.py`. "
        "Re-run at any time to check current status._",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit project documentation and produce a Markdown report."
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Repository root directory (default: auto-detected from script location)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Write report to this file (default: stdout)",
    )
    args = parser.parse_args(argv)

    if args.repo_root:
        repo_root = Path(args.repo_root).resolve()
    else:
        # scripts/ lives one level below project root
        repo_root = Path(__file__).resolve().parent.parent

    findings: list[Finding] = []
    findings.extend(audit_readme(repo_root))
    findings.extend(audit_progress_md(repo_root))
    findings.extend(audit_requirements_status(repo_root))
    findings.extend(audit_plans(repo_root))
    findings.extend(audit_readability(repo_root))

    report = render_report(findings, repo_root)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
        print(f"Report written to {output_path}", file=sys.stderr)
    else:
        print(report)

    return 0


if __name__ == "__main__":
    sys.exit(main())
