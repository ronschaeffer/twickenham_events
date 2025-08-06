#!/usr/bin/env python3
"""Quick test for midnight handling in normalize_time function."""

import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.twick_event import normalize_time


def test_midnight_handling():
    """Test various midnight formats."""
    test_cases = [
        ("midnight", ["00:00"]),
        ("12 midnight", ["00:00"]),
        ("midnight 12", ["00:00"]),
        ("Midnight", ["00:00"]),
        ("12:00am", ["00:00"]),
        ("Event at midnight", ["00:00"]),
        ("noon", ["12:00"]),
        ("12:00pm", ["12:00"]),
    ]

    print("Testing midnight handling in normalize_time:")
    print("=" * 50)

    for input_str, expected in test_cases:
        result = normalize_time(input_str)
        print(f"Input: '{input_str}'")
        print(f"Expected: {expected}")
        print(f"Got: {result}")
        print("✅ Pass" if result == expected else "❌ Fail")
        print("-" * 30)


if __name__ == "__main__":
    print("Starting midnight test...")
    test_midnight_handling()
    print("Test completed.")
