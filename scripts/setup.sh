#!/bin/bash

set -e

echo "🚀 Setting up Enterprise AI Agent Platform"
echo "=========================================="

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.11"

if [ "$(printf '%s
' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.11+ required. Found: $python_version"
    exit 1
fi

echo "✅ Python version: $python_version"

# Install UV if not present
if ! command -v uv &> /dev/null; then
    echo "📦 Installing UV package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

echo "✅ UV package manager installed"

# Create virtual environment and install dependencies
echo "📦 Installing dependencies..."
uv sync

# Copy environment template
if [ ! -f .env ]; then
    echo "📝 Creating .env from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your configuration"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your Snowflake, S3, and LLM credentials"
echo "2. Run: uv run uvicorn app.main:app --reload"
echo "3. Open: http://localhost:8000/docs"
