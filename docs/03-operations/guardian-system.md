# Guardian System Summary

## Overview

The Guardian system provides automatic protection for architectural integrity and test quality through two coordinated agents that validate changes before implementation.

## The Two Guardians

### 1. Architecture Guardian
**File**: [agents/02a-architecture-guardian.md](agents/02a-architecture-guardian.md)

**Purpose**: Protects system architecture and component boundaries

**Protects**:
- ✅ Component isolation (extractors, analyzers, workflows, database)
- ✅ SOLID principles
- ✅ Cross-cutting concerns separation
- ✅ Technology stack consistency

**Triggers**: Component boundary changes, schema changes, new dependencies, interface modifications

### 2. Test Guardian
**File**: [agents/04a-test-guardian.md](agents/04a-test-guardian.md)

**Purpose**: Protects test integrity and enforces test-first development

**Protects**:
- ✅ Business requirements (CONTRACT tests - strict)
- ✅ Technical implementations (IMPLEMENTATION tests - flexible)
- ✅ Test-first workflow
- ✅ Regression protection

**Triggers**: Test modifications, assertion changes, test deletions

## How It Works

### Automatic Activation

Both Guardians are activated automatically through [.github/copilot-instructions.md](.github/copilot-instructions.md):

1. **You make a request** to GitHub Copilot
2. **Copilot reads** the instructions automatically
3. **Guardians evaluate** if changes affect protected boundaries
4. **You receive warning** if violations detected
5. **You decide** how to proceed with full context

**No manual invocation needed** - protection is always active!

### Decision Flow

```
User Request
    ↓
Copilot Analyzes Intent
    ↓
┌───────────────────┬───────────────────┐
│                   │                   │
Architecture     Test              Both
Guardian         Guardian          Active
    ↓               ↓                 ↓
Checks           Checks          Coordinated
Boundaries       Tests           Review
    ↓               ↓                 ↓
✅ Approved      ✅ Approved      ✅ Approved
⚠️ Flag          ⚠️ Flag          ⚠️ Flag
🛑 Block         🛑 Block         🛑 Block
    ↓               ↓                 ↓
Present Options to User
```

## Test Organization Strategy

**See**: [docs/03-operations/test-organization.md](docs/03-operations/test-organization.md)

### CONTRACT Tests (Business Logic)
- **Location**: `tests/contract/`
- **Naming**: `test_contract_*`
- **Protection**: STRICT - rarely change
- **Purpose**: Define WHAT system should do

**Example**:
```python
def test_contract_extract_repositories_returns_list():
    """CONTRACT: extract_repositories must return list of Repository objects"""
    repos = extractor.extract_repositories("org")
    assert isinstance(repos, list)
```

### IMPLEMENTATION Tests (Technical Details)
- **Location**: `tests/implementation/`
- **Naming**: `test_impl_*`
- **Protection**: FLEXIBLE - can evolve
- **Purpose**: Validate HOW system does it

**Example**:
```python
def test_impl_github_pagination_uses_100_per_page():
    """IMPLEMENTATION: GitHub API pagination with 100 items per page"""
    assert extractor.PAGE_SIZE == 100
```

## Protection Levels

### 🛑 BLOCKED (Requires Approval)
- CONTRACT test modifications
- Breaking architectural boundaries
- Database schema changes without storage layer
- Disabling/skipping tests

### ⚠️ FLAGGED (Requires Justification)
- IMPLEMENTATION test modifications
- Cross-cutting concern additions
- New technology dependencies
- Mock behavior changes

### ✅ AUTO-APPROVED
- Bug fixes within single function
- Adding new tests
- Documentation updates
- Code formatting
- IMPLEMENTATION test updates (if CONTRACT tests pass)

## Practical Examples

### Example 1: Adding Caching

**Request**: "Add caching to GitHub extractor"

**Architecture Guardian**:
```
⚠️ ARCHITECTURE REVIEW REQUIRED

Proposed: Add cache to src/extractors/github/
Concern: Cross-cutting concerns should be in utils/

Recommended:
1. Create src/utils/cache.py
2. Apply caching at workflow level

Which would you prefer?
```

**Test Guardian**:
```
✅ CONTRACT tests must still pass
⚠️ Add IMPLEMENTATION tests for cache behavior

Approved if:
- Repository extraction still returns same data (contract)
- Cache hit/miss tested (implementation)
```

### Example 2: Changing Pagination

**Request**: "Change GitHub pagination from 100 to 50 items per page"

**Architecture Guardian**:
```
✅ APPROVED

Impact: LOW
Change: Implementation detail within extractor
No boundary violations detected
```

**Test Guardian**:
```
CONTRACT Test Analysis:
✅ test_contract_extract_repositories - Should NOT change
   (Business requirement: returns all repos, not specific count)

IMPLEMENTATION Test Analysis:
⚠️ test_impl_page_size - CAN change
   Update: PAGE_SIZE 100 → 50
   Justification: Performance optimization

Approved if CONTRACT tests still pass.
```

### Example 3: Bug Fix

**Request**: "Fix crash on empty organization"

**Test Guardian**:
```
✅ CORRECT WORKFLOW DETECTED

1. ✓ Add CONTRACT test first (should fail):
   def test_contract_handles_empty_org():
       repos = extractor.extract_repositories("empty-org")
       assert repos == []

2. ✓ Test fails (confirms bug)
3. → Fix implementation
4. → Test passes

Excellent test-first approach!
```

