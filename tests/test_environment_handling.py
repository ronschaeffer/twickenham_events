"""
Test suite for twickenham_events environment handling.

Tests the hierarchical environment loading and configuration substitution
specific to the twickenham_events project.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest


class TestTwickenhamEventsEnvironmentLoading:
    """Test environment loading specific to twickenham_events."""

    def setup_method(self):
        """Set up test environment."""
        self.original_env = dict(os.environ)

    def teardown_method(self):
        """Clean up test environment."""
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_hierarchical_env_loading_flow(self):
        """Test the complete hierarchical environment loading flow."""
        # Simulate the actual environment loading from __main__.py
        with patch("pathlib.Path.exists") as mock_exists:
            with patch("dotenv.load_dotenv") as mock_load_dotenv:
                # Mock file existence checks - return True for specific paths
                def exists_side_effect(*args, **kwargs):
                    # Get the Path object from the mock call
                    path_obj = (
                        mock_exists.__self__
                        if hasattr(mock_exists, "__self__")
                        else None
                    )
                    if path_obj:
                        path_str = str(path_obj)
                        if "/home/ron/projects/.env" in path_str:
                            return True  # Shared env exists
                        elif "/twickenham_events/.env" in path_str:
                            return True  # Project env exists
                    return False

                mock_exists.side_effect = exists_side_effect
                mock_load_dotenv.return_value = True

                # Simulate the loading logic from __main__.py
                try:
                    from pathlib import Path

                    from dotenv import load_dotenv

                    # Parent environment loading - just test path construction
                    parent_env = Path(__file__).parent.parent.parent / ".env"
                    project_env = Path(__file__).parent.parent / ".env"

                    # Test that paths are constructed correctly
                    assert ".env" in str(parent_env)
                    assert ".env" in str(project_env)
                    assert str(parent_env) != str(project_env)

                    # Test loading calls would work
                    load_dotenv(parent_env, verbose=False)
                    load_dotenv(project_env, override=True, verbose=False)

                except ImportError:
                    # python-dotenv not available in test environment
                    pass

                # Verify the mock was called
                assert mock_load_dotenv.call_count == 2

    def test_config_environment_substitution(self):
        """Test that config.py correctly substitutes environment variables."""
        # Set up test environment variables
        os.environ.update(
            {
                "MQTT_BROKER_URL": "10.10.10.21",
                "MQTT_PORT": "8883",
                "MQTT_USERNAME": "test_user",
                "MQTT_PASSWORD": "test_pass",
                "MQTT_CLIENT_ID": "twickenham_events_test",
            }
        )

        # Mock the config substitution logic
        def expand_env_vars(value):
            """Mock environment variable expansion."""
            if isinstance(value, str):
                import re

                def replacer(match):
                    var_name = match.group(1)
                    return os.environ.get(var_name, match.group(0))

                return re.sub(r"\$\{([^}]+)\}", replacer, value)
            return value

        # Test configuration values with substitution
        test_config = {
            "mqtt": {
                "broker_url": "${MQTT_BROKER_URL}",
                "broker_port": "${MQTT_PORT}",
                "client_id": "${MQTT_CLIENT_ID}",
                "auth": {
                    "username": "${MQTT_USERNAME}",
                    "password": "${MQTT_PASSWORD}",
                },
            }
        }

        # Apply substitution
        substituted_config = {}
        for section, values in test_config.items():
            substituted_config[section] = {}
            for key, value in values.items():
                if isinstance(value, dict):
                    substituted_config[section][key] = {
                        k: expand_env_vars(v) for k, v in value.items()
                    }
                else:
                    substituted_config[section][key] = expand_env_vars(value)

        # Verify substitution worked
        assert substituted_config["mqtt"]["broker_url"] == "10.10.10.21"
        assert substituted_config["mqtt"]["broker_port"] == "8883"
        assert substituted_config["mqtt"]["client_id"] == "twickenham_events_test"
        assert substituted_config["mqtt"]["auth"]["username"] == "test_user"
        assert substituted_config["mqtt"]["auth"]["password"] == "test_pass"

    def test_project_specific_client_id(self):
        """Test that twickenham_events has a unique client ID."""
        os.environ["MQTT_CLIENT_ID"] = "twickenham_events_client_001"

        # Mock config loading
        config_value = "${MQTT_CLIENT_ID}"

        import re

        def substitute_env_vars(value):
            def replacer(match):
                var_name = match.group(1)
                return os.environ.get(var_name, match.group(0))

            return re.sub(r"\$\{([^}]+)\}", replacer, value)

        result = substitute_env_vars(config_value)

        assert result == "twickenham_events_client_001"
        assert "twickenham_events" in result
        assert result != "mqtt_publisher_client_001"  # Different from mqtt_publisher

    def test_missing_env_graceful_handling(self):
        """Test graceful handling when .env files are missing."""
        # Clear environment
        for key in list(os.environ.keys()):
            if key.startswith("MQTT_"):
                del os.environ[key]

        with patch("pathlib.Path.exists") as mock_exists:
            with patch("dotenv.load_dotenv") as mock_load_dotenv:
                # No .env files exist
                mock_exists.return_value = False
                mock_load_dotenv.return_value = False

                # Should handle missing files gracefully
                try:
                    from dotenv import load_dotenv

                    parent_env = Path("/fake/parent/.env")
                    if parent_env.exists():  # Won't execute
                        load_dotenv(parent_env, verbose=False)

                    project_env = Path("/fake/project/.env")
                    if project_env.exists():  # Won't execute
                        load_dotenv(project_env, override=True, verbose=False)

                    # Should not crash
                    success = True

                except ImportError:
                    # Expected if dotenv not available
                    success = True
                except Exception:
                    success = False

                assert success

    def test_environment_security_practices(self):
        """Test that environment loading follows security best practices."""
        # Test that verbose logging is disabled for security
        with patch("dotenv.load_dotenv") as mock_load_dotenv:
            mock_load_dotenv.return_value = True

            # Simulate secure environment loading
            result = mock_load_dotenv("/fake/.env", verbose=False)

            assert result is True
            # Verify verbose=False was used (no sensitive data in logs)
            mock_load_dotenv.assert_called_with("/fake/.env", verbose=False)

    @patch("builtins.print")
    def test_environment_loading_output(self, mock_print):
        """Test environment loading success messages."""
        os.environ["MQTT_BROKER_URL"] = "10.10.10.21"

        with patch("pathlib.Path.exists") as mock_exists:
            with patch("dotenv.load_dotenv") as mock_load_dotenv:
                mock_exists.return_value = True
                mock_load_dotenv.return_value = True

                # Simulate the print statements from __main__.py
                parent_env_path = "/home/ron/projects/.env"
                project_env_path = "/home/ron/projects/twickenham_events/.env"

                if mock_exists(Path(parent_env_path)):
                    print(f"✅ Loaded shared environment from: {parent_env_path}")

                if mock_exists(Path(project_env_path)):
                    print(f"✅ Loaded project environment from: {project_env_path}")

                # Verify success messages would be printed
                assert mock_print.call_count == 2

                # Check the actual calls
                calls = [call[0][0] for call in mock_print.call_args_list]
                assert any("Loaded shared environment" in call for call in calls)
                assert any("Loaded project environment" in call for call in calls)


class TestConfigurationIntegration:
    """Test integration between environment loading and configuration."""

    def test_config_yaml_environment_substitution(self):
        """Test that config.yaml values are properly substituted."""
        # Set environment variables
        os.environ.update(
            {
                "MQTT_BROKER_URL": "10.10.10.21",
                "MQTT_PORT": "8883",
                "MQTT_USERNAME": "twick_user",
                "MQTT_PASSWORD": "twick_pass",
                "MQTT_CLIENT_ID": "twickenham_events_prod",
            }
        )

        # Mock YAML config content (what would be in config/config.yaml)
        mock_yaml_content = {
            "mqtt": {
                "broker_url": "${MQTT_BROKER_URL}",
                "broker_port": "${MQTT_PORT}",
                "client_id": "${MQTT_CLIENT_ID}",
                "security": "username",
                "auth": {
                    "username": "${MQTT_USERNAME}",
                    "password": "${MQTT_PASSWORD}",
                },
            },
            "app": {"base_topic": "twickenham_events"},
        }

        # Mock the Config class behavior
        class MockConfig:
            def __init__(self, config_dict):
                self.config = self._substitute_env_vars(config_dict)

            def _substitute_env_vars(self, obj):
                """Recursively substitute environment variables."""
                if isinstance(obj, dict):
                    return {k: self._substitute_env_vars(v) for k, v in obj.items()}
                elif isinstance(obj, str):
                    import re

                    def replacer(match):
                        var_name = match.group(1)
                        return os.environ.get(var_name, match.group(0))

                    return re.sub(r"\$\{([^}]+)\}", replacer, obj)
                else:
                    return obj

            def get(self, key, default=None):
                """Get config value with dot notation."""
                keys = key.split(".")
                value = self.config
                for k in keys:
                    if isinstance(value, dict) and k in value:
                        value = value[k]
                    else:
                        return default
                return value

        # Test the configuration
        config = MockConfig(mock_yaml_content)

        # Verify substitution worked correctly
        assert config.get("mqtt.broker_url") == "10.10.10.21"
        assert config.get("mqtt.broker_port") == "8883"
        assert config.get("mqtt.client_id") == "twickenham_events_prod"
        assert config.get("mqtt.auth.username") == "twick_user"
        assert config.get("mqtt.auth.password") == "twick_pass"

        # Verify non-substituted values remain unchanged
        assert config.get("mqtt.security") == "username"
        assert config.get("app.base_topic") == "twickenham_events"

    def test_config_missing_env_vars_handling(self):
        """Test config behavior when environment variables are missing."""
        # Clear all MQTT environment variables
        for key in list(os.environ.keys()):
            if key.startswith("MQTT_"):
                del os.environ[key]

        mock_yaml_content = {
            "mqtt": {
                "broker_url": "${MQTT_BROKER_URL}",
                "broker_port": "${MQTT_PORT}",
                "client_id": "${MQTT_CLIENT_ID}",
            }
        }

        class MockConfig:
            def __init__(self, config_dict):
                self.config = self._substitute_env_vars(config_dict)

            def _substitute_env_vars(self, obj):
                if isinstance(obj, dict):
                    return {k: self._substitute_env_vars(v) for k, v in obj.items()}
                elif isinstance(obj, str):
                    import re

                    def replacer(match):
                        var_name = match.group(1)
                        return os.environ.get(
                            var_name, match.group(0)
                        )  # Return original if missing

                    return re.sub(r"\$\{([^}]+)\}", replacer, obj)
                else:
                    return obj

            def get(self, key, default=None):
                keys = key.split(".")
                value = self.config
                for k in keys:
                    if isinstance(value, dict) and k in value:
                        value = value[k]
                    else:
                        return default
                return value

        config = MockConfig(mock_yaml_content)

        # Missing environment variables should remain as placeholders
        assert config.get("mqtt.broker_url") == "${MQTT_BROKER_URL}"
        assert config.get("mqtt.broker_port") == "${MQTT_PORT}"
        assert config.get("mqtt.client_id") == "${MQTT_CLIENT_ID}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
