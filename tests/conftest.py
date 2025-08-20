from pathlib import Path
import sys

# Ensure sibling ha_mqtt_publisher src is on sys.path for tests that import mqtt_publisher
_sibling_src = Path("/home/ron/projects/ha_mqtt_publisher/src")
if _sibling_src.exists():
    sys.path.insert(0, str(_sibling_src))

# Add project root to path so local src packages are importable
sys.path.insert(0, str(Path(__file__).parent.parent))
