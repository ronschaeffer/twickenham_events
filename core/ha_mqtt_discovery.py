# core/ha_mqtt_discovery.py

import json
from core.ha_discovery.entity import Sensor
from core.ha_discovery.status_sensor import StatusSensor
from core.ha_discovery.device import Device

from core.config import Config
from core.mqtt_publisher import MQTTPublisher
import json


def publish_discovery_configs(config: Config, publisher: MQTTPublisher):
    """
    Publishes the MQTT discovery configurations for all defined entities.
    """
    if not config.get('home_assistant.enabled'):
        return

    # Create a single device instance to be shared by all entities
    device = Device(config)

    # Define all entities that need to be discovered
    entities = []

    # Conditionally add the Status Sensor
    if config.get('mqtt.topics.status'):
        entities.append(StatusSensor(config, device))

    # Add other sensors
    entities.extend([
        # Sensor for All Upcoming Events
        Sensor(
            config=config,
            device=device,
            name="All Upcoming",
            unique_id="all_upcoming",
            state_topic=config.get('mqtt.topics.all_upcoming'),
            value_template="{{ value_json.events | count }}",
            json_attributes_topic=config.get('mqtt.topics.all_upcoming'),
            json_attributes_template="{{ value_json | tojson }}",
            icon="mdi:calendar-multiple"
        ),

        # Sensor for the very next event
        Sensor(
            config=config,
            device=device,
            name="Next Event",
            unique_id="next",
            state_topic=config.get('mqtt.topics.next'),
            value_template="{{ value_json.event.fixture if value_json.event else 'None' }}",
            json_attributes_topic=config.get('mqtt.topics.next'),
            json_attributes_template="{{ value_json | tojson }}",
            icon="mdi:calendar-star"
        )
    ])

    # Publish the discovery config for each entity
    for entity in entities:
        config_topic = entity.get_config_topic()
        config_payload = entity.get_config_payload()
        publisher.publish(
            topic=config_topic,
            payload=json.dumps(config_payload),
            retain=True
        )
        print(f"Published discovery config to {config_topic}")
