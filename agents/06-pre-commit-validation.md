# Pre-Commit Validation Agent

## Purpose

The Pre-Commit Validation Agent acts as a quality gate-keeper that ensures all work meets project standards BEFORE being committed to version control. It enforces five critical validation gates that prevent common problems from reaching git history.

**Key Principle**: Shift from reactive problem-detection (after commit) to proactive problem-prevention (before commit).

---

## Core Responsibilities

### 1. Branch Verification

- Prevent accidental commits to `main` branch
- Enforce feature branch naming convention (`feat/...`, `fix/...`, etc.)
- Block commits that would bypass version control workflows

### 2. Documentation Standards Validation

- Ensure documentation meets "Documentation Over Code" principle
- Check code content ≤ 30% of document size
- Verify code examples ≤ 15 lines each
- Prevent full function/class definitions in documentation
- Validate Architecture Guardian sections in implementation docs

### 3. Architectural Boundary Enforcement

- Verify extractor layer isolation (no DB writes)
- Verify analyzer independence (no extractor imports)
- Confirm workflow purity (orchestration only)
- Ensure database layer centralization

### 4. Test Requirement Verification

- All staged code changes must have passing tests
- No skipped tests allowed
- No test modifications to make code pass
- Existing tests must still pass (no regressions)

### 5. Commit Message Format Validation

- Verify commit message follows project format
- Ensure type is one of: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`
- Confirm description is descriptive and clear
- Validate test results statement when applicable

---

## Validation Gates

### Gate 1: Branch Verification

**Trigger**: Before every commit

**Validation**:

```bash
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" = "main" ]; then
  ❌ ERROR: Cannot commit to main
  exit 1
fi
```

**Impact**: Physically prevents commits to main branch

**Recovery**:

```bash
git reset HEAD~1              # Undo last commit
git checkout -b feat/feature  # Create feature branch
git commit -m "..."           # Re-apply commit
```

---

### Gate 2: Documentation Standards

**Trigger**: When `*.md` files are staged

**Validation**:

- Count code blocks: Should be ≤ 6 per document
- Check for full functions: Should be 0
- Estimate code %, should be ≤ 30%
- Verify Architecture Guardian section present (if implementation doc)

**Command**:

```bash
bash scripts/validate-documentation.sh docs/file.md
```

**Impact**: Catches guideline violations before commit

**Recovery**:

```bash
# Remove code examples or move to script files
# Update document structure
# Re-run validation
bash scripts/validate-documentation.sh docs/file.md
```

---

### Gate 3: Architecture Guardian

**Trigger**: When `*.py` files are staged in business logic

**Validation**:

- Extractors must not have database write operations
- Analyzers must not import from extractors
- Workflows must not contain business logic
- Database operations only in `src/database/`

**Implementation**:

```python
# Check: if "src/extractors" in file:
#   verify no "session.add", "session.execute"
# Check: if "src/analyzers" in file:
#   verify no "from src.extractors import"
```

**Reference**: `agents/02a-architecture-guardian.md`

**Impact**: Prevents architectural violations

**Recovery**:

```bash
# Move code to appropriate layer
# Remove cross-layer dependencies
# Re-test architecture verification
```

---

### Gate 4: Test Requirement

**Trigger**: When code in `src/` is staged

**Validation**:

```bash
bash scripts/run-tests-docker.sh
# Requirements:
# - Exit code = 0
# - All tests pass
# - No regressions
```

**Impact**: No failing code reaches version control

**Recovery**:

```bash
# Fix implementation
bash scripts/run-tests-docker.sh
# Unstage if tests still fail
git reset HEAD path/to/file.py
```

---

### Gate 5: Commit Message Format

**Trigger**: Before every commit (commit-msg hook)

**Validation**:

```
Format: type: description

Valid types: feat, fix, docs, refactor, test, chore
Example:
  feat: add team allocation

  - Implements FR-13.2
  - Adds 5 integration tests
