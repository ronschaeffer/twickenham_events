import pytest
from unittest.mock import MagicMock, patch
import json
from core.mqtt_publisher import MQTTPublisher

@pytest.fixture
def mock_mqtt():
    with patch('core.mqtt_publisher.mqtt.Client') as mock_client:
        instance = mock_client.return_value
        instance.connect = MagicMock()
        instance.disconnect = MagicMock()
        instance.publish = MagicMock()
        instance.loop_start = MagicMock()
        instance.loop_stop = MagicMock()
        yield instance

def test_mqtt_publisher_init(mock_mqtt):
    """Test MQTTPublisher initialization with various configurations."""
    # Test with basic settings
    publisher = MQTTPublisher("localhost", 1883, "test_client")
    assert not publisher._connected
    mock_mqtt.username_pw_set.assert_not_called()
    mock_mqtt.tls_set.assert_called_once()

    # Test with authentication
    publisher = MQTTPublisher("localhost", 1883, "test_client", 
                            username="user", password="pass")
    mock_mqtt.username_pw_set.assert_called_with("user", "pass")

    # Test without TLS
    publisher = MQTTPublisher("localhost", 1883, "test_client", use_tls=False)
    mock_mqtt.tls_set.assert_not_called()

def test_mqtt_publisher_connect_disconnect(mock_mqtt):
    """Test connection and disconnection."""
    publisher = MQTTPublisher("localhost", 1883, "test_client")
    
    # Test connect
    publisher.connect()
    mock_mqtt.connect.assert_called_once_with("localhost", 1883)
    mock_mqtt.loop_start.assert_called_once()
    assert publisher._connected

    # Test disconnect
    publisher.disconnect()
    mock_mqtt.loop_stop.assert_called_once()
    mock_mqtt.disconnect.assert_called_once()
    assert not publisher._connected

def test_mqtt_publisher_context_manager(mock_mqtt):
    """Test context manager functionality."""
    with MQTTPublisher("localhost", 1883, "test_client") as publisher:
        assert publisher._connected
        mock_mqtt.connect.assert_called_once()
    mock_mqtt.disconnect.assert_called_once()

def test_mqtt_publish_payload_types(mock_mqtt):
    """Test publishing different types of payloads."""
    publisher = MQTTPublisher("localhost", 1883, "test_client")
    publisher.connect()

    # Test string payload
    publisher.publish("test/topic", "test message")
    mock_mqtt.publish.assert_called_with("test/topic", "test message", 0, False)

    # Test dict payload
    test_dict = {"key": "value"}
    publisher.publish("test/topic", test_dict)
    mock_mqtt.publish.assert_called_with("test/topic", json.dumps(test_dict), 0, False)

    # Test list payload
    test_list = ["item1", "item2"]
    publisher.publish("test/topic", test_list)
    mock_mqtt.publish.assert_called_with("test/topic", json.dumps(test_list), 0, False)

def test_mqtt_publish_options(mock_mqtt):
    """Test publishing with different QoS and retain settings."""
    publisher = MQTTPublisher("localhost", 1883, "test_client")
    publisher.connect()

    # Test with QoS 1 and retain
    publisher.publish("test/topic", "test message", qos=1, retain=True)
    mock_mqtt.publish.assert_called_with("test/topic", "test message", 1, True)
