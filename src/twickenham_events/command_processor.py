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


def _iso_now() -> str:
    """Return current UTC time in ISO 8601 (Z) format without microseconds."""
    try:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    except Exception:
        # Fallback in unlikely environments without timezone; still ISO-like
        return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


try:
    # Prefer the upstream implementation when available
    from ha_mqtt_publisher.commands import (
        CommandProcessor as UpstreamCommandProcessor,  # type: ignore[import-not-found]
    )

    _UPSTREAM_OK = True

    class _TwEventsCommandProcessor(UpstreamCommandProcessor):
        """Wrapper around upstream CommandProcessor with twickenham_events defaults.

        Notes:
            - We keep our own lightweight command registry to support cooldowns and
              consistent registry payloads regardless of upstream features.
            - We do not depend on upstream's register/handle API beyond having a
              client with a publish() method provided at construction time.
        """

        def __init__(
            self,
            client: Any,
            ack_topic: str,
            result_topic: str,
            *args: Any,
            **kwargs: Any,
        ) -> None:
            """Initialize and record client and topics for consistent publishing.

            We don't rely on the upstream constructor signature. Instead, we
            store references used by our helper methods and then best-effort
            call the upstream __init__ with no arguments (or passed-through
            args) to keep compatibility if needed.
            """
            # Record attributes used by our _publish_json and registry helpers
            self.client = client
            self.ack_topic = ack_topic
            self.result_topic = result_topic
            try:
                # Try to call upstream init with provided args; ignore if incompatible
                super().__init__(*args, **kwargs)  # type: ignore[misc]
            except Exception:
                try:
                    super().__init__()  # type: ignore[misc]
                except Exception:
                    # Upstream init might require specific params; it's optional for us
                    pass

        # --- Local registry management -------------------------------------------------
        def register(  # type: ignore[override]
            self,
            name: str,
            handler: Callable[[Any], tuple[str, str, dict[str, Any]]],
            description: str = "",
            cooldown_seconds: int | None = None,
            requires_ai: bool = False,
            **kwargs: Any,
        ) -> None:
            """Register a command and store metadata locally for cooldown support."""
            if not hasattr(self, "_tw_events_commands"):
                self._tw_events_commands: dict[str, dict[str, Any]] = {}
            cmd_info: dict[str, Any] = {
                "name": name,
                "handler": handler,
                "description": description,
                "requires_ai": requires_ai,
            }
            if cooldown_seconds is not None:
                cmd_info["cooldown_seconds"] = cooldown_seconds
            for k, v in kwargs.items():
                cmd_info[k] = v
            self._tw_events_commands[name] = cmd_info

        # --- Execution and result handling --------------------------------------------
        def _publish_json(
            self, topic: str, payload: dict[str, Any], *, retain: bool = False
        ) -> None:
            if hasattr(self, "client") and hasattr(self.client, "publish"):
                try:
                    self.client.publish(topic, json.dumps(payload), retain=retain)
                except TypeError:
                    self.client.publish(topic, json.dumps(payload))

        def handle_raw(self, raw: str) -> None:  # type: ignore[override]
            """Parse a raw JSON command message and execute with cooldown support."""
            try:
                data = json.loads(raw)
            except Exception:
                return
            cmd = data.get("command")
            cid = data.get("id")
            if (
                not cmd
                or not hasattr(self, "_tw_events_commands")
                or cmd not in self._tw_events_commands
            ):
                self._publish_json(
                    getattr(self, "result_topic", "result"),
                    {
                        "id": cid,
                        "command": cmd,
                        "outcome": "unknown_command",
                        "message": "Command not registered",
                    },
                )
                return

            meta = self._tw_events_commands[cmd]
            cooldown = int(meta.get("cooldown_seconds", 0) or 0)
            # Cooldown check based on last success timestamp
            import time as _time

            now_s = int(_time.time())
            last_success = int(meta.get("last_success_ts", 0) or 0)
            if cooldown > 0 and last_success and (now_s - last_success) < cooldown:
                retry_after = max(0, cooldown - (now_s - last_success))
                self._publish_json(
                    getattr(self, "result_topic", "result"),
                    {
                        "id": cid,
                        "command": cmd,
                        "outcome": "cooldown",
                        "message": "Command is on cooldown",
                        "retry_after_s": retry_after,
                    },
                )
                return

            handler = meta.get("handler")
            try:
                outcome, message, extra = handler(
                    {"id": cid, "command": cmd, "raw": data}
                )  # type: ignore[misc]
            except Exception as exc:  # pragma: no cover - defensive
                outcome, message, extra = "error", f"Exception: {exc}", {}

            # Update success timestamp for registry if success
            if outcome == "success":
                meta["last_success_ts"] = now_s

            result_payload: dict[str, Any] = {
                "id": cid,
                "command": cmd,
                "outcome": outcome,
                "message": message,
            }
            if isinstance(extra, dict):
                result_payload.update(extra)
            self._publish_json(getattr(self, "result_topic", "result"), result_payload)

        # --- Registry payload and publishing ------------------------------------------
        def build_registry_payload(self) -> dict[str, Any]:  # type: ignore[override]
            """Build registry payload with service name set to 'twickenham_events'."""
            commands = []
            if hasattr(self, "_tw_events_commands"):
                for cmd in self._tw_events_commands.values():
                    commands.append({k: v for k, v in cmd.items() if k != "handler"})
            return {
                "service": "twickenham_events",
                "commands": commands,
                "timestamp": _iso_now(),
            }

        def publish_registry(self, topic: str, *, retain: bool = True) -> None:  # type: ignore[override]
            """Publish the command registry with twickenham_events service name."""
            payload = self.build_registry_payload()
            self._publish_json(topic, payload, retain=retain)

