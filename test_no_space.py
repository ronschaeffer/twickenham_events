#!/usr/bin/env python3
"""Quick test for no-space noon and midnight handling."""

import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.twick_event import normalize_time


def test_no_space_handling():
    """Test no-space noon and midnight formats."""
    test_cases = [
        # No-space cases
        ("12noon", ["12:00"]),
        ("12midnight", ["00:00"]),  # This should be ["00:00"]
        ("event at 12noon", ["12:00"]),
        ("event at 12midnight", ["00:00"]),
        # Existing cases (to ensure they still work)
        ("12 noon", ["12:00"]),
        ("12 midnight", ["00:00"]),
        ("noon", ["12:00"]),
        ("midnight", ["00:00"]),
    ]

    print("Testing no-space noon and midnight handling:")
    print("=" * 60)

    for input_str, expected in test_cases:
        result = normalize_time(input_str)
        print(f"Input: '{input_str}'")
        print(f"Expected: {expected}")
        print(f"Got: {result}")
        print("✅ Pass" if result == expected else "❌ Fail")
        print("-" * 40)


if __name__ == "__main__":
    test_no_space_handling()
