# Feature Development Workflow

**Critical:** This document ensures all feature development follows proper test-driven practices and architectural boundaries.

---

## ⚠️ GOLDEN RULES (Non-Negotiable)

1. **NEVER commit code that fails tests**
   - Tests are the contract and source of truth
   - If a test fails, the implementation is wrong, not the test
   - Fix implementation, don't modify tests to match broken code

2. **ALWAYS verify tests pass BEFORE committing**
   - Run full integration test suite
   - Confirm all tests pass in Docker environment
   - No exceptions, no "we'll fix it later"

3. **ALWAYS create feature branch BEFORE any code changes**
   - `git checkout -b feat/feature-name`
   - Work locally in feature branch, NOT on main
   - Never commit directly to main

4. **ALWAYS follow Test Guardian rules**
   - CONTRACT tests cannot be modified without requirement changes
   - IMPLEMENTATION tests can evolve with technical changes
   - See `agents/04a-test-guardian.md` for details

5. **ALWAYS follow Architecture Guardian rules**
   - Validate component boundaries before implementation
   - See `agents/02a-architecture-guardian.md` for details

---

## Feature Development Checklist

### Phase 1: Planning (Before Code)

- [ ] Feature branch created: `git checkout -b feat/feature-name`
- [ ] Requirements understood (review acceptance criteria)
- [ ] Architecture validated (no boundary violations)
- [ ] Test plan considered (what must be tested?)
- [ ] Integration test infrastructure available

### Phase 1.5: Pre-Flight Validation (New - Critical Step)

**Execute this phase before starting Phase 2 development.**

#### For Documentation Changes:
- [ ] Reviewed against `agents/00-documentation-standards.md`
- [ ] Code content ≤ 30% of document
- [ ] Each example ≤ 15 lines maximum
- [ ] ≤ 3 code examples per section
- [ ] NO full function/class definitions (reference actual files instead)
- [ ] If implementation doc: includes "Architecture Guardian" section

#### For Code Changes:
- [ ] Architecture Guardian review completed
- [ ] No boundary violations (see agents/02a-architecture-guardian.md)
  - Extractors: Platform-isolated, no DB writes
  - Analyzers: No extractor dependencies
  - Workflows: Orchestration only, no business logic
  - Database: Single layer for all DB operations
- [ ] New components placed in correct layer
- [ ] No cross-layer dependencies created

#### Branch Verification (Always):
- [ ] Current branch confirmed: `git status`
  - Must show: `On branch feat/...`
  - MUST NOT show: `On branch main`
- [ ] If on main: Create feature branch immediately
  - `git checkout -b feat/your-feature`
- [ ] Commit only to feature branch, NEVER to main

**Outcome**: Ready to proceed to Phase 2 development with confidence that all quality gates understood.

### Phase 2: Development (Local, Uncommitted)

- [ ] Write CONTRACT tests first (tests define requirements)
- [ ] Develop implementation to satisfy tests
- [ ] Write IMPLEMENTATION tests for technical details
- [ ] Follow existing code patterns and conventions
- [ ] Type hints on all Python code
- [ ] Docstrings for public APIs

### Phase 3: Validation (Critical Step - Do Not Skip)

