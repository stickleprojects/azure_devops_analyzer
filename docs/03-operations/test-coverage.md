# Test Coverage Report

## Quick Start

### Run Coverage Analysis
```bash
# Run all tests with coverage
./scripts/run_coverage.sh

# Or use pytest directly
python -m pytest --cov=src --cov-report=html --cov-report=term-missing

# View HTML report
xdg-open htmlcov/index.html
```

## Current Coverage Status

**Overall Coverage: 29.75%**

Date: January 23, 2026  
Tests Passed: 31/34 (3 skipped - require GITHUB_TOKEN)

### Coverage by Component

#### Well Covered (>80%)
- `src/config/github.py` - **88.57%** ✅
- `src/database/models/repository.py` - **98.39%** ✅
- `src/database/models/service.py` - **96.15%** ✅

#### Needs Improvement (30-50%)
- `src/extractors/base.py` - **49.16%** ⚠️
- `src/analyzers/parsers/base.py` - **48.00%** ⚠️
- `src/database/connection.py` - **35.14%** ⚠️
- `src/extractors/github/client.py` - **30.00%** ⚠️

#### Low Coverage (<30%)
- `src/extractors/github/extractor.py` - **27.34%** 🔴
- `src/analyzers/dependency_analyzer.py` - **25.00%** 🔴
- `src/analyzers/parsers/*.py` - **7-17%** 🔴
- `src/workflows/github_analysis.py` - **16.40%** 🔴
- `src/database/storage.py` - **10.18%** 🔴

#### Not Covered (0%)
- `src/analyzers/contributor_analyzer.py` - **0.00%** 🔴
- `src/extractors/azure_devops/*` - **0.00%** 🔴
- `src/scheduler/*` - **0.00%** 🔴

## Coverage Configuration

### Files
- **`.coveragerc`** - Coverage tool configuration
- **`pyproject.toml`** - Pytest and coverage integration settings
- **`htmlcov/`** - HTML coverage reports (gitignored)
- **`coverage.xml`** - XML coverage for CI/CD tools

### Coverage Settings
- **Branch coverage**: Enabled (tests both True/False paths)
- **Minimum coverage**: 70% (currently failing)
- **Source directory**: `src/`
- **Omitted**: tests, migrations, pycache, venv

## Recommendations for Improving Coverage

### Priority 1: Core Business Logic (High Impact)
These components are critical and need comprehensive tests:

1. **`src/database/storage.py`** (10.18%)
   - Add tests for CRUD operations
   - Test error handling for DB failures
   - Test transaction handling

2. **`src/extractors/github/extractor.py`** (27.34%)
   - Mock GitHub API responses
   - Test data extraction and transformation
   - Test error handling and rate limiting

3. **`src/workflows/github_analysis.py`** (16.40%)
   - Test complete workflow orchestration
   - Test data flow between components
   - Test error recovery

### Priority 2: Analyzers (Medium Impact)
Analyzer modules have low coverage:

1. **`src/analyzers/contributor_analyzer.py`** (0.00%)
   - Test contribution metrics calculation
   - Test data aggregation

2. **`src/analyzers/dependency_analyzer.py`** (25.00%)
   - Test dependency parsing
   - Test security vulnerability detection

3. **Language Parsers** (7-17%)
   - Create sample files for each language
   - Test dependency extraction
   - Test version detection

### Priority 3: Infrastructure (Lower Impact but Important)
1. **Scheduler/Celery** (0.00%)
   - Add integration tests for task execution
   - Test task retry logic
   - Test task scheduling

2. **Azure DevOps Extractor** (0.00%)
   - Mirror GitHub extractor test patterns
   - Add integration tests with mocked API

## Testing Best Practices

### Writing Effective Tests

1. **Follow the Test Guardian Principles**
   - Write CONTRACT tests for business requirements
   - Write IMPLEMENTATION tests for technical details
   - See [agents/04a-test-guardian.md](../agents/04a-test-guardian.md)

2. **Test Structure**
   ```python
   def test_feature_name():
       """CONTRACT: Business requirement description."""
       # Arrange - Set up test data
       # Act - Execute the code
       # Assert - Verify expectations
   ```

3. **Use Mocking for External Dependencies**
   ```python
   import pytest
   from unittest.mock import Mock, patch
   
   @patch('src.extractors.github.client.Github')
   def test_github_api(mock_github):
       # Mock API responses
       mock_github.return_value.get_repo.return_value = Mock(...)
   ```

4. **Test Edge Cases**
   - Empty inputs
   - Invalid data
   - Network failures
   - Rate limiting
   - Large datasets

### Running Specific Tests

```bash
# Run tests for specific module
pytest tests/test_github_config.py -v

# Run with coverage for specific source file
pytest --cov=src/config/github.py --cov-report=term-missing

# Run only fast tests (skip integration tests)
pytest -m "not slow" --cov=src

# Run with verbose output and show local variables
pytest -vl --cov=src
```

## CI/CD Integration

### GitHub Actions Example
```yaml
- name: Run tests with coverage
  run: |
    pytest --cov=src --cov-report=xml --cov-report=term
    
- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

### Coverage Badges
After integrating with Codecov or similar service:
```markdown
![Coverage](https://img.shields.io/codecov/c/github/stickleprojects/azure_devops_analyzer)
```

## Viewing Coverage Reports

### HTML Report (Recommended)
```bash
xdg-open htmlcov/index.html
```
- Interactive browsing
- Line-by-line coverage highlighting
- Branch coverage visualization
- Missing line numbers

### Terminal Report
```bash
python -m coverage report --show-missing
```
- Quick overview
- Shows missing line numbers
- Good for CI/CD pipelines

### XML Report
```bash
# Generated automatically at coverage.xml
# Used by CI/CD tools like Jenkins, GitLab CI, etc.
```

## Troubleshooting

### Coverage Not Measuring Correctly
1. Check that `src/` is in the coverage source path
2. Verify `.coveragerc` or `pyproject.toml` settings
3. Ensure tests are actually importing and running the code

### Tests Passing But Low Coverage
- Tests may only hit happy paths
- Add tests for error conditions
- Add tests for edge cases
- Check branch coverage (if/else paths)

### Coverage Tool Not Found
```bash
pip install pytest-cov coverage
```

## Next Steps

1. **Immediate** (This Week)
   - Add tests for `src/database/storage.py` to reach 50% coverage
   - Add basic tests for GitHub extractor
   - Document test patterns in `tests/README.md`

2. **Short Term** (This Month)
   - Reach 50% overall coverage
   - Add CI/CD coverage reporting
   - Set up coverage trending

3. **Long Term** (Next Quarter)
   - Reach 70% overall coverage
   - Add integration test suite
   - Implement test-driven development (TDD) for new features

## Related Documentation

- [Test Guardian Guide](../agents/04a-test-guardian.md) - Test modification rules
- [Test Organization](./test-organization.md) - Contract vs Implementation tests
- [Testing Strategy](../agents/04-testing.md) - Overall testing approach
