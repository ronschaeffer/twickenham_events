# core/ha_discovery/entity.py

from core.config import Config
from .device import Device


class Entity:
    """
    Base class for all Home Assistant entities. It defines the common
    attributes and methods that all entities (sensors, binary_sensors, etc.)
    will use for MQTT discovery.
    """

    def __init__(self, config: Config, device: Device, **kwargs):
        """
        Initializes the base Entity.

        Args:
            config: The application's Config object.
            device: The Device object representing the physical device.
        """
        self._config = config
        self.device = device
        self.name = "Unnamed"
        self.unique_id = "unnamed"
        self.state_topic = ""
        self.base_topic = self._config.get(
            'mqtt.base_topic', 'twickenham_events')
        self.component = "sensor"
        self.attributes = {}
        for key, value in kwargs.items():
            setattr(self, key, value)

    def get_config_topic(self) -> str:
        """
        Generates the MQTT topic for publishing the entity's discovery configuration.
        Format: <discovery_prefix>/<component>/<unique_id>/config
        """
        discovery_prefix = self._config.get(
            'home_assistant.discovery_prefix', 'homeassistant')
        return f"{discovery_prefix}/{self.component}/{self.unique_id}/config"

    def get_config_payload(self) -> dict:
        """Returns the base configuration payload for this entity."""
        # Construct a globally unique ID and a clean object ID
        prefix = self._config.get('app.unique_id_prefix', 'twickenham_events')
        object_id = f"{prefix}_{self.unique_id}"

        payload = {
            "name": self.name,
            "unique_id": object_id,  # Use the full, prefixed ID for uniqueness
            "device": self.device.get_device_info(),
            "state_topic": self.state_topic,
            "object_id": object_id  # Explicitly set the object_id for a clean entity_id
        }
        # Merge the specific entity attributes
        for key, value in self.__dict__.items():
            if key not in ['_config', 'device', 'name', 'unique_id', 'state_topic', 'component', 'attributes']:
                payload[key] = value
        payload.update(self.attributes)
        return payload


class Sensor(Entity):
    """
    Represents a Home Assistant Sensor entity. Inherits from Entity and
    sets the component type to "sensor".
    """

    def __init__(self, config: Config, device: Device, **kwargs):
        # Set the component to "sensor" before calling the parent constructor
        super().__init__(config, device, **kwargs)
        self.component = "sensor"

    def get_config_payload(self) -> dict:
        """
        Returns the complete configuration payload for the sensor, including
        any sensor-specific attributes.
        """
        # Start with the base payload from the Entity class
        payload = super().get_config_payload()
        # Add/override any sensor-specific attributes here if needed
        return payload
