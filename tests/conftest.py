from pathlib import Path
import sys

# Add only the src directory to path, not the project root
# This prevents accidentally picking up sibling workspace projects
project_root = Path(__file__).parent.parent
src_path = str(project_root / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)
