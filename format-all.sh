#!/bin/bash

# Multi-Project Formatter
# Formats code for all projects using Ruff

echo "🎨 Formatting all Python projects with Ruff..."
echo "==============================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to format a project
format_project() {
    local project_name=$1
    local project_path=$2
    
    echo -e "\n${BLUE}🎨 Formatting: $project_name${NC}"
    echo "----------------------------------------"
    
    if [ -d "$project_path" ]; then
        cd "$project_path"
        if [ -f ".venv/bin/python" ]; then
            echo "Using virtual environment: $project_path/.venv"
            
            # Run ruff check first
            echo -e "${YELLOW}Running Ruff check...${NC}"
            .venv/bin/python -m ruff check . --fix
            
            # Run ruff format
            echo -e "${YELLOW}Running Ruff format...${NC}"
            .venv/bin/python -m ruff format .
            
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}✅ $project_name formatted successfully!${NC}"
            else
                echo -e "${RED}❌ $project_name formatting had issues!${NC}"
            fi
        else
            echo -e "${RED}❌ No virtual environment found for $project_name${NC}"
        fi
    else
        echo -e "${RED}❌ Project directory not found: $project_path${NC}"
    fi
}

# Get the base directory (should be /home/ron/projects)
BASE_DIR="$(dirname "$(realpath "$0")")"
cd "$BASE_DIR"

# Format each project
format_project "Twickenham Events" "$BASE_DIR/twickenham_events"
format_project "MQTT Publisher" "$BASE_DIR/mqtt_publisher"

echo -e "\n${BLUE}🏁 All projects formatted!${NC}"