except ImportError:  # pragma: no cover - fallback path used in tests
    _UPSTREAM_OK = False

    class _FallbackCommandProcessor:
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

        def _publish_json(
            self, topic: str, payload: dict[str, Any], *, retain: bool = False
        ) -> None:
            try:
                self.client.publish(topic, json.dumps(payload), retain=retain)
            except TypeError:
                self.client.publish(topic, json.dumps(payload))

        def handle_raw(self, raw: str) -> None:
            """Parse a raw JSON command message and execute with cooldown support."""
            try:
                data = json.loads(raw)
            except Exception:
                return
            cmd = data.get("command")
            cid = data.get("id")
            if not cmd or cmd not in self.commands:
                self._publish_json(
                    self.result_topic,
                    {
                        "id": cid,
                        "command": cmd,
                        "outcome": "unknown_command",
                        "message": "Command not registered",
                    },
                )
                return

            meta = self.commands[cmd]
            cooldown = int(meta.get("cooldown_seconds", 0) or 0)
            import time as _time

            now_s = int(_time.time())
            last_success = int(meta.get("last_success_ts", 0) or 0)
            if cooldown > 0 and last_success and (now_s - last_success) < cooldown:
                retry_after = max(0, cooldown - (now_s - last_success))
                self._publish_json(
                    self.result_topic,
                    {
                        "id": cid,
                        "command": cmd,
                        "outcome": "cooldown",
                        "message": "Command is on cooldown",
                        "retry_after_s": retry_after,
                    },
                )
                return

            handler = meta.get("handler")
            try:
                outcome, message, extra = handler(
                    {"id": cid, "command": cmd, "raw": data}
                )  # type: ignore[misc]
            except Exception as exc:  # pragma: no cover - defensive
                outcome, message, extra = "error", f"Exception: {exc}", {}

            if outcome == "success":
                meta["last_success_ts"] = now_s

            result_payload: dict[str, Any] = {
                "id": cid,
                "command": cmd,
                "outcome": outcome,
                "message": message,
            }
            if isinstance(extra, dict):
                result_payload.update(extra)
            self._publish_json(self.result_topic, result_payload)


# Public alias selected based on import availability
if "_UPSTREAM_OK" in globals() and _UPSTREAM_OK:
    CommandProcessor = _TwEventsCommandProcessor  # type: ignore[assignment]
else:  # pragma: no cover - during fallback
    CommandProcessor = _FallbackCommandProcessor  # type: ignore[assignment]
