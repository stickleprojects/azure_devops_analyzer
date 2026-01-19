#!/usr/bin/env python3
"""
Setup script to install git hooks for Python code validation.

This script installs pre-commit and post-commit hooks that automatically
validate Python code before commits.

Usage:
    python scripts/setup_git_hooks.py
    python scripts/setup_git_hooks.py --uninstall
"""

import os
import sys
import argparse
import stat
from pathlib import Path


def get_git_hooks_dir():
    """Get the .git/hooks directory."""
    git_dir = Path.cwd() / ".git" / "hooks"
    return git_dir


def is_windows():
    """Check if running on Windows."""
    return sys.platform.startswith("win")


def install_hooks():
    """Install git hooks."""
    hooks_dir = get_git_hooks_dir()
    
    if not hooks_dir.exists():
        print(f"Error: Git hooks directory not found: {hooks_dir}")
        print("Make sure you're in the root of a git repository.")
        return False
    
    # Determine hook extension based on OS
    if is_windows():
        pre_commit_src = Path("scripts/hooks/pre-commit.ps1")
        post_commit_src = Path("scripts/hooks/post-commit.ps1")
    else:
        pre_commit_src = Path(".git/hooks/pre-commit")
        post_commit_src = Path(".git/hooks/post-commit")
    
    hooks_to_install = [
        (pre_commit_src, hooks_dir / "pre-commit"),
        (post_commit_src, hooks_dir / "post-commit"),
    ]
    
    print("Installing git hooks...")
    success = True
    
    for src, dst in hooks_to_install:
        if not src.exists():
            print(f"⚠  Source not found: {src}")
            continue
        
        try:
            # Copy hook
            dst.write_text(src.read_text())
            
            # Make executable (Unix)
            if not is_windows():
                st = dst.stat()
                dst.chmod(st.st_mode | stat.S_IEXEC)
            
            print(f"✓ Installed {dst.name}")
        except Exception as e:
            print(f"✗ Failed to install {dst.name}: {e}")
            success = False
    
    return success


def uninstall_hooks():
    """Uninstall git hooks."""
    hooks_dir = get_git_hooks_dir()
    
    if not hooks_dir.exists():
        print(f"Error: Git hooks directory not found: {hooks_dir}")
        return False
    
    hooks_to_remove = [
        hooks_dir / "pre-commit",
        hooks_dir / "post-commit",
    ]
    
    print("Uninstalling git hooks...")
    success = True
    
    for hook in hooks_to_remove:
        if hook.exists():
            try:
                hook.unlink()
                print(f"✓ Removed {hook.name}")
            except Exception as e:
                print(f"✗ Failed to remove {hook.name}: {e}")
                success = False
        else:
            print(f"- {hook.name} not installed")
    
    return success


def verify_hooks():
    """Verify hooks are installed and executable."""
    hooks_dir = get_git_hooks_dir()
    
    if not hooks_dir.exists():
        print(f"Error: Git hooks directory not found: {hooks_dir}")
        return False
    
    hooks = [
        hooks_dir / "pre-commit",
        hooks_dir / "post-commit",
    ]
    
    print("\nVerifying git hooks...")
    all_good = True
    
    for hook in hooks:
        if not hook.exists():
            print(f"✗ {hook.name} not installed")
            all_good = False
        elif is_windows() or (hook.stat().st_mode & stat.S_IEXEC):
            print(f"✓ {hook.name} installed and executable")
        else:
            print(f"⚠ {hook.name} not executable")
            all_good = False
    
    return all_good


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Setup git hooks for Python code validation",
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Uninstall git hooks",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify git hooks are installed",
    )
    
    args = parser.parse_args()
    
    if args.uninstall:
        success = uninstall_hooks()
    elif args.verify:
        success = verify_hooks()
    else:
        success = install_hooks()
        if success:
            print("\n✓ Git hooks installed successfully!")
            print("  Python code will be validated before each commit.")
            print("  To bypass: git commit --no-verify")
            verify_hooks()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
