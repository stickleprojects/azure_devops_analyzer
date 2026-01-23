# Test Organization Strategy

## Overview

We distinguish between two types of tests with different purposes and different rules for modification:

1. **Contract Tests** - Define WHAT the system should do (business requirements)
2. **Implementation Tests** - Define HOW the system does it (technical details)

## Test Type Definitions

### Contract Tests (Business/Behavioral)
**Purpose**: Validate business requirements and user-facing behavior

**Characteristics**:
- Define the external contract/API
- Should rarely change (only when requirements change)
- Platform-agnostic where possible
- Focus on outcomes, not mechanisms
- Protected by strict Test Guardian rules

**Examples**:
```python
# What: When I request repositories, I get repositories
def test_contract_extract_repositories_returns_list():
    """CONTRACT: extract_repositories must return a list of repository objects"""
    repos = extractor.extract_repositories("org-name")
    assert isinstance(repos, list)
    assert all(isinstance(r, Repository) for r in repos)

# What: Repository objects have required fields
def test_contract_repository_has_required_fields():
    """CONTRACT: Repository must have name, url, language"""
    repo = extractor.extract_repositories("org")[0]
    assert hasattr(repo, 'name')
    assert hasattr(repo, 'url')
    assert hasattr(repo, 'primary_language')

# What: Empty organizations return empty list (not error)
def test_contract_empty_organization_returns_empty_list():
    """CONTRACT: Empty org should return [] not raise exception"""
    repos = extractor.extract_repositories("empty-org")
    assert repos == []
```

### Implementation Tests (Technical/Internal)
**Purpose**: Validate implementation details and technical constraints

**Characteristics**:
- Test internal mechanisms
- Can change as implementation evolves
- Platform-specific optimizations
- Focus on "how" not "what"
- More flexible Test Guardian rules

**Examples**:
```python
# How: GitHub pagination is handled correctly
def test_impl_handles_github_pagination():
    """IMPLEMENTATION: GitHub API pagination with 100 items per page"""
    # This can change if we switch pagination strategy
    with mock_paginated_response(pages=3):
        repos = extractor.extract_repositories("large-org")
        assert len(repos) == 300  # Implementation detail

# How: Rate limiting triggers retry
def test_impl_retries_on_rate_limit():
    """IMPLEMENTATION: Rate limit triggers exponential backoff"""
    # This can change if we change retry strategy
    with mock_rate_limit_then_success():
        result = extractor._make_request("/repos")
        assert result is not None
        assert mock.call_count == 2  # Retried once

# How: Caching reduces API calls
def test_impl_caching_reduces_api_calls():
    """IMPLEMENTATION: Cache prevents duplicate API calls within 5 minutes"""
    # This can change if we change caching strategy
    extractor.get_repository("org/repo")
    extractor.get_repository("org/repo")
    assert api_mock.call_count == 1  # Second call cached
```

## Directory Structure

```
tests/
├── contract/                    # Contract tests - STRICT protection
│   ├── __init__.py
│   ├── test_github_contract.py      # GitHub contract tests
│   ├── test_azure_devops_contract.py
│   ├── test_analyzer_contract.py
│   └── test_workflow_contract.py
│
├── implementation/              # Implementation tests - FLEXIBLE
│   ├── __init__.py
│   ├── github/
│   │   ├── test_github_pagination.py
│   │   ├── test_github_rate_limiting.py
│   │   └── test_github_auth.py
│   ├── azure_devops/
│   │   ├── test_azure_pagination.py
│   │   └── test_azure_auth.py
│   └── database/
│       ├── test_connection_pooling.py
│       └── test_transaction_handling.py
│
├── integration/                 # End-to-end tests
│   ├── __init__.py
│   ├── test_full_extraction_workflow.py
│   └── test_database_integration.py
│
└── fixtures/                    # Shared test data
    ├── __init__.py
    ├── github_responses.py
    └── sample_repositories.py
```

## Naming Conventions

### Contract Test Naming
```python
# Pattern: test_contract_{component}_{behavior}
def test_contract_extract_repositories_returns_list(): ...
def test_contract_analyzer_handles_empty_input(): ...
def test_contract_storage_prevents_duplicate_repos(): ...
```

### Implementation Test Naming
```python
# Pattern: test_impl_{component}_{mechanism}
def test_impl_github_handles_pagination(): ...
def test_impl_rate_limit_backoff_strategy(): ...
def test_impl_connection_pool_reuse(): ...
```

### Docstring Convention
```python
def test_contract_something():
    """CONTRACT: Clear statement of business requirement"""
    
def test_impl_something():
    """IMPLEMENTATION: Description of technical mechanism being tested"""
```

