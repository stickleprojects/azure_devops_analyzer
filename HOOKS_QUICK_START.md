# Git Hooks Installation Summary

Quick reference for setting up automatic Python validation on commit.

## Installation

### Windows

```powershell
.\scripts\setup_git_hooks.ps1
```

### macOS / Linux

```bash
python scripts/setup_git_hooks.py
```

## What Gets Checked Automatically

✅ Python syntax validation  
✅ Import path correctness  
✅ Circular import detection  
✅ Unit test execution (if pytest installed)  
✅ Common code issues

## Disable a Check

```bash
git commit --no-verify
```

## Verify Installation

### Windows

```powershell
.\scripts\setup_git_hooks.ps1 -Verify
```

### macOS / Linux

```bash
python scripts/setup_git_hooks.py --verify
```

## Manual Testing (Without Commit)

```bash
# Run unit tests
pytest tests/test_imports_and_structure.py -v

# Validate syntax
python -m py_compile src/scheduler/tasks.py
python -m py_compile src/scheduler/celery_app.py
python -m py_compile scripts/submit_extraction_task.py
```

## Uninstall

### Windows

```powershell
.\scripts\setup_git_hooks.ps1 -Uninstall
```

### macOS / Linux

```bash
python scripts/setup_git_hooks.py --uninstall
```

---

See [GIT_HOOKS_SETUP.md](GIT_HOOKS_SETUP.md) for detailed documentation.
