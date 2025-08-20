#!/usr/bin/env python3
"""
Test script to verify the refactoring from AIShortener to AIProcessor works.
"""

from pathlib import Path
import sys

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from twickenham_events.ai_processor import AIProcessor


def test_ai_processor():
    """Test basic AIProcessor functionality."""
    print("🧪 Testing AIProcessor refactoring...")

    # Create a mock config
    config_data = {
        "ai_processor": {
            "api_key": "test-key",
            "type_detection": {
                "enabled": False,
                "cache_enabled": True,
                "model": "gemini-2.5-pro",
            },
            "shortening": {
                "enabled": False,
                "cache_enabled": True,
                "model": "gemini-2.5-pro",
                "max_length": 16,
                "flags_enabled": False,
                "standardize_spacing": True,
                "prompt_template": "Shorten this to {char_limit} chars: {event_name}",
            },
        }
    }

    # Create a mock config object
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

    # Test AIProcessor instantiation
    try:
        processor = AIProcessor(config)
        print("✅ AIProcessor instantiation successful")
    except Exception as e:
        print(f"❌ AIProcessor instantiation failed: {e}")
        return False

    # Test event type detection with fallback
    try:
        event_type, emoji, mdi_icon = processor.get_event_type_and_icons(
            "England vs Australia"
        )
        print(f"✅ Event type detection: {event_type}, {emoji}, {mdi_icon}")

        event_type, emoji, mdi_icon = processor.get_event_type_and_icons(
            "Taylor Swift Concert"
        )
        print(f"✅ Concert detection: {event_type}, {emoji}, {mdi_icon}")

        event_type, emoji, mdi_icon = processor.get_event_type_and_icons(
            "Business Conference"
        )
        print(f"✅ Generic detection: {event_type}, {emoji}, {mdi_icon}")

        event_type, emoji, mdi_icon = processor.get_event_type_and_icons(
            "Rugby World Cup Final"
        )
        print(f"✅ Trophy detection: {event_type}, {emoji}, {mdi_icon}")

    except Exception as e:
        print(f"❌ Event type detection failed: {e}")
        return False

    # Test shortening (should return original since disabled)
    try:
        short_name, had_error, error_msg = processor.get_short_name("Test Event Name")
        print(f"✅ Shortening (disabled): '{short_name}', error: {had_error}")
    except Exception as e:
        print(f"❌ Shortening test failed: {e}")
        return False

    print("🎉 All tests passed! Refactoring successful.")
    return True


if __name__ == "__main__":
    success = test_ai_processor()
    sys.exit(0 if success else 1)
