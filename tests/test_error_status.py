import pytest

from twickenham_events.config import Config
from twickenham_events.mqtt_client import MQTTClient


class DummyPublisher:
    def __init__(self, *_, **__):
        self.published = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def publish(self, topic, payload, retain=False):  # pragma: no cover - trivial
        self.published.append((topic, payload, retain))


# Patch point: replace MQTTPublisher inside module


@pytest.fixture(autouse=True)
def patch_publisher(monkeypatch):
    monkeypatch.setattr("twickenham_events.mqtt_client.MQTTPublisher", DummyPublisher)


@pytest.fixture
def base_config():
    cfg = Config.from_defaults()
    # Enable MQTT and required topics
    cfg._data["mqtt"]["enabled"] = True
    cfg._data["mqtt"]["topics"]["today"] = "twickenham_events/events/today"
    return cfg


def extract_status(published):
    for rec in published:
        # Records stored as (topic, payload) by our CapturingPublisher
        if len(rec) == 3:
            topic, payload, _retain = rec
        else:
            topic, payload = rec
        if topic.endswith("/status"):
            return payload
    return None


def test_status_active(monkeypatch, base_config):
    published_records = []

    class CapturingPublisher(DummyPublisher):
        def publish(self, topic, payload, retain=False):
            published_records.append((topic, payload))
            return super().publish(topic, payload, retain)

    monkeypatch.setattr(
        "twickenham_events.mqtt_client.MQTTPublisher", CapturingPublisher
    )
    client = MQTTClient(base_config)
    client.publish_events([{"fixture": "Match", "date": "2099-01-01"}])
    status = extract_status(published_records)
    assert status is not None
    assert status["status"] == "active"
    assert status["event_count"] == 1


def test_error_status_promotion(monkeypatch, base_config):
    client = MQTTClient(base_config)
    published_records = []

    class CapturingPublisher(DummyPublisher):
        def publish(self, topic, payload, retain=False):
            published_records.append((topic, payload))
            super().publish(topic, payload, retain)

    monkeypatch.setattr(
        "twickenham_events.mqtt_client.MQTTPublisher", CapturingPublisher
    )

    # Simulate no events + errors -> expect error status
    client.publish_events([], extra_status={"errors": ["network timeout"]})
    status = None
    for t, p in published_records:
        if t.endswith("/status"):
            status = p
            break
    assert status is not None, "Status topic not published"
    assert status["status"] == "error"
    assert status["error_count"] == 1
    assert status["errors"] == ["network timeout"]


def test_explicit_status_override(monkeypatch, base_config):
    client = MQTTClient(base_config)
    published_records = []

    class CapturingPublisher(DummyPublisher):
        def publish(self, topic, payload, retain=False):
            published_records.append((topic, payload))
            super().publish(topic, payload, retain)

    monkeypatch.setattr(
        "twickenham_events.mqtt_client.MQTTPublisher", CapturingPublisher
    )

    client.publish_events(
        [], extra_status={"errors": ["timeout"], "status": "no_events"}
    )
    status = None
    for t, p in published_records:
        if t.endswith("/status"):
            status = p
            break
    assert status is not None
    assert status["status"] == "no_events"
    assert status["error_count"] == 1


def test_error_count_autofill(monkeypatch, base_config):
    client = MQTTClient(base_config)
    published_records = []

    class CapturingPublisher(DummyPublisher):
        def publish(self, topic, payload, retain=False):
            published_records.append((topic, payload))
            super().publish(topic, payload, retain)

    monkeypatch.setattr(
        "twickenham_events.mqtt_client.MQTTPublisher", CapturingPublisher
    )

    # Provide errors without count -> expect count injected
    client.publish_events([], extra_status={"errors": ["e1", "e2", "e3"]})
    status = None
    for t, p in published_records:
        if t.endswith("/status"):
            status = p
            break
    assert status is not None
    assert status["error_count"] == 3
    assert status["status"] == "error"
