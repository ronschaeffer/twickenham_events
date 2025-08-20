#!/usr/bin/env python3
"""
Test version fallback when Git is not available
"""

from pathlib import Path
import sys
from unittest.mock import patch

sys.path.append(str(Path(__file__).parent))
from core.version import get_dynamic_version, get_git_version, get_project_version

print("🧪 Testing Version Fallback Scenarios")
print("=" * 50)

# Test 1: Normal Git version
print("✅ Normal Git version:")
print(f"   {get_git_version()}")

# Test 2: Simulate Git not available
print("\n🚫 Simulating Git not available:")
with patch(
    "subprocess.check_output", side_effect=FileNotFoundError("git command not found")
):
    git_fallback = get_git_version()
    print(f"   {git_fallback}")

# Test 3: Project version from pyproject.toml
print("\n📦 Project version from pyproject.toml:")
print(f"   {get_project_version()}")

# Test 4: Dynamic version (with fallback logic)
print("\n🎯 Dynamic version (best available):")
print(f"   {get_dynamic_version()}")

# Test 5: Simulate complete failure scenario
print("\n💥 Simulating both Git and pyproject.toml failures:")
with (
    patch("subprocess.check_output", side_effect=FileNotFoundError("git not found")),
    patch("builtins.open", side_effect=FileNotFoundError("pyproject.toml not found")),
):
    emergency_fallback = get_dynamic_version()
    print(f"   {emergency_fallback}")

print("\n" + "=" * 50)
print("All scenarios handled gracefully! 🎉")
