#!/bin/bash

# GitHub Secrets Setup Script
# Run this script to securely add secrets to your repository

echo "🔐 Setting up GitHub repository secrets..."
echo ""
echo "This script will prompt you to enter sensitive tokens."
echo "They will NOT be displayed on screen and will be sent directly to GitHub."
echo ""

# Set repository
REPO="stickleprojects/azure_devops_analyzer"

# GitHub Token for Live API Tests
echo "📝 Enter your GitHub Personal Access Token for live API tests:"
echo "   (This should have 'repo' and 'read:org' permissions)"
read -s GITHUB_TOKEN_LIVE_API
echo ""

if [ -n "$GITHUB_TOKEN_LIVE_API" ]; then
    echo "⏳ Setting GITHUB_TOKEN_LIVE_API..."
    echo "$GITHUB_TOKEN_LIVE_API" | gh secret set GITHUB_TOKEN_LIVE_API --repo "$REPO"
    echo "✅ GITHUB_TOKEN_LIVE_API set successfully"
else
    echo "⚠️  Skipping GITHUB_TOKEN_LIVE_API (empty input)"
fi

echo ""

# Azure DevOps PAT
echo "📝 Enter your Azure DevOps Personal Access Token:"
echo "   (This should have permissions to read repositories and projects)"
read -s AZURE_DEVOPS_PAT
echo ""

if [ -n "$AZURE_DEVOPS_PAT" ]; then
    echo "⏳ Setting AZURE_DEVOPS_PAT..."
    echo "$AZURE_DEVOPS_PAT" | gh secret set AZURE_DEVOPS_PAT --repo "$REPO"
    echo "✅ AZURE_DEVOPS_PAT set successfully"
else
    echo "⚠️  Skipping AZURE_DEVOPS_PAT (empty input)"
fi

echo ""
echo "🎉 Done! Your secrets have been securely stored in GitHub."
echo ""
echo "You can verify by running:"
echo "  gh secret list --repo $REPO"
