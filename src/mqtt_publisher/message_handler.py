"""Reusable MQTT command message handler for Home Assistant automations.

Provides handle_command_message for busy/idle ack, retained mirrors, and command mapping.
"""

import json
import time
from typing import Any


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
            result_obj = json.loads(text or "{}") if text else {}
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
        if text == "" or text.upper() == "PRESS":
            try:
                _ack = {
                    "status": "busy",
                    "command": cmd_name,
                    "received_ts": time.time(),
                }
                client.publish(ack_topic, json.dumps(_ack), qos=0, retain=False)
                try:
                    client.publish(last_ack_topic, json.dumps(_ack), qos=0, retain=True)
                except Exception:
                    pass
            except Exception:
                pass
            processor.handle_raw(cmd_name)
            return
        try:
            _cmd = text
            try:
                _obj = json.loads(text)
                _cmd = _obj.get("name") or _obj.get("command") or text
            except Exception:
                pass
            _ack = {
                "status": "busy",
                "command": str(_cmd).lower(),
                "received_ts": time.time(),
            }
            client.publish(ack_topic, json.dumps(_ack), qos=0, retain=False)
            try:
                client.publish(last_ack_topic, json.dumps(_ack), qos=0, retain=True)
            except Exception:
                pass
        except Exception:
            pass
        processor.handle_raw(text)
        return

    processor.handle_raw(payload_bytes)
