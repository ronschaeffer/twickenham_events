"""Regression tests ensuring event 'date' field integrity across pipeline.

Covers:
1. summarize_events produces per-event 'date'.
2. MQTT publish payloads retain 'date' and invariant: next == first all_upcoming.
3. Invariant: if all_upcoming not empty then next.event.date/fixture match first event.
"""

from __future__ import annotations

import re
from typing import Any

import pytest

from twickenham_events.config import Config
from twickenham_events.mqtt_client import MQTTClient
from twickenham_events.scraper import EventScraper


class DummyPublisher:  # mirrors pattern in other tests
    def __init__(self, *_, **__):
        self.published: list[tuple[str, dict[str, Any], bool]] = []

    def __enter__(self):  # pragma: no cover - trivial
        return self

    def __exit__(self, exc_type, exc, tb):  # pragma: no cover - trivial
        return False

    def publish(self, topic, payload, retain=False):  # pragma: no cover - trivial
        # store snapshot (topic, payload dict, retain flag)
        self.published.append((topic, payload, retain))


@pytest.fixture(autouse=True)
def patch_publisher(monkeypatch):
    monkeypatch.setattr("twickenham_events.mqtt_client.MQTTPublisher", DummyPublisher)


@pytest.fixture
def cfg():
    c = Config.from_defaults()
    c._data["mqtt"]["enabled"] = True
    # ensure topics present (today already added elsewhere; keep minimal set)
    topics = c._data["mqtt"]["topics"]
    topics.setdefault("all_upcoming", "twickenham_events/events/all_upcoming")
    topics.setdefault("next", "twickenham_events/events/next")
    topics.setdefault("status", "twickenham_events/status")
    topics.setdefault("today", "twickenham_events/events/today")
    return c


def _build_future_events(days: list[str]) -> list[dict[str, str]]:
    """Helper building minimal raw events (pre-normalization) with given future date strings already in ISO form.

    Using ISO format means normalize_date_range should pass through unchanged for supported patterns.
    """
    out: list[dict[str, str]] = []
    for idx, d in enumerate(days, start=1):
        out.append(
            {"date": d, "title": f"Fixture {idx}", "time": "12:30", "crowd": "82000"}
        )
    return out


def test_summarize_events_injects_date(cfg):
    scraper = EventScraper(cfg)
    # choose two far-future dates to avoid filtering (< today) logic
    raw = _build_future_events(["2099-01-01", "2099-01-02"])
    summarized = scraper.summarize_events(raw)
    # Flatten events from summaries
    flat = [e for day in summarized for e in day["events"]]
    assert flat, "Expected events present"
    for ev in flat:
        assert "date" in ev, f"Missing date in event: {ev}"
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", ev["date"]), "Date not normalized"


def test_mqtt_payload_contains_dates_and_invariant(monkeypatch, cfg):
    # Build pre-flatten list events as would be passed to publish_events (already have date)
    events = [
        {"fixture": "Match A", "date": "2099-02-01", "start_time": "12:30"},
        {"fixture": "Match B", "date": "2099-02-10", "start_time": "15:00"},
    ]
    client = MQTTClient(cfg)
    publisher_instances: list[DummyPublisher] = []

    class CapturingPublisher(DummyPublisher):
        def __enter__(self):
            publisher_instances.append(self)
            return self

    monkeypatch.setattr(
        "twickenham_events.mqtt_client.MQTTPublisher", CapturingPublisher
    )
    client.publish_events(events)
    assert publisher_instances, "Publisher not instantiated"
    # Collect payloads
    all_upcoming = next(
        (
            p
            for (t, p, _r) in publisher_instances[0].published
            if t.endswith("/all_upcoming")
        ),
        None,
    )
    next_payload = next(
        (p for (t, p, _r) in publisher_instances[0].published if t.endswith("/next")),
        None,
    )
    assert all_upcoming is not None, "all_upcoming topic missing"
    assert next_payload is not None, "next topic missing"
    evj = all_upcoming.get("events_json", {})
    first = None
    first_day_date = None
    if isinstance(evj, dict):
        by_month = evj.get("by_month") or []
        if isinstance(by_month, list) and by_month:
            days = by_month[0].get("days") or []
            if isinstance(days, list) and days:
                first_day_date = days[0].get("date")
                events = days[0].get("events") or []
                if isinstance(events, list) and events:
                    first = events[0]
    assert first is not None, "No first event found in events_json"
    # Invariant: next payload fixture/date match first events_json entry
    assert next_payload.get("fixture") == first.get("fixture")
    assert next_payload.get("date") == first_day_date


def test_next_matches_first_all_upcoming_with_real_summarize(monkeypatch, cfg):
    # Integration style: run through summarize_events then publish
    scraper = EventScraper(cfg)
    raw = _build_future_events(["2099-03-05", "2099-03-06"])  # two days same start time
    summarized = scraper.summarize_events(raw)
    flat = [e for day in summarized for e in day["events"]]
    client = MQTTClient(cfg)
    publisher_instances: list[DummyPublisher] = []

    class CapturingPublisher(DummyPublisher):
        def __enter__(self):
            publisher_instances.append(self)
            return self

    monkeypatch.setattr(
        "twickenham_events.mqtt_client.MQTTPublisher", CapturingPublisher
    )
    client.publish_events(flat)
    assert publisher_instances, "Publisher not instantiated"
    pub = publisher_instances[0]
    all_upcoming = next(
        (p for (t, p, _r) in pub.published if t.endswith("/all_upcoming")), None
    )
    next_payload = next(
        (p for (t, p, _r) in pub.published if t.endswith("/next")), None
    )
    assert all_upcoming and next_payload
    evj = all_upcoming.get("events_json", {})
    first = None
    first_day_date = None
    if isinstance(evj, dict):
        by_month = evj.get("by_month") or []
        if isinstance(by_month, list) and by_month:
            days = by_month[0].get("days") or []
            if isinstance(days, list) and days:
                first_day_date = days[0].get("date")
                events = days[0].get("events") or []
                if isinstance(events, list) and events:
                    first = events[0]
    assert first is not None
    assert next_payload.get("fixture") == first.get("fixture")
    assert next_payload.get("date") == first_day_date
