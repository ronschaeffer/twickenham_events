#!/usr/bin/env python3
"""
Debug script to see which pattern is matching "World Cup Quarter Final"
"""

import re


def debug_patterns():
    test_cases = [
        ("World Cup Quarter Final", False),  # Should NOT be trophy
        ("Rugby World Cup Final", True),  # Should be trophy
        ("Championship Decider", True),  # Should be trophy
        ("Premiership Semi Final", False),  # Should NOT be trophy
    ]

    trophy_patterns = [
        r"\b(grand final|cup final|title match|championship decider|title decider)\b",
        r"\b(world cup final|six nations final|premiership final|championship final)\b",
        r"\b(champions cup final|european cup final|heineken cup final)\b",
        r"\b(grand slam final|triple crown final)\b",
        r"\b(playoff final)\b",
        r"\b(winner takes all)\b",
        r"\b(champions league final|europa league final)\b",
    ]

    for event_name, should_match in test_cases:
        event_lower = event_name.lower()
        found_match = False

        print(
            f"Testing: '{event_name}' (expected: {'TROPHY' if should_match else 'NOT TROPHY'})"
        )

        for i, pattern in enumerate(trophy_patterns):
            match = re.search(pattern, event_lower)
            if match:
                print(f"✅ Pattern {i + 1} MATCHED: {pattern}")
                print(f"   Matched text: '{match.group()}'")
                found_match = True
                break

        if not found_match:
            print("❌ No patterns matched")

        result = "✅ CORRECT" if (found_match == should_match) else "❌ WRONG"
        print(f"Result: {result}")
        print()


if __name__ == "__main__":
    debug_patterns()
