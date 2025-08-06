#!/bin/bash

# Multi-Project Test Runner
# Runs tests for all projects in the workspace

echo "🧪 Running tests for all Python projects..."
echo "============================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to run tests for a project
run_tests() {
    local project_name=$1
    local project_path=$2

    echo -e "\n${BLUE}📋 Testing: $project_name${NC}"
    echo "----------------------------------------"

    if [ -d "$project_path" ]; then
        cd "$project_path"
        if [ -f ".venv/bin/python" ]; then
            echo "Using virtual environment: $project_path/.venv"
            .venv/bin/python -m pytest tests/ -v
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}✅ $project_name tests passed!${NC}"
            else
                echo -e "${RED}❌ $project_name tests failed!${NC}"
            fi
        else
            echo -e "${RED}❌ No virtual environment found for $project_name${NC}"
        fi
    else
        echo -e "${RED}❌ Project directory not found: $project_path${NC}"
    fi
}

# Get the base directory (should be /home/ron/projects)
BASE_DIR="$(dirname "$(dirname "$(realpath "$0")")")"
cd "$BASE_DIR"

# Run tests for each project
run_tests "Twickenham Events" "$BASE_DIR/twickenham_events"
run_tests "MQTT Publisher" "$BASE_DIR/mqtt_publisher"

echo -e "\n${BLUE}🏁 All tests completed!${NC}"
