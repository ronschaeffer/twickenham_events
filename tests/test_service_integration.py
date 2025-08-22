"""Integration-style test for service cycle using mocked MQTT client.

This test simulates a minimal service run (startup + one interval cycle)
by invoking the internal run_cycle logic through a simplified harness.
We avoid spinning real threads; instead we patch MQTT and directly call
publish_enhanced_device_discovery and AvailabilityPublisher.
"""

from unittest.mock import MagicMock, patch

from twickenham_events.config import Config
from twickenham_events.constants import AVAILABILITY_TOPIC
from twickenham_events.enhanced_discovery import (
    publish_enhanced_device_discovery as publish_all_discovery,
)
from twickenham_events.mqtt_client import MQTTClient
from twickenham_events.service_support import AvailabilityPublisher


def test_service_startup_and_availability(monkeypatch):
    config = Config(
        {
            "mqtt": {
                "enabled": True,
                "broker": "localhost",
                "port": 1883,
                "topics": {
                    "status": "twickenham_events/status",
                    "all_upcoming": "twickenham_events/events/all_upcoming",
                    "next": "twickenham_events/events/next",
                },
                "client_id": "test-client",
            }
        }
    )

    # Patch MQTTPublisher used inside MQTTClient
    mock_pub_instance = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.__enter__.return_value = mock_pub_instance

    with (
        patch("twickenham_events.mqtt_client.MQTTPublisher", return_value=mock_ctx),
        patch("twickenham_events.mqtt_client.MQTT_AVAILABLE", True),
    ):
        mqtt_client = MQTTClient(config)

        # Simulate availability publisher with fake paho client
        fake_paho = MagicMock()
        availability = AvailabilityPublisher(fake_paho, AVAILABILITY_TOPIC)

        # Publish discovery (buttons + availability sensor)
        publish_all_discovery(fake_paho, config)
        availability.online()

        # Simulate one publish cycle (no events)
        mqtt_client.publish_events(
            [], ai_processor=None, extra_status={"last_run_ts": 1}
        )

    # Assertions: availability online published
    avail_publishes = []
    for c in fake_paho.publish.call_args_list:
        # Support both positional and keyword args
        topic = None
        if c.args:
            topic = c.args[0]
        elif "topic" in c.kwargs:
            topic = c.kwargs["topic"]
        if topic == AVAILABILITY_TOPIC:
            avail_publishes.append(c)
    assert any(c[0][1] == "online" for c in avail_publishes)

    # Discovery topics published - new enhanced discovery publishes a single device config
    discovery_topics = []
    for c in fake_paho.publish.call_args_list:
        topic = None
        if c.args:
            topic = c.args[0]
        elif "topic" in c.kwargs:
            topic = c.kwargs["topic"]
        if topic and "/config" in topic:
            discovery_topics.append(topic)
    # Should have exactly one device-level discovery topic
    assert len(discovery_topics) == 1
    assert discovery_topics[0] == "homeassistant/device/twickenham_events/config"

    # Status publish included last_run_ts
    status_payloads = [
        c[0][1]
        for c in mock_pub_instance.publish.call_args_list
        if c[0][0] == "twickenham_events/status"
    ]
    assert status_payloads and status_payloads[0]["last_run_ts"] == 1
