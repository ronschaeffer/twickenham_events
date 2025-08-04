#!/bin/bash  
# Format code for this project only

# Set locale to avoid git warnings
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

# Colorsin/bash
# Format code for this project only

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}✨ Formatting 🏉 Twickenham Events...${NC}"

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Format with ruff
echo -e "${BLUE}🔧 Running ruff format...${NC}"
ruff format .

echo -e "${BLUE}🔧 Running ruff check --fix...${NC}"
ruff check --fix .

echo -e "${GREEN}✅ Formatting complete${NC}"
