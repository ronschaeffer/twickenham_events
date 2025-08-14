"""
Compatibility shim: expose legacy `mqtt_publisher` import path by delegating to
`ha_mqtt_publisher` package.

This allows older imports like:
    from mqtt_publisher.publisher import MQTTPublisher
    from mqtt_publisher.ha_discovery import Device, Sensor

to keep working while the project uses ha_mqtt_publisher internally.
"""

from __future__ import annotations

import importlib as _importlib
import sys as _sys

# Re-export package-level symbols if defined
_ha = _importlib.import_module("ha_mqtt_publisher")
if hasattr(_ha, "__all__"):
    for _name in _ha.__all__:
        globals()[_name] = getattr(_ha, _name)

# Alias common submodules used by tests/callers
_sys.modules[__name__ + ".publisher"] = _importlib.import_module(
    "ha_mqtt_publisher.publisher"
)
_sys.modules[__name__ + ".ha_discovery"] = _importlib.import_module(
    "ha_mqtt_publisher.ha_discovery"
)
