# Real-API Snapshots

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
