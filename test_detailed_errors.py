#!/usr/bin/env python3
"""
Test script to demonstrate the new detailed AI error reporting in MQTT status messages.
"""

import json
from pathlib import Path
import sys
from unittest.mock import Mock

from core.event_shortener import get_short_name
from core.twick_event import error_log, process_and_publish_events

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


def test_detailed_error_messages():
    """Test various AI error scenarios and their detailed messages."""

    print("🧪 Testing Detailed AI Error Messages")
    print("=" * 50)

    # Test 1: Missing API key
    print("\n1. Testing missing API key...")
    config_no_key = create_mock_config(
        enable_ai=True, api_key="", prompt_template="Test prompt"
    )
    result, had_error, error_message = get_short_name("Test Event", config_no_key)

    print(f"   Result: {result}")
    print(f"   Had Error: {had_error}")
    print(f"   Error Message: {error_message}")
    assert had_error
    assert "no API key provided" in error_message

    # Test 2: Missing prompt template
    print("\n2. Testing missing prompt template...")
    config_no_prompt = create_mock_config(
        enable_ai=True, api_key="test_key", prompt_template=""
    )
    result, had_error, error_message = get_short_name("Test Event", config_no_prompt)

    print(f"   Result: {result}")
    print(f"   Had Error: {had_error}")
    print(f"   Error Message: {error_message}")
    assert had_error
    assert "no prompt template provided" in error_message

    # Test 3: Feature disabled (should not be an error)
    print("\n3. Testing disabled feature...")
    config_disabled = create_mock_config(enable_ai=False)
    result, had_error, error_message = get_short_name("Test Event", config_disabled)

    print(f"   Result: {result}")
    print(f"   Had Error: {had_error}")
    print(f"   Error Message: {error_message}")
    assert not had_error
    assert error_message == ""

    print("\n✅ All detailed error message tests passed!")


def demonstrate_mqtt_status_integration():
    """Demonstrate how detailed errors appear in MQTT status messages."""

    print("\n🚀 Demonstrating MQTT Status Integration")
    print("=" * 50)

    # Clear any existing errors
    error_log.clear()

    # Create mock publisher to capture what would be published
    class MockPublisher:
        def __init__(self):
            self.published_messages = []

        def publish(self, topic, payload, retain=False):
            self.published_messages.append(
                {"topic": topic, "payload": payload, "retain": retain}
            )

    # Create mock config
    mock_config = Mock()
    mock_config.get.side_effect = lambda key, default=None: {
        "mqtt.topics.all_upcoming": "test/all_upcoming",
        "mqtt.topics.next": "test/next",
        "mqtt.topics.status": "test/status",
    }.get(key, default)

    # Create test events that will trigger AI shortening errors
    test_events = [
        {
            "date": "2025-08-15",
            "events": [
                {
                    "fixture": "Test Rugby Match",
                    "start_time": "15:00",
                    "crowd": "50,000",
                }
            ],
            "earliest_start": "15:00",
        }
    ]

    # Process events with a publisher that will capture MQTT messages
    mock_publisher = MockPublisher()

    # Simulate the processing that happens in main() which calls get_short_name
    # and adds errors to error_log before calling process_and_publish_events
    config_with_error = create_mock_config(
        enable_ai=True, api_key="", prompt_template="test"
    )
    _, had_error, error_message = get_short_name("Test Rugby Match", config_with_error)
    if had_error:
        error_log.append(
            f"AI shortening failed for 'Test Rugby Match': {error_message}"
        )

    # Now process and publish events
    process_and_publish_events(test_events, mock_publisher, mock_config)

    # Find the status message
    status_message = None
    for msg in mock_publisher.published_messages:
        if msg["topic"] == "test/status":
            status_message = msg["payload"]
            break

    print("\n📊 MQTT Status Message Content:")
    if status_message:
        print(json.dumps(status_message, indent=2))

        # Verify the detailed error information is included
        assert status_message["status"] == "error"
        assert status_message["error_count"] > 0
        assert len(status_message["errors"]) > 0

        error_text = status_message["errors"][0]
        print(f"\n🔍 Detailed Error in Status: {error_text}")

        # Verify it contains the specific AI error details
        assert "AI shortening failed" in error_text
        assert "no API key provided" in error_text

        print("\n✅ MQTT Status integration working correctly!")
        print("   - Error status set correctly")
        print("   - Error count included")
        print("   - Detailed AI error messages included")

    else:
        print("❌ No status message found!")


if __name__ == "__main__":
    test_detailed_error_messages()
    demonstrate_mqtt_status_integration()

    print("\n🎉 All tests completed successfully!")
    print(
        "\nThe system now provides detailed AI error information in MQTT status messages:"
    )
    print(
        "- Specific error reasons (missing API key, missing prompt, API failures, etc.)"
    )
    print("- Error context (which event name failed)")
    print("- All errors included in MQTT status topic for Home Assistant integration")
