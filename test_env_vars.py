#!/usr/bin/env python3
"""
Test script to verify environment variable expansion in config.
"""

import os
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from twickenham_events.config import Config


def test_environment_variables():
    """Test environment variable expansion functionality."""
    print("🔧 Testing Environment Variable Expansion")
    print("=" * 45)

    # Set some test environment variables
    test_vars = {
        "TEST_MQTT_BROKER": "test-broker.example.com",
        "TEST_MQTT_PORT": "8883",
        "TEST_GEMINI_KEY": "test-api-key-12345",
        "TWICK_MQTT_ENABLED": "true",  # Test TWICK_ prefix
    }

    for var, value in test_vars.items():
        os.environ[var] = value
        print(f"   Set {var} = {value}")

    print()

    # Create a temporary config dict with ${} syntax
    temp_config = {
        "mqtt": {
            "enabled": False,  # Will be overridden by TWICK_MQTT_ENABLED
            "broker_url": "${TEST_MQTT_BROKER}",
            "broker_port": "${TEST_MQTT_PORT}",
        },
        "ai_shortener": {
            "api_key": "${TEST_GEMINI_KEY}",
            "enabled": True,
        },
    }

    # Test the config expansion
    config = Config(temp_config)

    print("🧪 Testing Config Value Expansion:")
    print()

    # Test ${} expansion
    broker_url = config.get("mqtt.broker_url")
    broker_port = config.get("mqtt.broker_port")
    api_key = config.get("ai_shortener.api_key")

    print(f"   mqtt.broker_url: '{broker_url}' (expected: 'test-broker.example.com')")
    print(f"   mqtt.broker_port: '{broker_port}' (expected: '8883')")
    print(f"   ai_shortener.api_key: '{api_key}' (expected: 'test-api-key-12345')")
    print()

    # Test TWICK_ prefix override
    mqtt_enabled = config.get("mqtt.enabled")
    print(
        f"   mqtt.enabled: {mqtt_enabled} (expected: True - overridden by TWICK_MQTT_ENABLED)"
    )
    print()

    # Test MQTT config assembly
    print("🔗 Testing MQTT Config Assembly:")
    mqtt_config = config.get_mqtt_config()
    print(f"   broker_url: {mqtt_config.get('broker_url')}")
    print(f"   broker_port: {mqtt_config.get('broker_port')}")
    print()

    # Verify results
    success = True

    if broker_url != "test-broker.example.com":
        print("❌ FAIL: broker_url expansion failed")
        success = False

    if broker_port != "8883":
        print("❌ FAIL: broker_port expansion failed")
        success = False

    if api_key != "test-api-key-12345":
        print("❌ FAIL: api_key expansion failed")
        success = False

    if not mqtt_enabled:
        print("❌ FAIL: TWICK_ prefix override failed")
        success = False

    # Clean up environment variables
    for var in test_vars:
        del os.environ[var]

    if success:
        print("✅ All environment variable tests passed!")
        return True
    else:
        print("❌ Some environment variable tests failed!")
        return False


if __name__ == "__main__":
    try:
        success = test_environment_variables()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        sys.exit(1)
