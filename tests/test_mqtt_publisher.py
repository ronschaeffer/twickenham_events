from unittest.mock import MagicMock, patch

import paho.mqtt.client as mqtt


def test_mqtt_publish():
    """Basic MQTT publish test."""
    from mqtt_publisher.publisher import MQTTPublisher

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
