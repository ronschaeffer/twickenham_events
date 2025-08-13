"""Integration-style test for service cycle using mocked MQTT client.

This test simulates a minimal service run (startup + one interval cycle)
by invoking the internal run_cycle logic through a simplified harness.
We avoid spinning real threads; instead we patch MQTT and directly call
publish_all_discovery and AvailabilityPublisher.
"""

from unittest.mock import MagicMock, patch

from twickenham_events.config import Config
from twickenham_events.discovery_helper import AVAILABILITY_TOPIC, publish_all_discovery
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
        availability = AvailabilityPublisher(fake_paho)

        # Publish discovery (buttons + availability sensor)
        publish_all_discovery(fake_paho, config)
        availability.online()

        # Simulate one publish cycle (no events)
        mqtt_client.publish_events(
            [], ai_processor=None, extra_status={"last_run_ts": 1}
        )

    # Assertions: availability online published
    avail_publishes = [
        c for c in fake_paho.publish.call_args_list if c.args[0] == AVAILABILITY_TOPIC
    ]
    assert any(c.args[1] == "online" for c in avail_publishes)

    # Discovery topics published (at least 3: two buttons + binary sensor)
    discovery_topics = [
        c.args[0] for c in fake_paho.publish.call_args_list if "/config" in c.args[0]
    ]
    # Accept either legacy short prefix (tw_events_*) or new standardized (twickenham_events_*)
    assert any(
        "button/twickenham_events_refresh" in t or "button/tw_events_refresh" in t
        for t in discovery_topics
    )
    assert any(
        "button/twickenham_events_clear_cache" in t
        or "button/tw_events_clear_cache" in t
        for t in discovery_topics
    )
    # Availability binary sensor now standardized to full prefix unique_id
    assert any(
        "binary_sensor/twickenham_events_availability" in t
        or "binary_sensor/tw_events_availability" in t
        for t in discovery_topics
    )

    # Status publish included last_run_ts
    status_payloads = [
        c.args[1]
        for c in mock_pub_instance.publish.call_args_list
        if c.args[0] == "twickenham_events/status"
    ]
    assert status_payloads and status_payloads[0]["last_run_ts"] == 1
