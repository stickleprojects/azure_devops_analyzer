#!/bin/bash
# Branch protection setup script for main branch
# Requires: GitHub CLI (gh) installed and authenticated
# Purpose: Enforce PR requirements and code review on main branch

set -e

REPO="stickleprojects/azure_devops_analyzer"
BRANCH="main"
REQUIRED_CHECK_1="Documentation Validation"
REQUIRED_CHECK_2="CI Tests"
REQUIRED_APPROVALS=0

echo "🔐 Setting up branch protection for: $REPO (branch: $BRANCH)"
echo "=================================================="

# Check if GitHub CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) not found. Install it: https://cli.github.com"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "❌ Not authenticated with GitHub. Run: gh auth login"
    exit 1
fi

echo "✅ GitHub CLI authenticated"
echo ""

# Apply branch protection rules
echo "Configuring branch protection for: $BRANCH"
echo "---------------------------------------"

# Rule 1: Require pull request review settings before merging
echo "→ Configuring pull request review requirements..."
gh api repos/$REPO/branches/$BRANCH/protection \
  -X PUT \
  --input - << 'EOF'
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "Documentation Validation",
      "CI Tests"
    ]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "required_approving_review_count": 0
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF

echo ""
echo "✅ Branch protection rules applied:"
echo "   • Require pull request reviews ($REQUIRED_APPROVALS approval minimum)"
echo "   • Dismiss stale reviews"
echo "   • Require status checks: $REQUIRED_CHECK_1, $REQUIRED_CHECK_2"
echo "   • Enforce for administrators"
echo "   • Force pushes disabled"
echo "   • Branch deletion disabled"
echo ""
echo "🔒 Main branch is now protected!"
