# tests/ha_discovery/test_entity.py

import json
import pytest
from core.ha_discovery.entity import Sensor
from core.config import Config
from core.ha_discovery.device import Device


@pytest.fixture
def mock_config():
    """Provides a mock Config object for tests."""
    return Config(config_data={
        'home_assistant': {'discovery_prefix': 'homeassistant'},
        'app': {'name': 'TestApp', 'version': '1.0'}
    })


@pytest.fixture
def mock_device(mock_config):
    """Provides a mock Device object."""
    return Device(mock_config)


@pytest.fixture
def sample_sensor_config():
    """Provides a sample sensor configuration dictionary."""
    return {
        "name": "Test Sensor",
        "unique_id": "test_sensor_01",
        "state_topic": "test/sensor/state",
        "value_template": "{{ value_json.temperature }}",
        "json_attributes_topic": "test/sensor/attributes",
        "json_attributes_template": "{{ value_json | tojson }}",
        "icon": "mdi:thermometer"
    }


def test_sensor_initialization(sample_sensor_config, mock_config, mock_device):
    """Test that the Sensor class initializes correctly."""
    sensor = Sensor(config=mock_config, device=mock_device,
                    **sample_sensor_config)
    assert sensor.name == "Test Sensor"
    assert sensor.unique_id == "test_sensor_01"
    assert sensor.component == "sensor"


def test_get_config_topic(sample_sensor_config, mock_config, mock_device):
    """Test the generation of the MQTT discovery config topic."""
    sensor = Sensor(config=mock_config, device=mock_device,
                    **sample_sensor_config)
    discovery_prefix = mock_config.get('home_assistant.discovery_prefix')
    expected_topic = f"{discovery_prefix}/sensor/test_sensor_01/config"
    assert sensor.get_config_topic() == expected_topic


def test_get_config_payload(sample_sensor_config, mock_device, mock_config):
    """Test the generation of the JSON configuration payload with device info."""
    sensor = Sensor(config=mock_config, device=mock_device,
                    **sample_sensor_config)
    payload_dict = sensor.get_config_payload()
    payload_str = json.dumps(payload_dict)
    payload = json.loads(payload_str)

    # Check that all original keys are present
    # Note: The 'device' key is added by the get_config_payload method
    expected_keys = list(sample_sensor_config.keys()) + ['device']
    for key in expected_keys:
        assert key in payload

    # Check that the device information is correctly embedded
    assert payload["device"] == mock_device.get_device_info()
