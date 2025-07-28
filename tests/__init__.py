import sys
from pathlib import Path

# Add project root to Python path
root = str(Path(__file__).parent.parent)
if root not in sys.path:
    sys.path.insert(0, root)

# Empty file to make directory a package
