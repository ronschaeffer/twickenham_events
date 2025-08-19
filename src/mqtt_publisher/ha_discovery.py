from __future__ import annotations

from typing import Any


class Device:
    """Minimal compatibility Device for tests."""

    def __init__(
        self, config: Any, identifiers: list[str], name: str, manufacturer: str
    ):
        self.config = config
        self._info = {
            "identifiers": identifiers,
            "name": name,
            "manufacturer": manufacturer,
        }

    def get_device_info(self) -> dict[str, Any]:
        return self._info


class Sensor:
    """Minimal compatibility Sensor for tests."""

    component = "sensor"

    def __init__(
        self, config: Any, device: Device, name: str, unique_id: str, **kwargs: Any
    ):
        self.config = config
        self.device = device
        self.name = name
        self.unique_id = unique_id
        self.kwargs = kwargs

    def get_config_topic(self) -> str:
        prefix = self.config.get("home_assistant.discovery_prefix", "homeassistant")
        return f"{prefix}/sensor/{self.unique_id}/config"

    def get_config_payload(self) -> dict[str, Any]:
        # Start from provided kwargs (which include most config keys), then
        # ensure positional/explicit attrs are present so tests see them.
        payload = dict(self.kwargs)
        payload["name"] = self.name
        payload["device"] = self.device.get_device_info()
        # unique_id in payload is prefixed by app.unique_id_prefix per tests
        payload["unique_id"] = (
            f"{self.config.get('app.unique_id_prefix', '')}_{self.unique_id}"
        )
        payload["object_id"] = self.unique_id
        return payload
