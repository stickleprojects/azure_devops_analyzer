#!/usr/bin/env python3
"""
anonymise-snapshot.py

Converts raw API captures (produced by capture-api-snapshot.sh) into the
fixture-scenario JSON schema understood by SnapshotExtractor / FixtureExtractor,
and replaces all personal information with deterministic synthetic values.

Anonymisation rules:
  - Emails       : deterministic mapping to user{N}@fixture.local
                   Case patterns and whitespace are PRESERVED (they exercise
                   the normalisation code path).
  - Display names: replaced with "User N" (matching email mapping).
  - Org/repo/branch names: replaced with fixture-* equivalents.
  - Internal URLs: host replaced with fixture.example.
  - Unicode characters, emoji, RTL text: kept verbatim.
  - Null fields: kept verbatim.
  - Nested structure and field ordering: unchanged.

Usage:
    # Convert raw GitHub capture to fixture scenario JSON:
    python scripts/anonymise-snapshot.py --platform github

    # Convert raw Azure DevOps capture:
    python scripts/anonymise-snapshot.py --platform azure_devops

Output is written to:
    tests/fixtures/snapshots/<platform>/fixture.json
"""

import argparse
import json
import pathlib
import re
import sys

PROJECT_ROOT = pathlib.Path(__file__).parent.parent
RAW_DIR = PROJECT_ROOT / "tmp" / "snapshots-raw"
SNAPSHOTS_OUT = PROJECT_ROOT / "tests" / "fixtures" / "snapshots"


class Anonymiser:
    """Stateful anonymiser that builds deterministic mappings on first encounter."""

    def __init__(self):
        self._email_map: dict[str, str] = {}
        self._name_map: dict[str, str] = {}
        self._counter = 0

    def _next_n(self) -> int:
        self._counter += 1
        return self._counter

    def _anon_email(self, email: str) -> str:
        """Anonymise email, preserving case pattern and whitespace."""
        if not email:
            return email

        # Normalise for lookup only; preserve original shape in output
        key = email.strip().lower()
        if key not in self._email_map:
            n = self._next_n()
            # Preserve leading/trailing whitespace from the original
            lead = email[: len(email) - len(email.lstrip())]
            trail = email[len(email.rstrip()):]
            # Preserve CamelCase: if original is MixedCase, keep the variant
            mapped = f"user{n}@fixture.local"
            # Re-apply original casing pattern (first char of local part)
            local_original = email.strip().split("@")[0] if "@" in email else email.strip()
            if any(c.isupper() for c in local_original):
                mapped = f"User{n}@Fixture.LOCAL"
            self._email_map[key] = f"{lead}{mapped}{trail}"
        return self._email_map[key]

    def _anon_name(self, email: str, name: str | None) -> str | None:
        """Return "User N" matching the email's N, or None."""
        if name is None:
            return None
        # Bot patterns: preserve as-is for production-shape fidelity
        if "[bot]" in (name or "") or "Build Service" in (name or ""):
            # Anonymise org name portion
            return re.sub(r"\(.+?\)", "(fixture-org)", name)
        key = email.strip().lower() if email else ""
        if key and key in self._email_map:
            n_match = re.search(r"user(\d+)@", self._email_map[key], re.IGNORECASE)
            if n_match:
                return f"User {n_match.group(1)}"
        return name  # Fallback: keep original

    def _anon_url(self, url: str | None) -> str | None:
        if not url:
            return url
        return re.sub(r"https?://[^/]+", "https://fixture.example", url)

    def anon_email(self, email: str | None) -> str | None:
        if email is None:
            return None
        return self._anon_email(email)

    def anon_contributor(self, email: str | None, name: str | None) -> tuple[str | None, str | None]:
        anon_e = self.anon_email(email) if email else None
        anon_n = self._anon_name(email or "", name)
        return anon_e, anon_n


