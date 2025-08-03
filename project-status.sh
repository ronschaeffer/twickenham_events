#!/bin/bash

# Multi-Project Status Checker
# Shows status of all projects including git, dependencies, and environment info

echo "📊 Python Multi-Project Development Environment Status"
echo "======================================================"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Function to check project status
check_project() {
    local project_name=$1
    local project_path=$2
    
    echo -e "\n${BLUE}📁 Project: $project_name${NC}"
    echo "----------------------------------------"
    
    if [ -d "$project_path" ]; then
        cd "$project_path"
        
        # Check Python environment
        if [ -f ".venv/bin/python" ]; then
            python_version=$(.venv/bin/python --version 2>&1)
            echo -e "${GREEN}✅ Python Environment: $python_version${NC}"
            
            # Check if ruff is installed
            if .venv/bin/python -c "import ruff" 2>/dev/null; then
                ruff_version=$(.venv/bin/python -m ruff --version 2>&1)
                echo -e "${GREEN}✅ Ruff: $ruff_version${NC}"
            else
                echo -e "${YELLOW}⚠️  Ruff: Not found in environment${NC}"
            fi
            
            # Check pytest
            if .venv/bin/python -c "import pytest" 2>/dev/null; then
                pytest_version=$(.venv/bin/python -m pytest --version 2>&1 | head -n1)
                echo -e "${GREEN}✅ PyTest: $pytest_version${NC}"
            else
                echo -e "${YELLOW}⚠️  PyTest: Not found${NC}"
            fi
        else
            echo -e "${RED}❌ Python Environment: Not found${NC}"
        fi
        
        # Check git status
        if [ -d ".git" ]; then
            branch=$(git branch --show-current 2>/dev/null)
            status=$(git status --porcelain 2>/dev/null)
            if [ -z "$status" ]; then
                echo -e "${GREEN}✅ Git: Clean working directory on branch '$branch'${NC}"
            else
                changes=$(echo "$status" | wc -l)
                echo -e "${YELLOW}⚠️  Git: $changes uncommitted changes on branch '$branch'${NC}"
            fi
        else
            echo -e "${YELLOW}⚠️  Git: Not a git repository${NC}"
        fi
        
        # Check for common config files
        echo -e "${PURPLE}📋 Configuration files:${NC}"
        [ -f "pyproject.toml" ] && echo -e "  ${GREEN}✅ pyproject.toml${NC}" || echo -e "  ${RED}❌ pyproject.toml${NC}"
        [ -f "pytest.ini" ] && echo -e "  ${GREEN}✅ pytest.ini${NC}" || echo -e "  ${YELLOW}⚠️  pytest.ini${NC}"
        [ -f ".vscode/settings.json" ] && echo -e "  ${GREEN}✅ VS Code settings${NC}" || echo -e "  ${RED}❌ VS Code settings${NC}"
        
    else
        echo -e "${RED}❌ Project directory not found: $project_path${NC}"
    fi
}

# Get the base directory
BASE_DIR="$(dirname "$(realpath "$0")")"
cd "$BASE_DIR"

echo -e "${PURPLE}🏠 Base Directory: $BASE_DIR${NC}"
echo -e "${PURPLE}🖥️  Current User: $(whoami)${NC}"
echo -e "${PURPLE}🐚 Shell: $SHELL${NC}"

# Check each project
check_project "Twickenham Events" "$BASE_DIR/twickenham_events"
check_project "MQTT Publisher" "$BASE_DIR/mqtt_publisher"

# Check workspace file
echo -e "\n${BLUE}🗂️  Workspace Configuration${NC}"
echo "----------------------------------------"
if [ -f "$BASE_DIR/python-workspace.code-workspace" ]; then
    echo -e "${GREEN}✅ Workspace file: python-workspace.code-workspace${NC}"
else
    echo -e "${RED}❌ Workspace file: Not found${NC}"
fi

echo -e "\n${BLUE}🏁 Status check completed!${NC}"
