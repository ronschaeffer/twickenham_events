# core/ha_discovery/entity.py

import json


class Sensor:
    """Represents a Home Assistant MQTT Sensor."""

    def __init__(self, name, unique_id, state_topic, value_template, json_attributes_topic, json_attributes_template, icon):
        self.component = "sensor"
        self.name = name
        self.unique_id = unique_id
        self.state_topic = state_topic
        self.value_template = value_template
        self.json_attributes_topic = json_attributes_topic
        self.json_attributes_template = json_attributes_template
        self.icon = icon

    def get_config_topic(self, discovery_prefix):
        """Returns the discovery topic for this sensor."""
        return f"{discovery_prefix}/{self.component}/{self.unique_id}/config"

    def get_config_payload(self):
        """Returns the configuration payload for this sensor as a JSON string."""
        payload = {
            "name": self.name,
            "unique_id": self.unique_id,
            "state_topic": self.state_topic,
            "value_template": self.value_template,
            "json_attributes_topic": self.json_attributes_topic,
            "json_attributes_template": self.json_attributes_template,
            "icon": self.icon,
        }
        return json.dumps(payload)
