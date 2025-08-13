#!/usr/bin/env python3
"""One-off script to purge legacy per-entity Home Assistant discovery topics.

Run once (while broker reachable) AFTER switching to unified device-level discovery.
It publishes empty retained payloads to old sensor/button/binary_sensor topics so
only the single device config remains.

Usage:
  poetry run python scripts/cleanup_discovery.py --broker HOST --port 1883 \
      --username USER --password PASS --prefix homeassistant --base twickenham_events

If username/password omitted and broker allows anonymous, they are skipped.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable
import sys

try:
    import paho.mqtt.client as mqtt  # type: ignore
except Exception as e:  # pragma: no cover
    print(f"paho-mqtt required: {e}")
    sys.exit(2)

DEFAULT_COMPONENTS = [
    "status",
    "last_run",
    "upcoming",
    "next",
    "today",
    "refresh",
    "clear_cache",
    "event_count",
    "availability",
]


def build_topics(prefix: str, base: str, components: Iterable[str]) -> list[str]:
    topics: list[str] = []
    for comp in components:
        if comp == "availability":
            topics.append(f"{prefix}/binary_sensor/{base}_availability/config")
            topics.append(
                f"{prefix}/binary_sensor/tw_events_availability/config"
            )  # older
            continue
        part = "button" if comp in {"refresh", "clear_cache"} else "sensor"
        topics.append(f"{prefix}/{part}/{base}_{comp}/config")
        # historical shorter prefix (tw_events_*)
        short_base = "tw_events"
        topics.append(f"{prefix}/{part}/{short_base}_{comp}/config")
    return topics


def parse_args():
    p = argparse.ArgumentParser(description="Purge legacy discovery topics")
    p.add_argument("--broker", required=True)
    p.add_argument("--port", type=int, default=1883)
    p.add_argument("--username")
    p.add_argument("--password")
    p.add_argument("--prefix", default="homeassistant")
    p.add_argument("--base", default="twickenham_events")
    p.add_argument(
        "--extra", action="append", default=[], help="Additional component key to clear"
    )
    return p.parse_args()


def main():  # pragma: no cover
    a = parse_args()
    comps = DEFAULT_COMPONENTS + a.extra
    topics = build_topics(a.prefix, a.base, comps)
    client = mqtt.Client(protocol=mqtt.MQTTv5)
    if a.username and a.password:
        client.username_pw_set(a.username, a.password)
    client.connect(a.broker, a.port, 30)
    client.loop_start()
    for t in topics:
        client.publish(t, "", retain=True)
        print(f"cleared {t}")
    client.loop_stop()
    client.disconnect()
    print("✅ legacy discovery topics cleared")


if __name__ == "__main__":  # pragma: no cover
    main()
