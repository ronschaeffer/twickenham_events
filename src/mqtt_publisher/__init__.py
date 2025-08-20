"""Local compatibility shim for mqtt_publisher used by tests.

This package re-exports the real implementation from the sibling
`ha_mqtt_publisher` checkout during local development and testing.
"""

from .publisher import MQTTPublisher

__all__ = ["MQTTPublisher"]
