# tests/ha_discovery/test_status_sensor.py

import pytest
from unittest.mock import MagicMock
from core.ha_discovery.status_sensor import StatusSensor
from core.ha_discovery.device import Device
from core.config import Config


@pytest.fixture
def mock_config():
    """Provides a mock Config object."""
    config = MagicMock(spec=Config)
    config.get.side_effect = lambda key, default=None: {
        'home_assistant.discovery_prefix': 'homeassistant',
        'mqtt.base_topic': 'twickenham_events',
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


def test_status_sensor_initialization(mock_config, mock_device):
    """Test that the StatusSensor class initializes correctly."""
    sensor = StatusSensor(config=mock_config, device=mock_device)
    assert sensor.name == "Status"
    assert sensor.unique_id == "status"
    assert sensor.component == "binary_sensor"
    assert sensor.device_class == "problem"
    assert sensor.state_topic == "twickenham_events/status"


def test_status_sensor_get_config_payload(mock_config, mock_device):
    """Test the generation of the JSON configuration payload for the status sensor."""
    sensor = StatusSensor(config=mock_config, device=mock_device)
    payload_dict = sensor.get_config_payload()

    expected_keys = [
        "name",
        "unique_id",
        "device",
        "state_topic",
        "object_id",
        "device_class",
        "value_template",
        "json_attributes_topic",
        "json_attributes_template",
    ]
    for key in expected_keys:
        assert key in payload_dict

    assert payload_dict["name"] == "Status"
    assert payload_dict["unique_id"] == "twickenham_events_status"
    assert payload_dict["object_id"] == "twickenham_events_status"
    assert payload_dict["device_class"] == "problem"
    assert payload_dict["value_template"] == "{{ 'ON' if value_json.status == 'error' else 'OFF' }}"
    assert payload_dict["json_attributes_topic"] == "twickenham_events/status"
    assert payload_dict["json_attributes_template"] == "{{ value_json | tojson }}"
    assert payload_dict["device"] == mock_device.get_device_info()
