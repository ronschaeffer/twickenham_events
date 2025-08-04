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
                "broker_url": "test.broker.com",  # Add required field
                "auth": {
                    "username": "${TEST_USERNAME}",
                    "password": "${TEST_PASSWORD}",
                },
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


def test_config_validation_missing_broker_url():
    """Test that missing broker_url raises proper error."""
    config_data = {"mqtt": {"broker_port": 1883, "client_id": "test_client"}}

    config = Config(config_data=config_data)

    try:
        config.get_mqtt_config()
        raise AssertionError("Should have raised ValueError for missing broker_url")
    except ValueError as e:
        assert "broker_url is required" in str(e)


def test_config_validation_invalid_port():
    """Test that invalid port values raise proper errors."""
    test_cases = [
        ("invalid_port", "must be 1-65535"),
        (0, "must be 1-65535"),
        (65536, "must be 1-65535"),
        (-1, "must be 1-65535"),
    ]

    for invalid_port, expected_error in test_cases:
        config_data = {
            "mqtt": {"broker_url": "test.broker.com", "broker_port": invalid_port}
        }

        config = Config(config_data=config_data)

        try:
            config.get_mqtt_config()
            raise AssertionError(
                f"Should have raised ValueError for port: {invalid_port}"
            )
        except ValueError as e:
            assert expected_error in str(e)


def test_string_port_conversion():
    """Test that string ports are properly converted to integers."""
    config_data = {
        "mqtt": {
            "broker_url": "test.broker.com",
            "broker_port": "8883",  # String port
            "max_retries": "5",  # String retries
        }
    }

    config = Config(config_data=config_data)
    mqtt_config = config.get_mqtt_config()

    # Verify conversion happened
    assert isinstance(mqtt_config["broker_port"], int)
    assert mqtt_config["broker_port"] == 8883
    assert isinstance(mqtt_config["max_retries"], int)
    assert mqtt_config["max_retries"] == 5