```

**Impact**: Clean, searchable commit history

**Recovery**:

```bash
git commit --amend -m "type: corrected message"
```

---

## Validation Checklist

### Before Every Commit

- [ ] **Gate 1**: Branch is `feat/...` (not `main`)
  - `git status` must show feature branch
- [ ] **Gate 2**: Documentation standards (if .md modified)
  - `bash scripts/validate-documentation.sh docs/file.md`
- [ ] **Gate 3**: Architecture boundaries (if .py modified)
  - Verified no layer violations
- [ ] **Gate 4**: Tests passing (if src/ modified)
  - `bash scripts/run-tests-docker.sh` returns 0
- [ ] **Gate 5**: Commit message format valid
  - Follows: `type: description`

### Enforcement Mechanism

**Automated**:

- Pre-commit hook: Blocks main branch commits
- Pre-commit hook: Checks doc standards
- Pre-commit hook: Validates Python syntax
- Commit-msg hook: Validates message format

**Manual**:

- Developer verifies architecture compliance
- Developer runs tests locally
- Developer reviews own commit message

---

## Rejection Criteria (Commit Blocked)

Commit will be **rejected** and **blocked** if:

🔴 ❌ Current branch is `main`
🔴 ❌ Documentation has full function definitions
🔴 ❌ Documentation code % > 35%
🔴 ❌ Extractor contains database writes
🔴 ❌ Analyzer imports extractor
🔴 ❌ Any test fails (exit code ≠ 0)
🔴 ❌ Commit message invalid format

---

## Approval Criteria (Commit Allowed)

Commit will be **approved** and **allowed** if:

✅ ✅ Current branch starts with `feat/`, `fix/`, `docs/`, etc.
✅ ✅ Documentation passes standards check (if .md modified)
✅ ✅ Architecture Guardian approves (if .py modified)
✅ ✅ All tests pass locally (if src/ modified)
✅ ✅ Commit message follows format
✅ ✅ No violations detected in pre-commit hooks

---

## Implementation

### Files Involved

- **Pre-commit hook**: `.git/hooks/pre-commit`
  - Automated branch + doc validation
  - Blocks main branch commits
- **Validation script**: `scripts/validate-documentation.sh`
  - Documentation standards checker
  - Reports code %, code blocks, violations
- **Agent coordination**: `agents/02a-architecture-guardian.md`
  - Architecture validation rules
  - Boundary definitions
- **Test requirements**: `agents/04a-test-guardian.md`
  - Test validation rules
  - Coverage expectations

### Workflow Integration

```
Developer Creates Changes
         │
         ▼
    Run: git commit
         │
         ▼
Pre-Commit Hooks Run
├─ Gate 1: Branch check
├─ Gate 2: Doc standards (if .md)
├─ Gate 3: Architecture (if .py)
├─ Gate 4: Python syntax
└─ Gate 5: Message format
         │
    All pass? ──── Yes ──▶ Commit succeeds ✅
         │
         No
         │
         ▼
    Commit blocked ❌
    Error message shows which gate failed
    Developer fixes and retries
```

---

## Common Scenarios

### Scenario 1: Developer Forgets Feature Branch

**Problem**:

```bash
$ git status
On branch main

$ git commit ...
❌ ERROR: Cannot commit directly to main branch
```

**Solution**:

```bash
$ git reset HEAD~1
$ git checkout -b feat/my-feature
$ git commit ...
✅ Commit succeeds on feat/my-feature
```

---

### Scenario 2: Documentation Exceeds Code Limit

**Problem**:

```bash
$ git commit -m "docs: new architecture"
⚠️  Warning: Document has 8 code blocks
❌ Estimated code: 35% (exceeds 30%)
```

**Solution**:

```bash
# Remove or move code examples
# Keep only 3 essential examples
# Reference full implementations in scripts

$ bash scripts/validate-documentation.sh
✅ Documentation passed (4 blocks, 25% code)

$ git commit ...
✅ Commit succeeds
```

---

### Scenario 3: Test Failure on Commit

**Problem**:

```bash
$ git commit -m "feat: new feature"
Gate 4: Running tests...
❌ FAILED: 2 tests failing
Exit code: 1
```

**Solution**:

```bash
# Fix the failing tests
# Re-run locally to verify

$ bash scripts/run-tests-docker.sh
✅ All tests passing (exit code: 0)

$ git commit ...
✅ Commit succeeds
```

---

## Benefits

✅ **Prevents problems at commit time** (not after merge)  
✅ **Automated enforcement** (no human error)  
✅ **Fast feedback loops** (immediate problem detection)  
✅ **Clean git history** (only good commits reach git)  
✅ **Developer confidence** (know commit meets standards)  
✅ **Team efficiency** (no rework on already-merged code)

---

## Reference Documents

- `agents/02a-architecture-guardian.md` - Architecture boundary rules
- `agents/04a-test-guardian.md` - Test validation rules
- `agents/00-documentation-standards.md` - Documentation guidelines
- `.ai/instructions.md` - AI agent pre-commit requirements
- `docs/03-operations/feature-development-workflow.md` - Workflow Phase 1.5

---

## Next Steps

1. Verify pre-commit hooks are executable
2. Run validation scripts manually to understand output
3. Test each validation gate individually
4. Document any project-specific additions needed
5. Train team on recovery procedures
