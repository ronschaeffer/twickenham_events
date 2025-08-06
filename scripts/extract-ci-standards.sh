#!/bin/bash
# Quick CI Standards Extractor
# Extracts the working configuration from twickenham_events for use in other projects

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_PROJECT="$SCRIPT_DIR"
TARGET_PROJECT="$1"

if [ -z "$TARGET_PROJECT" ]; then
    echo "Usage: $0 <target-project-path>"
    echo ""
    echo "This script extracts the working CI configuration from twickenham_events"
    echo "and applies it to another project in your workspace."
    echo ""
    echo "Example: $0 ../my-other-project"
    exit 1
fi

if [ ! -d "$TARGET_PROJECT" ]; then
    echo "❌ Target project directory does not exist: $TARGET_PROJECT"
    exit 1
fi

echo "🔧 Extracting CI standards from twickenham_events..."
echo "📁 Source: $SOURCE_PROJECT"
echo "🎯 Target: $TARGET_PROJECT"
echo ""

# Create backup directory
BACKUP_DIR="$TARGET_PROJECT/.ci-migration-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "💾 Creating backup in: $BACKUP_DIR"

# Backup existing files
[ -f "$TARGET_PROJECT/pyproject.toml" ] && cp "$TARGET_PROJECT/pyproject.toml" "$BACKUP_DIR/"
[ -f "$TARGET_PROJECT/.pre-commit-config.yaml" ] && cp "$TARGET_PROJECT/.pre-commit-config.yaml" "$BACKUP_DIR/"
[ -d "$TARGET_PROJECT/.github" ] && cp -r "$TARGET_PROJECT/.github" "$BACKUP_DIR/"

echo ""
echo "📋 Extracting key configurations..."

# Extract Poetry configuration patterns
echo "🔧 1. Poetry Configuration (pyproject.toml)"
echo "   ✅ Dual dependency format: [project.dependencies] + [tool.poetry.dependencies]"
echo "   ✅ Python 3.9+ compatibility: python = \"^3.9\""
echo "   ✅ Dev dependencies: pytest, ruff, pre-commit"

# Extract ruff configuration
echo "🔧 2. Ruff Configuration"
echo "   ✅ Target version: py39"
echo "   ✅ Type annotation rules: UP006, UP007, UP035 ignored"
echo "   ✅ Line length: 88"

# Extract GitHub Actions
echo "🔧 3. GitHub Actions CI"
echo "   ✅ Python matrix: 3.9, 3.10, 3.11, 3.12"
echo "   ✅ Poetry workflow"
echo "   ✅ Coverage reporting"

# Extract pre-commit configuration
echo "🔧 4. Pre-commit Hooks"
echo "   ✅ Ruff linting and formatting"
echo "   ✅ Basic file cleanup"
echo "   ✅ Codespell"

echo ""
echo "📝 Creating configuration templates..."

# Create pyproject.toml template
cat > "$TARGET_PROJECT/pyproject.toml.template" << 'EOF'
# Generated from twickenham_events working configuration

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[project]
# PEP 621 format - sync with [tool.poetry.dependencies]
name = "YOUR_PROJECT_NAME"
version = "0.1.0"
description = "YOUR_PROJECT_DESCRIPTION"
requires-python = ">=3.9"
dependencies = [
    # Copy main dependencies from [tool.poetry.dependencies] below
    # Example: "requests>=2.31.0",
]

[tool.poetry]
name = "YOUR_PROJECT_NAME"
version = "0.1.0"
description = "YOUR_PROJECT_DESCRIPTION"

[tool.poetry.dependencies]
python = "^3.9"
# Add your project dependencies here
# Example: requests = "^2.31.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.0.0"
pytest-cov = "^4.0.0"
ruff = "^0.6.0"
pre-commit = "^3.5.0"

