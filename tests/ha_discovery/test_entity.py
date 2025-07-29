# tests/ha_discovery/test_entity.py

import json
import pytest
from core.ha_discovery.entity import Sensor


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


def test_sensor_initialization(sample_sensor_config):
    """Test that the Sensor class initializes correctly."""
    sensor = Sensor(**sample_sensor_config)
    assert sensor.name == "Test Sensor"
    assert sensor.unique_id == "test_sensor_01"
    assert sensor.component == "sensor"


def test_get_config_topic(sample_sensor_config):
    """Test the generation of the MQTT discovery config topic."""
    sensor = Sensor(**sample_sensor_config)
    discovery_prefix = "homeassistant"
    expected_topic = "homeassistant/sensor/test_sensor_01/config"
    assert sensor.get_config_topic(discovery_prefix) == expected_topic


@pytest.fixture
def sample_device_info():
    """Provides a sample device information dictionary."""
    return {
        "identifiers": ["test_device_01"],
        "name": "Test Device",
        "manufacturer": "Test Corp"
    }


def test_get_config_payload(sample_sensor_config, sample_device_info):
    """Test the generation of the JSON configuration payload with device info."""
    sensor = Sensor(**sample_sensor_config)
    payload_str = sensor.get_config_payload(sample_device_info)
    payload_dict = json.loads(payload_str)

    # Check that all keys from the sensor config are in the payload
    for key, value in sample_sensor_config.items():
        assert payload_dict[key] == value

    # Check that the device info is correctly included
    assert "device" in payload_dict
    assert payload_dict["device"] == sample_device_info

    # Ensure no extra top-level keys were added
    assert len(payload_dict) == len(sample_sensor_config) + 1
