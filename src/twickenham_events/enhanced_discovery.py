"""Enhanced discovery using ha-mqtt-publisher Entity-based approach.

This module replaces the custom discovery_helper.py with the new Entity-based
discovery system from ha-mqtt-publisher 0.3.4+.
"""

from __future__ import annotations

from typing import Any

from ha_mqtt_publisher import Device, Entity
from ha_mqtt_publisher.ha_discovery import publish_device_level_discovery

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

    entities = [
        # Status sensor
        Entity(
            config,
            device,
            component="sensor",
            unique_id=f"{base}_status",
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
            unique_id=f"{base}_last_run",
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
            unique_id=f"{base}_upcoming",
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
            unique_id=f"{base}_next",
            name="Next Event",
            state_topic=next_topic,
            value_template="{{ value_json.fixture if (value_json.fixture is defined and value_json.fixture) else '' }}",
            json_attributes_topic=next_topic,
            json_attributes_template="{{ {'start_time': (value_json.start_time | default(None)), 'date': (value_json.date | default(None)), 'fixture_short': (value_json.fixture_short | default(None)), 'crowd': (value_json.crowd | default(None)), 'emoji': (value_json.emoji | default(None)), 'icon': (value_json.icon | default(None)), 'event_index': (value_json.event_index | default(None)), 'event_count': (value_json.event_count | default(None))} | tojson }}",
            icon="mdi:calendar-clock",
        ),
        # Today events sensor
        Entity(
            config,
            device,
            component="sensor",
            unique_id=f"{base}_today",
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
            unique_id=f"{base}_refresh",
            name="Refresh",
            command_topic=f"{base}/cmd/refresh",
        ),
        Entity(
            config,
            device,
            component="button",
            unique_id=f"{base}_clear_cache",
            name="Clear All",
            command_topic=f"{base}/cmd/clear_cache",
        ),
        Entity(
            config,
            device,
            component="button",
            unique_id=f"{base}_restart",
            name="Restart Service",
            command_topic=f"{base}/cmd/restart",
            icon="mdi:restart",
        ),
        # Command status sensors
        Entity(
            config,
            device,
            component="sensor",
            unique_id=f"{base}_cmd_ack",
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
            unique_id=f"{base}_cmd_result",
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
            unique_id=f"{base}_last_ack",
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
            unique_id=f"{base}_last_result",
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
                unique_id=f"{base}_event_count",
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
    """Publish device-level discovery using enhanced Entity-based approach.

    This function is a drop-in replacement for the old publish_device_level_discovery
    but uses the new Entity-based system from ha-mqtt-publisher 0.3.4+.
    """
    device = build_device(config)
    entities = create_twickenham_entities(config, device, include_event_count_component)

    # Use the library's enhanced publish_device_level_discovery
    return publish_device_level_discovery(
        config,
        mqtt_client,
        device,
        entities,
        availability_topic=availability_topic,
        migrate_from_per_entity=migrate_from_per_entity,
    )
