# Test Fixes Needed - FR-6 Branch

**Branch:** `feature/fr-6-contributor-analytics`  
**Date:** 2026-01-24  
**Status:** ⚠️ DO NOT MERGE - Tests failing

## Issues Discovered

### 1. Integration Tests Stalling

- Tests hang during execution in Docker
- May timeout without completing
- **Possible causes:**
  - API rate limiting (GitHub/OSV/EOL)
  - Database connection timeouts
  - Infinite loops in new contributor metrics code
  - Docker resource constraints

**Debug steps:**

```bash
# Run with verbose output
./scripts/run-tests-docker.sh --live-api

# Check container logs
docker compose -f docker-compose.test.yml logs test-db
docker compose -f docker-compose.test.yml logs test-runner

# Monitor resource usage
docker stats
```

### 2. Test Failures

#### `test_extract_tracks_branches` - FAILED

**Location:** `tests/contract/integration/test_github_extraction_e2e.py`

**ROOT CAUSE:** Duplicate key violation - repository already exists in database

```
sqlalchemy.exc.IntegrityError: duplicate key value violates unique constraint "repositories_pkey"
DETAIL:  Key (repo_id)=(octocat/Hello-World) already exists.
```

**Issue:** Test is trying to insert the same repository that was created by a previous test

**Fix:**

1. Tests need to use `get_or_create_repository()` instead of direct insert
2. OR: Better test isolation/cleanup between tests
3. OR: Use unique repo names per test

#### `test_extract_tracks_contributors` - FAILED

**Location:** `tests/contract/integration/test_github_extraction_e2e.py`

**ROOT CAUSE:** Wrong function signature - `get_commits()` doesn't accept `max_commits` parameter

```
TypeError: GitHubExtractor.get_commits() got an unexpected keyword argument 'max_commits'
```

**Issue:** Test code calls:

```python
commits_data = extractor.get_commits(repo_id, max_commits=10)
```

But `GitHubExtractor.get_commits()` signature is different (check actual signature in extractor)

**Fix:**

```python
# Check actual signature in src/extractors/github/extractor.py
# Then update test to match, likely one of:
commits_data = extractor.get_commits(repo_id, limit=10)  # if it uses 'limit'
commits_data = extractor.get_commits(repo_id)[:10]       # or just slice results
```

### 3. Skipped Tests

#### `test_detect_technologies_from_repo` - SKIPPED

**Location:** `tests/contract/integration/test_github_extraction_e2e.py`  
**Skip reason:** "Unable to access file tree"

**Background:**

- Was already skipped before FR-6 work
- May be GitHub API permission issue
- Could be rate limiting
- Possibly needs specific repo access

**Options:**

1. Fix the underlying issue (GitHub API access)
2. Use a different test repository
3. Keep skipped but document why
4. Mark as expected skip with better message

## Test Execution Plan

### Step 1: Isolated Test Runs

Run each failing test individually to get detailed output:

```bash
# Docker test environment first
docker compose -f docker-compose.test.yml up -d test-db
docker compose -f docker-compose.test.yml run --rm test-migrations

# Then run specific tests
docker compose -f docker-compose.test.yml run --rm test-runner \
  pytest tests/contract/integration/test_github_extraction_e2e.py::TestGitHubExtractionBasic::test_extract_tracks_branches -vv --tb=long

docker compose -f docker-compose.test.yml run --rm test-runner \
  pytest tests/contract/integration/test_github_extraction_e2e.py::TestGitHubExtractionBasic::test_extract_tracks_contributors -vv --tb=long
```

### Step 2: Add Debug Logging

If errors aren't clear, add temporary debug prints:

```python
# In test_extract_tracks_branches
print(f"DEBUG: Extracted {len(branches_data)} branches")
print(f"DEBUG: Query returned {len(branches)} branch records")
for b in branches[:3]:
    print(f"DEBUG: Branch {b.name}: {b.branch_id}")

# In test_extract_tracks_contributors
print(f"DEBUG: Stored {len(commits_data)} commits")
contributors = test_session.query(Contributor).all()
print(f"DEBUG: Found {len(contributors)} contributors")
for c in contributors[:3]:
    print(f"DEBUG: Contributor {c.name} <{c.email}>")
```

### Step 3: Verify Workflow Integration

Check if the issue is in the test or the workflow:

```bash
# Run actual workflow extraction (not just test)
# This will help isolate if it's a workflow bug or test bug
docker compose -f docker-compose.test.yml run --rm test-runner \
  python -c "
from src.workflows.github_analysis import GitHubAnalysisWorkflow, ExtractionLimits
from src.database.connection import session_scope
from src.database.models import Contributor, Branch

limits = ExtractionLimits(max_branches=5, max_commits=10, max_pull_requests=5)
workflow = GitHubAnalysisWorkflow(limits=limits)
summary = workflow.run()

with session_scope() as session:
    branch_count = session.query(Branch).count()
    contrib_count = session.query(Contributor).count()
    print(f'Branches: {branch_count}')
    print(f'Contributors: {contrib_count}')
"
```

### Step 4: Check Database State

Verify data is actually being stored:

```bash
docker compose -f docker-compose.test.yml exec test-db psql -U analyzer -d analyzer -c "
  SELECT COUNT(*) as branches FROM branches;
  SELECT COUNT(*) as contributors FROM contributors;
  SELECT COUNT(*) as commits FROM commits;
  SELECT name, email FROM contributors LIMIT 5;
"
```

## Success Criteria

Before merging `feature/fr-6-contributor-analytics`:

- [ ] All integration tests pass (no failures)
- [ ] No test stalling/timeouts
- [ ] `test_extract_tracks_branches` - PASSING
- [ ] `test_extract_tracks_contributors` - PASSING
- [ ] New `test_contributor_metrics_e2e` tests - PASSING
- [ ] `test_detect_technologies_from_repo` - Either PASSING or documented skip reason
- [ ] Full test run completes in reasonable time (< 15 minutes)
- [ ] No errors in logs

## Notes

- It's late (yawn) - tackle this fresh tomorrow morning
- FR-6 implementation looks solid, this is likely test/environment issues
- Don't rush - proper testing is critical for contributor analytics
- Consider running tests multiple times to rule out flakiness
