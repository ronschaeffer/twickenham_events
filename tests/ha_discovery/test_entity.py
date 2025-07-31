# tests/ha_discovery/test_entity.py

import json
import pytest
from unittest.mock import MagicMock
from core.ha_discovery.entity import Sensor
from core.ha_discovery.device import Device
from core.config import Config


@pytest.fixture
def mock_config():
    """Provides a mock Config object."""
    config = MagicMock(spec=Config)
    config.get.side_effect = lambda key, default=None: {
        'home_assistant.discovery_prefix': 'homeassistant',
        'app.unique_id_prefix': 'twickenham_events'
    }.get(key, default)
    return config


@pytest.fixture
def mock_device(mock_config):
    """Provides a mock Device object."""
    device = MagicMock(spec=Device)
    device.get_device_info.return_value = {
        "identifiers": ["test_device_01"],
        "name": "Test Device",
        "manufacturer": "Test Corp"
    }
    return device


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
    expected_topic = "homeassistant/sensor/test_sensor_01/config"
    assert sensor.get_config_topic() == expected_topic


def test_get_config_payload(sample_sensor_config, mock_config, mock_device):
    """Test the generation of the JSON configuration payload with device info."""
    sensor = Sensor(config=mock_config, device=mock_device,
                    **sample_sensor_config)
    payload_dict = sensor.get_config_payload()

    # Check that all keys from the sensor config are in the payload
    # Note: The 'device', 'unique_id', and 'object_id' keys are modified by get_config_payload method
    expected_keys = list(sample_sensor_config.keys()) + ['device', 'object_id']
    # Remove 'unique_id' from sample_sensor_config keys since it's modified in the payload
    expected_keys = [k for k in expected_keys if k !=
                     'unique_id'] + ['unique_id']
    for key in expected_keys:
        assert key in payload_dict

    # Check that the device info is correctly included
    assert "device" in payload_dict
    assert payload_dict["device"] == mock_device.get_device_info()

    # Check a few key values
    assert payload_dict["name"] == sample_sensor_config["name"]
    assert payload_dict["unique_id"] == f"twickenham_events_{sample_sensor_config['unique_id']}"
