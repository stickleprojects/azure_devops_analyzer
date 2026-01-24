# GitHub Copilot Instructions for azure_devops_analyzer

## Session Continuity Agent - BEST-EFFORT ACTIVATION

**ACTIVATION**: When user greets with casual phrases, **attempt to engage** Session Continuity Agent defined in `agents/07-session-continuity-agent.md`.

**Note:** Greeting detection is probabilistic. If automatic activation doesn't occur, the user can explicitly request: "analyze last session" or "show backlog".

### Greeting Triggers (Best-Effort Auto-Activate):
- "good morning" / "good afternoon" / "good evening"
- "hello" / "hi" / "hey"
- "let's pick up" / "let's continue" / "continue"
- "where were we" / "pick up where we left off"

### Alternative Explicit Prompts (If Greeting Fails):
- "analyze last session"
- "show me the backlog"
- "what should I work on?"
- "where did I leave off?"

### Agent Activation Process:
```
WHEN greeting detected OR explicit request:
1. Respond with warm greeting
2. Read PROGRESS.md (most recent session)
3. Check git status for uncommitted changes
4. Analyze if work is incomplete or complete
5. IF incomplete → Present "Continue" summary with next steps
6. IF complete → Load backlog from requirements-status.md and present priorities
7. WAIT for user selection before proceeding
```

### Assisted Task Completion (User-Prompted):
When user asks "is this task complete?", the agent checks:
- Test status (all passing?)
- Git status (committed/staged?)
- Implementation status (complete?)
- Suggests marking complete if criteria met
- Updates documentation with user approval

**Important:** Agent requires user interaction. No automatic background monitoring.

### Session Continuity Flow:
```markdown
**Agent Output Format:**

📋 Last Session Summary (DATE)
- Completed: [key achievements]
- In Progress: [incomplete tasks]
- Uncommitted: [file changes]

**Next Action:**
[Specific actionable suggestions]

OR (if complete):

✅ Last Session Complete
- Top Priority Backlog:
  1. [Item with status, impact, effort]
  2. [Item with status, impact, effort]

Which would you like to tackle?
```

**Full agent specification:** [agents/07-session-continuity-agent.md](../agents/07-session-continuity-agent.md)

**User guide:** [docs/03-operations/copilot-session-guide.md](../docs/03-operations/copilot-session-guide.md) - Learn when and how to prompt the agent

---

## Architecture Guardian - AUTOMATIC VALIDATION

**CRITICAL**: Before implementing ANY code changes, automatically validate against architectural boundaries defined in `agents/02a-architecture-guardian.md`.

### Automatic Guardian Checks Required For:
1. **Component boundary changes** - New files in extractors/, analyzers/, workflows/, database/
2. **Database schema changes** - Modifications to schema.sql, migrations/, or database/storage.py
3. **Cross-cutting concerns** - Logging, caching, auth, error handling, configuration
4. **New dependencies** - Additions to requirements.txt or docker-compose.yml
5. **Interface changes** - Modifications to base classes or public APIs

### Guardian Validation Process:
```
BEFORE implementing:
1. Identify affected architectural layers
2. Check against boundary rules in 02a-architecture-guardian.md
3. Evaluate impact: LOW/MEDIUM/HIGH
4. If boundary violation detected → STOP and present alternatives
5. If flagged → Present options to user before proceeding
6. If approved → Proceed with implementation
```

### Protected Architectural Boundaries:
- **Extractors**: Platform-isolated, no analysis logic, no direct DB writes
- **Analyzers**: Platform-agnostic, return data structures only
- **Database layer**: ONLY module for DB operations (storage.py)
- **Workflows**: Orchestration only, delegates to extractors/analyzers
- **Cross-cutting concerns**: Must live in utils/, not in business logic

### When Changes Are Flagged:
Present this format to user:
```
⚠️ ARCHITECTURE REVIEW REQUIRED

Proposed Change: [description]
Affected Components: [list]
Boundary Concern: [specific violation]
Recommended Alternative: [suggestion]

Options:
1. Implement recommended alternative (maintains architecture)
2. Proceed as-is (accept architectural debt)
3. Discuss architectural redesign

Which would you prefer?
```

### Auto-Approve Criteria (No Guardian Check Needed):
- Bug fixes within single function (no interface changes)
- Test additions (see Test Guardian for test modifications)
- Documentation updates
- Code formatting/linting
- Internal refactoring within one module (no external API changes)

## Test Guardian - AUTOMATIC VALIDATION

**CRITICAL**: Before modifying ANY tests, automatically validate against test integrity rules defined in `agents/04a-test-guardian.md`.

### The Iron Rule
**If a test fails after implementation changes, the implementation is probably wrong, not the test.**

### Automatic Test Guardian Checks Required For:
1. **Test assertion changes** - Modified expected values, relaxed constraints
2. **Test deletions** - Removed test cases or disabled tests
3. **Test scope changes** - Modified mock behavior, changed test data
4. **Implementation with failing tests** - Tests must pass or be fixed first

