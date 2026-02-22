# Task: Create scripts/verify_canary.py

Create `scripts/verify_canary.py` — a post-scan verification script that checks whether
a repository's data is fully present in the database.

## CLI interface

```
Usage: python scripts/verify_canary.py --repo-id <repo_id>

Options:
  --repo-id    Repository name to verify (matches the `name` column in `repositories`)
```

Reads `DATABASE_URL` from the environment. Exits 0 on overall PASS, 1 on any FAIL.

## Checks to run (in order)

Run each check independently and collect results before printing.

| Label          | Query |
|----------------|-------|
| `commits`      | `SELECT COUNT(*) FROM commits c JOIN repositories r ON r.id = c.repository_id WHERE r.name = :repo_id` |
| `pull_requests`| `SELECT COUNT(*) FROM pull_requests p JOIN repositories r ON r.id = p.repository_id WHERE r.name = :repo_id` |
| `dependencies` | `SELECT COUNT(*) FROM dependencies d JOIN repositories r ON r.id = d.repository_id WHERE r.name = :repo_id` |
| `languages`    | `SELECT COUNT(*) FROM languages l JOIN repositories r ON r.id = l.repository_id WHERE r.name = :repo_id` |
| `canary_join`  | The full inner-join canary query (see below) — PASS if exactly 1 row returned |

Canary join query:
```sql
SELECT r.id
FROM repositories r
INNER JOIN commits c       ON r.id = c.repository_id
INNER JOIN pull_requests p ON r.id = p.repository_id
INNER JOIN dependencies d  ON r.id = d.repository_id
INNER JOIN languages l     ON r.id = l.repository_id
WHERE r.name = :repo_id
LIMIT 1
```

## Output format

```
Verifying canary repo: <repo_id>

  [PASS] commits       — 142 rows
  [PASS] pull_requests — 37 rows
  [FAIL] dependencies  — 0 rows
  [PASS] languages     — 3 rows
  [FAIL] canary_join   — no row present

Overall: FAIL
```

## Implementation notes

- Use `sqlalchemy` for the database connection: `create_engine(os.environ["DATABASE_URL"])`.
- Use `text()` for raw SQL with `:repo_id` bind parameter.
- For count queries: PASS if `count > 0`, FAIL if `count == 0`.
- For canary_join: PASS if any row is returned, FAIL if no row.
- Collect all results, print summary, then exit with `sys.exit(0)` if all PASS else `sys.exit(1)`.

## Imports

```python
import argparse
import os
import sys
from sqlalchemy import create_engine, text
```

## Output

Write the complete, runnable Python source for `scripts/verify_canary.py`.
Keep it simple — a `main()` function and `if __name__ == "__main__"` guard.
No classes needed.
