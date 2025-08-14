"""Reusable discovery publishing helpers.

Abstracts Home Assistant MQTT discovery payload creation so future
library replacement is centralized here.
"""

from __future__ import annotations

from collections.abc import Iterable
import json
from typing import Any

AVAILABILITY_TOPIC = "twickenham_events/availability"
LEGACY_AVAILABILITY_UNIQUE_IDS = [
    "tw_events_availability",  # pre-prefix change
]
LEGACY_ENTITY_SENSOR_UNIQUE_IDS = [
    "twickenham_events_status",
    "twickenham_events_event_count",
    "twickenham_events_last_run",
]
LEGACY_BUTTON_UNIQUE_IDS = [
    # Historical shorter prefix; kept for cleanup only
    "tw_events_refresh",
    "tw_events_clear_cache",
]
LEGACY_BUNDLE_SENSOR_UNIQUE_IDS = [
    "twickenham_events_event_count",
    "twickenham_events_last_run",
]


def build_device(config) -> dict:
    """Build a minimal device payload (expandable later)."""
    prefix = config.get("app.unique_id_prefix", "twickenham_events")
    return {
        "identifiers": [prefix],
        "name": config.get("app.name", "Twickenham Events"),
        # Updated simplified branding defaults
        "model": config.get("app.model", "Twick Events"),
        "manufacturer": config.get("app.manufacturer", "ronschaeffer"),
        "sw_version": config.get("app.sw_version", "unknown"),
    }


def button_configs(config) -> list[dict]:
    """Return list of button discovery specs (unique_id, name, command_topic)."""
    base = config.get("app.unique_id_prefix", "twickenham_events")
    return [
        {
            "unique_id": f"{base}_refresh",
            "name": "Twickenham Refresh",
            "command_topic": f"{base}/cmd/refresh",
        },
        {
            "unique_id": f"{base}_clear_cache",
            "name": "Twickenham Clear Cache",
            "command_topic": f"{base}/cmd/clear_cache",
        },
    ]


def publish_buttons_discovery(
    mqtt_client,
    config,
    buttons: Iterable[dict] | None = None,
    availability_topic: str = AVAILABILITY_TOPIC,
) -> None:
    """Publish discovery configs for buttons.

    mqtt_client: paho-mqtt client with publish method
    config: application config
    buttons: optional iterable overriding default button list
    """
    discovery_prefix = config.service_discovery_prefix
    device = build_device(config)
    buttons = list(buttons) if buttons is not None else button_configs(config)
    for btn in buttons:
        unique_id = btn["unique_id"]
        payload = {
            "name": btn["name"],
            "unique_id": unique_id,
            "command_topic": btn["command_topic"],
            "device": device,
            "availability": [{"topic": availability_topic}],
        }
        topic = f"{discovery_prefix}/button/{unique_id}/config"
        mqtt_client.publish(topic, json.dumps(payload), retain=True)


def publish_availability_binary_sensor(
    mqtt_client, config, availability_topic: str = AVAILABILITY_TOPIC
) -> None:
    """Publish discovery for an availability binary_sensor (optional)."""
    discovery_prefix = config.service_discovery_prefix
    device = build_device(config)
    payload = {
        "name": "Twickenham Events Availability",
        "unique_id": f"{config.get('app.unique_id_prefix', 'twickenham_events')}_availability",
        "state_topic": availability_topic,
        "payload_on": "online",
        "payload_off": "offline",
        "device": device,
        "availability": [{"topic": availability_topic}],
    }
    topic = f"{discovery_prefix}/binary_sensor/{payload['unique_id']}/config"
    mqtt_client.publish(topic, json.dumps(payload), retain=True)


def publish_device_bundle(
    mqtt_client, config, availability_topic: str = AVAILABILITY_TOPIC
):
    """Publish a single status sensor with full attributes instead of multiple entities.

    The sensor exposes the status value, and attaches the entire status JSON payload
    (including event_count, last_run_*, interval_seconds, etc.) as attributes using
    Home Assistant's json_attributes_topic.
    Legacy individual sensors (event_count, last_run) are cleared.
    """
    discovery_prefix = config.service_discovery_prefix
    device = build_device(config)
    status_topic = config.get_mqtt_topics().get("status", "twickenham_events/status")
    base = config.get("app.unique_id_prefix", "twickenham_events")

    # Clear legacy per-field sensors if they existed
    for legacy_id in (f"{base}_event_count", f"{base}_last_run"):
        legacy_topic = f"{discovery_prefix}/sensor/{legacy_id}/config"
        mqtt_client.publish(legacy_topic, "", retain=True)

    sensor = {
        "unique_id": f"{base}_status",
        "name": "Twickenham Events Status",
        "state_topic": status_topic,
        "value_template": "{{ value_json.status }}",
        "icon": "mdi:information",
        "entity_category": "diagnostic",
        "json_attributes_topic": status_topic,
    }
    payload = {
        **sensor,
        "device": device,
        "availability": [{"topic": availability_topic}],
    }
    topic = f"{discovery_prefix}/sensor/{sensor['unique_id']}/config"
    mqtt_client.publish(topic, json.dumps(payload), retain=True)


