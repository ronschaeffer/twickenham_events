#!/bin/bash
# Quick run script for this project

#!/bin/bash
# Run the Twickenham Events scraper

# Set locale to avoid git warnings
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 Running 🏉 Twickenham Events...${NC}"

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo -e "${GREEN}✅ Activated virtual environment${NC}"
fi

# Add your run command here
echo -e "${BLUE}💡 Add your project run command to .dev-scripts/run.sh${NC}"
