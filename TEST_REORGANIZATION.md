# Test Organization Change - Integration Tests Now CONTRACT Tests

**Date:** January 24, 2026
**Branch:** `feature/integration-tests`
**Commit:** 026dd05

## Change Summary

Moved integration tests from `tests/integration/` to `tests/contract/integration/` to ensure they receive proper Test Guardian protection.

## Why This Change?

### Problem Identified
Integration tests were placed in `tests/integration/` but they validate **business requirements**, not implementation details:
- ✅ Data MUST reach PostgreSQL correctly (business requirement)
- ✅ Enrichment MUST populate specific fields (business requirement)
- ✅ Timestamps MUST be UTC-aware (business requirement)
- ✅ Foreign keys MUST be enforced (data integrity requirement)

These are CONTRACT tests, not IMPLEMENTATION tests.

### Solution Implemented
Moved tests to `tests/contract/integration/` to:
1. **Get Test Guardian protection** - Changes to these tests now require documented business requirement changes
2. **Clarify intent** - Location makes it clear these are contract tests
3. **Enforce discipline** - Cannot "fix tests to match broken implementation"

## Test Guardian Protection

### Before (tests/integration/)
- ⚠️ No automatic Test Guardian recognition
- ⚠️ Could modify test assertions without review
- ⚠️ Risk of "fixing tests to match implementation"

### After (tests/contract/integration/)
- ✅ Automatic Test Guardian protection
- ✅ Test assertion changes flagged for review
- ✅ Must document business requirement changes
- ✅ Protected from weakening or deletion

## What This Means

### For Test Modifications

If you need to change an integration test assertion:

**❌ NOT ALLOWED without justification:**
```python
# tests/contract/integration/test_github_extraction_e2e.py
- assert repo.created_at is not None
+ assert repo.created_at is not None or repo.created_at == ""  # Relaxing constraint
```

**Test Guardian will flag:** "CONTRACT TEST MODIFICATION - Why did business requirement change?"

**✅ MUST provide:**
- Documented business requirement change
- ADR if architectural decision involved
- Stakeholder approval for contract change

### For New Tests

When adding new integration tests:

1. Place in `tests/contract/integration/`
2. Use CONTRACT docstring pattern
3. Validate business requirements, not implementation
4. Follow test-first approach (write test before implementation)

## File Moves

| Old Path | New Path |
|----------|----------|
| `tests/integration/__init__.py` | `tests/contract/integration/__init__.py` |
| `tests/integration/conftest.py` | `tests/contract/integration/conftest.py` |
| `tests/integration/test_github_extraction_e2e.py` | `tests/contract/integration/test_github_extraction_e2e.py` |
| `tests/integration/test_dependency_enrichment_e2e.py` | `tests/contract/integration/test_dependency_enrichment_e2e.py` |
| `tests/integration/README.md` | `tests/contract/integration/README.md` |

## Updated Commands

All pytest commands now use the new path:

```bash
# Run all integration tests
pytest tests/contract/integration/ -v

# Run without live APIs
pytest tests/contract/integration/ -m "not live_api" -v

# Run specific test
pytest tests/contract/integration/test_github_extraction_e2e.py -v
```

## Documentation Updated

- ✅ [Integration Test README](../tests/contract/integration/README.md) - Added Test Guardian note
- ✅ [Integration Test Design](../docs/04-implementation/integration-test-design.md) - Updated all paths
- ✅ [Integration Test Setup](../docs/04-implementation/integration-test-setup.md) - Updated all commands
- ✅ [Session Summary](../INTEGRATION_TEST_SESSION_SUMMARY.md) - Updated all references
- ✅ [Test Guardian Agent](../agents/04a-test-guardian.md) - Explicitly includes integration tests
- ✅ [PROGRESS.md](../PROGRESS.md) - Updated session notes

## Test Structure Now

```
tests/
├── contract/                    ← CONTRACT tests (strict protection)
│   ├── integration/            ← Integration tests (E2E business requirements)
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_github_extraction_e2e.py
│   │   ├── test_dependency_enrichment_e2e.py
│   │   └── README.md
│   ├── test_dependency_enrichment.py  ← Unit contract tests
│   └── test_workflow_enrichment_integration.py
├── implementation/              ← IMPLEMENTATION tests (flexible)
│   └── (future technical tests)
└── (other test files)
```

## Benefits

1. **Clarity** - Location immediately indicates test type
2. **Protection** - Test Guardian prevents casual modification
3. **Discipline** - Enforces test-first approach
4. **Documentation** - Contract changes require documentation
5. **Confidence** - Business requirements protected from drift

## Next Steps

When running tests, use the new path:

```bash
# Set up test database
export TEST_DATABASE_URL="postgresql://postgres:password@localhost/analyzer_test"

# Run integration tests
pytest tests/contract/integration/ -m "not live_api" -v
```

## References

- [Test Guardian Agent](../agents/04a-test-guardian.md) - Protection rules
- [Test Organization Guide](../docs/03-operations/test-organization.md) - CONTRACT vs IMPLEMENTATION
- [Integration Test README](../tests/contract/integration/README.md) - Test documentation

---

**Key Takeaway:** Integration tests are now CONTRACT tests with strict Test Guardian protection, ensuring business requirements remain stable and well-documented.
