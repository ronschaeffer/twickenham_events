"""
Tests for enhanced web server environment variable support.

Tests the new unified WEB_SERVER_EXTERNAL_URL functionality and
environment variable override behavior in the config system.
"""

import os
from unittest.mock import patch

import pytest

from twickenham_events.config import Config
from twickenham_events.network_utils import build_smart_external_url, get_docker_host_ip


class TestWebServerEnvironmentVariables:
    """Test web server environment variable handling."""

    def test_web_server_external_url_parsing(self):
        """Test WEB_SERVER_EXTERNAL_URL parsing for host IP extraction."""
        test_cases = [
            ("http://10.10.10.20:47476", "10.10.10.20"),
            ("https://example.com:8080", "example.com"),
            ("http://192.168.1.100:80", "192.168.1.100"),
            ("https://subdomain.example.com/path", "subdomain.example.com"),
        ]

        for url, expected_host in test_cases:
            with patch.dict(os.environ, {"WEB_SERVER_EXTERNAL_URL": url}, clear=False):
                detected_ip = get_docker_host_ip()
                assert detected_ip == expected_host

    def test_web_server_external_url_invalid_parsing(self):
        """Test WEB_SERVER_EXTERNAL_URL with invalid URLs."""
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",
            "just-text",
            "",
        ]

        for invalid_url in invalid_urls:
            with patch.dict(
                os.environ, {"WEB_SERVER_EXTERNAL_URL": invalid_url}, clear=False
            ):
                # Should fall back to other detection methods
                detected_ip = get_docker_host_ip()
                # Should not crash and should return None or fallback value
                assert detected_ip is None or detected_ip != invalid_url

    def test_web_server_external_url_precedence(self):
        """Test that WEB_SERVER_EXTERNAL_URL takes precedence over DOCKER_HOST_IP."""
        with patch.dict(
            os.environ,
            {
                "WEB_SERVER_EXTERNAL_URL": "http://10.10.10.20:47476",
                "DOCKER_HOST_IP": "192.168.1.100",
            },
            clear=False,
        ):
            detected_ip = get_docker_host_ip()
            # Should use the IP from WEB_SERVER_EXTERNAL_URL, not DOCKER_HOST_IP
            assert detected_ip == "10.10.10.20"

    def test_legacy_docker_host_ip_fallback(self):
        """Test fallback to legacy DOCKER_HOST_IP when WEB_SERVER_EXTERNAL_URL not set."""
        # Clear WEB_SERVER_EXTERNAL_URL and set DOCKER_HOST_IP
        env_vars = {"DOCKER_HOST_IP": "192.168.1.100"}
        if "WEB_SERVER_EXTERNAL_URL" in os.environ:
            del os.environ["WEB_SERVER_EXTERNAL_URL"]

        with patch.dict(os.environ, env_vars, clear=False):
            detected_ip = get_docker_host_ip()
            assert detected_ip == "192.168.1.100"

    def test_unified_external_url_with_smart_url_building(self):
        """Test unified external URL functionality with smart URL building."""
        with patch.dict(
            os.environ,
            {"WEB_SERVER_EXTERNAL_URL": "http://10.10.10.20:47476"},
            clear=False,
        ):
            # Should use the external URL directly when provided
            result = build_smart_external_url(
                "0.0.0.0", 47476, external_url_base="http://10.10.10.20:47476"
            )
            assert result == "http://10.10.10.20:47476"

    def test_web_server_config_environment_overrides(self):
        """Test that environment variables override config.yaml values."""
        config = Config.from_defaults()

        # Test each web server environment variable override
        test_overrides = {
            "WEB_SERVER_ENABLED": ("true", True),
            "WEB_SERVER_HOST": ("192.168.1.100", "192.168.1.100"),
            "WEB_SERVER_PORT": ("9090", 9090),
            "WEB_SERVER_EXTERNAL_URL": ("http://example.com", "http://example.com"),
            "WEB_SERVER_ACCESS_LOG": ("true", True),
            "WEB_SERVER_CORS_ENABLED": ("false", False),
            "WEB_SERVER_CORS_ORIGINS": (
                "http://localhost:3000,https://example.com",
                ["http://localhost:3000", "https://example.com"],
            ),
        }

        for env_var, (env_value, expected_result) in test_overrides.items():
            with patch.dict(os.environ, {env_var: env_value}, clear=False):
                if env_var == "WEB_SERVER_ENABLED":
                    assert config.web_enabled == expected_result
                elif env_var == "WEB_SERVER_HOST":
                    assert config.web_host == expected_result
                elif env_var == "WEB_SERVER_PORT":
                    assert config.web_port == expected_result
                elif env_var == "WEB_SERVER_EXTERNAL_URL":
                    assert config.web_external_url_base == expected_result
                elif env_var == "WEB_SERVER_ACCESS_LOG":
                    assert config.web_access_log == expected_result
                elif env_var == "WEB_SERVER_CORS_ENABLED":
                    assert config.web_cors_enabled == expected_result
                elif env_var == "WEB_SERVER_CORS_ORIGINS":
                    assert config.web_cors_origins == expected_result

    def test_web_server_boolean_parsing(self):
        """Test boolean environment variable parsing for web server settings."""
        boolean_test_cases = [
            ("true", True),
            ("false", False),
            ("1", True),
            ("0", False),
            ("yes", True),
            ("no", False),
            ("on", True),
            ("off", False),
            ("TRUE", True),
            ("FALSE", False),
        ]

        config = Config.from_defaults()

        for env_value, expected in boolean_test_cases:
            with patch.dict(os.environ, {"WEB_SERVER_ENABLED": env_value}, clear=False):
                assert config.web_enabled == expected

    def test_web_server_port_parsing(self):
        """Test port number parsing and validation."""
        config = Config.from_defaults()

        # Valid port numbers
        valid_ports = ["80", "443", "8080", "47476", "65535"]
        for port_str in valid_ports:
            with patch.dict(os.environ, {"WEB_SERVER_PORT": port_str}, clear=False):
                assert config.web_port == int(port_str)

        # Invalid port should fall back to config default
        with patch.dict(os.environ, {"WEB_SERVER_PORT": "invalid"}, clear=False):
            # Should fall back to default or handle gracefully
            port = config.web_port
            assert isinstance(port, int)
            assert 1 <= port <= 65535

    def test_cors_origins_parsing(self):
        """Test CORS origins parsing from environment variable."""
        config = Config.from_defaults()

        test_cases = [
            ("*", ["*"]),
            ("http://localhost:3000", ["http://localhost:3000"]),
            (
                "http://localhost:3000,https://example.com",
                ["http://localhost:3000", "https://example.com"],
            ),
            (
                "http://localhost:3000, https://example.com, http://test.com",
                ["http://localhost:3000", "https://example.com", "http://test.com"],
            ),
        ]

        for env_value, expected in test_cases:
            with patch.dict(
                os.environ, {"WEB_SERVER_CORS_ORIGINS": env_value}, clear=False
            ):
                assert config.web_cors_origins == expected


