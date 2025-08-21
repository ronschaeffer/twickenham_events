"""
Tests for the configuration validation script.

Tests the validate_config.py script functionality including:
- Environment variable validation
- Config.yaml reference checking
- Boolean, port, URL, and host validation
- Missing variable detection
- Component status checking
"""

import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

# Add scripts directory to path for importing validate_config
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import validate_config


class TestConfigValidationScript:
    """Test the configuration validation script functions."""

    def test_load_env_file_valid(self):
        """Test loading a valid .env file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("# Comment line\n")
            f.write("VALID_VAR=true\n")
            f.write("ANOTHER_VAR=test_value\n")
            f.write("\n")  # Empty line
            f.write("PORT_VAR=8080\n")
            f.name = f.name

        try:
            result = validate_config.load_env_file(f.name)
            assert result == {
                "VALID_VAR": "true",
                "ANOTHER_VAR": "test_value",
                "PORT_VAR": "8080",
            }
        finally:
            os.unlink(f.name)

    def test_load_env_file_missing(self):
        """Test loading non-existent .env file."""
        result = validate_config.load_env_file("nonexistent.env")
        assert result == {}

    def test_load_config_references_valid(self):
        """Test loading config.yaml with variable references."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write('setting1: "${VAR1}"\n')
            f.write('setting2: "${VAR2}"\n')
            f.write("nested:\n")
            f.write('  value: "${NESTED_VAR}"\n')
            f.name = f.name

        try:
            result = validate_config.load_config_references(f.name)
            assert result == {"VAR1": True, "VAR2": True, "NESTED_VAR": True}
        finally:
            os.unlink(f.name)

    def test_validate_boolean_valid(self):
        """Test boolean validation with valid values."""
        valid_cases = [
            ("true", "✅"),
            ("false", "✅"),
            ("TRUE", "✅"),
            ("False", "✅"),
            ("1", "✅"),
            ("0", "✅"),
            ("yes", "✅"),
            ("no", "✅"),
            ("on", "✅"),
            ("off", "✅"),
        ]

        for value, expected_status in valid_cases:
            result = validate_config.validate_boolean("TEST_VAR", value)
            assert expected_status in result
            assert f"TEST_VAR={value}" in result

    def test_validate_boolean_invalid(self):
        """Test boolean validation with invalid values."""
        invalid_cases = ["maybe", "TEST_VAR", "123", "invalid"]

        for value in invalid_cases:
            result = validate_config.validate_boolean("TEST_VAR", value)
            assert "❌" in result
            assert "should be true/false" in result

    def test_validate_port_valid(self):
        """Test port validation with valid values."""
        valid_ports = ["1", "80", "443", "8080", "47476", "65535"]

        for port in valid_ports:
            result = validate_config.validate_port("TEST_PORT", port)
            assert "✅" in result
            assert "valid port" in result

    def test_validate_port_invalid(self):
        """Test port validation with invalid values."""
        invalid_cases = [
            ("0", "port out of range"),
            ("65536", "port out of range"),
            ("abc", "not a valid port number"),
            ("-1", "port out of range"),
        ]

        for port, expected_error in invalid_cases:
            result = validate_config.validate_port("TEST_PORT", port)
            assert "❌" in result
            assert expected_error in result

    def test_validate_url_valid(self):
        """Test URL validation with valid values."""
        valid_urls = [
            "http://example.com",
            "https://example.com:8080",
            "http://10.10.10.20:47476",
            "https://subdomain.example.com/path",
        ]

        for url in valid_urls:
            result = validate_config.validate_url("TEST_URL", url)
            assert "✅" in result
            assert "valid URL" in result

    def test_validate_url_warning(self):
        """Test URL validation with questionable values."""
        questionable_urls = ["ftp://example.com", "example.com", "localhost:8080"]

        for url in questionable_urls:
            result = validate_config.validate_url("TEST_URL", url)
            assert "⚠️" in result
            assert "should start with http://" in result

    def test_validate_host_valid(self):
        """Test host validation with valid values."""
        valid_hosts = [
            "0.0.0.0",
            "127.0.0.1",
            "localhost",
            "192.168.1.100",
            "10.10.10.20",
        ]

        for host in valid_hosts:
            result = validate_config.validate_host("TEST_HOST", host)
            assert "✅" in result
            assert "valid host" in result

    def test_validate_host_warning(self):
        """Test host validation with questionable values."""
        questionable_hosts = ["example.com", "my-server"]

        for host in questionable_hosts:
            result = validate_config.validate_host("TEST_HOST", host)
            assert "⚠️" in result
            assert "should be IP address or hostname" in result

    def test_validate_security_mode_valid(self):
        """Test MQTT security mode validation."""
        valid_modes = ["none", "username", "cert", "username_cert"]

        for mode in valid_modes:
            result = validate_config.validate_security_mode("MQTT_SECURITY", mode)
            assert "✅" in result
            assert "valid security mode" in result

    def test_validate_security_mode_invalid(self):
        """Test MQTT security mode validation with invalid values."""
        invalid_modes = ["invalid", "password", "tls", "oauth"]

        for mode in invalid_modes:
            result = validate_config.validate_security_mode("MQTT_SECURITY", mode)
            assert "❌" in result
            assert "should be: none, username, cert, or username_cert" in result


