# core/ha_mqtt_discovery.py

from mqtt_publisher.ha_discovery import (
    Device,
    Sensor,
    StatusSensor,
    publish_discovery_configs,
)
from mqtt_publisher.publisher import MQTTPublisher

from core.config import Config


def publish_discovery_configs_for_twickenham(config: Config, publisher: MQTTPublisher):
    """
    Publishes the MQTT discovery configurations for Twickenham Events entities.
    """
    if not config.get("home_assistant.enabled"):
        return

    # Create a single device instance to be shared by all entities
    device = Device(config)

    # Define all entities that need to be discovered
    entities = []

    # Conditionally add the Status Sensor
    if config.get("mqtt.topics.status"):
        entities.append(StatusSensor(config, device))

    # Add other sensors specific to Twickenham Events
    entities.extend(
        [
            # Sensor for All Upcoming Events
            Sensor(
                config=config,
                device=device,
                name="All Upcoming",
                unique_id="all_upcoming",
                state_topic=config.get("mqtt.topics.all_upcoming"),
                value_template="{{ value_json.events | count }}",
                json_attributes_topic=config.get("mqtt.topics.all_upcoming"),
                json_attributes_template="{{ value_json | tojson }}",
                icon="mdi:calendar-multiple",
            ),
            # Sensor for the very next event
            Sensor(
                config=config,
                device=device,
                name="Next Event",
                unique_id="next",
                state_topic=config.get("mqtt.topics.next"),
                value_template="{{ value_json.event.fixture if value_json.event else 'None' }}",
                json_attributes_topic=config.get("mqtt.topics.next"),
                json_attributes_template="{{ value_json | tojson }}",
                icon="mdi:calendar-star",
            ),
        ]
    )

    # Use the reference implementation to publish discovery configs
    publish_discovery_configs(config, publisher, entities, device)
