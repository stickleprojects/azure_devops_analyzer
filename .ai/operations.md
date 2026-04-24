# Operational Details & Project Conventions

This file complements `.ai/principles.md` with project-specific conventions and operational procedures. Refer to this when implementing changes, running tests, or managing the development environment.

---

## Pre-Commit Validation Gates

Every commit must pass these gates (in order):

### Gate 1: Branch Check

```bash
git status
# Must show: "On branch feat/..." not main
```

Create feature branch if needed: `git checkout -b feat/your-feature`

### Gate 2: Architecture Review

Validate changes against component boundaries in `agents/02a-architecture-guardian.md`:

- ✓ Extractors contain only extraction logic (no analysis, no database writes)
- ✓ Analyzers are platform-agnostic (no extractor imports)
- ✓ Database layer is single source of truth for writes (via `src/database/storage.py`)
- ✓ Workflows orchestrate only (no embedded business logic)
- ✓ Cross-cutting concerns in `src/utils/` only

If uncertain about a change: check the Architecture Guardian reference, or ask the user.

### Gate 3: Run Tests

```bash
bash scripts/run-tests-docker.sh
# Verify: exit code 0, no failures, no skipped tests
```

Docker is source of truth (catches environment issues local Python misses).

### Gate 3.6: CI/Local Parity Check (Required for test/DB/CI changes)

If a change touches any of the following, you must validate using the same execution shape as GitHub Actions:

- `.github/workflows/tests.yml`
- `tests/**`
- `database/schema.sql` or `database/migrations/**`
- `tests/contract/database/conftest.py` (or other test DB setup code)

Required parity actions:

1. Run tests in Docker (never local python).
2. Run the same pytest scopes used by CI (unit + contract/integration + coverage path) or the exact failing subset first, then the full suite.
3. When tests insert rows via raw SQL fixtures, set values explicitly for non-null/PK fields. Do not rely on implicit defaults or autoincrement behavior unless the test verifies that behavior.
4. Keep schema source alignment explicit: if test setup uses SQLAlchemy models (`Base.metadata.create_all`) and production uses SQL migrations, verify fixture assumptions against both.

Recommended CI-shape command pattern for targeted validation:

```bash
docker compose -f docker-compose.test.yml run --rm test-runner sh -c "pytest <same-path-or-scope-as-ci> -v --tb=short"
```

Then run full validation before commit:

```bash
bash scripts/run-tests-docker.sh
```

### Gate 4: Test Integrity Check (if modifying tests)

Before changing any test, consult `agents/04a-test-guardian.md`:

- **Contract tests** (in `tests/contract/`): Define requirements. Cannot modify without documented requirement change + approval. Fix implementation instead.
- **Implementation tests** (in `tests/implementation/`): Can evolve with technical changes, provided contract tests still pass.
- Never skip/disable tests to make builds pass. If a test fails, fix implementation.

### Gate 5: Documentation Review (if modifying docs)

Verify:

- Code examples: ≤ 15 lines each, max 3 per section
- Code content: ≤ 30% of total document
- Structure: Explain concept first, then show example (if needed)
- Links: Use links instead of copying large code blocks

---

## Session Continuity

### At Session Start

1. **Read progress**: Check `PROGRESS.md` for recent work
2. **Check git status**: Look for uncommitted changes or incomplete features
3. **Verify branch**: Should be on `feat/...` branch, not main
4. **Assess work**: Is previous work complete or in-progress?

**If work is in-progress:**

- Summarize completed tasks
- List remaining tasks with next specific action
- Suggest user pick from incomplete or move to backlog

**If work is complete:**

- Check backlog in `docs/01-strategy/requirements-status.md`
- Present top priorities with effort/impact assessment
- Ask which user wants to tackle

### At Session End

Update `PROGRESS.md` with:

- What was accomplished (features, bugs, refactors, tests)
- What remains incomplete (and why, if blocked)
- Next specific action (what should be started next session)
- Any blockers or questions

See `agents/07-session-continuity-agent.md` for detailed session tracking patterns.

---

## Project Conventions

### Git & Branching

- **Branch naming**: `feat/feature-name`, `fix/bug-name`, `docs/change`, `refactor/what`
- **Never commit to main**: All work on feature branches
- **Commit messages**: Clear description of what and why
- **No fast-forward merges**: Preserves feature branch history

### Docker

- **Use Docker Compose V2**: `docker compose` (not `docker-compose`)
- **Environment file**: `.env` supports variable references like `$VARIABLE_NAME`
- **Generate `.env` when missing/incomplete**: Run `./Start-RepoAnalysis.sh --regenerate-env` (or `./start-repoanalysis.sh --regenerate-env`) and have the user answer the interactive prompts
- **Resolve variables**: Use `./scripts/resolve_env.sh` to create `.env.resolved` if needed
- **Start services**: `docker compose --env-file .env.resolved up -d`