class TestConfigValidationIntegration:
    """Test the full validation script integration."""

    def test_main_function_with_valid_config(self):
        """Test main function with complete valid configuration."""
        # Create temporary files
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            config_file = config_dir / "config.yaml"

            # Write valid .env file
            env_file.write_text("""
WEB_SERVER_ENABLED=true
WEB_SERVER_HOST=0.0.0.0
WEB_SERVER_PORT=47476
WEB_SERVER_EXTERNAL_URL=http://10.10.10.20:47476
MQTT_ENABLED=true
MQTT_BROKER_URL=10.10.10.20
MQTT_BROKER_PORT=1883
""")

            # Write config.yaml with references
            config_file.write_text("""
web_server:
  enabled: "${WEB_SERVER_ENABLED}"
  host: "${WEB_SERVER_HOST}"
  port: "${WEB_SERVER_PORT}"
mqtt:
  enabled: "${MQTT_ENABLED}"
  broker_url: "${MQTT_BROKER_URL}"
  broker_port: "${MQTT_BROKER_PORT}"
""")

            # Mock the file paths and run validation
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                # Import and reload to use new directory
                import importlib

                importlib.reload(validate_config)

                # Capture output by mocking print
                with patch("builtins.print") as mock_print:
                    result = validate_config.main()

                # Should return 0 for success since all variables are present
                assert result == 0

                # Check that validation messages were printed
                printed_output = "\\n".join(
                    call.args[0] for call in mock_print.call_args_list
                )
                assert "settings valid" in printed_output
                assert "Configuration complete" in printed_output

            finally:
                os.chdir(original_cwd)

    def test_main_function_with_missing_vars(self):
        """Test main function with missing environment variables."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            config_file = config_dir / "config.yaml"

            # Write incomplete .env file
            env_file.write_text("WEB_SERVER_ENABLED=true\\n")

            # Write config.yaml with more references
            config_file.write_text("""
web_server:
  enabled: "${WEB_SERVER_ENABLED}"
  host: "${WEB_SERVER_HOST}"
  port: "${WEB_SERVER_PORT}"
""")

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                import importlib

                importlib.reload(validate_config)

                with patch("builtins.print") as mock_print:
                    result = validate_config.main()

                # Should return 1 for failure due to missing variables
                assert result == 1

                printed_output = "\\n".join(
                    call.args[0] for call in mock_print.call_args_list
                )
                assert "missing from .env" in printed_output

            finally:
                os.chdir(original_cwd)


if __name__ == "__main__":
    import pytest

    pytest.main([__file__])
