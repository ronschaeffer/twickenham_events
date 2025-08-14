"""Thin wrapper re-export of the shared library CommandProcessor.

This preserves local imports while delegating all behavior to
ha_mqtt_publisher.commands.CommandProcessor.
"""

from __future__ import annotations

from typing import Any

try:
    from ha_mqtt_publisher.commands import (  # type: ignore
        CommandProcessor as _LibCommandProcessor,
    )
except Exception as _e:  # pragma: no cover - defensive fallback
    raise ImportError(
        "ha_mqtt_publisher.commands.CommandProcessor not available; install mqtt_publisher"
    ) from _e


class CommandProcessor(_LibCommandProcessor):  # type: ignore[misc]
    """Project-tailored defaults while reusing library implementation."""

    def build_registry_payload(
        self, *, service_name: str = "twickenham_events"
    ) -> dict[str, Any]:
        return super().build_registry_payload(service_name=service_name)

    def publish_registry(
        self,
        topic: str,
        *,
        retain: bool = True,
        service_name: str = "twickenham_events",
    ) -> None:
        return super().publish_registry(topic, retain=retain, service_name=service_name)


__all__ = ["CommandProcessor"]
