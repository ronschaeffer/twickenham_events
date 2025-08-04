"""
Test enhanced configuration following mqtt_publisher best practices.
"""

import os
from unittest.mock import patch

from core.config import Config


def test_port_auto_conversion():
    """Test that port values are automatically converted to integers."""
    config_data = {
        "mqtt": {
            "broker_port": "8883",
            "another_port": "1883",
        }
    }

    config = Config(config_data=config_data)

    # Test port auto-conversion
    assert config.get("mqtt.broker_port") == 8883
    assert isinstance(config.get("mqtt.broker_port"), int)
    assert config.get("mqtt.another_port") == 1883
    assert isinstance(config.get("mqtt.another_port"), int)


def test_mqtt_config_builder():
    """Test the MQTT configuration builder method."""
    with patch.dict(
        os.environ,
        {
            "MQTT_BROKER_URL": "test.broker.com",
            "MQTT_BROKER_PORT": "8883",
            "MQTT_CLIENT_ID": "test_client",
            "MQTT_USERNAME": "test_user",
            "MQTT_PASSWORD": "test_pass",
        },
    ):
        config_data = {
            "mqtt": {
                "broker_url": "${MQTT_BROKER_URL}",
                "broker_port": "${MQTT_BROKER_PORT}",
                "client_id": "${MQTT_CLIENT_ID}",
                "security": "username",
                "auth": {
                    "username": "${MQTT_USERNAME}",
                    "password": "${MQTT_PASSWORD}",
                },
                "tls": None,
                "max_retries": 5,
            }
        }

        config = Config(config_data=config_data)
        mqtt_config = config.get_mqtt_config()

        # Verify all expected keys are present
        expected_keys = [
            "broker_url",
            "broker_port",
            "client_id",
            "security",
            "auth",
            "tls",
            "max_retries",
        ]
        assert all(key in mqtt_config for key in expected_keys)

        # Verify environment variable substitution
        assert mqtt_config["broker_url"] == "test.broker.com"
        assert mqtt_config["broker_port"] == 8883  # Auto-converted to int
        assert mqtt_config["client_id"] == "test_client"
        assert mqtt_config["security"] == "username"
        assert mqtt_config["auth"]["username"] == "test_user"
        assert mqtt_config["auth"]["password"] == "test_pass"
        assert mqtt_config["tls"] is None
        assert mqtt_config["max_retries"] == 5

        # Verify types
        assert isinstance(mqtt_config["broker_port"], int)
        assert isinstance(mqtt_config["max_retries"], int)


def test_mqtt_config_with_defaults():
    """Test MQTT configuration with default values."""
    config_data = {
        "mqtt": {
            "broker_url": "localhost",
            "security": "none",
            "auth": {
                "username": None,
                "password": None,
            },
        }
    }

    config = Config(config_data=config_data)
    mqtt_config = config.get_mqtt_config()

    # Test defaults
    assert mqtt_config["broker_port"] == 1883  # Default port
    assert mqtt_config["client_id"] == "twickenham_event_publisher"  # Default client_id
    assert mqtt_config["max_retries"] == 3  # Default retries


def test_environment_variable_handling():
    """Test environment variable substitution in nested configs."""
    with patch.dict(
        os.environ, {"TEST_USERNAME": "env_user", "TEST_PASSWORD": "env_pass"}
    ):
        config_data = {
            "mqtt": {
                "auth": {
                    "username": "${TEST_USERNAME}",
                    "password": "${TEST_PASSWORD}",
                }
            }
        }

        config = Config(config_data=config_data)

        # Test individual access (this should work)
        assert config.get("mqtt.auth.username") == "env_user"
        assert config.get("mqtt.auth.password") == "env_pass"

        # Test via mqtt_config builder
        mqtt_config = config.get_mqtt_config()
        assert mqtt_config["auth"]["username"] == "env_user"
        assert mqtt_config["auth"]["password"] == "env_pass"
