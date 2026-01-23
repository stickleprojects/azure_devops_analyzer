#!/bin/bash
# Test Coverage Script for Python Code
# Runs pytest with coverage analysis for the src/ directory

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Running Tests with Coverage Analysis${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Navigate to project root
cd "$PROJECT_DIR"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo -e "${RED}Error: Virtual environment not found!${NC}"
    echo "Please create a virtual environment first:"
    echo "  python -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Use the virtual environment Python
PYTHON_CMD="$PROJECT_DIR/venv/bin/python"

# Check if pytest is installed
if ! $PYTHON_CMD -c "import pytest" 2>/dev/null; then
    echo -e "${RED}Error: pytest not installed!${NC}"
    echo "Installing requirements..."
    $PYTHON_CMD -m pip install -r requirements.txt
fi

echo -e "${YELLOW}Running pytest with coverage...${NC}"
echo ""

# Run tests with coverage
# Remove --cov-fail-under to always show results
$PYTHON_CMD -m pytest \
    --cov=src \
    --cov-report=term-missing:skip-covered \
    --cov-report=html \
    --cov-report=xml \
    -v

PYTEST_EXIT_CODE=$?

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Coverage Reports Generated${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "  📊 Terminal Report: (shown above)"
echo -e "  📁 HTML Report:     ${YELLOW}htmlcov/index.html${NC}"
echo -e "  📄 XML Report:      ${YELLOW}coverage.xml${NC}"
echo ""
echo -e "To view HTML report in browser:"
echo -e "  ${YELLOW}xdg-open htmlcov/index.html${NC}"
echo ""

# Show coverage summary
if [ -f ".coverage" ]; then
    echo -e "${GREEN}Coverage Summary:${NC}"
    $PYTHON_CMD -m coverage report --precision=2 | grep TOTAL || true
    echo ""
fi

exit $PYTEST_EXIT_CODE
