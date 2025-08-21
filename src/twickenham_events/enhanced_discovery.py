"""Enhanced discovery for Home Assistant using a device-bundle payload.

We still use ha-mqtt-publisher's Device/Entity classes to define components,
but we publish the device-level bundle ourselves to exactly match Home
Assistant's device-based discovery schema (with abbreviated device keys).

Why: After switching to the PyPI ha_mqtt_publisher, HA sometimes ignored our
bundle while single-entity discovery worked. Root cause was that our `dev`
block used non-abbreviated keys (manufacturer, model, sw_version...) which HA
accepts for single-entity discovery but expects abbreviated keys in device
bundles more strictly. This module emits:

    Topic: <prefix>/device/<device_id>/config
    Payload keys: dev (abbrev), o (origin), cmps (components map), availability

This restores the previously working behavior without requiring library
changes and keeps the public API here stable.
"""

from __future__ import annotations

from typing import Any

from ha_mqtt_publisher import Device, Entity

from . import __version__

AVAILABILITY_TOPIC = "twickenham_events/availability"


def build_device(config: Any) -> Device:
    """Build the Home Assistant device description with proper version info."""
    return Device(
        config,
        identifiers=["twickenham_events"],
        name=config.get("app.name", "Twickenham Events"),
        manufacturer=config.get("app.manufacturer", "ronschaeffer"),
        model=config.get("app.model", "Twick Events"),  # Simplified branding
        sw_version=__version__,  # Dynamic version from package
        configuration_url=config.get("app.configuration_url"),
    )


def create_twickenham_entities(
    config: Any,
    device: Device,
    include_event_count_component: bool = True,
) -> list[Entity]:
    """Create Entity objects for Twickenham Events discovery."""
    base = config.get("app.unique_id_prefix", "twickenham_events")
    status_topic = config.get_mqtt_topics().get("status", f"{base}/status")
    all_upcoming_topic = config.get_mqtt_topics().get(
        "all_upcoming", f"{base}/events/all_upcoming"
    )
    next_topic = config.get_mqtt_topics().get("next", f"{base}/events/next")
    today_topic = config.get_mqtt_topics().get("today", f"{base}/events/today")

    # Command topics (fixed)
    ack_topic = "twickenham_events/commands/ack"
    result_topic = "twickenham_events/commands/result"
    last_ack_topic = "twickenham_events/commands/last_ack"
    last_result_topic = "twickenham_events/commands/last_result"

    # IMPORTANT: Use short unique_ids here. Our Entity class will prefix them
    # with app.unique_id_prefix when building the payload unique_id. This
    # avoids double-prefixing like "twickenham_events_twickenham_events_status".

    entities = [
        # Status sensor
        Entity(
            config,
            device,
            component="sensor",
            unique_id="status",
            name="Status",
            state_topic=status_topic,
            value_template="{{ value_json.status }}",
            json_attributes_topic=status_topic,
            icon="mdi:information",
            entity_category="diagnostic",
        ),
        # Last run sensor
        Entity(
            config,
            device,
            component="sensor",
            unique_id="last_run",
            name="Last Run",
            state_topic=status_topic,
            value_template="{{ value_json.last_run_iso | default(value_json.last_updated) }}",
            device_class="timestamp",
            entity_category="diagnostic",
        ),
        # Upcoming events sensor
        Entity(
            config,
            device,
            component="sensor",
            unique_id="upcoming",
            name="Upcoming Events",
            state_topic=all_upcoming_topic,
            value_template="{{ value_json.count if (value_json.count is defined) else 0 }}",
            json_attributes_topic=all_upcoming_topic,
            icon="mdi:calendar-multiple",
        ),
        # Next event sensor
        Entity(
            config,
            device,
            component="sensor",
            unique_id="next",
            name="Next Event",
            state_topic=next_topic,
            value_template="{{ value_json.fixture if (value_json.fixture is defined and value_json.fixture) else '' }}",
            json_attributes_topic=next_topic,
            json_attributes_template="{{ {'start_time': (value_json.start_time | default(None)), 'date': (value_json.date | default(None)), 'fixture_short': (value_json.fixture_short | default(None)), 'crowd': (value_json.crowd | default(None)), 'emoji': (value_json.emoji | default(None)), 'mdi_icon': (value_json.mdi_icon | default(value_json.icon | default(None))), 'icon': (value_json.icon | default(None)), 'event_index': (value_json.event_index | default(None)), 'event_count': (value_json.event_count | default(None))} | tojson }}",
            icon="mdi:calendar-clock",
        ),
        # Today events sensor
        Entity(
            config,
            device,
            component="sensor",
            unique_id="today",
            name="Today Events",
            state_topic=today_topic,
            value_template="{{ value_json.events_today if value_json.events_today is defined else 0 }}",
            json_attributes_topic=today_topic,
            icon="mdi:calendar-today",
        ),
        # Command buttons
        Entity(
            config,
            device,
            component="button",
            unique_id="refresh",
            name="Refresh",
            command_topic=f"{base}/cmd/refresh",
        ),
        Entity(
            config,
            device,
            component="button",
            unique_id="clear_cache",
            name="Clear All",
            command_topic=f"{base}/cmd/clear_cache",
        ),
        Entity(
            config,
            device,
            component="button",
            unique_id="restart",
            name="Restart Service",
            command_topic=f"{base}/cmd/restart",
            icon="mdi:restart",
        ),
        # Command status sensors
        Entity(
            config,
            device,
            component="sensor",
            unique_id="cmd_ack",
            name="Last Command Ack",
            state_topic=ack_topic,
            value_template="{% set s = value_json.status %}{% if s == 'received' %}busy{% else %}{{ s | default(value_json.command) | default(value_json.name) | default(value_json.id) | default('') }}{% endif %}",
            json_attributes_topic=ack_topic,
            icon="mdi:progress-wrench",
            entity_category="diagnostic",
            expire_after=120,
        ),
        Entity(
            config,
            device,
            component="sensor",
            unique_id="cmd_result",
            name="Last Command Result",
            state_topic=result_topic,
            value_template="{{ value_json.status | default(value_json.outcome) | default('') }}",
            json_attributes_topic=result_topic,
            icon="mdi:progress-check",
            entity_category="diagnostic",
        ),
        Entity(
            config,
            device,
            component="sensor",
            unique_id="last_ack",
            name="Last Ack (retained)",
            state_topic=last_ack_topic,
            value_template="{{ value_json.status | default(value_json.command) | default('') }}",
            json_attributes_topic=last_ack_topic,
            icon="mdi:clock-outline",
            entity_category="diagnostic",
        ),
        Entity(
            config,
            device,
            component="sensor",
            unique_id="last_result",
            name="Last Result (retained)",
            state_topic=last_result_topic,
            value_template="{{ value_json.status | default(value_json.outcome) | default('') }}",
            json_attributes_topic=last_result_topic,
            icon="mdi:clock-check",
            entity_category="diagnostic",
        ),
    ]

    # Conditionally add event count sensor
    if include_event_count_component:
        entities.append(
            Entity(
                config,
                device,
                component="sensor",
                unique_id="event_count",
                name="Event Count",
                state_topic=status_topic,
                value_template="{{ value_json.event_count }}",
                state_class="measurement",
                entity_category="diagnostic",
            )
        )

    return entities


