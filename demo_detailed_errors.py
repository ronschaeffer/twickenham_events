#!/usr/bin/env python3
"""
Simple test to demonstrate the new detailed AI error reporting.
"""

from pathlib import Path
import sys
from unittest.mock import Mock

from core.event_shortener import get_short_name

# Add project root to the Python path
sys.path.append(str(Path(__file__).parent))


def create_mock_config(enable_ai=True, api_key="", prompt_template=""):
    """Create a mock config for testing."""
    config = Mock()
    config.get.side_effect = lambda key, default=None: {
        "ai_shortener.enabled": enable_ai,
        "ai_shortener.api_key": api_key,
        "ai_shortener.model": "gemini-2.5-pro",
        "ai_shortener.max_length": 16,
        "ai_shortener.prompt_template": prompt_template,
        "ai_shortener.flags_enabled": False,
        "ai_shortener.standardize_spacing": True,
        "ai_shortener.cache_enabled": False,  # Disable cache for testing
    }.get(key, default)
    return config


def main():
    """Test various AI error scenarios and their detailed messages."""

    print("🧪 Testing Detailed AI Error Messages")
    print("=" * 50)

    # Test 1: Missing API key
    print("\n1. Testing missing API key...")
    config_no_key = create_mock_config(
        enable_ai=True, api_key="", prompt_template="Test prompt"
    )
    result, had_error, error_message = get_short_name("Test Event", config_no_key)

    print(f"   Result: '{result}'")
    print(f"   Had Error: {had_error}")
    print(f"   Error Message: '{error_message}'")

    # Test 2: Missing prompt template
    print("\n2. Testing missing prompt template...")
    config_no_prompt = create_mock_config(
        enable_ai=True, api_key="test_key", prompt_template=""
    )
    result, had_error, error_message = get_short_name("Test Event", config_no_prompt)

    print(f"   Result: '{result}'")
    print(f"   Had Error: {had_error}")
    print(f"   Error Message: '{error_message}'")

    # Test 3: Feature disabled (should not be an error)
    print("\n3. Testing disabled feature...")
    config_disabled = create_mock_config(enable_ai=False)
    result, had_error, error_message = get_short_name("Test Event", config_disabled)

    print(f"   Result: '{result}'")
    print(f"   Had Error: {had_error}")
    print(f"   Error Message: '{error_message}'")

    # Test 4: Missing dependencies (google.generativeai not available)
    print("\n4. Testing missing dependencies...")
    # This will naturally trigger because the library isn't installed
    config_full = create_mock_config(
        enable_ai=True, api_key="test_key", prompt_template="Test: {event_name}"
    )
    result, had_error, error_message = get_short_name("Rugby Match", config_full)

    print(f"   Result: '{result}'")
    print(f"   Had Error: {had_error}")
    print(f"   Error Message: '{error_message}'")

    print("\n" + "=" * 50)
    print("🎉 DEMONSTRATION COMPLETE!")
    print("\nBefore this change:")
    print(
        "  - MQTT status only showed generic error: 'Error shortening event name: Test Event'"
    )
    print("\nAfter this change:")
    print("  - MQTT status shows specific errors like:")
    print(
        "    • 'AI shortening failed for 'Test Event': AI shortener enabled but no API key provided'"
    )
    print(
        "    • 'AI shortening failed for 'Rugby Match': google.generativeai library not available'"
    )
    print(
        "    • 'AI shortening failed for 'Event Name': Generated name exceeds visual width limit'"
    )
    print("\nThis makes debugging much easier in Home Assistant!")


if __name__ == "__main__":
    main()
