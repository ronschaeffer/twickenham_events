"""MQTT publisher integration tests."""

from unittest.mock import MagicMock, patch

import paho.mqtt.client as mqtt


def test_mqtt_publisher_import():
    """Test that we can import the MQTT publisher from the PyPI package."""
    try:
        from ha_mqtt_publisher.publisher import MQTTPublisher

        assert MQTTPublisher is not None
        assert hasattr(MQTTPublisher, "__init__")
    except ImportError as e:
        # Skip the test if import fails in CI environment
        import pytest

        pytest.skip(f"ha_mqtt_publisher not available: {e}")


def test_mqtt_publish():
    """Basic MQTT publish test."""
    try:
        from ha_mqtt_publisher.publisher import MQTTPublisher
    except ImportError:
        import pytest

        pytest.skip("ha_mqtt_publisher not available")

    mock_client = MagicMock()
    mock_client.publish.return_value = MagicMock(rc=mqtt.MQTT_ERR_SUCCESS)

    with patch("paho.mqtt.client.Client", return_value=mock_client):
        publisher = MQTTPublisher("localhost", 1883, "test")
        publisher._connected = True

        result = publisher.publish("test/topic", "test message")
        assert result is True
        mock_client.publish.assert_called_once_with(
            "test/topic", "test message", qos=0, retain=False
        )