### Test Guardian Validation Process:
```
WHEN modifying tests:
1. Identify TEST TYPE (contract vs implementation - see below)
2. CONTRACT tests → STRICT protection (business requirements)
3. IMPLEMENTATION tests → FLEXIBLE (technical details can evolve)
4. If test failing after implementation → FIX IMPLEMENTATION, not test
5. For new features → Write CONTRACT tests FIRST (should fail before implementation)
6. For bug fixes → Add regression test FIRST (should fail before fix)
7. For refactoring → Tests should NOT need changes (behavior unchanged)
```

### Test Organization (CRITICAL - Read First):
**We distinguish two test types with different rules:**

#### CONTRACT Tests (Business Requirements) - STRICT
- **Location**: `tests/contract/` or named `test_contract_*`
- **Purpose**: Define WHAT system should do (business behavior)
- **Docstring**: Start with `"""CONTRACT: ...`
- **Protection**: CANNOT change without documented requirement change + approval
- **Examples**: API contracts, business rules, user-facing behavior
- **If it fails**: FIX IMPLEMENTATION - contract defines requirements

#### IMPLEMENTATION Tests (Technical Details) - FLEXIBLE
- **Location**: `tests/implementation/` or named `test_impl_*`  
- **Purpose**: Validate HOW system does it (technical mechanisms)
- **Docstring**: Start with `"""IMPLEMENTATION: ...`
- **Protection**: CAN change with implementation (if contracts still pass)
- **Examples**: Pagination, rate limiting, caching, retry logic, connection pooling
- **If it fails**: May fix test if implementation strategy changed

**Decision Rule**: *"If implementation changes completely but behavior stays same, should this test still pass?"*
- YES → CONTRACT test (strict)
- NO → IMPLEMENTATION test (flexible)

**See [docs/03-operations/test-organization.md](docs/03-operations/test-organization.md) for complete guide.**

### Protected Test Principles:
- **Tests define the contract** - Implementation must satisfy tests
- **Test-first approach** - Write failing tests before implementing
- **Regression protection** - Add test before fixing bug
- **No assertion weakening** - Don't relax expectations to pass
- **No test disabling** - Fix implementation or requirement, not test

### When Test Changes Are Flagged:

**For CONTRACT Test Changes:**
```
🛑 CONTRACT TEST MODIFICATION BLOCKED

Test: [test name]
Type: CONTRACT (business requirement)
Change: [what changed]

CONTRACT TESTS DEFINE BUSINESS REQUIREMENTS.
Changes require documented requirement change + stakeholder approval.

CRITICAL QUESTIONS:
1. Why did business requirement change?
2. Should implementation be fixed instead?
3. Is there an ADR for this change?

Options:
1. Fix implementation to match contract (tests are correct)
2. Document requirement change + update ALL related contracts
3. Create separate IMPLEMENTATION test if this is technical detail

Which would you prefer?
```

**For IMPLEMENTATION Test Changes:**
```
⚠️ IMPLEMENTATION TEST MODIFICATION

Test: [test name]
Type: IMPLEMENTATION (technical detail)
Change: [what changed]

IMPLEMENTATION TESTS can evolve with code.

Validation:
✓ Contract tests still pass?
✓ Technical reason documented?
✓ No business behavior impact?

Approved if above criteria met.
```

### Auto-Approve Test Changes:
- Adding new test cases (not modifying existing)
- Improving test structure/readability (assertions unchanged)
- Test infrastructure improvements (fixtures, helpers)
- Better assertion messages
- Test documentation

### 🛑 BLOCK These Test Changes:
- Changing assertion expected values without requirement documentation
- Removing test cases without explanation
- Skipping/disabling tests to make build pass
- Relaxing error handling checks
- Weakening validation constraints

## Project-Specific Conventions

### Docker
- **ALWAYS use `docker compose`** (Docker Compose V2), NOT `docker-compose` (V1)
- Docker Compose V1 is deprecated and not installed on this system

### Environment Variables
- The `.env` file supports **indirect variable references** like `$VARIABLE_NAME`
- PowerShell helpers (`EnvironmentHelpers.ps1`, `EnvFileHelpers.ps1`) resolve these references
- Docker Compose reads `.env` directly and does NOT resolve indirect references
- Use `./scripts/resolve_env.sh` to create `.env.resolved` with resolved values
- When starting Docker services, use: `docker compose --env-file .env.resolved up -d`

### Python Environment
- Python 3.12.4 managed via pyenv
- Always use `configure_python_environment` tool before running Python commands
- Use `mcp_pylance_mcp_s_pylanceRunCodeSnippet` for running Python snippets (preferred over terminal)

### Code Style
- Follow existing patterns in the codebase
- Use type hints in Python code
- Keep database operations in `src/database/storage.py`
- Extractors go in `src/extractors/{platform}/`

### Testing
- Run tests with `runTests` tool, not manual terminal commands
- Test files in `tests/` directory

### Common Issues
1. **Placeholder data in database**: Environment variables not properly resolved - check `.env.resolved`
2. **Celery workers failing**: Ensure `.env.resolved` is up to date and services restarted with correct env file
3. **Import errors**: Verify Python environment is configured correctly

## Workflow
1. When making environment changes, regenerate resolved env: `./scripts/resolve_env.sh`
2. Restart services with resolved env: `docker compose --env-file .env.resolved restart {service}`
3. Check logs: `docker compose logs -f {service}`