class TestConfigEnvironmentIntegration:
    """Test integration between .env files and config.yaml."""

    def test_environment_variable_substitution(self):
        """Test that ${VARIABLE} substitution works in config.yaml."""
        config = Config.from_defaults()

        # Test substitution for web server settings
        with patch.dict(
            os.environ,
            {
                "WEB_SERVER_ENABLED": "true",
                "WEB_SERVER_HOST": "0.0.0.0",
                "WEB_SERVER_PORT": "47476",
            },
            clear=False,
        ):
            assert config.web_enabled is True
            assert config.web_host == "0.0.0.0"
            assert config.web_port == 47476

    def test_missing_environment_variables(self):
        """Test behavior when referenced environment variables are missing."""
        config = Config.from_defaults()

        # Clear specific environment variables
        vars_to_clear = ["WEB_SERVER_ENABLED", "WEB_SERVER_HOST", "WEB_SERVER_PORT"]
        for var in vars_to_clear:
            if var in os.environ:
                del os.environ[var]

        # Should fall back to config defaults
        # (The actual behavior depends on implementation -
        # some might use None, others might have defaults)
        web_enabled = config.web_enabled
        web_host = config.web_host
        web_port = config.web_port

        # At minimum, these should not crash
        assert isinstance(web_enabled, bool)
        assert isinstance(web_host, str)
        assert isinstance(web_port, int)

    def test_docker_networking_integration(self):
        """Test integration between Docker networking and web server config."""
        with patch.dict(
            os.environ,
            {
                "WEB_SERVER_ENABLED": "true",
                "WEB_SERVER_HOST": "0.0.0.0",
                "WEB_SERVER_PORT": "47476",
                "WEB_SERVER_EXTERNAL_URL": "http://10.10.10.20:47476",
            },
            clear=False,
        ):
            config = Config.from_defaults()

            # Web server should be enabled and configured
            assert config.web_enabled is True
            assert config.web_host == "0.0.0.0"
            assert config.web_port == 47476
            assert config.web_external_url_base == "http://10.10.10.20:47476"

            # Docker host detection should use the external URL
            detected_ip = get_docker_host_ip()
            assert detected_ip == "10.10.10.20"

            # Smart URL building should use the external URL
            smart_url = build_smart_external_url(
                "0.0.0.0", 47476, external_url_base=config.web_external_url_base
            )
            assert smart_url == "http://10.10.10.20:47476"


if __name__ == "__main__":
    import pytest

    pytest.main([__file__])
