#!/usr/bin/env python3
"""Force removal of all legacy Twickenham Events MQTT discovery topics.

Publishes empty retained payloads to every known historical discovery topic so the
broker forgets them (retain deletion). Run before or after deploying the new
single device-level discovery.

Usage:
  poetry run python scripts/mqtt_purge_legacy_discovery.py --broker 10.10.10.21 --port 1883 \
      --username USER --password PASS

If credentials / TLS handled via env/config you can omit username/password.
"""

from __future__ import annotations

import argparse
import time

import paho.mqtt.client as mqtt

LEGACY_IDS = [
    # Long prefix forms
    "twickenham_events_status",
    "twickenham_events_event_count",
    "twickenham_events_last_run",
    "twickenham_events_availability",
    # Short prefix forms
    "tw_events_status",
    "tw_events_event_count",
    "tw_events_last_run",
    "tw_events_availability",
]
LEGACY_BUTTONS = [
    "tw_events_refresh",
    "tw_events_clear_cache",
]
NEW_BUTTONS = [
    "twickenham_events_refresh",
    "twickenham_events_clear_cache",
]


def parse_args():
    p = argparse.ArgumentParser(description="Purge legacy discovery topics (retained)")
    p.add_argument("--broker", default="localhost")
    p.add_argument("--port", type=int, default=1883)
    p.add_argument("--username")
    p.add_argument("--password")
    p.add_argument(
        "--discovery-prefix", default="homeassistant", help="HA discovery prefix"
    )
    p.add_argument("--base", default="twickenham_events", help="base unique id prefix")
    return p.parse_args()


def main():
    args = parse_args()
    client = mqtt.Client(client_id="tw_events_purge")
    if args.username and args.password:
        client.username_pw_set(args.username, args.password)
    client.connect(args.broker, args.port, 30)
    client.loop_start()

    topics = []
    dp = args.discovery_prefix.rstrip("/")

    # Per-entity sensors / binary sensor forms
    for sid in LEGACY_IDS:
        if sid.endswith("_availability"):
            topics.append(f"{dp}/binary_sensor/{sid}/config")
        else:
            topics.append(f"{dp}/sensor/{sid}/config")
    # Buttons (legacy + new if wanting a reset)
    for bid in LEGACY_BUTTONS + NEW_BUTTONS:
        topics.append(f"{dp}/button/{bid}/config")
    # Device-level (in case we want a clean slate)
    topics.append(f"{dp}/device/{args.base}/config")

    print("Purging topics (retained deletion):")
    for t in topics:
        print(f"  - {t}")
        client.publish(t, "", retain=True)

    time.sleep(0.5)
    client.loop_stop()
    client.disconnect()
    print("Done. Old discovery configs removed from broker.")


if __name__ == "__main__":  # pragma: no cover
    main()
