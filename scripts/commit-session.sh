#!/bin/bash
# Quick commit script for session cleanup

echo "=== Session Cleanup Script ==="
echo ""

# Remove stray file
if [ -f "=7.1.0b4" ]; then
    echo "Removing stray file: =7.1.0b4"
    rm "=7.1.0b4"
fi

# Show status
echo ""
echo "=== Current Changes ==="
git status --short
echo ""

# Show stats
echo "=== Change Statistics ==="
git diff --stat
echo ""

# Prompt for commit
read -p "Ready to commit? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git add .
    
    echo ""
    echo "=== Creating commit ==="
    git commit -m "feat: Complete FR-2 language/tech detection + platform parity docs

- Implement language detection for both GitHub and Azure DevOps
- Add TechnologyDetector analyzer (8 categories, 26+ languages)
- Create Azure DevOps workflow mirroring GitHub
- Add 10 integration tests for Azure DevOps
- Document comprehensive platform parity
- Add FR-1.5 requirement (repository metadata)
- Update FR-8.2 priority to High (README extraction)
- Both platforms now required to extract README and metadata

FR-2: Complete (3/3)
Platform Parity: Core features complete, README/metadata pending for Azure DevOps
Progress: 16/45 complete, 9/45 partial"
    
    echo ""
    echo "=== Commit Complete ==="
    git log -1 --oneline
    echo ""
    echo "Next: git push origin feature/complete-fr2-language-detection"
else
    echo "Commit cancelled. Changes remain uncommitted."
fi
