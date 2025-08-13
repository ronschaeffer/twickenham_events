from unittest.mock import MagicMock, patch

from twickenham_events.config import Config
from twickenham_events.mqtt_client import MQTTClient


def test_status_payload_fields(monkeypatch):
    # Minimal config enabling MQTT
    cfg_dict = {
        "mqtt": {
            "enabled": True,
            "broker": "localhost",
            "port": 1883,
            "tls": False,
            "topics": {
                "all_upcoming": "twickenham_events/events/all_upcoming",
                "next": "twickenham_events/events/next",
                "status": "twickenham_events/status",
            },
        },
        "ai_processor": {"shortening": {"enabled": True}},
    }
    config = Config(cfg_dict)

    # Fake events
    events = [
        {"fixture": "England vs Wales", "date": "2099-01-01"},
        {"fixture": "Concert ABC", "date": "2099-01-02"},
    ]

    mock_publisher = MagicMock()
    mock_client_ctx = MagicMock()
    mock_client_ctx.__enter__.return_value = mock_publisher

    with patch(
        "twickenham_events.mqtt_client.MQTTPublisher", return_value=mock_client_ctx
    ):
        client = MQTTClient(config)

        # Provide a dummy ai_processor which raises once to increment ai_error_count
        class DummyAI:
            calls = 0

            def get_event_type_and_icons(self, _fixture):
                DummyAI.calls += 1
                if DummyAI.calls == 1:
                    raise RuntimeError("fail once")
                return ("rugby", "🏉", "mdi:rugby")

        ai = DummyAI()
        client.publish_events(events, ai_processor=ai)

    # Collect published payloads
    published = {
        call.args[0]: call.args[1] for call in mock_publisher.publish.call_args_list
    }

    status_payload = published["twickenham_events/status"]
    assert status_payload["event_count"] == 2
    assert status_payload["ai_error_count"] == 1  # one failure
    assert "publish_error_count" in status_payload
    assert status_payload["ai_enabled"] is True
    assert "sw_version" in status_payload

    today_payload = published["twickenham_events/events/today"]
    assert set(today_payload.keys()) == {
        "date",
        "has_event_today",
        "events_today",
        "last_updated",
    }
