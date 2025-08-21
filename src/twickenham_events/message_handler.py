"""Command message handler extracted for testability.

Provides a single function handle_command_message that encapsulates the logic
previously embedded in __main__.py's on_message callback.
"""

from __future__ import annotations

import json
import time
from typing import Any
import uuid


def handle_command_message(
    client: Any,
    config: Any,
    processor: Any,
    msg: Any,
    ack_topic: str,
    last_ack_topic: str,
    result_topic: str,
    last_result_topic: str,
) -> None:
    """Process an incoming MQTT message for command handling.

    Mirrors last ack/result to retained topics and publishes a transient ack
    with status busy/idle to ack_topic.
    """
    base = config.get("app.unique_id_prefix", "twickenham_events")
    cmd_prefix = f"{base}/cmd/"

    topic = getattr(msg, "topic", "") or ""
    payload_bytes: bytes = getattr(msg, "payload", b"") or b""
    text = payload_bytes.decode("utf-8", errors="ignore").strip()

    # If we received a command result, mirror to retained last_result and
    # immediately publish a final 'idle' ack (also mirror retained last_ack)
    if topic == result_topic:
        try:
            # Try to carry over command id/name for traceability if present
            result_obj = json.loads(text or "{}") if text else {}
            # Mirror result to retained topic for post-restart visibility
            try:
                client.publish(
                    last_result_topic, json.dumps(result_obj), qos=0, retain=True
                )
            except Exception:
                pass
            ack_payload = {
                "status": "idle",
                "command": "idle",
                "id": result_obj.get("id"),
                "completed_ts": result_obj.get("completed_ts") or time.time(),
            }
            client.publish(ack_topic, json.dumps(ack_payload), qos=0, retain=False)
            # Mirror last ack retained as well
            try:
                client.publish(
                    last_ack_topic, json.dumps(ack_payload), qos=0, retain=True
                )
            except Exception:
                pass
        except Exception:
            pass
        return

    if topic.startswith(cmd_prefix):
        cmd_name = topic[len(cmd_prefix) :].strip().lower()
        # If payload is "PRESS" (standard HA button) or empty, infer command from topic
        if text == "" or text.upper() == "PRESS":
            now = time.time()
            try:
                _ack = {
                    "status": "busy",
                    "command": cmd_name,
                    "received_ts": now,
                }
                client.publish(ack_topic, json.dumps(_ack), qos=0, retain=False)
                # Mirror retained last ack
                try:
                    client.publish(last_ack_topic, json.dumps(_ack), qos=0, retain=True)
                except Exception:
                    pass
            except Exception:
                pass
            # Build a minimal JSON command envelope for the processor
            cmd_obj = {
                "id": str(uuid.uuid4()),
                "command": cmd_name,
                "requested_ts": now,
                "received_ts": now,
                "source": "ha_button",
            }
            try:
                processor.handle_raw(json.dumps(cmd_obj))
            except Exception:
                # Last resort: send a bare command structure
                processor.handle_raw(json.dumps({"command": cmd_name}))
            return
        # Otherwise, pass through payload (may be JSON with args/ids). If not JSON, wrap it.
        _obj = None
        try:
            now = time.time()
            _cmd = text
            try:
                _obj = json.loads(text)
                _cmd = _obj.get("name") or _obj.get("command") or text
            except Exception:
                # Not JSON; wrap as a command name
                _obj = {"command": str(text).strip().lower()}
            _ack = {
                "status": "busy",
                "command": str(_cmd).lower(),
                "received_ts": now,
            }
            client.publish(ack_topic, json.dumps(_ack), qos=0, retain=False)
            try:
                client.publish(last_ack_topic, json.dumps(_ack), qos=0, retain=True)
            except Exception:
                pass
        except Exception:
            pass
        # Always forward JSON to the processor
        try:
            payload_for_processor = json.dumps(_obj) if isinstance(_obj, dict) else text
        except Exception:
            payload_for_processor = text
        processor.handle_raw(payload_for_processor)
        return

    # Non-command topics (defensive; we only subscribe to cmd/#)
    processor.handle_raw(payload_bytes)