## Benefits

### For You
- ✅ **Peace of mind** - Architecture protected automatically
- ✅ **Clear guidance** - Know exactly what's safe vs risky
- ✅ **Faster decisions** - Guardians provide alternatives
- ✅ **Less refactoring** - Catch issues before they're committed

### For Your Team
- ✅ **Consistent patterns** - Everyone follows same rules
- ✅ **Knowledge preservation** - Architecture decisions enforced
- ✅ **Quality assurance** - Tests remain trustworthy
- ✅ **Onboarding** - New developers learn architecture through Guardians

### For Your Codebase
- ✅ **Maintainable** - Clear boundaries prevent tangling
- ✅ **Testable** - Strong test discipline maintained
- ✅ **Evolvable** - Can change implementation safely
- ✅ **Reliable** - Regressions caught early

## When Guardians Activate

### Architecture Guardian Activates When:
- [ ] Creating new files in extractors/, analyzers/, workflows/, database/
- [ ] Modifying database/schema.sql or migrations/
- [ ] Changing database/storage.py public API
- [ ] Adding to requirements.txt or docker-compose.yml
- [ ] Modifying base classes or interfaces
- [ ] Implementing cross-cutting concerns

### Test Guardian Activates When:
- [ ] Modifying test assertions
- [ ] Changing expected values in tests
- [ ] Removing or skipping tests
- [ ] Modifying mock behavior
- [ ] Test failing after implementation change
- [ ] Adding new features without tests first

## Overriding Guardians

### When Guardian Flags Change
You have three options:

1. **Accept recommendation** (maintains architecture/tests)
   - Guardian provides alternative approach
   - Implement recommended pattern

2. **Proceed as-is** (accept debt)
   - Document reason in PR description
   - Add TODO for future refactoring
   - Get approval in code review

3. **Discuss redesign** (major change)
   - Create ADR document
   - Update architecture docs
   - Update Guardian rules if needed

### When to Override
- ✅ Prototyping (document as tech debt)
- ✅ Performance emergency (document and plan refactor)
- ✅ Architectural evolution (update docs and ADRs)

### When NOT to Override
- ❌ "It's faster this way" - short-term thinking
- ❌ "Tests are annoying" - they caught a real issue
- ❌ "Just to ship quickly" - creates maintenance burden

## Maintenance

### Quarterly Review
- Review flagged changes that were approved "as-is"
- Assess accumulated architectural debt
- Update Guardian rules based on learnings
- Refactor repeated patterns

### When Architecture Evolves
1. Update architecture docs first
2. Create ADR for significant changes
3. Update Guardian rules in [agents/02a-architecture-guardian.md](agents/02a-architecture-guardian.md)
4. Update [.github/copilot-instructions.md](.github/copilot-instructions.md)

### When Test Patterns Change
1. Update test organization in [docs/03-operations/test-organization.md](docs/03-operations/test-organization.md)
2. Update Guardian rules in [agents/04a-test-guardian.md](agents/04a-test-guardian.md)
3. Update [.github/copilot-instructions.md](.github/copilot-instructions.md)
4. Migrate existing tests to new structure

## Quick Reference

### For New Features
1. Write CONTRACT tests first (should fail)
2. Architecture Guardian checks boundaries
3. Implement feature
4. CONTRACT tests pass
5. Add IMPLEMENTATION tests if needed
6. Both Guardians approve

### For Bug Fixes
1. Add regression test first (should fail)
2. Fix implementation
3. Test passes
4. Guardians verify no other tests modified

### For Refactoring
1. All tests pass before starting
2. Refactor implementation
3. All tests still pass (no modifications)
4. Guardians approve - behavior unchanged

### For Optimization
1. CONTRACT tests remain unchanged
2. Update IMPLEMENTATION tests as needed
3. Document performance improvement
4. Guardians approve if contracts pass

## Emergency Bypass

If you absolutely must bypass Guardians (emergency production fix):

1. **Document clearly** in commit message:
   ```
   EMERGENCY FIX: [description]
   
   Guardian bypass reason: [emergency justification]
   Technical debt created: [what needs fixing later]
   Tracking: [issue number]
   ```

2. **Create follow-up issue** immediately
3. **Schedule refactoring** in next sprint
4. **Review in retrospective**

## Success Metrics

Your Guardian system is working when:
- ✅ Zero architectural violations reach main
- ✅ No CONTRACT tests modified without documented requirement change
- ✅ IMPLEMENTATION tests evolve smoothly with code
- ✅ Code reviews focus on logic, not structure
- ✅ New developers understand boundaries clearly
- ✅ Refactoring is confident and safe

## Support

### Need Help?
- Read detailed docs: [agents/02a-architecture-guardian.md](agents/02a-architecture-guardian.md)
- Read test guide: [docs/03-operations/test-organization.md](docs/03-operations/test-organization.md)
- Review examples in [agents/04a-test-guardian.md](agents/04a-test-guardian.md)

### Improving Guardians
- Found a false positive? Update Guardian rules
- New pattern emerged? Document in architecture
- Better way to organize? Update docs and rules

## Remember

**Guardians exist to enable speed, not prevent progress.**

Clear rules + automated validation = confident, rapid development

Fast iteration within architectural boundaries is the goal.
