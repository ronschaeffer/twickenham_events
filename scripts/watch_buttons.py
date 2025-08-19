#!/usr/bin/env python3
"""
Watch Twickenham Events MQTT command traffic and results in real time.

Subscribes to:
- <base>/cmd/#              (button presses and raw commands)
- twickenham_events/commands/ack
- twickenham_events/commands/result

Reads broker/auth from config/config.yaml via twickenham_events.config.Config
"""

from __future__ import annotations

import json
import signal
import sys
import time

import paho.mqtt.client as mqtt

from twickenham_events.config import Config


def pretty(payload: bytes) -> str:
    txt = payload.decode("utf-8", errors="ignore").strip()
    if not txt:
        return "<empty>"
    try:
        obj = json.loads(txt)
        return json.dumps(obj, indent=2, sort_keys=True)
    except Exception:
        return txt


def main() -> int:
    cfg = Config.from_file("config/config.yaml")
    base = cfg.get("app.unique_id_prefix", "twickenham_events")

    broker = cfg.mqtt_broker
    port = cfg.mqtt_port

    topics = [
        (f"{base}/cmd/#", 0),
        ("twickenham_events/commands/ack", 0),
        ("twickenham_events/commands/result", 0),
    ]

    client_id = f"{cfg.mqtt_client_id}-watch-{int(time.time())}"
    client = mqtt.Client(client_id=client_id)

    # Auth
    if (
        cfg.get("mqtt.security") == "username"
        and cfg.mqtt_username
        and cfg.mqtt_password
    ):
        client.username_pw_set(cfg.mqtt_username, cfg.mqtt_password)

    # Simple handlers
    from ha_mqtt_publisher.mqtt_utils import extract_reason_code

    def on_connect(client, userdata, *args, **kwargs):
        # Support both v1 and v2 callback signatures. Extract reason_code if present.
        reason_code = extract_reason_code(*args, **kwargs)
        print(
            f"[watch] connected rc={reason_code} -> subscribing {', '.join(t for t, _ in topics)}"
        )
        for t, qos in topics:
            client.subscribe(t, qos=qos)

    def on_message(client, userdata, msg, *args, **kwargs):
        ts = time.strftime("%H:%M:%S")
        print(f"[{ts}] {msg.topic}:\n{pretty(msg.payload)}\n---")

    client.on_connect = on_connect
    client.on_message = on_message

    # Graceful exit on Ctrl+C
    def _sigint(*_):
        try:
            client.disconnect()
        finally:
            sys.exit(0)

    signal.signal(signal.SIGINT, _sigint)

    client.connect(broker, port, keepalive=60)
    client.loop_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