## Test Guardian Rules by Type

### Contract Tests - STRICT Protection

**Changes Require**:
- ✋ **STOP** - Documented requirement change from stakeholder
- ✋ **STOP** - ADR explaining behavior change
- ✋ **STOP** - Update to all related contract tests

**Forbidden**:
- ❌ Changing assertions to match new implementation
- ❌ Relaxing constraints
- ❌ Removing test cases
- ❌ Making tests more permissive

**Guardian Response**:
```
🛑 CONTRACT TEST MODIFICATION BLOCKED

Test: test_contract_extract_repositories_returns_list
Type: CONTRACT TEST (business requirement)
Change: Modified expected return type

CONTRACT TESTS DEFINE BUSINESS REQUIREMENTS.
Changes require:
1. Documented requirement change
2. Stakeholder approval
3. ADR if architectural impact
4. Update all dependent contract tests

Is this a genuine requirement change? If not, fix implementation.
```

### Implementation Tests - FLEXIBLE

**Changes Allowed**:
- ✅ Updating for new implementation strategy
- ✅ Changing technical details (pagination size, retry count, etc.)
- ✅ Optimizing performance characteristics
- ✅ Refactoring test structure

**Still Require Justification**:
- ⚠️ Removing tests (why no longer needed?)
- ⚠️ Weakening error handling (still robust?)
- ⚠️ Reducing coverage (acceptable trade-off?)

**Guardian Response**:
```
⚠️ IMPLEMENTATION TEST MODIFICATION

Test: test_impl_github_handles_pagination
Type: IMPLEMENTATION TEST (technical detail)
Change: Modified page size from 100 to 50

IMPLEMENTATION TESTS can change with implementation.
Validation:
✓ Contract tests still pass (behavior unchanged)
✓ Technical change documented in commit message
⚠ Performance impact considered

Approved - implementation detail change allowed.
```

## Decision Tree: Contract vs Implementation

```
Is this test validating a business requirement or user-facing behavior?
│
├─ YES → CONTRACT TEST
│   └─ Place in tests/contract/
│       Use strict protection rules
│
└─ NO → Is it testing internal mechanisms or technical details?
    │
    ├─ YES → IMPLEMENTATION TEST
    │   └─ Place in tests/implementation/
    │       Use flexible protection rules
    │
    └─ UNCLEAR → Default to CONTRACT TEST
        └─ Better to be too strict than too loose
```

## Examples by Component

### GitHub Extractor

**Contract Tests** (`tests/contract/test_github_contract.py`):
```python
def test_contract_extract_repositories_returns_valid_repos():
    """CONTRACT: Must return Repository objects with required fields"""
    
def test_contract_handles_invalid_organization():
    """CONTRACT: Invalid org returns empty list, not exception"""
    
def test_contract_repository_data_completeness():
    """CONTRACT: Repository has name, url, description, language"""
```

**Implementation Tests** (`tests/implementation/github/test_github_pagination.py`):
```python
def test_impl_pagination_handles_100_per_page():
    """IMPLEMENTATION: GitHub API pagination with 100 items per page"""
    
def test_impl_pagination_stops_at_last_page():
    """IMPLEMENTATION: Pagination correctly detects last page"""
```

### Repository Analyzer

**Contract Tests** (`tests/contract/test_analyzer_contract.py`):
```python
def test_contract_analyzer_returns_language_distribution():
    """CONTRACT: analyze_languages returns dict of language percentages"""
    
def test_contract_empty_repo_returns_empty_analysis():
    """CONTRACT: Empty repository returns valid empty analysis structure"""
```

**Implementation Tests** (`tests/implementation/analyzer/test_language_detection.py`):
```python
def test_impl_uses_file_extensions_for_detection():
    """IMPLEMENTATION: Language detection uses file extension mapping"""
    
def test_impl_caches_language_analysis():
    """IMPLEMENTATION: Analysis results cached for 1 hour"""
```

### Database Storage

**Contract Tests** (`tests/contract/test_storage_contract.py`):
```python
def test_contract_save_repository_persists_data():
    """CONTRACT: Saved repository can be retrieved"""
    
def test_contract_duplicate_save_updates_not_errors():
    """CONTRACT: Saving same repo twice updates, doesn't error"""
```

**Implementation Tests** (`tests/implementation/database/test_transaction_handling.py`):
```python
def test_impl_uses_transaction_for_batch_insert():
    """IMPLEMENTATION: Batch insert uses single transaction"""
    
def test_impl_rollback_on_constraint_violation():
    """IMPLEMENTATION: Transaction rolls back on unique constraint violation"""
```

## Migration Strategy

### For Existing Tests

