from pathlib import Path
import sys

# Add project root to path so local src packages are importable
sys.path.insert(0, str(Path(__file__).parent.parent))
