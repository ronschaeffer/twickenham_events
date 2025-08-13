from twickenham_events.config import Config
from twickenham_events.mqtt_client import MQTTClient
from twickenham_events.service_cycle import (
    _LAST_ERRORS_CACHE,
    _LAST_ERRORS_STRUCT,
    build_extra_status,
)


class DummyPublisher:
    def __init__(self, *_, **__):
        self.published = []

    def __enter__(self):  # pragma: no cover - trivial
        return self

    def __exit__(self, exc_type, exc, tb):  # pragma: no cover
        return False

    def publish(self, topic, payload, retain=False):  # pragma: no cover - trivial
        self.published.append((topic, payload, retain))


def _get_status_from_instances(instances):
    for inst in instances:
        for t, p, *_ in inst.published:
            if t.endswith("/status"):
                status = p
    # Return last found
    try:
        return status  # type: ignore
    except UnboundLocalError:
        return None


def _base_config():
    cfg = Config.from_defaults()
    cfg._data["mqtt"]["enabled"] = True
    cfg._data["mqtt"]["topics"]["today"] = "twickenham_events/events/today"
    return cfg


def test_errors_with_events_status_active(monkeypatch):
    publisher_instances = []

    class CapturingPublisher(DummyPublisher):
        def __enter__(self):
            publisher_instances.append(self)
            return self

    monkeypatch.setattr(
        "twickenham_events.mqtt_client.MQTTPublisher", CapturingPublisher
    )
    cfg = _base_config()
    client = MQTTClient(cfg)
    extra = build_extra_status(
        scraper=type("S", (), {"error_log": ["e1"]})(),
        flat_events=[{"fixture": "X"}],
        trigger="t",
        interval=1,
        run_ts=0,
        reset_cache=True,
    )
    client.publish_events([{"fixture": "X", "date": "2099-01-01"}], extra_status=extra)
    status = _get_status_from_instances(publisher_instances)
    assert status is not None
    assert status["status"] == "active"  # events present keeps active
    assert status.get("error_count") == 1


def test_explicit_override_error_with_events(monkeypatch):
    publisher_instances = []

    class CapturingPublisher(DummyPublisher):
        def __enter__(self):
            publisher_instances.append(self)
            return self

    monkeypatch.setattr(
        "twickenham_events.mqtt_client.MQTTPublisher", CapturingPublisher
    )
    cfg = _base_config()
    client = MQTTClient(cfg)
    extra = build_extra_status(
        scraper=type("S", (), {"error_log": ["e1"]})(),
        flat_events=[{"fixture": "X"}],
        trigger="t",
        interval=1,
        run_ts=0,
        reset_cache=True,
    )
    extra["status"] = "error"
    client.publish_events([{"fixture": "X", "date": "2099-01-01"}], extra_status=extra)
    status = _get_status_from_instances(publisher_instances)
    assert status is not None
    assert status["status"] == "error"


def test_boundary_truncation(monkeypatch):
    publisher_instances = []

    class CapturingPublisher(DummyPublisher):
        def __enter__(self):
            publisher_instances.append(self)
            return self

    monkeypatch.setattr(
        "twickenham_events.mqtt_client.MQTTPublisher", CapturingPublisher
    )
    cfg = _base_config()
    client = MQTTClient(cfg)
    errors25 = [f"e{i}" for i in range(25)]
    extra = build_extra_status(
        scraper=type("S", (), {"error_log": errors25})(),
        flat_events=[],
        trigger="t",
        interval=1,
        run_ts=0,
        reset_cache=True,
    )
    client.publish_events([], extra_status=extra)
    status = _get_status_from_instances(publisher_instances)
    assert status is not None
    assert status["error_count"] == 25
    errors26 = [f"e{i}" for i in range(26)]
    extra2 = build_extra_status(
        scraper=type("S", (), {"error_log": errors26})(),
        flat_events=[],
        trigger="t",
        interval=1,
        run_ts=1,
    )
    client.publish_events([], extra_status=extra2)
    status2 = _get_status_from_instances(publisher_instances)
    assert status2 is not None
    assert status2["error_count"] == 25
    first_messages = {e["message"] for e in status2["errors"]}
    assert "e0" not in first_messages  # truncated


def test_dedupe_mixed_forms(monkeypatch):
    publisher_instances = []

    class CapturingPublisher(DummyPublisher):
        def __enter__(self):
            publisher_instances.append(self)
            return self

    monkeypatch.setattr(
        "twickenham_events.mqtt_client.MQTTPublisher", CapturingPublisher
    )
    cfg = _base_config()
    client = MQTTClient(cfg)
    # First entry as string
    extra1 = build_extra_status(
        scraper=type("S", (), {"error_log": ["timeout"]})(),
        flat_events=[],
        trigger="t",
        interval=1,
        run_ts=0,
        reset_cache=True,
    )
    client.publish_events([], extra_status=extra1)
    # Second cycle: dict with same message should not increase unique count
    extra2 = build_extra_status(
        scraper=type("S", (), {"error_log": ["timeout", {"message": "timeout"}]})(),
        flat_events=[],
        trigger="t",
        interval=1,
        run_ts=1,
    )
    client.publish_events([], extra_status=extra2)
    status = _get_status_from_instances(publisher_instances)
    assert status is not None
    assert status["error_count"] == 1


def test_cache_reset_reemits(monkeypatch):
    publisher_instances = []

    class CapturingPublisher(DummyPublisher):
        def __enter__(self):
            publisher_instances.append(self)
            return self

    monkeypatch.setattr(
        "twickenham_events.mqtt_client.MQTTPublisher", CapturingPublisher
    )
    cfg = _base_config()
    client = MQTTClient(cfg)
    # Initial error
    extra1 = build_extra_status(
        scraper=type("S", (), {"error_log": ["e"]})(),
        flat_events=[],
        trigger="t",
        interval=1,
        run_ts=0,
        reset_cache=True,
    )
    client.publish_events([], extra_status=extra1)
    # No new errors -> still 1
    extra2 = build_extra_status(
        scraper=type("S", (), {"error_log": ["e"]})(),
        flat_events=[],
        trigger="t",
        interval=1,
        run_ts=1,
    )
    client.publish_events([], extra_status=extra2)
    # Reset cache then same error should appear again as fresh (error_count still 1 but ensures path works)
    extra3 = build_extra_status(
        scraper=type("S", (), {"error_log": ["e"]})(),
        flat_events=[],
        trigger="t",
        interval=1,
        run_ts=2,
        reset_cache=True,
    )
    client.publish_events([], extra_status=extra3)
    status = _get_status_from_instances(publisher_instances)
    assert status is not None
    assert status["error_count"] == 1
    # Clean up shared cache
    _LAST_ERRORS_CACHE.clear()
    _LAST_ERRORS_STRUCT.clear()
