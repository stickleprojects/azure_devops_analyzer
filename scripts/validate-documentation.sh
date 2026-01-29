#!/bin/bash
# Documentation standards validation script
# Checks if documentation files comply with agents/00-documentation-standards.md

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Default to current directory if no argument
TARGET="${1:-.}"

echo "📋 Validating documentation: $TARGET"
echo "=========================================="

VIOLATIONS=0
WARNINGS=0

# Function to check a single file
check_file() {
  local FILE="$1"
  
  if [ ! -f "$FILE" ]; then
    return
  fi
  
  echo ""
  echo "Checking: $FILE"
  
  # Count total lines
  TOTAL_LINES=$(wc -l < "$FILE")
  
  # Count code blocks
  CODE_BLOCKS=$(grep -c '^```' "$FILE" || echo "0")
  
  # Estimate code lines (rough: ~7 lines per block average)
  CODE_LINES=$((CODE_BLOCKS * 7))
  CODE_PERCENTAGE=$((CODE_LINES * 100 / TOTAL_LINES))
  
  echo "  📊 Total lines: $TOTAL_LINES"
  echo "  📦 Code blocks: $CODE_BLOCKS"
  echo "  💾 Est. code lines: ~$CODE_LINES (${CODE_PERCENTAGE}%)"
  
  # Check for violations
  
  # Violation 1: Full function definitions
  if grep -q "^def " "$FILE" 2>/dev/null; then
    echo "  ${RED}❌ Contains full Python function definitions${NC}"
    echo "     Move implementations to script files, reference instead"
    VIOLATIONS=$((VIOLATIONS + 1))
  fi
  
  if grep -q "^async def " "$FILE" 2>/dev/null; then
    echo "  ${RED}❌ Contains async function definitions${NC}"
    VIOLATIONS=$((VIOLATIONS + 1))
  fi
  
  if grep -q "^class " "$FILE" 2>/dev/null; then
    echo "  ${RED}❌ Contains full class definitions${NC}"
    echo "     Classes belong in Python files, not documentation"
    VIOLATIONS=$((VIOLATIONS + 1))
  fi
  
  # Warning 1: Too many code blocks
  if [ "$CODE_BLOCKS" -gt 6 ]; then
    echo "  ${YELLOW}⚠️  More than 6 code blocks (current: $CODE_BLOCKS)${NC}"
    echo "     Implies code content > 30% - verify this is intentional"
    WARNINGS=$((WARNINGS + 1))
  fi
  
  # Warning 2: Code percentage too high
  if [ "$CODE_PERCENTAGE" -gt 35 ]; then
    echo "  ${YELLOW}⚠️  Estimated code content: ${CODE_PERCENTAGE}% (recommended: ≤30%)${NC}"
    WARNINGS=$((WARNINGS + 1))
  fi
  
  # Check for implementation docs without Architecture Guardian
  if [[ "$FILE" == *"implementation"* ]] || [[ "$FILE" == *"04-implementation"* ]]; then
    if ! grep -q "Architecture Guardian" "$FILE" 2>/dev/null; then
      echo "  ${YELLOW}⚠️  Implementation doc missing 'Architecture Guardian' section${NC}"
      echo "     Add validation checklist per agents/02a-architecture-guardian.md"
      WARNINGS=$((WARNINGS + 1))
    fi
  fi
  
  # Check for proper structure
  if ! grep -q "^## " "$FILE" 2>/dev/null; then
    echo "  ${YELLOW}⚠️  No section headings (##) found${NC}"
    WARNINGS=$((WARNINGS + 1))
  fi
  
  # Check for orphaned code references
  if grep -q "See \`\`\`" "$FILE" 2>/dev/null; then
    echo "  ${YELLOW}⚠️  Possible orphaned code reference without file link${NC}"
    WARNINGS=$((WARNINGS + 1))
  fi
  
  # Positive feedback
  if [ "$CODE_PERCENTAGE" -le 30 ] && [ "$CODE_BLOCKS" -le 6 ]; then
    echo "  ${GREEN}✅ Code content within guidelines${NC}"
  fi
}

# Process files
if [ -d "$TARGET" ]; then
  # Directory provided - check all .md files
  echo "Scanning directory: $TARGET"
  find "$TARGET" -name "*.md" -type f | while read -r FILE; do
    check_file "$FILE"
  done
elif [ -f "$TARGET" ]; then
  # Single file provided
  check_file "$TARGET"
else
  echo "❌ File or directory not found: $TARGET"
  exit 1
fi

# Summary
echo ""
echo "=========================================="
echo "📊 Summary:"
echo "  ❌ Violations: $VIOLATIONS"
echo "  ⚠️  Warnings: $WARNINGS"

if [ "$VIOLATIONS" -gt 0 ]; then
  echo ""
  echo "${RED}Validation FAILED - fix violations above${NC}"
  exit 1
elif [ "$WARNINGS" -gt 0 ]; then
  echo ""
  echo "${YELLOW}Validation passed with warnings - review above${NC}"
  exit 0
else
  echo ""
  echo "${GREEN}✅ Validation PASSED - documentation meets standards${NC}"
  exit 0
fi
