"""Compatibility shim that re-exports the real MQTTPublisher from
`ha_mqtt_publisher.publisher` during local development.
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
import sys

# Add sibling project src to sys.path if available so imports resolve in tests
_root = Path(__file__).resolve().parents[3]
_sibling_src = Path("/home/ron/projects/ha_mqtt_publisher/src")
if _sibling_src.exists():
    sys.path.insert(0, str(_sibling_src))

try:
    _mod = import_module("ha_mqtt_publisher.publisher")
    MQTTPublisher = _mod.MQTTPublisher
except Exception as exc:  # pragma: no cover - dev shim
    raise ImportError(
        "Could not import MQTTPublisher from ha_mqtt_publisher.publisher"
    ) from exc

__all__ = ["MQTTPublisher"]
