#!/usr/bin/env python3
"""
Update ha_entities.yaml with dynamic Git-based version
"""

from pathlib import Path
import re
import sys

# Add parent directory to path to import our modules
sys.path.append(str(Path(__file__).parent.parent))
from core.version import get_dynamic_version


def update_ha_entities_version():
    """Update the sw_version in ha_entities.yaml with current Git version."""
    ha_entities_path = Path(__file__).parent / "config" / "ha_entities.yaml"

    if not ha_entities_path.exists():
        print(f"❌ {ha_entities_path} not found")
        return False

    # Get current dynamic version
    current_version = get_dynamic_version()
    print(f"🔄 Updating sw_version to: {current_version}")

    # Read the file
    with open(ha_entities_path, "r") as f:
        content = f.read()

    # Update sw_version line
    updated_content = re.sub(
        r'(\s*sw_version:\s*)["\']?[^"\'\n]*["\']?', rf'\1"{current_version}"', content
    )

    # Write back to file
    with open(ha_entities_path, "w") as f:
        f.write(updated_content)

    print(f"✅ Updated {ha_entities_path}")
    return True


if __name__ == "__main__":
    update_ha_entities_version()
