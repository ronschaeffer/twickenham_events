#!/usr/bin/env python3
"""Test script to debug Poetry script entry point issues"""

print("Starting import test...")

try:
    print("Testing sys import...")
    import sys

    print("✓ sys imported successfully")

    print("Testing core.__main__ import...")
    from core.__main__ import main

    print("✓ core.__main__.main imported successfully")

    print("Testing main function call...")
    print("Arguments:", sys.argv)

    if len(sys.argv) > 1 and sys.argv[1] == "--version":
        print("Version test requested")
        # Try just importing version module
        from core.version import get_dynamic_version

        version = get_dynamic_version()
        print(f"Version: {version}")
    else:
        print("Would call main() here")
        # main()  # Comment out to avoid full execution during debug

except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()
