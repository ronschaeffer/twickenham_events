#!/usr/bin/env python3
"""Runtime validation script for Twickenham Events MQTT topics.

Purpose:
  1. Subscribe to expected retained topics.
  2. Trigger a one-shot service run (or reuse an existing run) to publish.
  3. Collect messages for a short window.
  4. Validate presence + basic schema of each payload and report discrepancies.

Usage:
  poetry run python scripts/mqtt_validate.py --broker 10.10.10.21 --port 8883 \
      --topics twickenham_events/status twickenham_events/events/all_upcoming \
      twickenham_events/events/next twickenham_events/events/today twickenham_events/availability

If --run-service is supplied, the script will invoke `twick-events service --once` in a
subprocess BEFORE validating (gives a fresh publish).

Exit codes:
  0 = all required topics received & validated
  1 = missing topics or validation errors

Notes:
  - Designed for quick manual verification; not a strict unit test.
  - TLS NOT auto-enabled; mirrors current non-TLS config even on 8883.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
import ssl
import subprocess
import sys
import time
from typing import Any

try:
    from ha_mqtt_publisher.mqtt_utils import extract_reason_code  # type: ignore
except Exception:  # pragma: no cover - upstream helper optional

    def extract_reason_code(*args, **kwargs):
        """Lightweight fallback: try to extract an int-style reason code from
        whatever signature the paho callback provided. Return None if not found.
        """
        # Common positions: (rc,), (client, userdata, flags, rc), (client, userdata, reason_code, props)
        for a in args:
            if isinstance(a, int):
                return a
            try:
                if hasattr(a, "rc"):
                    return int(a.rc)
                if hasattr(a, "reason_code"):
                    return int(a.reason_code)
            except Exception:
                pass
        for v in kwargs.values():
            if isinstance(v, int):
                return v
            try:
                if hasattr(v, "rc"):
                    return int(v.rc)
                if hasattr(v, "reason_code"):
                    return int(v.reason_code)
            except Exception:
                pass
        return None


import paho.mqtt.client as mqtt

try:  # paho >=2.x
    from paho.mqtt.client import CallbackAPIVersion  # type: ignore
except Exception:  # pragma: no cover
    CallbackAPIVersion = None  # type: ignore

try:  # local import for shared configuration
    from twickenham_events.config import Config  # type: ignore
except Exception:  # pragma: no cover
    Config = None  # type: ignore

DEFAULT_TOPICS = [
    "twickenham_events/status",
    "twickenham_events/events/all_upcoming",
    "twickenham_events/events/next",
    "twickenham_events/events/today",
    "twickenham_events/availability",
]

# Expected component keys (cmps) in device-level discovery bundle
EXPECTED_DISCOVERY_COMPONENTS = {
    "status",
    "last_run",
    "upcoming",
    "next",
    "today",
    "refresh",
    "clear_cache",
    # event_count optional
}


@dataclass
class MessageRecord:
    topic: str
    payload: Any
    received_at: float


def parse_args() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Validate Twickenham Events MQTT publishes")
    p.add_argument("--broker", default="localhost")
    p.add_argument("--port", type=int, default=1883)
    p.add_argument("--client-id", default="tw_events_validator")
    p.add_argument("--username")
    p.add_argument("--password")
    p.add_argument(
        "--timeout", type=float, default=3.0, help="seconds to wait after subscribe"
    )
    p.add_argument(
        "--discovery-timeout",
        type=float,
        default=0.0,
        help=(
            "optional extended timeout (seconds) just for discovery topics; "
            "if > main --timeout, the validator will continue waiting up to this total time "
            "for only the discovery topics after all data topics have arrived or the main timeout expires"
        ),
    )
    p.add_argument(
        "--run-service",
        action="store_true",
        help="invoke 'twick-events service --once' before validation",
    )
    p.add_argument(
        "--topics",
        nargs="*",
        default=DEFAULT_TOPICS,
        help="explicit topic list to validate",
    )
    p.add_argument(
        "--include-discovery",
        action="store_true",
        help="also validate Home Assistant discovery config topics",
    )
    p.add_argument(
        "--purge-discovery",
        action="store_true",
        help="clear all legacy & device discovery topics before (re)publishing",
    )
    p.add_argument(
        "--strict",
        action="store_true",
        help="enable deeper cross-topic content validation",
    )
    p.add_argument(
        "--presence-only",
        action="store_true",
        help="only check that topics are present (skip schema/content validation)",
    )
    p.add_argument(
        "--config",
        default="config/config.yaml",
        help="path to application config (for credential auto-load)",
    )
    return p


def launch_service_once():
    try:
        # Use module invocation to avoid dependency on console script installation
        subprocess.run(
            [sys.executable, "-m", "twickenham_events", "service", "--once"], check=True
        )
    except Exception as e:
        print(f"WARNING: service run failed: {e}")


def basic_schema_checks(topic: str, payload: Any) -> list[str]:
    errors: list[str] = []
    if topic.endswith("/status"):
        if not isinstance(payload, dict):
            errors.append("status: not a dict")
        else:
            for key in ["status", "event_count", "last_updated"]:
                if key not in payload:
                    errors.append(f"status: missing {key}")
    elif topic.endswith("/all_upcoming"):
        if not isinstance(payload, dict):
            errors.append("all_upcoming: payload not a dict")
        else:
            if "count" not in payload:
                errors.append("all_upcoming: missing count")
            if "last_updated" not in payload:
                errors.append("all_upcoming: missing last_updated")
            # Validate events_json structure and per-event keys used by HA cards
            evj = payload.get("events_json")
            if not isinstance(evj, dict):
                errors.append("all_upcoming: missing events_json dict")
            else:
                by_month = evj.get("by_month")
                if not isinstance(by_month, list):
                    errors.append("all_upcoming: events_json.by_month not a list")
                else:
                    for mi, month in enumerate(by_month):
                        if not isinstance(month, dict):
                            errors.append(f"all_upcoming: by_month[{mi}] not a dict")
                            continue
                        for mkey in ("key", "label", "days"):
                            if mkey not in month:
                                errors.append(
                                    f"all_upcoming: by_month[{mi}] missing {mkey}"
                                )
                        days = month.get("days") if isinstance(month, dict) else None
                        if isinstance(days, list):
                            for di, day in enumerate(days):
                                if not isinstance(day, dict):
                                    errors.append(
                                        f"all_upcoming: days[{di}] not a dict (month {mi})"
                                    )
                                    continue
                                for dkey in ("date", "label", "events"):
                                    if dkey not in day:
                                        errors.append(
                                            f"all_upcoming: by_month[{mi}].days[{di}] missing {dkey}"
                                        )
                                events = day.get("events")
                                if isinstance(events, list):
                                    for ei, ev in enumerate(events):
                                        if not isinstance(ev, dict):
                                            errors.append(
                                                f"all_upcoming: event[{ei}] not a dict (month {mi} day {di})"
                                            )
                                            continue
                                        # Each event must expose these keys for HA cards
                                        required_ev_keys = (
                                            "fixture",
                                            "start_time",
                                            "fixture_short",
                                            "emoji",
                                            "icon",
                                            "crowd",
                                        )
                                        for rk in required_ev_keys:
                                            if rk not in ev:
                                                errors.append(
                                                    f"all_upcoming: by_month[{mi}].days[{di}].events[{ei}] missing {rk}"
                                                )
    elif topic.endswith("/next"):
        if not isinstance(payload, dict) or "last_updated" not in payload:
            errors.append("next: missing last_updated")
    elif topic.endswith("/today"):
        if not isinstance(payload, dict) or "has_event_today" not in payload:
            errors.append("today: missing has_event_today")
    elif topic.endswith("/availability") and payload not in ("online", "offline"):
        errors.append("availability: invalid value")
    # Device-level discovery topic heuristic: contains /device/ and ends with /config and payload is dict
    elif "/device/" in topic and topic.endswith("/config"):
        # Device-level discovery bundle must now ONLY use 'cmps' (legacy ents/entities rejected)
        if not isinstance(payload, dict):
            errors.append("discovery: payload not dict")
        else:
            if "dev" not in payload:
                errors.append("discovery: missing dev")
            # Reject legacy keys outright if present
            if "ents" in payload:
                errors.append("discovery: unexpected legacy key 'ents' (cmps only)")
            if "entities" in payload:
                errors.append("discovery: unexpected legacy key 'entities' (cmps only)")
            components = payload.get("cmps")
            if not isinstance(components, dict):
                errors.append("discovery: missing or invalid cmps dict (required)")
            else:
                missing = [
                    c for c in EXPECTED_DISCOVERY_COMPONENTS if c not in components
                ]
                if missing:
                    errors.append(f"discovery: missing cmps {missing}")
                for name, comp in components.items():
                    if not isinstance(comp, dict):
                        errors.append(f"discovery: component {name} not dict")
                        continue
                    if "p" not in comp:
                        errors.append(f"discovery: component {name} missing 'p'")
                    if name in ("refresh", "clear_cache") and comp.get("p") != "button":
                        errors.append(f"discovery: component {name} expected button")
    return errors


def main(argv: list[str]) -> int:
    args = parse_args().parse_args(argv)
    topics = list(args.topics)

    # Auto-load config for credentials if available and not explicitly provided
    loaded_config = None
    if Config is not None:
        try:
            loaded_config = Config.from_file(args.config)
        except Exception as e:  # pragma: no cover - config optional
            print(f"NOTE: Could not load config {args.config}: {e}")

    # Autodetect broker/port from config if user didn't override (helps when using --run-service)
    if loaded_config:
        cfg_broker = loaded_config.get("mqtt.broker_url") or loaded_config.get(
            "mqtt.host"
        )
        cfg_port = loaded_config.get("mqtt.broker_port") or loaded_config.get(
            "mqtt.port"
        )
        # Only override defaults if user kept default values (localhost/1883) and config supplies something
        if args.broker == "localhost" and cfg_broker:
            args.broker = cfg_broker
            print(f"Autodetected broker from config: {args.broker}")
        if args.port == 1883 and cfg_port:
            try:
                args.port = int(cfg_port)
                print(f"Autodetected port from config: {args.port}")
            except Exception:  # pragma: no cover
                pass

    if args.username is None and loaded_config and loaded_config.mqtt_username:
        args.username = loaded_config.mqtt_username
        print("Using MQTT username from config/env")
    if args.password is None and loaded_config and loaded_config.mqtt_password:
        args.password = loaded_config.mqtt_password
        print("Using MQTT password from config/env")

    discovery_topics: list[str] = []
    # Discovery topic inclusion policy:
    #  - If --include-discovery is passed, include.
    #  - If --strict is enabled, ALWAYS include (assert presence) even without flag.
    if loaded_config is not None:
        base = loaded_config.get("app.unique_id_prefix", "twickenham_events")
        prefix = loaded_config.service_discovery_prefix
        device_topic = f"{prefix}/device/{base}/config"
        if args.include_discovery or args.strict:
            if device_topic not in topics:
                topics.append(device_topic)
            discovery_topics = [device_topic]
            reason = (
                "strict mode" if args.strict and not args.include_discovery else "flag"
            )
            print(f"Including discovery topic ({reason}):")
            print(f"  - {device_topic}")

    # Discovery purge (before potential service run)
    if args.purge_discovery and loaded_config is not None:
        base = loaded_config.get("app.unique_id_prefix", "twickenham_events")
        prefix = loaded_config.service_discovery_prefix
        purge_topics = [
            # Current device-level bundle
            f"{prefix}/device/{base}/config",
            # Current standardized buttons
            f"{prefix}/button/{base}_refresh/config",
            f"{prefix}/button/{base}_clear_cache/config",
            # Legacy per-entity sensors (long prefix)
            f"{prefix}/sensor/{base}_status/config",
            f"{prefix}/sensor/{base}_event_count/config",
            f"{prefix}/sensor/{base}_last_run/config",
            f"{prefix}/binary_sensor/{base}_availability/config",
            # Legacy short-prefix forms (tw_events_*) just in case
            f"{prefix}/sensor/tw_events_status/config",
            f"{prefix}/sensor/tw_events_event_count/config",
            f"{prefix}/sensor/tw_events_last_run/config",
            f"{prefix}/binary_sensor/tw_events_availability/config",
            f"{prefix}/button/tw_events_refresh/config",
            f"{prefix}/button/tw_events_clear_cache/config",
        ]
        print("Purging discovery topics:")
        if CallbackAPIVersion is not None:  # use modern callback API
            purge_client = mqtt.Client(
                client_id=args.client_id + "_purge",
                protocol=mqtt.MQTTv5,
                callback_api_version=CallbackAPIVersion.VERSION2,
            )
        else:
            purge_client = mqtt.Client(
                client_id=args.client_id + "_purge", protocol=mqtt.MQTTv5
            )
        if args.username and args.password:
            purge_client.username_pw_set(args.username, args.password)
        purge_client.connect(args.broker, args.port, 30)
        purge_client.loop_start()
        for pt in purge_topics:
            purge_client.publish(pt, "", retain=True)
        time.sleep(0.4)
        purge_client.loop_stop()
        purge_client.disconnect()
    if args.run_service:
        print("Running one-shot service to refresh retained topics...")
        launch_service_once()

    records: dict[str, MessageRecord] = {}
    done = dict.fromkeys(topics, False)

    def on_connect(client, userdata, *args, **kwargs):  # type: ignore
        # Accept both v1 and v2 signatures. Use helper to extract an int-like reason_code.
        reason_code = extract_reason_code(*args, **kwargs)
        # If reason_code is None (some brokers / callback variants), assume
        # the connection succeeded and proceed to subscribe. Only treat a
        # numeric non-zero code as an explicit failure.
        if reason_code is None or reason_code == 0:
            for t in topics:
                client.subscribe(t)
        else:
            print(f"ERROR: connect failed rc={reason_code}")

    def on_message(client, userdata, msg, *args, **kwargs):  # type: ignore
        try:
            payload_raw = msg.payload.decode("utf-8") if msg.payload else ""
            try:
                payload = json.loads(payload_raw)
            except Exception:
                payload = payload_raw
            records[msg.topic] = MessageRecord(msg.topic, payload, time.time())
            done[msg.topic] = True
        except Exception as e:  # pragma: no cover
            print(f"decode error {e}")

    # Use MQTTv5 protocol to suppress older callback API deprecation warnings (if supported)
    if CallbackAPIVersion is not None:
        client = mqtt.Client(
            client_id=args.client_id,
            protocol=mqtt.MQTTv5,
            callback_api_version=CallbackAPIVersion.VERSION2,
        )
    else:
        client = mqtt.Client(client_id=args.client_id, protocol=mqtt.MQTTv5)
    if args.username and args.password:
        client.username_pw_set(args.username, args.password)
    elif loaded_config and loaded_config.get("mqtt.security") == "username":
        print(
            "WARNING: Security=username but no credentials applied (connection may fail)"
        )
    client.on_connect = on_connect
    client.on_message = on_message

    # If configuration / environment indicates TLS should be used, configure client
    # to use TLS with permissive verification when no CA is provided (matches
    # service behavior for local validation).
    try:
        tls_requested = False
        if loaded_config is not None:
            tls_requested = bool(loaded_config.get("mqtt.tls"))
        _tls_env = os.getenv("MQTT_USE_TLS")
        if _tls_env and _tls_env.lower() in ("true", "1", "yes", "on"):
            tls_requested = True
        # If connecting to standard non-TLS port, avoid enabling TLS unless explicitly forced via env
        if args.port == 1883:
            _force_tls_env = os.getenv("MQTT_USE_TLS")
            if not (
                _force_tls_env and _force_tls_env.lower() in ("true", "1", "yes", "on")
            ):
                tls_requested = False
        # Honor TLS_VERIFY env var for validator behavior
        tls_verify_env = os.getenv("TLS_VERIFY")
        verify_flag = None
        if tls_verify_env is not None:
            try:
                verify_flag = str(tls_verify_env).lower() in ("true", "1", "yes", "on")
            except Exception:
                verify_flag = None
        if tls_requested:
            # If config provided a dict of TLS options, prefer explicit cert paths
            cfg_tls = None
            try:
                cfg_tls = (
                    loaded_config.get("mqtt.tls") if loaded_config is not None else None
                )
            except Exception:
                cfg_tls = None
            try:
                if isinstance(cfg_tls, dict):
                    ca = cfg_tls.get("ca_certs")
                    certfile = cfg_tls.get("certfile")
                    keyfile = cfg_tls.get("keyfile")
                    # Use provided certs if present
                    if ca or certfile:
                        client.tls_set(ca_certs=ca, certfile=certfile, keyfile=keyfile)
                        if verify_flag is False:
                            client.tls_insecure_set(True)
                    else:
                        # Permissive fallback for local validation (no CA available)
                        if verify_flag is True:
                            client.tls_set()  # default verification
                        else:
                            client.tls_set(cert_reqs=ssl.CERT_NONE)
                            client.tls_insecure_set(True)
                else:
                    # Boolean/envar-driven TLS: use permissive mode for validation
                    if verify_flag is True:
                        client.tls_set()
                    else:
                        client.tls_set(cert_reqs=ssl.CERT_NONE)
                        client.tls_insecure_set(True)
            except Exception:
                # Non-fatal; proceed without TLS if TLS setup fails for any reason
                pass
    except Exception:
        # Non-fatal; proceed without TLS if TLS setup fails for any reason
        pass

    print(f"Connecting to {args.broker}:{args.port} ...")
    client.connect(args.broker, args.port, keepalive=30)
    client.loop_start()

    # Waiting strategy:
    # 1. Wait up to --timeout for all topics (data + discovery).
    # 2. If discovery not all received and --discovery-timeout > --timeout, continue
    #    waiting (without failing) for remaining discovery topics until extended deadline.
    main_deadline = time.time() + args.timeout
    extended_deadline = (
        time.time() + args.discovery_timeout
        if args.discovery_timeout and args.discovery_timeout > args.timeout
        else main_deadline
    )
    while True:
        now = time.time()
        # If all topics received, break early
        if all(done.values()):
            break
        # During primary phase wait for all topics
        if now < main_deadline:
            time.sleep(0.05)
            continue
        # Past primary phase: only continue if we have an extended window and only discovery topics remain
        if now <= extended_deadline:
            remaining = [t for t, ok in done.items() if not ok]
            # If non-discovery topics still missing, we won't get them now; break.
            if any(r not in discovery_topics for r in remaining):
                break
            # Provide a lightweight periodic notice every ~1s
            if int(now) % 1 == 0:
                pass  # (could add debug print if needed)
            time.sleep(0.05)
            continue
        # Extended window expired
        break

    client.loop_stop()
    client.disconnect()

    missing = [t for t, ok in done.items() if not ok]
    errors: list[str] = []
    if not args.presence_only:
        for rec in records.values():
            errors.extend(basic_schema_checks(rec.topic, rec.payload))

        # Strict cross-topic validation
        if args.strict and not missing:
            try:
                status = records.get("twickenham_events/status")
                all_upcoming = records.get("twickenham_events/events/all_upcoming")
                next_topic = records.get("twickenham_events/events/next")
                today_topic = records.get("twickenham_events/events/today")
                avail = records.get("twickenham_events/availability")
                # Status internal consistency
                if status and isinstance(status.payload, dict):
                    ec = status.payload.get("event_count")
                    if all_upcoming and isinstance(all_upcoming.payload, dict):
                        count_val = all_upcoming.payload.get("count")
                        if isinstance(count_val, int) and ec != count_val:
                            errors.append(
                                f"strict: event_count mismatch status={ec} count={count_val}"
                            )
                # next event must match first upcoming if both available
                if (
                    next_topic
                    and all_upcoming
                    and isinstance(next_topic.payload, dict)
                    and isinstance(all_upcoming.payload, dict)
                ):
                    # Next sensor exposes flattened fields; compare fixture against first events_json entry
                    nf = (
                        next_topic.payload.get("fixture")
                        if isinstance(next_topic.payload, dict)
                        else None
                    )
                    if not nf:
                        # fallback to short or older fields if present
                        rec = records.get("twickenham_events/events/next")
                        if rec and isinstance(rec.payload, dict):
                            nf = rec.payload.get("fixture") or rec.payload.get(
                                "fixture_short"
                            )
                    first_fixture = None
                    evj = (
                        all_upcoming.payload.get("events_json")
                        if isinstance(all_upcoming.payload, dict)
                        else None
                    )
                    if isinstance(evj, dict):
                        by_month = evj.get("by_month") or []
                        if isinstance(by_month, list) and by_month:
                            days = by_month[0].get("days") or []
                            if isinstance(days, list) and days:
                                first_events = days[0].get("events") or []
                                if isinstance(first_events, list) and first_events:
                                    first_fixture = first_events[0].get(
                                        "fixture"
                                    ) or first_events[0].get("fixture_short")
                    if nf and first_fixture and nf != first_fixture:
                        errors.append(
                            "strict: next.fixture mismatch first events_json entry"
                        )
                # today topic consistency
                if today_topic and isinstance(today_topic.payload, dict):
                    has_today = today_topic.payload.get("has_event_today")
                    events_today = today_topic.payload.get("events_today")
                    if (
                        isinstance(events_today, int)
                        and bool(events_today > 0) != has_today
                    ):
                        errors.append(
                            "strict: today.has_event_today != (events_today>0)"
                        )
                # availability correlation
                if (
                    avail
                    and isinstance(avail.payload, str)
                    and avail.payload == "offline"
                ):
                    errors.append("strict: availability offline while data present")
                # Device-level discovery component presence
                device_disc = (
                    records.get(discovery_topics[0]) if discovery_topics else None
                )
                if device_disc and isinstance(device_disc.payload, dict):
                    # In strict mode only 'cmps' is acceptable; legacy keys should have been flagged earlier
                    components = (
                        device_disc.payload.get("cmps")
                        if isinstance(device_disc.payload.get("cmps"), dict)
                        else None
                    )
                    if components is None:
                        errors.append("strict: device discovery missing cmps dict")
                    else:
                        missing_cmps = [
                            c
                            for c in EXPECTED_DISCOVERY_COMPONENTS
                            if c not in components
                        ]
                        if missing_cmps:
                            errors.append(
                                f"strict: missing discovery cmps {missing_cmps}"
                            )
            except Exception as e:  # pragma: no cover
                errors.append(f"strict: validation exception {e}")

    if missing:
        print("\nMissing topics:")
        for t in missing:
            print(f"  - {t}")
    if errors:
        print("\nValidation errors:")
        for e in errors:
            print(f"  - {e}")

    print("\nSummary:")
    for t in topics:
        label = "DISC" if t in discovery_topics else "DATA"
        if t in records:
            print(f"  [{label}] {t}: OK ({type(records[t].payload).__name__})")
        else:
            print(f"  [{label}] {t}: MISSING")

    # In presence-only mode we only require topics to be present
    if args.presence_only:
        if not missing:
            print("\n✅ All topics received (presence-only mode)")
            return 0
        else:
            print("\n❌ Missing topics in presence-only mode")
            return 1

    if not missing and not errors:
        print("\n✅ All topics received and validated")
        return 0
    print("\n❌ Issues detected")
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