def publish_device_level_discovery(
    mqtt_client,
    config,
    availability_topic: str = AVAILABILITY_TOPIC,
    include_event_count_component: bool = True,
    migrate_from_per_entity: bool = False,
):
    """Publish device-based discovery (single payload with 'cmps' component map)."""
    discovery_prefix = config.service_discovery_prefix
    base = config.get("app.unique_id_prefix", "twickenham_events")
    status_topic = config.get_mqtt_topics().get("status", f"{base}/status")
    all_upcoming_topic = config.get_mqtt_topics().get(
        "all_upcoming", f"{base}/events/all_upcoming"
    )
    next_topic = config.get_mqtt_topics().get("next", f"{base}/events/next")
    today_topic = config.get_mqtt_topics().get("today", f"{base}/events/today")
    device = build_device(config)
    origin = {
        "name": base,
        "sw": device.get("sw_version", "unknown"),
        "url": config.get("app.repository_url")
        or config.get("app.project_url")
        or "https://github.com/ronschaeffer/twickenham_events",
    }
    # Command topics (fixed)
    ack_topic = "twickenham_events/commands/ack"
    result_topic = "twickenham_events/commands/result"
    last_ack_topic = "twickenham_events/commands/last_ack"
    last_result_topic = "twickenham_events/commands/last_result"
    entities: dict[str, dict[str, Any]] = {
        "status": {
            "p": "sensor",
            "unique_id": f"{base}_status",
            "name": "Status",
            "value_template": "{{ value_json.status }}",
            "json_attributes_topic": status_topic,
            "icon": "mdi:information",
            "entity_category": "diagnostic",
        },
        "last_run": {
            "p": "sensor",
            "unique_id": f"{base}_last_run",
            "name": "Last Run",
            "value_template": "{{ value_json.last_run_iso | default(value_json.last_updated) }}",
            "device_class": "timestamp",
            "entity_category": "diagnostic",
        },
        "upcoming": {
            "p": "sensor",
            "unique_id": f"{base}_upcoming",
            "name": "Upcoming Events",
            "state_topic": all_upcoming_topic,
            "value_template": "{{ value_json.count if (value_json.count is defined) else 0 }}",
            "json_attributes_topic": all_upcoming_topic,
            "icon": "mdi:calendar-multiple",
        },
        "next": {
            "p": "sensor",
            "unique_id": f"{base}_next",
            "name": "Next Event",
            "state_topic": next_topic,
            "value_template": "{{ value_json.fixture if (value_json.fixture is defined and value_json.fixture) else '' }}",
            "json_attributes_topic": next_topic,
            "icon": "mdi:calendar-clock",
        },
        "today": {
            "p": "sensor",
            "unique_id": f"{base}_today",
            "name": "Today Events",
            "state_topic": today_topic,
            "value_template": "{{ value_json.events_today if value_json.events_today is defined else 0 }}",
            "json_attributes_topic": today_topic,
            "icon": "mdi:calendar-today",
        },
        "refresh": {
            "p": "button",
            "unique_id": f"{base}_refresh",
            "name": "Refresh",
            "command_topic": f"{base}/cmd/refresh",
        },
        "clear_cache": {
            "p": "button",
            "unique_id": f"{base}_clear_cache",
            "name": "Clear All",
            "command_topic": f"{base}/cmd/clear_cache",
        },
        "restart": {
            "p": "button",
            "unique_id": f"{base}_restart",
            "name": "Restart Service",
            "command_topic": f"{base}/cmd/restart",
            "icon": "mdi:restart",
        },
        "cmd_ack": {
            "p": "sensor",
            "unique_id": f"{base}_cmd_ack",
            "name": "Last Command Ack",
            "state_topic": ack_topic,
            "value_template": "{% set s = value_json.status %}{% if s == 'received' %}busy{% else %}{{ s | default(value_json.command) | default(value_json.name) | default(value_json.id) | default('') }}{% endif %}",
            "json_attributes_topic": ack_topic,
            "icon": "mdi:progress-wrench",
            "entity_category": "diagnostic",
            # Auto-clear if no updates for a while (service not running)
            "expire_after": 120,
        },
        "cmd_result": {
            "p": "sensor",
            "unique_id": f"{base}_cmd_result",
            "name": "Last Command Result",
            "state_topic": result_topic,
            "value_template": "{{ value_json.status | default(value_json.outcome) | default('') }}",
            "json_attributes_topic": result_topic,
            "icon": "mdi:progress-check",
            "entity_category": "diagnostic",
        },
        "last_ack": {
            "p": "sensor",
            "unique_id": f"{base}_last_ack",
            "name": "Last Ack (retained)",
            "state_topic": last_ack_topic,
            "value_template": "{{ value_json.status | default(value_json.command) | default('') }}",
            "json_attributes_topic": last_ack_topic,
            "icon": "mdi:clock-outline",
            "entity_category": "diagnostic",
        },
        "last_result": {
            "p": "sensor",
            "unique_id": f"{base}_last_result",
            "name": "Last Result (retained)",
            "state_topic": last_result_topic,
            "value_template": "{{ value_json.status | default(value_json.outcome) | default('') }}",
            "json_attributes_topic": last_result_topic,
            "icon": "mdi:clock-check",
            "entity_category": "diagnostic",
        },
    }
    if include_event_count_component:
        entities["event_count"] = {
            "p": "sensor",
            "unique_id": f"{base}_event_count",
            "name": "Event Count",
            "value_template": "{{ value_json.event_count }}",
            "state_class": "measurement",
            "entity_category": "diagnostic",
        }
    payload = {
        "dev": {
            "ids": device["identifiers"][0],
            "name": device["name"],
            "mf": device.get("manufacturer"),
            "mdl": device.get("model"),
            "sw": device.get("sw_version"),
        },
        "o": origin,
        # Primary key expected by current HA device discovery implementation
        "cmps": entities,
        "state_topic": status_topic,
        "availability": [{"topic": availability_topic}],
        "payload_available": "online",
        "payload_not_available": "offline",
        "qos": 0,
    }
    device_topic = f"{discovery_prefix}/device/{base}/config"
    if migrate_from_per_entity:
        migrate_marker = json.dumps({"migrate_discovery": True})
        for t in [
            *(
                f"{discovery_prefix}/sensor/{base}_{s}/config"
                for s in [
                    "status",
                    "last_run",
                    "upcoming",
                    "next",
                    "today",
                    "event_count",
                    "cmd_ack",
                    "cmd_result",
                ]
            ),
            f"{discovery_prefix}/button/{base}_refresh/config",
            f"{discovery_prefix}/button/{base}_clear_cache/config",
            f"{discovery_prefix}/button/{base}_restart/config",
        ]:
            mqtt_client.publish(t, migrate_marker, retain=True)
    mqtt_client.publish(device_topic, json.dumps(payload), retain=True)
    if migrate_from_per_entity:
        for t in [
            *(
                f"{discovery_prefix}/sensor/{base}_{s}/config"
                for s in [
                    "status",
                    "last_run",
                    "upcoming",
                    "next",
                    "today",
                    "event_count",
                    "cmd_ack",
                    "cmd_result",
                ]
            ),
            f"{discovery_prefix}/button/{base}_refresh/config",
            f"{discovery_prefix}/button/{base}_clear_cache/config",
            f"{discovery_prefix}/button/{base}_restart/config",
        ]:
            mqtt_client.publish(t, "", retain=True)
    return device_topic


def publish_all_discovery(
    mqtt_client, config, availability_topic: str = AVAILABILITY_TOPIC
):
    """Publish buttons + availability binary sensor."""
    publish_buttons_discovery(
        mqtt_client, config, availability_topic=availability_topic
    )
    publish_availability_binary_sensor(
        mqtt_client, config, availability_topic=availability_topic
    )
    publish_device_bundle(mqtt_client, config, availability_topic=availability_topic)


def cleanup_legacy_discovery(mqtt_client, config) -> list[str]:
    """Publish blank retained payloads to legacy discovery topics to clear duplicates.

    Returns list of topics cleared.
    """
    discovery_prefix = config.service_discovery_prefix
    cleared = []
    for legacy_id in LEGACY_AVAILABILITY_UNIQUE_IDS:
        topic = f"{discovery_prefix}/binary_sensor/{legacy_id}/config"
        mqtt_client.publish(topic, "", retain=True)
        cleared.append(topic)
    return cleared
