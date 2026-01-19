# Git Hooks Setup Guide

Automatic Python code validation on every commit using git hooks.

## Overview

Git hooks are scripts that run automatically at specific points in the git workflow. This project includes **pre-commit hooks** that validate Python code before commits are allowed.

## What Gets Validated

Before each commit, the hook automatically:

1. ✅ Checks Python syntax for all changed files
2. ✅ Runs import structure tests
3. ✅ Detects common issues (non-existent imports, wrong paths)
4. ⛔ Blocks commits if validation fails

## Quick Start

### Windows (PowerShell)

```powershell
# Install hooks
.\scripts\setup_git_hooks.ps1

# Verify installation
.\scripts\setup_git_hooks.ps1 -Verify

# Uninstall if needed
.\scripts\setup_git_hooks.ps1 -Uninstall
```

### macOS / Linux (Bash)

```bash
# Install hooks
python scripts/setup_git_hooks.py

# Verify installation
python scripts/setup_git_hooks.py --verify

# Uninstall if needed
python scripts/setup_git_hooks.py --uninstall
```

## How It Works

### When You Commit

```bash
$ git commit -m "Fix imports in tasks.py"

=== Pre-commit Python Validation ===

Checking Python files:
  - src/scheduler/tasks.py

[1/3] Validating Python syntax...
✓ src/scheduler/tasks.py

[2/3] Running import structure tests...
✓ All import tests passed

[3/3] Checking for common Python issues...
✓ No common issues detected

=== Pre-commit Check Summary ===
✓ All checks passed! Proceeding with commit.

[main 3c4a2f1] Fix imports in tasks.py
 1 file changed, 5 insertions(+)
```

### If Validation Fails

```bash
$ git commit -m "Add new feature"

=== Pre-commit Python Validation ===

[1/3] Validating Python syntax...
✗ Syntax error in src/scheduler/tasks.py

=== Pre-commit Check Summary ===
✗ 1 error(s) found. Commit aborted.

To bypass this check, use: git commit --no-verify
```

## Hook Details

### Pre-commit Hook (`.git/hooks/pre-commit`)

**Triggered**: Before every commit  
**Actions**:

1. Finds all Python files in the commit
2. Validates syntax using `python -m py_compile`
3. Runs unit tests from `tests/test_imports_and_structure.py`
4. Checks for known issues (bad imports, circular dependencies)
5. Aborts commit if any checks fail

### Post-commit Hook (`.git/hooks/post-commit`)

**Triggered**: After successful commit  
**Actions**:

1. Lists modified Python files
2. Provides helpful tips for running full test suite
3. Non-blocking (doesn't prevent commit)

## Bypassing Hooks

If you need to commit despite validation failures:

```bash
git commit --no-verify
```

⚠️ Use sparingly - hooks are there to maintain code quality!

## Manual Testing

You can also run validations manually without committing:

### Run All Tests

```bash
pytest tests/test_imports_and_structure.py -v
```

### Check Syntax Only

```bash
python -m py_compile src/scheduler/tasks.py
python -m py_compile src/scheduler/celery_app.py
python -m py_compile scripts/submit_extraction_task.py
```

### Verify Specific Files

```bash
# Check for common issues
grep -n "from tasks\." src/scheduler/tasks.py
grep -n "from scheduler\.celery_app" src/scheduler/tasks.py
```

## Requirements

### For Hook Execution

- Python 3.8+ (for syntax checking)
- git

### For Full Test Suite

- pytest (install with: `pip install pytest`)

If pytest isn't installed, hooks will skip unit tests but still perform syntax checks.

## Troubleshooting

### Hooks Not Running

**Check if hooks are installed:**

```bash
# Windows
.\scripts\setup_git_hooks.ps1 -Verify

# Unix
python scripts/setup_git_hooks.py --verify
```

**Reinstall hooks:**

```bash
# Windows
.\scripts\setup_git_hooks.ps1

# Unix
python scripts/setup_git_hooks.py
```

### Permission Denied Error (Unix)

```bash
# Make hooks executable
chmod +x .git/hooks/pre-commit
chmod +x .git/hooks/post-commit
```

### Tests Not Running

Ensure pytest is installed:

```bash
pip install pytest
```

The hooks will still work without pytest (syntax checks run regardless).

## Configuration

### Skip Tests on Commit

If you want to skip expensive tests during commit but still validate syntax:

```bash
# Windows PowerShell
.\.git\hooks\pre-commit -SkipTests

# Or use --no-verify to skip all hooks
git commit --no-verify
```

### Custom Validation

To add additional validation:

1. Edit `.git/hooks/pre-commit`
2. Add your checks before the final summary
3. Increment the `ERRORS` counter if validation fails

## Integration with CI/CD

These hooks complement CI/CD pipelines:

- **Local hooks**: Catch issues immediately during development
- **CI/CD**: Provides comprehensive testing before merge

Both should run - hooks for fast feedback, CI for comprehensive testing.

## Hook Files

- `.git/hooks/pre-commit` - Main validation hook (bash version)
- `scripts/hooks/pre-commit.ps1` - PowerShell version for Windows
- `.git/hooks/post-commit` - Post-commit feedback hook
- `scripts/setup_git_hooks.py` - Python setup script (Unix/macOS)
- `scripts/setup_git_hooks.ps1` - PowerShell setup script (Windows)

## Best Practices

1. **Always let hooks run** - They catch real issues
2. **Fix issues before committing** - Don't use `--no-verify` as a habit
3. **Install for all team members** - Consistency across the team
4. **Review hook output** - Understand what's being validated
5. **Update hooks as needed** - Add checks for new patterns/issues

## See Also

- [PYTHON_VERIFICATION.md](PYTHON_VERIFICATION.md) - Detailed testing guide
- [tests/test_imports_and_structure.py](tests/test_imports_and_structure.py) - Available tests
