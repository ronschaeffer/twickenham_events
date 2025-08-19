"""Minimal CommandProcessor fallback used when the upstream package is
unavailable.

This module provides a small, well-typed CommandProcessor implementation
that exposes the minimal API the tests expect. If the real
``ha_mqtt_publisher.commands.CommandProcessor`` is installable we defer to it.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any, Callable

try:
    # Prefer the upstream implementation when available
    from ha_mqtt_publisher.commands import (
        CommandProcessor as UpstreamCommandProcessor,  # type: ignore[import-not-found]
    )

    class CommandProcessor(UpstreamCommandProcessor):
        """Wrapper around upstream CommandProcessor with twickenham_events defaults."""

        def build_registry_payload(self) -> dict[str, Any]:
            """Build registry payload with service name set to 'twickenham_events'."""
            payload = super().build_registry_payload()
            payload["service"] = "twickenham_events"
            return payload

        def publish_registry(self, topic: str, *, retain: bool = True) -> None:
            """Publish the command registry with twickenham_events service name."""
            payload = self.build_registry_payload()
            if hasattr(self, "_publish") and self._publish:
                self._publish(topic, payload, retain=retain)
            elif hasattr(self, "client") and hasattr(self.client, "publish"):
                self.client.publish(topic, json.dumps(payload), retain=retain)

except ImportError:  # pragma: no cover - fallback path used in tests

    def _iso_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    class CommandProcessor:
        """A minimal, non-blocking fallback CommandProcessor compatible with
        tests that construct it as (client, ack_topic, result_topic).
        """

        def __init__(self, client: Any, ack_topic: str, result_topic: str):
            self.client = client
            self.ack_topic = ack_topic
            self.result_topic = result_topic
            self.commands: dict[str, dict[str, Any]] = {}

        def register(
            self,
            name: str,
            handler: Callable[[Any], tuple[str, str, dict[str, Any]]],
            description: str = "",
            cooldown_seconds: int | None = None,
            requires_ai: bool = False,
            **kwargs: Any,
        ) -> None:
            """Register a command handler."""
            cmd_info: dict[str, Any] = {
                "name": name,
                "handler": handler,
                "description": description,
                "requires_ai": requires_ai,
            }
            if cooldown_seconds is not None:
                cmd_info["cooldown_seconds"] = cooldown_seconds
            # Accept and store any additional metadata (e.g., outcome_codes)
            for k, v in kwargs.items():
                cmd_info[k] = v
            self.commands[name] = cmd_info

        def build_registry_payload(self) -> dict[str, Any]:
            """Build the registry payload with service name set to 'twickenham_events'."""
            return {
                "service": "twickenham_events",
                "commands": [
                    {k: v for k, v in cmd.items() if k != "handler"}
                    for cmd in self.commands.values()
                ],
                "timestamp": _iso_now(),
            }

        def publish_registry(self, topic: str, *, retain: bool = True) -> None:
            """Publish the command registry to the specified topic."""
            payload = self.build_registry_payload()
            try:
                self.client.publish(topic, json.dumps(payload), retain=retain)
            except TypeError:
                # Some clients may not accept retain kw; fall back to positional
                self.client.publish(topic, json.dumps(payload))

        def enable_auto_registry_publish(self, topic: str) -> None:
            """Record registry topic and publish immediately (minimal behavior)."""
            setattr(self, "_registry_topic", topic)
            try:
                self.publish_registry(topic, retain=True)
            except Exception:
                # Non-fatal; just ensure the method exists to avoid AttributeError
                pass
