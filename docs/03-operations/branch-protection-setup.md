# Branch Protection Setup Guide

## Overview

This guide explains how to protect the main branch to ensure all merges go through pull requests with required reviews.

## What Gets Protected

When branch protection is enabled on `main`:

✅ **All PRs require**:
- At least 1 approval before merge
- Stale reviews are dismissed when new commits are pushed
- Status checks must pass

✅ **Prevented actions**:
- Force pushes to main (even admins)
- Direct deletion of main branch
- Merging without approvals

✅ **Enforced for**:
- All users (including repository administrators)

## Quick Setup (Using GitHub CLI)

### Prerequisites
1. **GitHub CLI installed**: https://cli.github.com
2. **Authenticated with GitHub**:
   ```bash
   gh auth login
   ```

### Apply Protection

Run the setup script:

```bash
bash scripts/setup-branch-protection.sh
```

**Output** (example):
```
✅ Branch protection rules applied:
   • Require pull request reviews (1 approval minimum)
   • Dismiss stale reviews
   • Enforce for administrators
   • Force pushes disabled
   • Branch deletion disabled

🔒 Main branch is now protected!
```

## Manual Setup (Via GitHub Web UI)

If you prefer to set this up manually:

1. Go to: `https://github.com/stickleprojects/azure_devops_analyzer/settings/branches`
2. Click **"Add rule"** (or edit existing `main` rule)
3. Enter branch name pattern: `main`
4. Enable these settings:
   - ✅ **Require a pull request before merging**
   - ✅ **Dismiss stale pull request approvals when new commits are pushed**
   - ✅ **Require approval of reviews before merging** (1 required)
   - ✅ **Require status checks to pass before merging**
   - ✅ **Include administrators** (enforce for all users)
5. Disable these:
   - ☐ Allow force pushes
   - ☐ Allow deletions
6. Click **"Create"** or **"Save changes"**

## Verification

After setup, verify the protection is active:

```bash
# Using GitHub CLI
gh api repos/stickleprojects/azure_devops_analyzer/branches/main/protection

# Or check via web UI:
# https://github.com/stickleprojects/azure_devops_analyzer/settings/branches
```

## Related Documentation

- **PR Requirements**: See [feature-development-workflow.md](../docs/03-operations/feature-development-workflow.md)
- **Code Review Standards**: See [05-code-review.md](../agents/05-code-review.md)
- **Pre-Commit Validation**: See [.ai/instructions.md](../.ai/instructions.md#pre-commit-validation-gates)
- **Session Continuity**: See [session-continuity.md](../docs/03-operations/session-continuity.md)

## Updating Protection Rules

To modify protection rules later:

```bash
# View current settings
gh api repos/stickleprojects/azure_devops_analyzer/branches/main/protection

# Re-run the setup script to update
bash scripts/setup-branch-protection.sh
```

To remove protection:

```bash
gh api -X DELETE repos/stickleprojects/azure_devops_analyzer/branches/main/protection
```

## FAQ

**Q: Can administrators bypass branch protection?**  
A: No - the protection is enforced for everyone, including repository admins.

**Q: What if a PR is stale but still valid?**  
A: Reviewers need to re-review after new commits are pushed. This ensures review remains current.

**Q: Can I merge without approval if I'm the owner?**  
A: No - branch protection applies equally to all users.

**Q: Do I need status checks configured?**  
A: The script doesn't require them, but they can be added. Any CI/CD workflows will automatically be required.

---

**Last Updated**: 2026-01-29  
**Status**: ✅ Branch protection active