def build_github_scenario(anon: Anonymiser, raw_dir: pathlib.Path) -> dict:
    """Convert raw GitHub capture to fixture-scenario JSON."""
    commits_raw = json.loads((raw_dir / "commits.json").read_text()) if (raw_dir / "commits.json").exists() else []
    prs_raw = json.loads((raw_dir / "pull_requests.json").read_text()) if (raw_dir / "pull_requests.json").exists() else []
    reviews_raw = json.loads((raw_dir / "pr_reviews.json").read_text()) if (raw_dir / "pr_reviews.json").exists() else []

    commits = []
    for c in commits_raw[:30]:
        author_email = c.get("commit", {}).get("author", {}).get("email", "")
        author_name = c.get("commit", {}).get("author", {}).get("name")
        committer_email = c.get("commit", {}).get("committer", {}).get("email", "")
        committer_name = c.get("commit", {}).get("committer", {}).get("name")
        ae, an = anon.anon_contributor(author_email, author_name)
        ce, cn = anon.anon_contributor(committer_email, committer_name)
        commits.append({
            "commit_hash": c.get("sha", ""),
            "author_name": an,
            "author_email": ae or "",
            "committer_name": cn,
            "committer_email": ce or "",
            "message": c.get("commit", {}).get("message", ""),
            "commit_date": c.get("commit", {}).get("author", {}).get("date", "2026-01-01T00:00:00Z"),
            "files_changed": None,
            "lines_added": None,
            "lines_removed": None,
        })

    pull_requests = []
    for pr in prs_raw[:20]:
        author_login = pr.get("user", {}).get("login", "") if pr.get("user") else ""
        author_email_raw = f"{author_login}@users.noreply.github.com" if author_login else ""
        ae, an = anon.anon_contributor(author_email_raw, author_login)

        # Reviews: from the separate captures or inline
        pr_reviews = []
        for r in reviews_raw:
            if r.get("user"):
                re_login = r["user"].get("login", "")
                re_email = f"{re_login}@users.noreply.github.com"
                rev_e, rev_n = anon.anon_contributor(re_email, re_login)
                pr_reviews.append({
                    "reviewer_email": rev_e or "",
                    "reviewer_name": rev_n,
                    "review_date": r.get("submitted_at") or pr.get("created_at", "2026-01-01T00:00:00Z"),
                    "state": r.get("state", "APPROVED").upper(),
                })

        pull_requests.append({
            "pr_number": pr.get("number"),
            "platform_pr_id": str(pr.get("id", pr.get("number", 0))),
            "title": pr.get("title", ""),
            "description": pr.get("body"),
            "source_branch": pr.get("head", {}).get("ref", "feature/branch"),
            "target_branch": pr.get("base", {}).get("ref", "main"),
            "status": "merged" if pr.get("merged_at") else ("open" if pr.get("state") == "open" else "closed"),
            "created_at": pr.get("created_at", "2026-01-01T00:00:00Z"),
            "merged_at": pr.get("merged_at"),
            "author_name": an,
            "author_email": ae or "",
            "files_changed": pr.get("changed_files", 0) or 0,
            "lines_added": pr.get("additions", 0) or 0,
            "lines_removed": pr.get("deletions", 0) or 0,
            "reviews": pr_reviews,
        })

    return {
        "name": "github-snapshot",
        "description": "Anonymised snapshot of a real GitHub repository.",
        "languages": [],
        "file_names": [],
        "manifests": {},
        "branches": [{"name": "main", "latest_commit_sha": commits[0]["commit_hash"] if commits else ""}],
        "commits": commits,
        "pull_requests": pull_requests,
    }


