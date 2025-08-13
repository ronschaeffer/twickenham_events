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

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def publish(self, topic, payload, retain=False):
        self.published.append((topic, payload))


class DummyScraper:
    def __init__(self, error_log_seq):
        self._seq = list(error_log_seq)
        self.error_log = []

    def advance(self):
        if self._seq:
            self.error_log.append(self._seq.pop(0))


def test_service_loop_error_dedup(monkeypatch):
    cfg = Config.from_defaults()
    cfg._data["mqtt"]["enabled"] = True
    cfg._data["mqtt"]["topics"]["today"] = "twickenham_events/events/today"

    # Patch publisher
    publisher_instances = []

    class CapturingPublisher(DummyPublisher):
        def __enter__(self):
            publisher_instances.append(self)
            return self

    monkeypatch.setattr(
        "twickenham_events.mqtt_client.MQTTPublisher", CapturingPublisher
    )

    # Prepare client and scraper
    client = MQTTClient(cfg)
    scraper = DummyScraper(["e1", "e1", "e2"])  # duplicate e1 first

    # First cycle: add e1
    scraper.advance()
    extra1 = build_extra_status(scraper, [], "test", 60, run_ts=0, reset_cache=True)
    client.publish_events([], extra_status=extra1)
    first_status = [
        p
        for inst in publisher_instances
        for t, p in inst.published
        if t.endswith("/status")
    ][-1]
    assert first_status["error_count"] == 1

    # Second cycle: duplicate e1 again -> cumulative list still length 1 (no new unique message)
    scraper.advance()  # adds another e1
    extra2 = build_extra_status(scraper, [], "test", 60, run_ts=1)
    client.publish_events([], extra_status=extra2)
    second_status = [
        p
        for inst in publisher_instances
        for t, p in inst.published
        if t.endswith("/status")
    ][-1]
    # error_count may remain 1 (no new delta)
    assert second_status["error_count"] == 1

    # Third cycle: new e2 -> cumulative becomes 2
    scraper.advance()
    extra3 = build_extra_status(scraper, [], "test", 60, run_ts=2)
    client.publish_events([], extra_status=extra3)
    third_status = [
        p
        for inst in publisher_instances
        for t, p in inst.published
        if t.endswith("/status")
    ][-1]
    assert third_status["error_count"] == 2

    # Clean global cache for isolation (important if tests parallelize)
    _LAST_ERRORS_CACHE.clear()
    _LAST_ERRORS_STRUCT.clear()