### Python

- **Version**: Python 3.12.4 (managed via pyenv)
- **Type hints**: Use type hints in all code
- **Database layer**: Keep DB operations in `src/database/storage.py` ONLY
- **Extractors location**: `src/extractors/{platform}/`
- **Execution**: Never run python code locally - always host inside docker, there is a script `scripts/run-tests-docker.sh` as an example

### Code Style

- Follow existing patterns in the codebase
- No unnecessary comments on unchanged code
- Keep functions focused and testable

### Testing

- **Test files location**: `tests/` directory
- **Integration tests**: `tests/contract/integration/` for end-to-end validation
- **Run tests**: `bash scripts/run-tests-docker.sh`
- **Live API tests**: `bash scripts/run-tests-docker.sh --live-api`

### Documentation

- **Read first**: `docs/03-operations/feature-development-workflow.md` before starting features
- **Progress tracking**: `PROGRESS.md` (session-by-session detailed log)
- **Feature status**: `docs/01-strategy/requirements-status.md` (backlog tracking)
- **Architecture reference**: `docs/02-architecture/` directory

---

## Key Directories & Files

```
.ai/
  ├─ principles.md           ← Mental framework (7 core principles)
  ├─ operations.md           ← This file (conventions & procedures)
  └─ instructions.md         ← Legacy redirect (being phased out, ignore)

agents/
  ├─ 00-documentation-standards.md
  ├─ 02a-architecture-guardian.md  ← Reference when validating architecture
  ├─ 04a-test-guardian.md          ← Reference when modifying tests
  ├─ 05-code-review.md             ← How to perform code review (Claude only)
  └─ 07-session-continuity-agent.md ← Reference for session tracking

src/
  ├─ extractors/             ← Platform-specific data extraction
  ├─ analyzers/              ← Platform-agnostic analysis
  ├─ workflows/              ← Orchestration
  ├─ database/               ← Storage layer (ONLY place for DB writes)
  └─ utils/                  ← Cross-cutting concerns

tests/
  ├─ contract/               ← Business requirements (strict)
  └─ implementation/         ← Technical details (flexible)

PROGRESS.md                   ← Session tracking (most recent at bottom)
```

---

## Common Tasks

### Starting a new feature

1. Create feature branch: `git checkout -b feat/feature-name`
2. Write contract test first (what behavior do you want?)
3. Implement to pass test
4. Run `bash scripts/run-tests-docker.sh` (gate 3)
5. Commit with clear message describing what + why

### Fixing a bug

1. Write failing regression test (in contract tests if user-facing bug)
2. Fix implementation to pass test
3. Run full test suite
4. Commit with explanation of root cause + fix

### Refactoring

1. Ensure all tests pass before starting
2. Make changes
3. Re-run tests (must still pass)
4. Commit with description of what changed + why

### Adding a dependency

1. Update `requirements.txt` or `docker-compose.yml`
2. Validate it doesn't violate architecture (check boundaries)
3. Test in Docker environment
4. Document why it was needed

---

## When Uncertain

**Question**: "Should I modify this test to make the code pass?"  
**Answer**: No. Fix implementation instead. Tests define truth (Principle 1).

**Question**: "Can this analyzer call this extractor?"  
**Answer**: No. Analyzers must be platform-agnostic. Use the database layer (Principle 2).

**Question**: "Should I add business logic to a workflow?"  
**Answer**: No. Workflows orchestrate only. Embed logic in extractors/analyzers (Principle 2).

**Question**: "Can I commit this on main if tests pass?"  
**Answer**: No. Always work on feature branches (Principle 4).

**Question**: "Should I include this large code example in documentation?"  
**Answer**: Probably not. Explain the concept first, then decide if code is needed (Principle 3).

For other questions, refer to the principle that applies, or ask the user for clarification.

---

## Validation Script Commands

```bash
# Validate documentation
bash scripts/validate-documentation.sh docs/your-file.md

# Run all tests
bash scripts/run-tests-docker.sh

# Run only unit tests
bash scripts/run-tests-docker.sh --unit

# Run live API tests
bash scripts/run-tests-docker.sh --live-api

# Run coverage report
bash scripts/run_coverage.sh

# Resolve environment variables
./scripts/resolve_env.sh
```

---

## Reference Documents

For deep dives on specific topics:

- **Architecture boundaries**: `agents/02a-architecture-guardian.md`
- **Test integrity**: `agents/04a-test-guardian.md`
- **Session continuity**: `agents/07-session-continuity-agent.md`
- **Documentation standards**: `agents/00-documentation-standards.md`
- **Feature workflow**: `docs/03-operations/feature-development-workflow.md`
- **Full system architecture**: `docs/02-architecture/system-architecture.md`
