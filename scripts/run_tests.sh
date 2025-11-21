#!/bin/bash

set -e

echo "🧪 Running Enterprise AI Agent Tests"
echo "===================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Activate virtual environment if using uv
if command -v uv &> /dev/null; then
    echo -e "${YELLOW}Using UV package manager${NC}"
fi

# Run unit tests
echo -e "${YELLOW}Running Unit Tests...${NC}"
uv run pytest tests/unit -m unit -v --tb=short

# Run integration tests
echo -e "${YELLOW}Running Integration Tests...${NC}"
uv run pytest tests/integration -m integration -v --tb=short

# Run coverage
echo -e "${YELLOW}Generating Code Coverage Report...${NC}"
uv run pytest --cov=app --cov-report=html --cov-report=term-missing --cov-fail-under=80

# Check coverage threshold
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed! Coverage >= 80%${NC}"
    echo ""
    echo "📊 Coverage report: htmlcov/index.html"
else
    echo -e "${RED}❌ Tests failed or coverage < 80%${NC}"
    exit 1
fi
