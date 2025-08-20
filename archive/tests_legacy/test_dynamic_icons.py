#!/usr/bin/env python3
"""
Test script to verify dynamic icon detection functionality.
"""

from pathlib import Path
import sys

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from twickenham_events.ai_processor import AIProcessor


def test_dynamic_icons():
    """Test dynamic icon detection functionality."""
    print("🧪 Testing dynamic icon detection...")

    # Mock config that enables fallback patterns (AI disabled)
    config_data = {
        "ai_processor": {
            "api_key": "${GEMINI_API_KEY}",
            "type_detection": {
                "enabled": False,  # Force fallback to regex patterns
                "cache_enabled": False,
            },
        }
    }

    class MockConfig:
        def __init__(self, data):
            self.data = data

        def get(self, key, default=None):
            keys = key.split(".")
            value = self.data
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            return value

    config = MockConfig(config_data)
    processor = AIProcessor(config)

    # Test various event types
    test_cases = [
        # Trophy events - should detect as trophy (highest priority)
        ("Rugby World Cup Final", "trophy", "🏆", "mdi:trophy"),
        ("Six Nations Championship Final", "trophy", "🏆", "mdi:trophy"),
        ("Premiership Final", "trophy", "🏆", "mdi:trophy"),
        ("Champions Cup Final", "trophy", "🏆", "mdi:trophy"),
        ("Grand Final", "trophy", "🏆", "mdi:trophy"),
        ("Championship Decider", "trophy", "🏆", "mdi:trophy"),
        # Rugby events - should detect as rugby
        ("England vs Australia", "rugby", "🏉", "mdi:rugby"),
        ("Six Nations Championship", "rugby", "🏉", "mdi:rugby"),
        ("World Cup Quarter Final", "rugby", "🏉", "mdi:rugby"),
        ("Harlequins v Leicester", "rugby", "🏉", "mdi:rugby"),
        # Concert events - should detect as concert
        ("Taylor Swift | The Eras Tour", "concert", "🎵", "mdi:music"),
        ("Live in Concert", "concert", "🎵", "mdi:music"),
        ("Music Festival", "concert", "🎵", "mdi:music"),
        ("Jazz Performance", "concert", "🎵", "mdi:music"),
        # Generic events - should detect as generic
        ("Business Conference", "generic", "🏟️", "mdi:stadium"),
        ("Corporate Event", "generic", "🏟️", "mdi:stadium"),
        ("Meeting", "generic", "🏟️", "mdi:stadium"),
    ]

    print("\n📊 Testing event type detection:")

    for event_name, expected_type, expected_emoji, expected_mdi in test_cases:
        try:
            event_type, emoji, mdi_icon = processor.get_event_type_and_icons(event_name)

            status = (
                "✅"
                if (
                    event_type == expected_type
                    and emoji == expected_emoji
                    and mdi_icon == expected_mdi
                )
                else "❌"
            )

            print(f"  {status} '{event_name}'")
            print(f"      → Type: {event_type} (expected: {expected_type})")
            print(f"      → Emoji: {emoji} (expected: {expected_emoji})")
            print(f"      → MDI: {mdi_icon} (expected: {expected_mdi})")
            print()

        except Exception as e:
            print(f"  ❌ '{event_name}' - Error: {e}")

    print("🎉 Dynamic icon detection test complete!")


if __name__ == "__main__":
    test_dynamic_icons()
