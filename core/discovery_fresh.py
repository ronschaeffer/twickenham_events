# Home Assistant MQTT Discovery - Fresh Implementation
# This module handles publishing discovery configurations for all Twickenham Events entities

import json
import logging

from mqtt_publisher.publisher import MQTTPublisher

from core.config import Config


def publish_twickenham_discovery(config: Config, publisher: MQTTPublisher):
    """
    Publishes Home Assistant MQTT discovery configurations for all Twickenham Events entities.
    Creates a single device with three entities: Status, All Upcoming, and Next Event.
    """
    if not config.get("home_assistant.enabled", True):
        logging.info("Home Assistant integration disabled")
        return

    # Get discovery prefix from config
    discovery_prefix = config.get("home_assistant.discovery_prefix", "homeassistant")

    # Device information shared by all entities
    device_info = {
        "identifiers": ["twickenham_events"],
        "name": "Twickenham Events",
        "manufacturer": "Ron Schaeffer",
        "model": "Event Scraper v1.0",
        "sw_version": "0.1.0",
    }

    # 1. Status Binary Sensor (for error detection)
    status_config = {
        "name": "Status",
        "unique_id": "twickenham_events_status",
        "object_id": "twickenham_events_status",
        "device": device_info,
        "state_topic": "twickenham_events/status",
        "json_attributes_topic": "twickenham_events/status",
        "device_class": "problem",
        "value_template": "{{ 'ON' if value_json.status == 'error' else 'OFF' }}",
        "json_attributes_template": "{{ value_json | tojson }}",
        "icon": "mdi:alert-circle",
    }

    status_topic = f"{discovery_prefix}/binary_sensor/twickenham_events_status/config"
    publisher.publish(status_topic, json.dumps(status_config), retain=True)
    print(f"Published discovery: {status_topic}")

    # 2. All Upcoming Events Sensor
    all_upcoming_config = {
        "name": "All Upcoming",
        "unique_id": "twickenham_events_all_upcoming",
        "object_id": "twickenham_events_all_upcoming",
        "device": device_info,
        "state_topic": "twickenham_events/events/all_upcoming",
        "json_attributes_topic": "twickenham_events/events/all_upcoming",
        "value_template": "{{ value_json.count }}",
        "json_attributes_template": "{{ value_json | tojson }}",
        "icon": "mdi:calendar-multiple",
        "unit_of_measurement": "events",
    }

    all_upcoming_topic = (
        f"{discovery_prefix}/sensor/twickenham_events_all_upcoming/config"
    )
    publisher.publish(all_upcoming_topic, json.dumps(all_upcoming_config), retain=True)
    print(f"Published discovery: {all_upcoming_topic}")

    # 3. Next Event Sensor
    next_event_config = {
        "name": "Next Event",
        "unique_id": "twickenham_events_next",
        "object_id": "twickenham_events_next",
        "device": device_info,
        "state_topic": "twickenham_events/events/next",
        "json_attributes_topic": "twickenham_events/events/next",
        "value_template": "{{ value_json.fixture if value_json.fixture else 'None' }}",
        "json_attributes_template": "{{ value_json | tojson }}",
        "icon": "mdi:calendar-star",
    }

    next_event_topic = f"{discovery_prefix}/sensor/twickenham_events_next/config"
    publisher.publish(next_event_topic, json.dumps(next_event_config), retain=True)
    print(f"Published discovery: {next_event_topic}")

    logging.info("Published all Twickenham Events discovery configurations")
