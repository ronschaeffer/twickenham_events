#!/usr/bin/env python3
"""Quick test for noon and midnight handling in normalize_time function."""

import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.twick_event import normalize_time


def test_noon_and_midnight_handling():
    """Test various noon and midnight formats."""
    test_cases = [
        # Noon test cases
        ("noon", ["12:00"]),
        ("12 noon", ["12:00"]),
        ("noon 12", ["12:00"]),
        ("Noon", ["12:00"]),
        ("12:00pm", ["12:00"]),
        ("Event at noon", ["12:00"]),
        # Midnight test cases (to ensure they still work)
        ("midnight", ["00:00"]),
        ("12 midnight", ["00:00"]),
        ("midnight 12", ["00:00"]),
        ("Midnight", ["00:00"]),
        ("12:00am", ["00:00"]),
        ("Event at midnight", ["00:00"]),
        # Mixed cases
        ("noon and midnight", ["00:00", "12:00"]),
        ("12 noon & 12 midnight", ["00:00", "12:00"]),
    ]

    print("Testing noon and midnight handling in normalize_time:")
    print("=" * 60)

    for input_str, expected in test_cases:
        result = normalize_time(input_str)
        print(f"Input: '{input_str}'")
        print(f"Expected: {expected}")
        print(f"Got: {result}")
        print("✅ Pass" if result == expected else "❌ Fail")
        print("-" * 40)


if __name__ == "__main__":
    print("Starting noon and midnight test...")
    test_noon_and_midnight_handling()
    print("Test completed.")