def publish_enhanced_device_discovery(
    mqtt_client: Any,
    config: Any,
    availability_topic: str = AVAILABILITY_TOPIC,
    include_event_count_component: bool = True,
    migrate_from_per_entity: bool = False,
) -> str:
    """Publish device-level discovery using HA's device bundle format.

    Emits a payload with abbreviated device keys (dev.ids/mf/mdl/sw) and a
    `cmps` map where each entry has `p` set to the component and includes the
    standard entity options like topics and unique_id.
    """
    import json

    # Build device and entities
    device = build_device(config)
    entities = create_twickenham_entities(config, device, include_event_count_component)

    # Discovery prefix and device_id
    discovery_prefix = config.get("home_assistant.discovery_prefix", "homeassistant")
    device_id = (
        device.identifiers[0]
        if isinstance(device.identifiers, list) and device.identifiers
        else (device.identifiers or "twickenham_events")
    )
    topic = f"{discovery_prefix}/device/{device_id}/config"

    # Abbreviated device info (HA expects abbreviated keys in bundles)
    dev = {
        "ids": device_id,
        "name": device.name,
    }
    if getattr(device, "manufacturer", None):
        dev["mf"] = device.manufacturer
    if getattr(device, "model", None):
        dev["mdl"] = device.model
    if getattr(device, "sw_version", None):
        dev["sw"] = device.sw_version
    if getattr(device, "hw_version", None):
        dev["hw"] = device.hw_version

    # Origin block (required; abbreviated fields supported)
    origin = {
        "name": config.get("app.unique_id_prefix", "twickenham_events"),
        "sw": __version__,
    }
    if getattr(device, "configuration_url", None):
        origin["url"] = device.configuration_url

    # Build compact component payloads
    cmps: dict[str, dict] = {}
    for e in entities:
        comp = e.get_config_payload().copy()
        # Remove device context; represented once in dev
        comp.pop("device", None)
        # Ensure platform key
        comp["p"] = e.component
        # Use the short unique_id token as bundle key (e.g., "status")
        key = e.unique_id
        cmps[key] = comp

    payload = {
        "dev": dev,
        "o": origin,
        "cmps": cmps,
        "qos": int(config.get("mqtt.default_qos", 0)),
    }

    if availability_topic:
        payload["availability"] = [{"topic": availability_topic}]
        payload["payload_available"] = "online"
        payload["payload_not_available"] = "offline"

    # Publish retained bundle
    mqtt_client.publish(topic=topic, payload=json.dumps(payload), retain=True)
    return topic
