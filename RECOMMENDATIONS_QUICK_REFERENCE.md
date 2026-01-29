# Implementation Recommendations: Quick Reference

## Problem Summary

| Problem                                           | Root Cause                                 | Prevention                            |
| ------------------------------------------------- | ------------------------------------------ | ------------------------------------- |
| **Doc guidelines not followed (500+ lines code)** | No pre-flight validation against standards | Pre-commit documentation checker      |
| **Branch/commit risk (main vs feat/...)**         | No automated branch verification           | Pre-commit hook to block main commits |

---

## Immediate Actions (P0 - Do First)

### 1. Create Pre-Commit Hook

**File**: `.git/hooks/pre-commit`

Prevents commits to main branch automatically:

```bash
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" = "main" ]; then
  echo "❌ Cannot commit to main - use feature branch"
  exit 1
fi
```

**Impact**: Physically prevents the "commit to main" mistake

---

### 2. Create Documentation Validator Script

**File**: `scripts/validate-documentation.sh`

Auto-checks documentation against guidelines:

```bash
# Validates:
# - Code blocks ≤6 per doc (implies ≤30% code)
# - No embedded full function definitions
# - Architecture Guardian section present (for impl docs)
```

**Impact**: Catches guideline violations before commit

---

### 3. Update `.ai/instructions.md`

Add explicit validation gate section:

```markdown
## Pre-Commit Validation (Critical - Cannot Skip)

Before every `git commit`:

1. Verify branch: `git status` shows "On branch feat/..."
2. Verify tests pass: `bash scripts/run-tests-docker.sh`
3. If .md files: Run `bash scripts/validate-documentation.sh`
4. Verify commit message format: `type: description`
```

**Impact**: Clear instructions to AI agents on what to validate

---

### 4. Update Feature Development Workflow

**File**: `docs/03-operations/feature-development-workflow.md`

Add "Phase 1.5: Pre-Flight Validation" between Phase 1 (Planning) and Phase 2 (Development):

```markdown
### Phase 1.5: Pre-Flight Validation

✅ Documentation:

- [ ] Review against agents/00-documentation-standards.md
- [ ] Code content ≤30%
- [ ] Examples ≤15 lines each
- [ ] ≤3 examples per section

✅ Code:

- [ ] Architecture Guardian review done
- [ ] No boundary violations
- [ ] Tests will be run before commit

✅ Branch:

- [ ] Current branch is `feat/...`
- [ ] NOT on main
```

**Impact**: Makes validation an explicit, documented phase

---

## Short-term Improvements (P1 - Next)

### 5. Create Validation Agent

**File**: `agents/06-pre-commit-validation.md`

Formalizes pre-commit gate-keeping:

- Gate 1: Branch verification
- Gate 2: Documentation standards
- Gate 3: Architecture Guardian check
- Gate 4: Test passing requirement
- Gate 5: Commit message format

**Impact**: AI agents have explicit validation responsibilities

---

### 6. Update Session Continuity Agent

**File**: `agents/07-session-continuity-agent.md`

Add session startup validation:

```markdown
## Session Validation Checklist

Before any work:

1. Branch check: `git status`
2. Guidelines review: Know the rules being enforced
3. Uncommitted changes: Clear before proceeding
4. Last session review: What was incomplete
```

**Impact**: Sessions start with proper context and validation

---

## Long-term Process Improvements (P2 - Future)

### 7. Enhanced Documentation Standards

**File**: `agents/00-documentation-standards.md`

Add new section "Pre-Commit Documentation Validation Checklist":

- Automated checklist for documentation files
- Code budget enforcement (≤30%)
- Example size limits (≤15 lines)
- Quick validation commands

---

### 8. Enhanced Test Guardian

**File**: `agents/04a-test-guardian.md`

Add "Pre-Commit Test Validation" section:

- Requirement: All tests pass before commit
- Requirement: No test modifications to make code pass
- Guidance: Run tests locally before pushing

---

### 9. Architecture Guardian Enforcement

**File**: `agents/02a-architecture-guardian.md`

Add explicit pre-commit validation step:

- Validation that new code respects boundaries
- Checklist for new components
- Reference to validation script

---

## How These Prevent Each Problem

### Problem 1: Documentation Guidelines Not Followed

**Prevention Chain**:

1. Developer creates documentation
2. **Pre-commit hook** blocks commit (if code >30%)
3. Developer runs `scripts/validate-documentation.sh`
4. Script shows violations and blocks commit
5. Developer fixes document to comply
6. Commit succeeds

**Result**: No guideline violations make it into git

---

### Problem 2: Commits to Main Branch

**Prevention Chain**:

1. Developer accidentally on main branch
2. **Pre-commit hook** checks current branch
3. Hook detects "main" and exits with error
4. Commit blocked immediately
5. Developer must create feature branch first
6. Commit succeeds on feat/...

**Result**: Impossible to commit to main

---

## Validation Flow After Improvements

```
Start Work
    │
    ▼
┌─────────────────────────┐
│ GATE 1: Branch Check    │
│ Pre-commit hook verifies│
│ NOT on main             │
└─────────────┬───────────┘
              │ ❌ on main?
              │ → Create feature branch
              │ ✅ on feat/...?
              ▼
┌─────────────────────────┐
│ GATE 2: Doc Standards   │
│ If .md modified:        │
│ validate-documentation  │
└─────────────┬───────────┘
              │ ❌ >30% code?
              │ → Reduce code content
              │ ✅ passes?
              ▼
┌─────────────────────────┐
│ GATE 3: Architecture    │
│ Guardian approval?      │
└─────────────┬───────────┘
              │ ❌ violations?
              │ → Fix boundaries
              │ ✅ approved?
              ▼
┌─────────────────────────┐
│ GATE 4: Tests Pass      │
│ run-tests-docker.sh     │
└─────────────┬───────────┘
              │ ❌ failures?
              │ → Fix implementation
              │ ✅ all pass?
              ▼
┌─────────────────────────┐
│ GATE 5: Commit Format   │
│ Message valid?          │
└─────────────┬───────────┘
              │ ❌ wrong format?
              │ → Use: type: description
              │ ✅ correct?
              ▼
┌─────────────────────────┐
│ ✅ Commit Succeeds      │
│ All gates passed        │
└─────────────────────────┘
```

---

## Files to Modify/Create

| File                                                 | Action     | Complexity               |
| ---------------------------------------------------- | ---------- | ------------------------ |
| `.git/hooks/pre-commit`                              | **CREATE** | Simple bash script       |
| `scripts/validate-documentation.sh`                  | **CREATE** | Simple bash script       |
| `.ai/instructions.md`                                | **UPDATE** | Add validation section   |
| `docs/03-operations/feature-development-workflow.md` | **UPDATE** | Add Phase 1.5            |
| `agents/06-pre-commit-validation.md`                 | **CREATE** | New agent doc            |
| `agents/07-session-continuity-agent.md`              | **UPDATE** | Add validation checklist |
| `agents/00-documentation-standards.md`               | **UPDATE** | Add validation checklist |
| `agents/04a-test-guardian.md`                        | **UPDATE** | Add pre-commit section   |

**Total**: 4 files to create, 4 files to update

---

## Next Steps

1. **This session**: Analysis complete + recommendations documented
2. **Next session (P0)**: Implement pre-commit hook + validation script
3. **Following session (P1)**: Update agents/workflow docs
4. **Later (P2)**: Create formal pre-commit validation agent

This transforms reactive problem-catching into proactive problem-prevention.
