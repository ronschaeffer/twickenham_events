#!/usr/bin/env python3
"""Debug script for health check"""

import sys
import traceback

print("Python version:", sys.version)
print("Arguments:", sys.argv)

try:
    from core.health_check import main

    print("Imported main successfully")
    main()
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()
