# Session Problem Analysis: January 29, 2026

**Session Goal**: Design and document contributor-to-team allocation architecture (FR-13.2, FR-13.3)

**Problems Identified**:
1. ❌ **Documentation Guideline Violations**: Initial document violated "Documentation Over Code" principle (500+ lines of code in 1,105-line doc)
2. ❌ **Branch/Commit Risk**: Risk of committing to wrong branch (though actual commits were correct to `feat/team-management`)

---

## Problem 1: Documentation Guideline Violations

### What Happened

The initial `contributor-team-allocation-strategy.md` document contained:
- Complete Python function implementations (150+ lines)
- 10+ CLI command examples (50+ lines)
- Programmatic API usage examples (20+ lines)
- Workflow integration code walkthrough (15+ lines)
- **Total violation**: ~500 lines of code in 1,105-line document (45% code)

**Guideline Requirement**: [agents/00-documentation-standards.md](agents/00-documentation-standards.md)
- Max 30% code per document
- Max 15 lines per example
- Max 3 examples per section
- Only include code when "absolutely necessary"

### Root Cause Analysis

**Primary Cause**: No pre-flight validation against guidelines

The document was created with these problems:

1. **No pre-commit review**: Document was committed without being checked against `agents/00-documentation-standards.md`
2. **Conflated purposes**: Document tried to be both:
   - Architecture description (what we're building)
   - Implementation guide (how to build it)
3. **No guardian validation**: Didn't follow Architecture Guardian approval checklist before creation
4. **Missing validation workflow**: No step to "review against guidelines" before committing

**Why It Wasn't Caught**:
- Guidelines exist but weren't explicitly checked before content creation
- Workflow doesn't have a "pre-flight documentation check" step
- Agent created document → created review → *then* identified violations (backwards)

---

## Problem 2: Branch/Commit Risk

### What Happened

The user reported concern that code was committed to `main` branch instead of feature branch.

While the final commit was correct (`feat/team-management`), this indicates a **workflow risk**:
- During session, changes were made to multiple files
- If developer isn't vigilant, could accidentally commit to `main`
- Feature development checklist exists but **pre-commit verification missing**

### Root Cause Analysis

**Primary Cause**: No automated pre-commit branch verification

1. **Workflow allows commits from any branch**: Git doesn't prevent committing to `main`
2. **Manual verification required**: Relies on developer remembering to check current branch
3. **No agent-level enforcement**: AI agents don't verify branch before git commands
4. **Instructions incomplete**: `.ai/instructions.md` emphasizes "create feature branch" but lacks enforcement

**Why It Could Happen Again**:
- Developer could run `git commit` without checking `git status` first
- Pre-commit hook doesn't validate branch
- Workflow checklist item "ALWAYS create feature branch BEFORE code changes" is aspirational, not enforced

---

## Why These Problems Occurred Together

These two issues share a **common root cause**: Lack of validation gates before committing.

```
Current Flow:
┌─────────────────────────────────┐
│ Create content                  │
│ (Document/Code)                 │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ Commit to git                   │
│ (Assumes all is correct)         │
└──────────────┬──────────────────┘
               │
               ▼
         ✅ or ❌ Issues found

Improved Flow (Recommended):
┌─────────────────────────────────┐
│ Create content                  │
│ (Document/Code)                 │
└──────────────┬──────────────────┘
               │
               ▼
    ┌──────────────────────────┐
    │ VALIDATION GATE 1:       │
    │ Check guidelines         │
    │ (Documentation, etc.)    │
    └──────────────┬───────────┘
                   │
                   ▼
    ┌──────────────────────────┐
    │ VALIDATION GATE 2:       │
    │ Verify branch name       │
    │ (feat/*, not main)       │
    └──────────────┬───────────┘
                   │
                   ▼
    ┌──────────────────────────┐
    │ VALIDATION GATE 3:       │
    │ Run tests (if code)      │
    │ All passing required     │
    └──────────────┬───────────┘
                   │
                   ▼
┌─────────────────────────────────┐
│ Commit to git                   │
│ (Only after all gates pass)     │
└──────────────┬──────────────────┘
```

---

## Recommended Improvements

### 1. Add Documentation Pre-Flight Checklist

**Location**: Update `agents/00-documentation-standards.md`

**Add new section**: "Pre-Commit Documentation Validation"

```markdown
## Pre-Commit Documentation Validation Checklist

Before committing any documentation file (*.md), verify:

### Code Content Check
- [ ] Code represents ≤30% of document
- [ ] Each code example ≤15 lines
- [ ] ≤3 code examples per section
- [ ] Code ONLY included when absolutely necessary (algorithm, security, API contract)
- [ ] Full implementations linked to actual files, not embedded

### Structure Check  
- [ ] Principles explained in prose BEFORE any code examples
- [ ] Complex concepts use tables/lists instead of code
- [ ] Section headings clearly distinguish "what" from "how"
- [ ] Architecture documented separately from implementation guide

### Completeness Check
- [ ] Architecture Guardian validation section present (if applicable)
- [ ] References to actual implementation files (if applicable)
- [ ] Test strategy linked to actual test files (if applicable)
- [ ] No orphaned references to non-existent files

### Quick Check Command
```bash
# Count code fence blocks
grep -c '^```' docs/04-implementation/your-doc.md

# If > 6 blocks total, likely over 30% code limit
```
```

### 2. Update Feature Development Workflow

**Location**: `docs/03-operations/feature-development-workflow.md`

**Add new phase**: "Phase 1.5: Pre-Commit Validation" (before Phase 2)

```markdown
### Phase 1.5: Pre-Flight Validation (New)

**Critical**: Execute before starting Phase 2 development

#### For Documentation Changes:
- [ ] Document reviewed against `agents/00-documentation-standards.md`
- [ ] Code content ≤30% of total
- [ ] Each example ≤15 lines
- [ ] All code blocks (Python, SQL, bash) ≤3 per section
- [ ] Run guideline checklist: `bash scripts/validate-documentation.sh [file]`

#### For Code Changes:
- [ ] Architecture Guardian review completed
- [ ] No extractor logic in analyzers, analyzers in workflows, etc.
- [ ] Database operations only in `src/database/` layer
- [ ] New components documented in architecture files

#### Branch Verification:
- [ ] Verify on feature branch: `git status` shows `On branch feat/...`
- [ ] If on `main`: create feature branch `git checkout -b feat/your-feature`
- [ ] Commit only to feature branch, NEVER to main
```

### 3. Enhance Agent Instructions

**Location**: Update `.ai/instructions.md`

**Add new section**: "Pre-Commit Validation Requirements"

```markdown
## Pre-Commit Validation (Critical - Cannot Skip)

### Every Commit Must Pass:

#### 1. Branch Verification
```bash
BEFORE git commit:
  git status
  # Output must show: "On branch feat/..."
  # If "On branch main" → immediately: git checkout -b feat/your-feature
```

#### 2. Documentation Validation  
- If modifying `*.md` files:
  - Count code blocks: should be ≤6 per document
  - Verify against agents/00-documentation-standards.md
  - Run: `bash scripts/validate-documentation.sh`

#### 3. Code Validation
- If modifying `*.py` files:
  - Run full test suite: `bash scripts/run-tests-docker.sh`
  - All tests must pass (exit code 0)
  - No modifications to tests without requirement approval

#### 4. Commit Message Validation
- Format: `type: description\n\n- bullet points`
- Examples: `feat: add team allocation`, `docs: refactor architecture doc`

**Rule**: Never commit without passing all 4 validation gates.
```

### 4. Create Documentation Validation Script

**Location**: `scripts/validate-documentation.sh` (NEW)

```bash
#!/bin/bash
# Validate documentation against standards

FILE=${1:-.}

echo "Validating documentation: $FILE"
echo "================================"

# Count code blocks
CODE_BLOCKS=$(grep -c '^```' "$FILE" 2>/dev/null || echo "0")
echo "✓ Code blocks: $CODE_BLOCKS"
if [ "$CODE_BLOCKS" -gt 6 ]; then
  echo "  ⚠️  WARNING: > 3 code blocks per section (might exceed 30% limit)"
fi

# Check for common violations
if grep -q "^def " "$FILE" 2>/dev/null; then
  echo "  🔴 ERROR: Contains full Python function definitions"
  exit 1
fi

# Check for architecture guardian section in implementation docs
if [[ "$FILE" == *"implementation"* ]]; then
  if ! grep -q "Architecture Guardian" "$FILE" 2>/dev/null; then
    echo "  🟡 WARNING: Implementation doc missing Architecture Guardian section"
  fi
fi

echo "✅ Documentation validation passed"
```

### 5. Create Pre-Commit Hook

**Location**: `.git/hooks/pre-commit` (NEW)

```bash
#!/bin/bash
# Pre-commit validation hook

echo "Running pre-commit validation..."

# 1. Check branch
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" = "main" ]; then
  echo "❌ ERROR: Attempting to commit to main branch"
  echo "Please create a feature branch: git checkout -b feat/your-feature"
  exit 1
fi

# 2. Check for staged documentation files
DOCS=$(git diff --cached --name-only | grep '\.md$' || true)
if [ ! -z "$DOCS" ]; then
  for doc in $DOCS; do
    CODE_BLOCKS=$(grep -c '^```' "$doc" 2>/dev/null || echo "0")
    if [ "$CODE_BLOCKS" -gt 6 ]; then
      echo "⚠️  $doc has many code blocks - verify against standards"
    fi
  done
fi

# 3. Run Python validation (if py files staged)
PY_FILES=$(git diff --cached --name-only | grep '\.py$' || true)
if [ ! -z "$PY_FILES" ]; then
  echo "Validating Python files..."
  python -m py_compile $PY_FILES || exit 1
fi

echo "✅ Pre-commit validation passed"
exit 0
```

---

## Recommended Agent Updates

### 1. Update `agents/07-session-continuity-agent.md`

**Add validation checkpoint at session start**:

```markdown
## Session Validation Checklist

Before proceeding with any work:

1. ✅ Verify current branch: `git status`
   - Should show `On branch feat/...` (not `main`)
   - If on main, immediately create feature branch

2. ✅ Verify guidelines understood:
   - Documentation: agents/00-documentation-standards.md  
   - Code: agents/02a-architecture-guardian.md
   - Tests: agents/04a-test-guardian.md

3. ✅ Check for uncommitted changes:
   - If changes exist: commit or stash before proceeding
   - Clear working directory

4. ✅ Review last session's work:
   - Identify what was incomplete
   - Determine next steps
```

### 2. Update `agents/04a-test-guardian.md`

**Add section**: "Pre-Commit Test Validation"

```markdown
## Pre-Commit Test Validation

Before any commit containing code changes:

1. **Run full test suite**:
   ```bash
   bash scripts/run-tests-docker.sh
   ```

2. **Verify output**:
   - Exit code = 0 (all tests pass)
   - No skipped tests
   - No new test failures
   - Existing tests still pass (no regressions)

3. **Never modify tests to make them pass**:
   - If test fails, fix implementation
   - If requirement changed, update contract test
   - If technical approach changed, update implementation test
```

### 3. Create New Agent: `agents/06-pre-commit-validation.md`

This would be a NEW agent specifically for pre-commit validation:

```markdown
# Pre-Commit Validation Agent

## Purpose
Ensures all work meets quality gates before being committed to version control.

## Validation Gates

### Gate 1: Branch Verification
- Confirm current branch is NOT `main`
- Confirm branch follows `feat/feature-name` pattern

### Gate 2: Documentation Standards
- For any *.md changes: pass documentation validation checklist
- Code content ≤30%, examples ≤15 lines, ≤3 per section

### Gate 3: Architectural Boundaries
- For any Python code: validate against Architecture Guardian rules
- Check new files in correct layer (extractors, analyzers, database, workflows, etc.)

### Gate 4: Test Coverage
- For any code changes: all tests must pass
- Run: `bash scripts/run-tests-docker.sh`
- Exit code must be 0

### Gate 5: Commit Message Quality
- Format: `type: description\n\n- bullets`
- Example: `feat: add team allocation script\n\n- implements FR-13\n- adds 5 tests`

## Rejection Criteria

Reject commit if:
- ❌ Current branch is `main`
- ❌ Documentation has >6 code blocks OR >30% code
- ❌ Code violates architectural boundaries
- ❌ Any test fails
- ❌ Commit message doesn't follow format

## Approval Criteria

Approve commit only if:
- ✅ Feature branch (feat/...)
- ✅ Documentation passes standards check
- ✅ Architecture Guardian approves
- ✅ All tests passing
- ✅ Clear commit message
```

---

## Implementation Priority

| Priority | Change | Effort | Impact |
|----------|--------|--------|--------|
| **🔴 P0** | Add pre-commit hook (.git/hooks/pre-commit) | 30min | Prevents main branch commits |
| **🔴 P0** | Add documentation validation script | 45min | Catches guideline violations |
| **🟡 P1** | Update `.ai/instructions.md` with validation gates | 1hr | Guides AI agents in validation |
| **🟡 P1** | Add "Pre-Flight Validation" phase to workflow | 1hr | Documents requirements |
| **🟢 P2** | Create `agents/06-pre-commit-validation.md` | 1.5hr | Formalizes validation process |
| **🟢 P2** | Update existing agent docs | 2hr | Cross-reference new validation rules |

---

## Session Outcome

✅ **Problems Identified**: Both issues root-caused  
✅ **Fixes Applied**: Document refactored to compliance (674 lines, <30% code)  
✅ **Improvements Recommended**: 5 specific agent/workflow updates documented

**Next Session Action**: Implement pre-commit validation improvements (P0 items) to prevent recurrence.

---

## How to Prevent These Problems Going Forward

### During Development
1. **BEFORE committing**: Run validation gates
2. **Documentation**: Check against standards checklist
3. **Code**: Run tests, verify architecture
4. **Branch**: Always confirm `git status` shows feat/...

### Agent Improvements  
1. **Pre-flight checks**: Validate guidelines before creating content
2. **Automated gates**: Pre-commit hook + validation scripts
3. **Clear instructions**: Updated agent guidelines with explicit requirements
4. **Workflow checkpoints**: Add validation phases to documented workflow

### Outcome
These improvements shift from "catch problems after commit" to "prevent problems before commit" via automated validation gates.
