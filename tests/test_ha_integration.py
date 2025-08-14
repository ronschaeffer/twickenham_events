from twickenham_events import ha_integration as hi
from twickenham_events.config import Config


class DummyDevice:
    def __init__(self, *_, **__):
        pass


class DummyEntity:
    def __init__(self, *_, **kwargs):
        # capture common kwargs for assertions
        self.unique_id = kwargs.get("unique_id")
        self.state_topic = kwargs.get("state_topic", "")


def test_build_entities_includes_event_today_binary_sensor(monkeypatch):
    cfg = Config.from_defaults()

    # Monkeypatch HA discovery classes with dummies
    monkeypatch.setattr(hi, "Device", DummyDevice, raising=True)
    monkeypatch.setattr(hi, "Sensor", DummyEntity, raising=True)
    monkeypatch.setattr(hi, "BinarySensor", DummyEntity, raising=True)

    device = hi.build_device(cfg)
    entities = hi.build_entities(cfg, device, ai_enabled=True)

    assert any(
        getattr(e, "unique_id", None) == "event_today"
        or getattr(e, "state_topic", "") == "tw_events/next/event_today"
        for e in entities
    ), "Expected event_today binary sensor present"


def test_publish_discovery_bundle_calls_underlying(monkeypatch):
    cfg = Config.from_defaults()

    # Monkeypatch HA discovery classes
    monkeypatch.setattr(hi, "Device", DummyDevice, raising=True)
    monkeypatch.setattr(hi, "Sensor", DummyEntity, raising=True)
    monkeypatch.setattr(hi, "BinarySensor", DummyEntity, raising=True)

    dev = hi.build_device(cfg)
    ents = hi.build_entities(cfg, dev)

    # Monkeypatch the module-level symbol used by our wrapper
    called = {}

    def fake_publish_device_bundle(*, config, publisher, device, entities, device_id):
        called["args"] = {
            "config": config,
            "publisher": publisher,
            "device": device,
            "entities": entities,
            "device_id": device_id,
        }
        return True

    monkeypatch.setattr(hi, "publish_device_bundle", fake_publish_device_bundle)
    # Ensure wrapper doesn't early-return due to guard
    monkeypatch.setattr(hi, "HA_DISCOVERY_AVAILABLE", True, raising=True)

    class DummyPublisher:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    ok = hi.publish_discovery_bundle(cfg, DummyPublisher(), ents, dev)
    assert ok is True
    assert called["args"]["device_id"] == "twickenham_events"
    assert called["args"]["device"] is dev
    assert called["args"]["entities"] is ents
