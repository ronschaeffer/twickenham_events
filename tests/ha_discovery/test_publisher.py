# tests/ha_discovery/test_publisher.py

import pytest
import yaml
from unittest.mock import patch, MagicMock
from core.ha_discovery.publisher import HADiscoveryPublisher
from core.config import Config


@pytest.fixture
def mock_config(tmp_path):
    """Creates a mock Config object for testing."""
    config_content = {
        'home_assistant': {
            'enabled': True,
            'discovery_prefix': 'homeassistant'
        },
        'mqtt': {
            'broker_url': 'localhost',
            'broker_port': 1883,
            'client_id': 'test_client'
        }
    }
    config_file = tmp_path / "test_config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(config_content, f)
    return Config(str(config_file))


@pytest.fixture
def mock_entities_file(tmp_path):
    """Creates a mock entities YAML file for testing."""
    entities_content = [
        {
            "name": "Test Sensor 1",
            "unique_id": "test_sensor_01",
            "state_topic": "test/sensor1/state",
            "value_template": "{{ value_json.val1 }}",
            "json_attributes_topic": "test/sensor1/attr",
            "json_attributes_template": "{{ value_json | tojson }}",
            "icon": "mdi:test-tube"
        }
    ]
    entities_file = tmp_path / "test_entities.yaml"
    with open(entities_file, 'w') as f:
        yaml.dump(entities_content, f)
    return str(entities_file)


@patch('core.ha_discovery.publisher.MQTTPublisher')
def test_publish_discovery_topics_enabled(mock_mqtt_publisher, mock_config, mock_entities_file):
    """Test that discovery topics are published when HA integration is enabled."""
    # Arrange
    mock_publisher_instance = MagicMock()
    mock_mqtt_publisher.return_value.__enter__.return_value = mock_publisher_instance

    ha_publisher = HADiscoveryPublisher(mock_config, mock_entities_file)

    # Act
    ha_publisher.publish_discovery_topics()

    # Assert
    mock_mqtt_publisher.assert_called_once()
    mock_publisher_instance.publish.assert_called_once()

    # Check the content of the call
    call_args = mock_publisher_instance.publish.call_args
    topic = call_args[0][0]
    payload = call_args[0][1]

    assert topic == "homeassistant/sensor/test_sensor_01/config"
    assert '"name": "Test Sensor 1"' in payload
    assert '"unique_id": "test_sensor_01"' in payload


@patch('core.ha_discovery.publisher.MQTTPublisher')
def test_publish_discovery_topics_disabled(mock_mqtt_publisher, tmp_path, mock_entities_file):
    """Test that discovery topics are NOT published when HA integration is disabled."""
    # Arrange
    config_content = {
        'home_assistant': {'enabled': False},
        'mqtt': {'broker_url': 'localhost', 'broker_port': 1883, 'client_id': 'test_client'}
    }
    config_file = tmp_path / "disabled_config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(config_content, f)

    disabled_config = Config(str(config_file))
    ha_publisher = HADiscoveryPublisher(disabled_config, mock_entities_file)

    # Act
    ha_publisher.publish_discovery_topics()

    # Assert
    mock_mqtt_publisher.assert_not_called()


@patch('core.ha_discovery.publisher.MQTTPublisher')
def test_load_entities_file_not_found(mock_mqtt_publisher, mock_config):
    """Test that the publisher handles a missing entities file gracefully."""
    # Arrange
    ha_publisher = HADiscoveryPublisher(
        mock_config, "/path/to/nonexistent/file.yaml")

    # Act
    ha_publisher.publish_discovery_topics()

    # Assert
    # Should not raise an exception and entities list should be empty
    assert ha_publisher.entities == []
    # MQTTPublisher should not be instantiated if there are no entities
    mock_mqtt_publisher.assert_not_called()
