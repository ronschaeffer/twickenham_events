import json

from twickenham_events.config import Config


class DummyPublisher:
    def __init__(self, *_, **__):
        self.published = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def publish(self, topic, payload, retain=False):
        # normalize payload to dict
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = payload
        self.published.append((topic, payload, retain))


def test_all_upcoming_includes_required_keys(monkeypatch, tmp_path):
    cfg = Config.from_defaults()

    # minimal config override for MQTT topics
    cfg._data["mqtt"]["enabled"] = True
    cfg._data["mqtt"]["topics"] = {
        "all_upcoming": "twickenham_events/events/all_upcoming",
        "next": "twickenham_events/events/next",
        "status": "twickenham_events/status",
    }

    # Capture the DummyPublisher instance used by MQTTClient
    published = []

    class CapturingPublisher(DummyPublisher):
        def __enter__(self):
            # attach published list back to outer scope
            self.published = published
            return self

    from twickenham_events import mqtt_client

    monkeypatch.setattr(mqtt_client, "MQTTPublisher", CapturingPublisher)

    client = mqtt_client.MQTTClient(cfg)

    sample_events = [{"fixture": "A vs B", "date": "2025-09-01", "start_time": "19:00"}]

    client.publish_events(sample_events)

    # Find the all_upcoming publish
    found = None
    for topic, payload, _ in published:
        if topic == "twickenham_events/events/all_upcoming":
            found = payload
            break

    assert found is not None, "all_upcoming was not published"
    assert "count" in found
    assert "last_updated" in found
    assert "events_json" in found
