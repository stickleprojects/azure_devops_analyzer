# Real-API Snapshots

_Last reviewed: 2026-04-30_

This directory contains anonymised recordings of real API responses from
GitHub and Azure DevOps. They serve as a test corpus that exercises the
same data shapes as production traffic, without requiring live credentials
in CI.

## Directory layout

```
snapshots/
  github/
    commits.json       – GET /repos/{owner}/{repo}/commits response
    pull_requests.json – GET /repos/{owner}/{repo}/pulls response
    pr_reviews.json    – GET /repos/{owner}/{repo}/pulls/{n}/reviews response
  azure_devops/
    commits.json       – GET /_apis/git/repositories/{id}/commits
    pull_requests.json – GET /_apis/git/repositories/{id}/pullrequests
    pr_reviews.json    – GET /_apis/git/pullrequests/{id}/reviewers
  README.md            – this file
```

## Anonymisation rules

Snapshots are produced by `scripts/capture-api-snapshot.sh` and then
sanitised by `scripts/anonymise-snapshot.py`, which applies the following
transformations **before** committing:

1. **Emails**: `real@company.com` → `user{N}@fixture.local` (deterministic
   mapping; case patterns and whitespace preserved).
2. **Display names**: replaced with `User N` (sequential, deterministic).
3. **Organisation / repo / branch names**: replaced with `fixture-org`,
   `fixture-repo`, `feature/branch-N` etc.
4. **Unicode characters, emoji, RTL text**: preserved verbatim — these are
   the production-shape quirks the snapshot must exercise.
5. **Null fields**: preserved verbatim.
6. **Nested structure and field ordering**: unchanged.
7. **Internal hostnames / URLs**: replaced with `https://fixture.example`.

## Initial seed

The `github/fixture.json` and `azure_devops/fixture.json` files committed to
this repository are **hand-authored seeds** written to match the output schema
that `anonymise-snapshot.py` would produce.  They are not the output of a real
`capture-api-snapshot.sh` + `anonymise-snapshot.py` run.  The capture scripts
are the **refresh path** for future updates; the hand-authored files are a
bootstrap placeholder that lets CI run without live credentials.

## Refresh cadence

Refresh snapshots quarterly or when an API version change is detected.
Run:

```bash
bash scripts/capture-api-snapshot.sh   # requires live creds in env
python scripts/anonymise-snapshot.py   # strips PII, preserves shape
```

Then commit the updated files.

## Privacy guarantee

Committed snapshots contain **no live credentials, no internal hostnames,
no customer PII**. The anonymisation script is the enforcement mechanism.
Reviewers should verify the output before merging any snapshot refresh.
