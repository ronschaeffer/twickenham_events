"""Home Assistant MQTT Discovery integration for Twickenham Events.

Creates device + sensors and publishes a bundle-only discovery config using
the local ha-mqtt-publisher library (path dependency).

Design choices (per user requirements):
 - Bundle-only mode (no per-entity discovery topics)
 - All state topics retained
 - entity_category="diagnostic" for diagnostic sensors
 - state_class="measurement" for numeric changing metrics
 - New binary_sensor: twick_events_event_today
 - AI enabled flag sensor (boolean-ish text sensor) if AI shortening enabled
 - sw_version dynamically pulled from package __version__
 - model name default simplified to "Twick Events"
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from . import __version__
from .config import Config

if TYPE_CHECKING:
    from ha_mqtt_publisher.ha_discovery import (
        BinarySensor,
        Device,
        Sensor,
        publish_device_bundle as _publish_device_bundle,
    )

    HA_DISCOVERY_AVAILABLE = True
else:  # runtime import with fallback
    try:
        from ha_mqtt_publisher.ha_discovery import (
            BinarySensor,  # type: ignore
            Device,  # type: ignore
            Sensor,  # type: ignore
            publish_device_bundle as _publish_device_bundle,  # type: ignore
        )

        HA_DISCOVERY_AVAILABLE = True
    except ImportError:  # pragma: no cover - defensive
        HA_DISCOVERY_AVAILABLE = False

        class _Missing:
            def __init__(self, *_, **__):
                raise ImportError("ha_mqtt_publisher not available; install dependency")

        # Provide stubs so type names exist, but raise if constructed/used
        BinarySensor = _Missing  # type: ignore
        Device = _Missing  # type: ignore
        Sensor = _Missing  # type: ignore

        def _publish_device_bundle(*args, **kwargs):  # type: ignore
            raise ImportError("ha_mqtt_publisher not available; install dependency")


# Provide a public name that tests and callers can patch
def publish_device_bundle(*args, **kwargs):  # type: ignore
    return _publish_device_bundle(*args, **kwargs)


DEVICE_ID = "twickenham_events"


def _fmt_ts(dt: datetime | None) -> str | None:
    if not dt:
        return None
    return dt.isoformat()


def build_device(config: Config) -> Device:
    """Build the Home Assistant device description."""
    return Device(
        config,
        identifiers=[DEVICE_ID],
        name=config.get("app.name", "Twickenham Events"),
        manufacturer=config.get("app.manufacturer", "ronschaeffer"),
        model=config.get("app.model", "Twick Events"),
        sw_version=__version__,  # dynamic
        configuration_url=config.get("app.configuration_url"),
    )


def build_entities(
    config: Config,
    device: Device,
    scrape_stats: dict[str, Any] | None = None,
    next_event: dict[str, Any] | None = None,
    events: list[dict[str, Any]] | None = None,
    ai_enabled: bool = False,
) -> list:
    """Create required entities based on latest scrape context.

    We keep existing sensor set (as-is requirement) and add:
      - Binary sensor event_today
      - AI enabled + cache entries sensors when AI is enabled
    """
    if events is None:
        events = []
    scrape_stats = scrape_stats or {}

    entities = []

    def add_sensor(name: str, unique: str, state_topic: str, **extra):
        entities.append(
            Sensor(
                config,
                device,
                name=name,
                unique_id=unique,
                state_topic=state_topic,
                retain=True,
                **extra,
            )
        )

    # Primary next event sensors
    add_sensor("Next Event Fixture", "next_fixture", "tw_events/next/fixture")
    add_sensor("Next Event Short", "next_short", "tw_events/next/fixture_short")
    add_sensor("Next Event Date", "next_date", "tw_events/next/date")
    add_sensor("Next Event Time", "next_time", "tw_events/next/time")
    add_sensor("Next Event Crowd", "next_crowd", "tw_events/next/crowd")
    add_sensor("Next Event Type", "next_type", "tw_events/next/type")
    add_sensor(
        "Days Until Next Event",
        "days_until",
        "tw_events/next/days_until",
        state_class="measurement",
    )
    add_sensor(
        "Events Today",
        "events_today",
        "tw_events/meta/events_today",
        state_class="measurement",
    )
    add_sensor(
        "Total Upcoming Events",
        "total_upcoming",
        "tw_events/meta/total_upcoming",
        state_class="measurement",
    )
    add_sensor(
        "Last Scrape Timestamp",
        "last_scrape_ts",
        "tw_events/meta/last_scrape_ts",
        entity_category="diagnostic",
    )
    add_sensor(
        "Error Count",
        "error_count",
        "tw_events/meta/error_count",
        entity_category="diagnostic",
        state_class="measurement",
    )

    if ai_enabled:
        add_sensor(
            "AI Enabled",
            "ai_enabled",
            "tw_events/ai/enabled",
            entity_category="diagnostic",
        )
        add_sensor(
            "AI Cache Entries",
            "ai_cache_entries",
            "tw_events/ai/cache_entries",
            entity_category="diagnostic",
            state_class="measurement",
        )

    # Binary sensor: event today
    entities.append(
        BinarySensor(
            config,
            device,
            name="Event Today",
            unique_id="event_today",
            state_topic="tw_events/next/event_today",
            retain=True,
            device_class="presence",
        )
    )

    return entities


def publish_discovery_bundle(
    config: Config,
    publisher,
    entities: list,
    device: Device,
) -> bool:
    """Publish device-centric bundle only."""
    if not HA_DISCOVERY_AVAILABLE:
        return False
    return publish_device_bundle(
        config=config,
        publisher=publisher,
        device=device,
        entities=entities,
        device_id=DEVICE_ID,
    )


__all__ = ["build_device", "build_entities", "publish_discovery_bundle"]
