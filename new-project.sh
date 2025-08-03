#!/bin/bash

# New Python Project Setup Script
# Quickly sets up a new Python project with standard structure

if [ $# -eq 0 ]; then
    echo "Usage: $0 <project_name>"
    echo "Example: $0 my_new_project"
    exit 1
fi

PROJECT_NAME=$1
BASE_DIR="$(dirname "$(realpath "$0")")"
PROJECT_DIR="$BASE_DIR/$PROJECT_NAME"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Setting up new Python project: $PROJECT_NAME${NC}"
echo "=================================================="

# Check if project already exists
if [ -d "$PROJECT_DIR" ]; then
    echo -e "${RED}❌ Project directory already exists: $PROJECT_DIR${NC}"
    exit 1
fi

# Create project directory
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# Initialize git
git init
echo -e "${GREEN}✅ Initialized git repository${NC}"

# Create basic directory structure
mkdir -p src/$PROJECT_NAME
mkdir -p tests
mkdir -p docs
mkdir -p config
mkdir -p .vscode

echo -e "${GREEN}✅ Created directory structure${NC}"

# Create pyproject.toml with basic structure
cat > pyproject.toml << 'EOF'
[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "PROJECT_NAME_PLACEHOLDER"
version = "0.1.0"
description = "A new Python project"
authors = [{name = "Ron Schaeffer", email = "ron@example.com"}]
requires-python = ">=3.11"
dependencies = [
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "ruff>=0.12",
    "mypy>=1.0",
]

[tool.ruff]
line-length = 88
target-version = "py311"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
EOF

# Replace placeholder in pyproject.toml
sed -i "s/PROJECT_NAME_PLACEHOLDER/$PROJECT_NAME/g" pyproject.toml

echo -e "${GREEN}✅ Created pyproject.toml${NC}"

echo -e "\n${BLUE}🎉 Basic project $PROJECT_NAME structure created!${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. cd $PROJECT_DIR"
echo -e "  2. python -m venv .venv"
echo -e "  3. source .venv/bin/activate"
echo -e "  4. pip install -e .[dev]"
echo -e "  5. code ."
