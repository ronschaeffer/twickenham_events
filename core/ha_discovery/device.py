# core/ha_discovery/device.py

from core.config import Config


class Device:
    """
    Represents a Home Assistant device. This class is used to create a device
    that groups multiple entities (sensors, binary_sensors, etc.) together.
    """

    def __init__(self, config: Config):
        """
        Initializes the Device object.

        Args:
            config: The application's Config object.
        """
        self._config = config
        self.identifiers = [
            self._config.get("app.unique_id_prefix", "twickenham_events")
        ]
        self.name = self._config.get("app.name", "Twickenham Events")
        self.manufacturer = self._config.get(
            "app.manufacturer", "Twickenham Events Publisher"
        )
        self.model = self._config.get("app.model", "TwickEvent-Py")

    def get_device_info(self) -> dict:
        """
        Returns a dictionary containing the device information, which is used
        in the discovery payload for each entity.
        """
        return {
            "identifiers": self.identifiers,
            "name": self.name,
            "manufacturer": self.manufacturer,
            "model": self.model,
        }
