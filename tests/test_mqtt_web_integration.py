"""
Test enhanced MQTT status reporting with web server URLs.

This test verifies that the MQTT client properly includes web server
status information in the status payload for Home Assistant integration.
"""

import os
from unittest.mock import patch

from twickenham_events.config import Config
from twickenham_events.mqtt_client import MQTTClient, _get_web_server_status


class TestMQTTWebServerIntegration:
    """Test MQTT integration with web server status."""

    def test_web_server_status_disabled(self):
        """Test web server status when disabled."""
        # Mock the environment variable to ensure web server is disabled
        with patch.dict(os.environ, {"WEB_SERVER_ENABLED": "false"}, clear=False):
            config = Config.from_defaults()
            assert not config.web_enabled

            status = _get_web_server_status(config)
            assert status == {}

    def test_web_server_status_enabled_internal(self):
        """Test web server status with internal URLs only."""
        # Clear environment variables to ensure clean test
        with patch.dict(os.environ, {}, clear=True):
            config = Config.from_defaults()
            config._data["web_server"]["enabled"] = True
            config._data["web_server"]["host"] = "localhost"
            config._data["web_server"]["port"] = 8080

            status = _get_web_server_status(config)

            assert status["enabled"] is True
            assert status["base_url"] == "http://localhost:8080"
            assert status["internal_binding"] == "http://localhost:8080"
            assert status["external_url_base"] is None

            # Check URLs
            urls = status["urls"]
            assert urls["calendar"] == "http://localhost:8080/calendar"
            assert urls["events"] == "http://localhost:8080/events"
            assert (
                urls["calendar_direct"] == "http://localhost:8080/twickenham_events.ics"
            )

            # Check Home Assistant specific fields
            ha = status["home_assistant"]
            assert ha["calendar_url"] == "http://localhost:8080/calendar"
            assert ha["events_json_url"] == "http://localhost:8080/events"
            assert ha["webhook_ready"] is True

    def test_web_server_status_external_url(self):
        """Test web server status with external URL base."""
        # Clear environment variables to ensure clean test
        with patch.dict(os.environ, {}, clear=True):
            config = Config.from_defaults()
            config._data["web_server"]["enabled"] = True
            config._data["web_server"]["host"] = "0.0.0.0"
            config._data["web_server"]["port"] = 8080
            config._data["web_server"]["external_url_base"] = (
                "https://twickenham.example.com"
            )

            status = _get_web_server_status(config)

            assert status["enabled"] is True
            assert status["base_url"] == "https://twickenham.example.com"
            assert status["internal_binding"] == "http://0.0.0.0:8080"
            assert status["external_url_base"] == "https://twickenham.example.com"

            # URLs should use external base
            urls = status["urls"]
            assert urls["calendar"] == "https://twickenham.example.com/calendar"
            assert urls["events"] == "https://twickenham.example.com/events"

    def test_web_server_status_localhost_binding(self):
        """Test that 0.0.0.0 binding auto-detects the best IP address."""
        # Clear environment variables to ensure clean test
        with patch.dict(os.environ, {}, clear=True):
            config = Config.from_defaults()
            config._data["web_server"]["enabled"] = True
            config._data["web_server"]["host"] = "0.0.0.0"
            config._data["web_server"]["port"] = 9090

            status = _get_web_server_status(config)

            # Should auto-detect a usable IP address (not 0.0.0.0)
            base_url = status["base_url"]
            assert base_url.startswith("http://")
            assert ":9090" in base_url
        assert "0.0.0.0" not in base_url  # Should not use the bind address

        # The detected IP should be a valid IPv4 address
        import re

        ip_match = re.search(r"http://(\d+\.\d+\.\d+\.\d+):9090", base_url)
        assert ip_match is not None, f"Expected valid IP in URL: {base_url}"

    def test_mqtt_client_with_web_server(self, monkeypatch):
        """Test MQTT client includes web server status in payload."""
        config = Config.from_defaults()
        config._data["web_server"]["enabled"] = True
        config._data["web_server"]["external_url_base"] = "https://test.example.com"
        config._data["mqtt"]["enabled"] = True
        config._data["mqtt"]["topics"]["status"] = "test/status"

        # Mock the publisher to capture published data
        published_data = []

        class MockPublisher:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                pass

            def publish(self, topic, payload, retain=False):
                published_data.append((topic, payload))
                return True

        monkeypatch.setattr(
            "twickenham_events.mqtt_client.MQTTPublisher", MockPublisher
        )

        client = MQTTClient(config)
        client.publish_events([{"fixture": "Test Match", "date": "2099-01-01"}])

        # Find the status payload
        status_payload = None
        for topic, payload in published_data:
            if topic == "test/status":
                import json

                status_payload = (
                    json.loads(payload) if isinstance(payload, str) else payload
                )
                break

        assert status_payload is not None
        assert "web_server" in status_payload

        web_server = status_payload["web_server"]
        assert web_server["enabled"] is True
        assert web_server["base_url"] == "https://test.example.com"
        assert "home_assistant" in web_server
        assert (
            web_server["home_assistant"]["calendar_url"]
            == "https://test.example.com/calendar"
        )