1. **Review each test and categorize**:
   ```python
   # Current
   def test_extract_repositories():
       ...
   
   # Categorized
   def test_contract_extract_repositories_returns_list():
       """CONTRACT: Returns list of Repository objects"""
       ...
   ```

2. **Move to appropriate directory**:
   - Contract → `tests/contract/`
   - Implementation → `tests/implementation/`

3. **Update imports and pytest configuration**:
   ```python
   # pytest.ini or pyproject.toml
   [tool.pytest.ini_options]
   markers = [
       "contract: Contract tests (strict protection)",
       "implementation: Implementation tests (flexible)",
   ]
   ```

4. **Add markers**:
   ```python
   @pytest.mark.contract
   def test_contract_something(): ...
   
   @pytest.mark.implementation
   def test_impl_something(): ...
   ```

## CI/CD Integration

### Separate Test Runs
```yaml
# .github/workflows/test.yml
jobs:
  contract-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Run Contract Tests
        run: pytest tests/contract/ -v
      # Contract test failures BLOCK merges
  
  implementation-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Run Implementation Tests
        run: pytest tests/implementation/ -v
      # Implementation failures are warnings, not blockers
```

### Coverage Requirements
```yaml
# Different coverage thresholds
contract-tests:
  minimum-coverage: 95%  # Very high bar
  
implementation-tests:
  minimum-coverage: 70%  # More flexible
```

## Best Practices

### When Writing New Tests

**Ask yourself**: 
> "If the implementation changes completely but behavior stays the same, should this test still pass?"

- **YES** → Contract test
- **NO** → Implementation test

### Contract Test Guidelines

1. **Test behavior, not implementation**:
   ```python
   # ✅ GOOD - Tests behavior
   def test_contract_extract_returns_repositories():
       repos = extract()
       assert all(has_required_fields(r) for r in repos)
   
   # ❌ BAD - Tests implementation
   def test_uses_github_api_v3():
       assert extractor.api_version == "v3"
   ```

2. **Platform-agnostic when possible**:
   ```python
   # ✅ GOOD - Could work with any platform
   def test_contract_extractor_handles_auth_failure():
       with invalid_credentials():
           with pytest.raises(AuthenticationError):
               extract()
   
   # ❌ BAD - GitHub-specific
   def test_github_returns_401_on_bad_token():
       ...
   ```

### Implementation Test Guidelines

1. **Be explicit about what's being tested**:
   ```python
   def test_impl_uses_connection_pool():
       """IMPLEMENTATION: Uses connection pool to reduce overhead
       
       This test validates our connection pooling optimization.
       If we change connection strategy, this test should be updated.
       """
   ```

2. **Document acceptable ranges**:
   ```python
   def test_impl_pagination_page_size():
       """IMPLEMENTATION: Uses 100 items per page for optimal performance
       
       This value is a performance optimization and can be tuned.
       Acceptable range: 50-200 depending on API response times.
       """
       assert extractor.page_size == 100
   ```

## Guardian Integration

The Test Guardian will:

1. **Detect test type** from directory or naming:
   - `tests/contract/` → Apply STRICT rules
   - `tests/implementation/` → Apply FLEXIBLE rules
   - `test_contract_*` → STRICT
   - `test_impl_*` → FLEXIBLE

2. **Apply appropriate protection level**:
   - Contract tests require detailed justification
   - Implementation tests allowed with explanation

3. **Enforce test-first for contracts**:
   - New features must have contract tests FIRST
   - Implementation tests can be added during or after

## Benefits

1. **Clarity**: Developers immediately know test purpose
2. **Flexibility**: Implementation can evolve without test churn
3. **Protection**: Business requirements strictly protected
4. **Efficiency**: Less time arguing about test modifications
5. **Documentation**: Tests serve as living documentation of "what" vs "how"

## Summary

| Aspect              | Contract Tests               | Implementation Tests       |
| ------------------- | ---------------------------- | -------------------------- |
| **Purpose**         | Define business requirements | Validate technical details |
| **Location**        | `tests/contract/`            | `tests/implementation/`    |
| **Naming**          | `test_contract_*`            | `test_impl_*`              |
| **Protection**      | STRICT - rarely change       | FLEXIBLE - can evolve      |
| **Changes require** | Requirement docs + ADR       | Justification in commit    |
| **Focus**           | WHAT (behavior)              | HOW (mechanism)            |
| **Platform**        | Agnostic when possible       | Platform-specific OK       |
| **Guardian**        | Blocks modifications         | Allows with explanation    |
| **CI/CD**           | Must pass to merge           | Can warn without blocking  |

This organization provides clarity and flexibility while maintaining appropriate protection for critical business logic.
