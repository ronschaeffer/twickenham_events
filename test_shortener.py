#!/usr/bin/env python3
"""Test script for event shortener functionality."""

from core.event_shortener import get_short_name, calculate_visual_width
from core.config import Config
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))


def main():
    """Test the event shortener functionality."""
    # Load config
    config_path = Path('./config/config.yaml')
    config = Config(config_path=str(config_path))

    print("=== Event Shortener Test ===")
    print(f"AI Shortener enabled: {config.get('ai_shortener.enabled')}")
    print(f"Flags enabled: {config.get('ai_shortener.flags_enabled')}")
    print(f"Model: {config.get('ai_shortener.model')}")
    print(f"Max length: {config.get('ai_shortener.max_length')}")
    print()

    # Test cases
    test_cases = [
        "Women's Rugby World Cup Final",  # Cached, no flags
        "Argentina V South Africa",       # Cached, with flags
        # New event (will use cache or fail gracefully)
        "England vs Australia",
    ]

    for test_event in test_cases:
        print(f"Testing: '{test_event}'")
        try:
            result, had_error = get_short_name(test_event, config)
            visual_width = calculate_visual_width(result)
            max_length = config.get('ai_shortener.max_length', 25)

            print(f"  Result: '{result}'")
            print(f"  Visual width: {visual_width} units (max: {max_length})")
            print(f"  Had error: {had_error}")
            print(
                f"  ✅ {'Cached' if not had_error and result != test_event else 'Original returned'}")
        except Exception as e:
            print(f"  ❌ Exception: {e}")
        print()

    print("Test complete!")


if __name__ == "__main__":
    main()