- [ ] Run: `bash scripts/run-tests-docker.sh`
- [ ] Confirm: All tests pass ✅
- [ ] Confirm: No regressions (existing tests still pass)
- [ ] Confirm: Pre-commit validation passes
- [ ] If failures: Fix implementation and re-test (don't modify tests)

### Phase 4: Commit (Only After Tests Pass)

- [ ] Stage changes: `git add -A`
- [ ] Commit with clear message:

  ```
  git commit -m "feat: Brief description

  - Implements FR-X.Y feature
  - Adds N new integration tests
  - Updates schema/models if applicable

  Tests: All N tests passing
  "
  ```

### Phase 5: Pull Request & Review

- [ ] Create PR from `feat/feature-name` → `main`
- [ ] PR title matches commit message
- [ ] PR description explains WHAT and WHY
- [ ] Tests pass in CI/CD
- [ ] Code review approved
- [ ] No changes to CONTRACT tests without requirement approval

### Phase 6: Merge

- [ ] Merge PR to main
- [ ] Verify main branch tests still pass
- [ ] Update PROGRESS.md with completion details

---

## Testing Workflow (Cannot Be Skipped)

### Before Every Commit

```bash
# 1. Start test database
docker compose -f docker-compose.test.yml up -d test-db

# 2. Wait for database to be ready
sleep 10

# 3. Run ALL integration tests
bash scripts/run-tests-docker.sh

# 4. Verify output:
# ✅ All tests passed
# ✅ No errors in test setup
# ✅ No regressions in existing tests
```

### What "All Tests Pass" Means

- All contract tests passing (business requirements met)
- All implementation tests passing (technical validation)
- No skipped tests (no `@pytest.mark.skip`)
- No test failures in output
- Exit code: 0

### If Tests Fail

- **DO NOT modify tests to make them pass**
- **DO modify implementation**
- Understand why test is failing
- Fix the root cause in implementation
- Re-run tests
- Repeat until all pass

---

## Commit Message Guidelines

### Format

```
<type>: <subject>

<body>
```

### Types

- `feat:` - New feature implementation
- `fix:` - Bug fix
- `test:` - Test additions/updates
- `docs:` - Documentation updates
- `refactor:` - Code reorganization (no functional change)

### Examples

```
feat: Add team contributor management

- Implements FR-11.2: Many-to-many team relationships
- Implements FR-11.3: Team membership tracking
- Implements FR-11.5: Team metric aggregation

New Models:
- TeamContributor: Junction table with effective dates
- TeamMetric: Time-series team metrics

New Service:
- team_analytics.py: 6 query functions

Tests: 11 new integration tests, all passing
```

```
test: Add fixtures for organization and teams

- Adds organization fixture (test data setup)
- Adds teams fixture (3 test teams)
- Adds contributors fixture (5 test contributors)

Supports: test_team_management_e2e.py integration tests
```

---

## Architecture Validation Checklist

Before implementing, check:

### New Models/Database Changes

- [ ] Schema changes validated (no breaking changes to existing code)
- [ ] Migrations created (only incremental changes)
- [ ] Foreign key relationships correct
- [ ] Cascade deletes considered
- [ ] Backward compatibility maintained

### New Service Modules

- [ ] Location correct (extractors/, analyzers/, database/, workflows/)
- [ ] No cross-boundary violations
- [ ] No database operations outside storage layer
- [ ] Type hints on all functions

### Test Organization

- [ ] Contract tests in `tests/contract/`
- [ ] Implementation tests in `tests/implementation/`
- [ ] Docstrings start with `"""CONTRACT:` or `"""IMPLEMENTATION:`
- [ ] Integration tests use proper fixtures

---

## Common Mistakes & Prevention

### Mistake 1: Committing Before Tests Pass

**Prevention:** Make running tests a REQUIRED step before `git commit`

- Add pre-commit hook that runs tests
- Create CI/CD branch protection rule
- Document in this workflow (this file) ← You are here

### Mistake 2: Modifying Contract Tests When Implementation Fails

**Prevention:** Remember The Iron Rule

- If test fails → Implementation is wrong
- If implementation and test disagree → Fix implementation
- Only change tests if requirement actually changed (with documentation)

### Mistake 3: Committing to Main Instead of Feature Branch

**Prevention:** Enforce feature branches

- Use: `git checkout -b feat/name` immediately after starting
- Never work on main branch
- Use git hooks to prevent main commits: See below

### Mistake 4: Large Commits Without Testing

**Prevention:** Smaller, tested commits

- Test frequently during development
- Commit after each tested component
- Keep commits atomic and focused

---

## Git Workflow Setup

### Prevent Accidental Main Commits

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Prevent commits to main unless explicitly approved
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" = "main" ]; then
  echo "❌ STOP: You are about to commit directly to main"
  echo "Use: git checkout -b feat/feature-name"
  exit 1
fi
exit 0
```

Make executable:

```bash
chmod +x .git/hooks/pre-commit
```

### Force Test Pass Before Commit

Create `.git/hooks/pre-commit-tests`:

```bash
#!/bin/bash
# Uncomment to enforce tests before commit
# bash scripts/run-tests-docker.sh || exit 1
# echo "✅ Tests passed, proceeding with commit"
exit 0
```

---

## Session Continuity

### Starting a New Session

1. Read this file (you're already doing it!)
2. Read `PROGRESS.md` to understand current state
3. Check if there are uncommitted changes: `git status`
4. If incomplete work: `git checkout feat/feature-name` to resume
5. If starting new work: Create new feature branch

### During Development

- Update PROGRESS.md incrementally
- Note test status and blockers
- Document decisions and alternatives considered

### Ending a Session

- Ensure tests pass or document why they don't
- Commit all tested code
- Update PROGRESS.md with completion status
- Create PR if ready for review

---

## References

- **Test Guardian Rules**: `agents/04a-test-guardian.md`
- **Architecture Guardian Rules**: `agents/02a-architecture-guardian.md`
- **Session Continuity**: `agents/07-session-continuity-agent.md`
- **AI Instructions**: `.ai/instructions.md`
- **Progress Tracking**: `PROGRESS.md`
- **Requirements Status**: `docs/01-strategy/requirements-status.md`

---

## Quick Reference

### Fastest Path to Working Feature

```bash
# 1. Create feature branch
git checkout -b feat/my-feature

# 2. Develop and test (locally, uncommitted)
# - Write contract tests
# - Write implementation
# - Write implementation tests
# - Run: bash scripts/run-tests-docker.sh

# 3. When tests pass:
git add -A
git commit -m "feat: Description"
git push origin feat/my-feature

# 4. Create PR on GitHub
# - Wait for review and CI
# - Merge when approved

# 5. Done! ✅
```

### If Tests Fail

```bash
# DO NOT DO THIS:
git commit -m "tests broken, will fix later" ❌

# DO THIS:
bash scripts/run-tests-docker.sh  # See what failed
# [fix implementation]
bash scripts/run-tests-docker.sh  # Verify
git add -A
git commit -m "feat: Fixed implementation to pass tests" ✅
```

---

**Last Updated**: 2026-01-29  
**Purpose**: Prevent test failures in commits, enforce proper Git workflow, protect test integrity
