"""Additional tests for configuration enhancements and integration scenarios."""

from unittest.mock import MagicMock, patch

from core.__main__ import load_environment
from core.config import Config


class TestEnvironmentLoading:
    """Test the enhanced environment loading function."""

    def test_load_environment_calls_load_dotenv(self):
        """Test that load_environment calls load_dotenv correctly."""
        with patch("core.__main__.Path") as mock_path:
            with patch("core.__main__.load_dotenv") as mock_load_dotenv:
                # Mock Path.exists to return True for both files
                mock_path_instance = MagicMock()
                mock_path_instance.exists.return_value = True
                mock_path.return_value = mock_path_instance

                load_environment()

                # Should be called twice - once for parent, once for project
                assert mock_load_dotenv.call_count == 2

    def test_load_environment_handles_missing_files(self):
        """Test loading when .env files don't exist."""
        with patch("core.__main__.Path") as mock_path:
            with patch("core.__main__.load_dotenv") as mock_load_dotenv:
                # Mock Path.exists to return False
                mock_path_instance = MagicMock()
                mock_path_instance.exists.return_value = False
                mock_path.return_value = mock_path_instance

                load_environment()

                # Should still be called twice, but with non-existent files
                assert mock_load_dotenv.call_count == 2


class TestConfigIntegration:
    """Test integration scenarios with the enhanced config."""

    def test_config_with_real_mqtt_structure(self):
        """Test config with realistic MQTT configuration structure."""
        config_data = {
            "mqtt": {
                "enabled": True,
                "broker_url": "test.broker.com",
                "broker_port": "8883",  # String that should be converted
                "client_id": "test_client",
                "security": "username",
                "auth": {"username": "test_user", "password": "test_pass"},
                "tls": None,
                "max_retries": 5,
            }
        }

        config = Config(config_data=config_data)
        mqtt_config = config.get_mqtt_config()

        # Verify the complete MQTT config structure
        assert mqtt_config["broker_url"] == "test.broker.com"
        assert mqtt_config["broker_port"] == 8883  # Should be converted to int
        assert isinstance(mqtt_config["broker_port"], int)
        assert mqtt_config["client_id"] == "test_client"
        assert mqtt_config["security"] == "username"
        assert mqtt_config["auth"]["username"] == "test_user"
        assert mqtt_config["auth"]["password"] == "test_pass"
        assert mqtt_config["tls"] is None
        assert mqtt_config["max_retries"] == 5

    def test_mqtt_config_with_defaults(self):
        """Test MQTT config when some values are missing."""
        config_data = {
            "mqtt": {
                "broker_url": "test.broker.com",
                "security": "none",
            }
        }

        config = Config(config_data=config_data)
        mqtt_config = config.get_mqtt_config()

        # Verify defaults are applied correctly
        assert mqtt_config["broker_url"] == "test.broker.com"
        assert mqtt_config["broker_port"] == 1883  # Default
        assert mqtt_config["client_id"] == "twickenham_event_publisher"  # Default
        assert mqtt_config["security"] == "none"
        assert mqtt_config["auth"]["username"] is None
        assert mqtt_config["auth"]["password"] is None
        assert mqtt_config["tls"] is None  # Default
        assert mqtt_config["max_retries"] == 3  # Default


class TestMainIntegration:
    """Test integration scenarios for the main script."""

    def test_load_environment_is_called(self):
        """Test that load_environment is called in main."""
        with patch("core.__main__.load_environment") as mock_load_env:
            with patch("core.__main__.Config") as mock_config:
                with patch("core.__main__.fetch_events", return_value=[]):
                    mock_config_instance = MagicMock()
                    mock_config_instance.get.return_value = "test_value"
                    mock_config.return_value = mock_config_instance

                    from core.__main__ import main

                    main()

                    # Verify load_environment was called
                    mock_load_env.assert_called_once()

    def test_mqtt_config_integration_in_main(self):
        """Test that MQTT config integration works in main."""
        mock_mqtt_config = {
            "broker_url": "test.broker.com",
            "broker_port": 8883,
            "client_id": "test_client",
            "security": "none",
            "auth": {"username": None, "password": None},
            "tls": None,
            "max_retries": 3,
        }

        with patch("core.__main__.load_environment"):
            with patch("core.__main__.Config") as mock_config:
                with patch(
                    "core.__main__.fetch_events", return_value=[{"test": "event"}]
                ):
                    with patch("core.__main__.summarise_events", return_value=[]):
                        with patch("core.__main__.MQTTPublisher") as mock_publisher:
                            mock_config_instance = MagicMock()
                            mock_config_instance.get.side_effect = (
                                lambda key, default=None: {
                                    "mqtt.enabled": True,
                                    "scraping.url": "test_url",
                                    "home_assistant.enabled": False,
                                }.get(key, default)
                            )
                            mock_config_instance.get_mqtt_config.return_value = (
                                mock_mqtt_config
                            )
                            mock_config.return_value = mock_config_instance

                            from core.__main__ import main

                            main()

                            # Verify MQTT config was used correctly
                            mock_config_instance.get_mqtt_config.assert_called_once()
                            mock_publisher.assert_called_once_with(**mock_mqtt_config)
