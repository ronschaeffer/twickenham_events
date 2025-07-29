# core/ha_discovery/publisher.py

import yaml
from .entity import Sensor
from ..mqtt_publisher import MQTTPublisher


class HADiscoveryPublisher:
    """Handles publishing of Home Assistant MQTT discovery topics."""

    def __init__(self, config, entities_config_path):
        self.config = config
        self.entities_config_path = entities_config_path
        self.entities = self._load_entities()

    def _load_entities(self):
        """Loads entity configurations from the YAML file."""
        try:
            with open(self.entities_config_path, 'r') as f:
                entities_config = yaml.safe_load(f)
                return [Sensor(**e) for e in entities_config]
        except FileNotFoundError:
            return []

    def publish_discovery_topics(self):
        """Publishes the discovery topics for all configured entities."""
        if not self.config.get('home_assistant.enabled', False) or not self.entities:
            return

        discovery_prefix = self.config.get(
            'home_assistant.discovery_prefix', 'homeassistant')

        broker_url = self.config.get('mqtt.broker_url')
        broker_port = self.config.get('mqtt.broker_port')
        client_id = self.config.get('mqtt.client_id')
        security = self.config.get('mqtt.security', 'none')
        auth = self.config.get('mqtt.auth')
        tls = self.config.get('mqtt.tls')

        with MQTTPublisher(broker_url, broker_port, client_id, security, auth, tls) as publisher:
            for entity in self.entities:
                config_topic = entity.get_config_topic(discovery_prefix)
                config_payload = entity.get_config_payload()
                publisher.publish(config_topic, config_payload, retain=True)
                print(f"Published discovery topic for {entity.name}")
