#!/bin/bash
# Pre-commit script to ensure code quality

set -e

echo "🔍 Running pre-commit checks..."

# Run ruff linting and formatting
echo "🔧 Running ruff checks and fixes..."
poetry run ruff check . --fix
poetry run ruff format .

# Check if there are any remaining issues
echo "✅ Checking for remaining issues..."
poetry run ruff check .

# Run tests if they exist
if [ -d "tests" ]; then
    echo "🧪 Running tests..."
    poetry run pytest --quiet
fi

echo "🎉 All checks passed! Ready to commit."
