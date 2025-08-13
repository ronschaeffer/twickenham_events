import pytest

from twickenham_events.config import Config
from twickenham_events.mqtt_client import MQTTClient


class FakePublisher:
    def __init__(self, **_cfg):
        self.published = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def publish(self, topic, payload, retain=False):
        # store a tuple of (topic, payload)
        self.published.append((topic, payload, retain))


@pytest.fixture(autouse=True)
def patch_publisher(monkeypatch):
    from twickenham_events import mqtt_client as mc

    monkeypatch.setattr(mc, "MQTTPublisher", FakePublisher)
    return


def minimal_config():
    # Provide minimal config enabling mqtt with topics
    cfg_dict = {
        "mqtt": {
            "enabled": True,
            "broker_url": "example.com",
            "broker_port": 1883,
            "client_id": "test_id",
            "topics": {
                "all_upcoming": "twickenham_events/events/all_upcoming",
                "next": "twickenham_events/events/next",
                "status": "twickenham_events/status",
                "today": "twickenham_events/events/today",
            },
        }
    }
    return Config(cfg_dict)


def test_status_payload_includes_last_updated_and_logged(caplog):
    caplog.set_level("DEBUG")
    client = MQTTClient(minimal_config())
    events = [{"fixture": "Sample Event", "date": "2030-01-01", "start_time": "12:00"}]
    client.publish_events(events)
    debug_lines = [
        r.message for r in caplog.records if "status_payload_pre_publish" in r.message
    ]
    assert debug_lines, "status payload debug log missing"
    assert "last_updated" in debug_lines[0]
