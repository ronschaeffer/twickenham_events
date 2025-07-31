"""
Defines the Home Assistant MQTT discovery payload for the status binary_sensor.
"""
from .entity import Entity


class StatusSensor(Entity):
    """
    Represents the status binary_sensor in Home Assistant.
    """

    def __init__(self, config, device):
        """
        Initializes the StatusSensor.

        Args:
            config (Config): The application's configuration object.
            device (Device): The device information for HA discovery.
        """
        super().__init__(config, device)
        self.component = "binary_sensor"
        self.device_class = "problem"
        self.unique_id = "status"
        self.name = "Status"
        self.state_topic = f"{self.base_topic}/status"
        self.value_template = "{{ 'ON' if value_json.status == 'error' else 'OFF' }}"
        self.json_attributes_topic = f"{self.base_topic}/status"
        self.json_attributes_template = "{{ value_json | tojson }}"

    def get_config_payload(self):
        """
        Returns the discovery configuration payload for the status sensor.
        """
        payload = super().get_config_payload()
        payload.update({
            "device_class": self.device_class,
            "value_template": self.value_template,
            "json_attributes_topic": self.json_attributes_topic,
            "json_attributes_template": self.json_attributes_template,
        })
        return payload