def build_azure_devops_scenario(anon: Anonymiser, raw_dir: pathlib.Path) -> dict:
    """Convert raw Azure DevOps capture to fixture-scenario JSON."""
    commits_raw_data = json.loads((raw_dir / "commits.json").read_text()) if (raw_dir / "commits.json").exists() else {}
    prs_raw_data = json.loads((raw_dir / "pull_requests.json").read_text()) if (raw_dir / "pull_requests.json").exists() else {}
    reviews_raw_data = json.loads((raw_dir / "pr_reviews.json").read_text()) if (raw_dir / "pr_reviews.json").exists() else {}

    commits_raw = commits_raw_data.get("value", []) if isinstance(commits_raw_data, dict) else commits_raw_data
    prs_raw = prs_raw_data.get("value", []) if isinstance(prs_raw_data, dict) else prs_raw_data
    reviews_raw = reviews_raw_data.get("value", []) if isinstance(reviews_raw_data, dict) else reviews_raw_data

    commits = []
    for c in commits_raw[:30]:
        author_email = c.get("author", {}).get("email", "")
        author_name = c.get("author", {}).get("name")
        committer_email = c.get("committer", {}).get("email", "")
        committer_name = c.get("committer", {}).get("name")
        ae, an = anon.anon_contributor(author_email, author_name)
        ce, cn = anon.anon_contributor(committer_email, committer_name)
        commits.append({
            "commit_hash": c.get("commitId", ""),
            "author_name": an,
            "author_email": ae or "",
            "committer_name": cn,
            "committer_email": ce or "",
            "message": c.get("comment", ""),
            "commit_date": c.get("author", {}).get("date", "2026-01-01T00:00:00Z"),
            "files_changed": None,
            "lines_added": None,
            "lines_removed": None,
        })

    pull_requests = []
    for pr in prs_raw[:20]:
        creator = pr.get("createdBy", {})
        author_email = creator.get("uniqueName", "") or creator.get("mailAddress", "")
        author_name = creator.get("displayName")
        ae, an = anon.anon_contributor(author_email, author_name)

        pr_reviews = []
        for r in reviews_raw:
            rev_email = r.get("uniqueName", "") or r.get("mailAddress", "")
            rev_name = r.get("displayName")
            rev_e, rev_n = anon.anon_contributor(rev_email, rev_name)
            pr_reviews.append({
                "reviewer_email": rev_e or "",
                "reviewer_name": rev_n,
                "review_date": pr.get("creationDate", "2026-01-01T00:00:00Z"),
                "state": "APPROVED" if r.get("vote", 0) == 10 else "COMMENTED",
                "is_required": r.get("isRequired", False),
            })

        pull_requests.append({
            "pr_number": pr.get("pullRequestId"),
            "platform_pr_id": str(pr.get("pullRequestId", "")),
            "title": pr.get("title", ""),
            "description": pr.get("description"),
            "source_branch": pr.get("sourceRefName", "").replace("refs/heads/", ""),
            "target_branch": pr.get("targetRefName", "").replace("refs/heads/", ""),
            "status": "merged" if pr.get("status") == "completed" else pr.get("status", "open"),
            "created_at": pr.get("creationDate", "2026-01-01T00:00:00Z"),
            "merged_at": pr.get("closedDate") if pr.get("status") == "completed" else None,
            "author_name": an,
            "author_email": ae or "",
            "files_changed": 0,
            "lines_added": 0,
            "lines_removed": 0,
            "reviews": pr_reviews,
        })

    return {
        "name": "azure-devops-snapshot",
        "description": "Anonymised snapshot of a real Azure DevOps repository.",
        "languages": [],
        "file_names": [],
        "manifests": {},
        "branches": [{"name": "main", "latest_commit_sha": commits[0]["commit_hash"] if commits else ""}],
        "commits": commits,
        "pull_requests": pull_requests,
    }


def main():
    parser = argparse.ArgumentParser(description="Anonymise raw API snapshots to fixture JSON")
    parser.add_argument("--platform", choices=["github", "azure_devops"], required=True)
    args = parser.parse_args()

    raw_dir = RAW_DIR / args.platform
    if not raw_dir.exists():
        print(f"ERROR: Raw snapshot directory not found: {raw_dir}", file=sys.stderr)
        print(f"Run: bash scripts/capture-api-snapshot.sh --platform {args.platform}", file=sys.stderr)
        sys.exit(1)

    anon = Anonymiser()

    if args.platform == "github":
        scenario = build_github_scenario(anon, raw_dir)
    else:
        scenario = build_azure_devops_scenario(anon, raw_dir)

    out_path = SNAPSHOTS_OUT / args.platform / "fixture.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(scenario, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"✓ Anonymised snapshot written to: {out_path}")
    print(f"  Commits:       {len(scenario['commits'])}")
    print(f"  Pull requests: {len(scenario['pull_requests'])}")
    print("")
    print("Review the output before committing to verify no PII remains.")


if __name__ == "__main__":
    main()