[tool.ruff]
target-version = "py39"  # Critical: Ensures Python 3.9+ compatibility
line-length = 88
select = ["E", "F", "W", "C", "I", "N", "UP"]
ignore = [
    "UP006",  # Allow typing.Dict instead of dict
    "UP007",  # Allow typing.Union instead of |
    "UP035",  # Allow typing.List instead of list
]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--cov=YOUR_PROJECT_NAME",
    "--cov-report=term-missing",
    "--cov-report=xml",
    "--tb=short"
]
EOF

# Copy working GitHub Actions
mkdir -p "$TARGET_PROJECT/.github/workflows"
if [ -f "$SOURCE_PROJECT/.github/workflows/ci.yml" ]; then
    cp "$SOURCE_PROJECT/.github/workflows/ci.yml" "$TARGET_PROJECT/.github/workflows/ci.yml.template"
    echo "✅ Copied CI workflow template"
fi

if [ -f "$SOURCE_PROJECT/.github/workflows/code-quality.yml" ]; then
    cp "$SOURCE_PROJECT/.github/workflows/code-quality.yml" "$TARGET_PROJECT/.github/workflows/code-quality.yml.template"
    echo "✅ Copied code quality workflow template"
fi

# Copy working pre-commit configuration
if [ -f "$SOURCE_PROJECT/.pre-commit-config.yaml" ]; then
    cp "$SOURCE_PROJECT/.pre-commit-config.yaml" "$TARGET_PROJECT/.pre-commit-config.yaml.template"
    echo "✅ Copied pre-commit configuration template"
fi

# Create migration guide
cat > "$TARGET_PROJECT/CI_MIGRATION_GUIDE.md" << 'EOF'
# CI Migration Guide

This directory contains templates extracted from the working `twickenham_events` project.

## Quick Setup

1. **Update pyproject.toml**:
   ```bash
   # Review and merge pyproject.toml.template with your existing pyproject.toml
   # Key changes needed:
   # - Add [project.dependencies] section (sync with Poetry)
   # - Set python = "^3.9" for compatibility
   # - Add ruff configuration with target-version = "py39"
   # - Add ignored rules: UP006, UP007, UP035
   ```

2. **Copy GitHub Actions**:
   ```bash
   cp .github/workflows/*.template .github/workflows/
   rename 's/\.template$//' .github/workflows/*.template
   # Edit workflows to match your project name
   ```

3. **Setup Pre-commit**:
   ```bash
   cp .pre-commit-config.yaml.template .pre-commit-config.yaml
   pre-commit install
   ```

4. **Update Code for Python 3.9 Compatibility**:
   ```bash
   # Replace modern union syntax:
   # OLD: dict | None
   # NEW: Optional[Dict[str, Any]]

   # Add imports:
   from typing import Any, Dict, List, Optional
   ```

5. **Test Locally**:
   ```bash
   poetry install --with dev
   poetry run ruff check .
   poetry run pytest
   pre-commit run --all-files
   ```

## Key Lessons Applied

- **Python 3.9+ compatibility**: No `dict | None` syntax
- **Dual dependencies**: Both PEP 621 and Poetry formats
- **Matrix testing**: Python 3.9-3.12 in CI
- **Consistent tooling**: Ruff + pre-commit integration

## Troubleshooting

- If CI fails on Python 3.9: Check for modern union syntax
- If Poetry fails: Ensure dependencies are in both sections
- If pre-commit fails: Run `pre-commit run --all-files` locally first
EOF

echo ""
echo "✅ Configuration templates created!"
echo ""
echo "📋 Next Steps:"
echo "1. cd $TARGET_PROJECT"
echo "2. Review and merge pyproject.toml.template with your existing pyproject.toml"
echo "3. Copy .github/workflows/*.template to actual workflow files"
echo "4. Copy .pre-commit-config.yaml.template to .pre-commit-config.yaml"
echo "5. Update any dict | None syntax to Optional[Dict[str, Any]]"
echo "6. Run: poetry install --with dev && pre-commit install"
echo "7. Test: poetry run pytest && pre-commit run --all-files"
echo ""
echo "📖 See CI_MIGRATION_GUIDE.md for detailed instructions"
echo ""
echo "💾 Backup created in: $BACKUP_DIR"
