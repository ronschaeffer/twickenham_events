#!/bin/bash

# Update all pre-commit environments
# Updates pre-commit hooks for all projects

echo "🔄 Updating pre-commit environments for all projects..."
echo "======================================================"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to update pre-commit for a project
update_precommit() {
    local project_name=$1
    local project_path=$2
    
    echo -e "\n${BLUE}🔄 Updating pre-commit: $project_name${NC}"
    echo "----------------------------------------"
    
    if [ -d "$project_path" ]; then
        cd "$project_path"
        
        if [ -f ".pre-commit-config.yaml" ]; then
            if [ -f ".venv/bin/pre-commit" ]; then
                echo "Updating pre-commit environment..."
                .venv/bin/pre-commit autoupdate
                .venv/bin/pre-commit install --overwrite
                
                if [ $? -eq 0 ]; then
                    echo -e "${GREEN}✅ $project_name pre-commit updated successfully!${NC}"
                else
                    echo -e "${RED}❌ $project_name pre-commit update had issues!${NC}"
                fi
            else
                echo -e "${YELLOW}⚠️  Pre-commit not found in virtual environment for $project_name${NC}"
            fi
        else
            echo -e "${YELLOW}⚠️  No .pre-commit-config.yaml found for $project_name${NC}"
        fi
    else
        echo -e "${RED}❌ Project directory not found: $project_path${NC}"
    fi
}

# Get the base directory
BASE_DIR="/home/ron/projects"
cd "$BASE_DIR"

# Update pre-commit for each project
update_precommit "Twickenham Events" "$BASE_DIR/twickenham_events"
update_precommit "MQTT Publisher" "$BASE_DIR/mqtt_publisher"

echo -e "\n${BLUE}🏁 All pre-commit environments updated!${NC}"
