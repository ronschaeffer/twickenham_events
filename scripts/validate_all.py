#!/usr/bin/env python3
"""Run all artifact validators (ICS, upcoming_events, MQTT) in sequence.

Return first failing exit code (1 for validation failure, 2 for IO/exec error) while
printing a compact summary. Assumes scripts are executable with same Python.

Usage examples:
  poetry run python scripts/validate_all.py --ics output/twickenham_events.ics \
      --upcoming output/upcoming_events.json --mqtt --mqtt-host localhost

You can skip a validator via the corresponding --no-* flag.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

try:
    from twickenham_events.config import Config  # type: ignore
except Exception:  # pragma: no cover
    Config = None  # type: ignore

ROOT = Path(__file__).resolve().parent

VALIDATORS = {
    "ics": "ics_validate.py",
    "upcoming": "upcoming_events_validate.py",
    "mqtt": "mqtt_validate.py",  # existing script
}


def parse_args():
    p = argparse.ArgumentParser(description="Run all validation scripts")
    p.add_argument(
        "--ics", default="output/twickenham_events.ics", help="ICS file path"
    )
    p.add_argument(
        "--upcoming", default="output/upcoming_events.json", help="Upcoming JSON path"
    )
    p.add_argument(
        "--mqtt", action="store_true", help="Enable MQTT validation (default off)"
    )
    p.add_argument(
        "--mqtt-include-discovery",
        action="store_true",
        help="Include device-level discovery validation in MQTT step",
    )
    p.add_argument(
        "--mqtt-discovery-timeout",
        type=float,
        default=0.0,
        help="Extended seconds to wait specifically for discovery topics (passed to mqtt_validate --discovery-timeout)",
    )
    p.add_argument("--no-ics", action="store_true", help="Skip ICS validation")
    p.add_argument(
        "--no-upcoming", action="store_true", help="Skip upcoming events validation"
    )
    # pass-through MQTT args
    p.add_argument("--broker", default="localhost", help="MQTT broker host")
    p.add_argument("--mqtt-port", type=int, default=1883)
    p.add_argument("--mqtt-username")
    p.add_argument("--mqtt-password")
    p.add_argument(
        "--strict", action="store_true", help="Strict mode for MQTT validator"
    )
    p.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Timeout for MQTT validator subscription",
    )
    p.add_argument(
        "--mqtt-timeout",
        type=float,
        default=None,
        help="Override timeout (seconds) passed to MQTT validator (preferred over --timeout)",
    )
    p.add_argument(
        "--mqtt-run-service",
        action="store_true",
        help="Invoke service one-shot before validating MQTT topics",
    )
    p.add_argument(
        "--allow-empty-upcoming",
        action="store_true",
        help="Permit upcoming events JSON to have zero events (off-season)",
    )
    p.add_argument(
        "--scrape-run",
        action="store_true",
        help="Run 'twick-events scrape --output <dir>' before validation to refresh artifacts",
    )
    p.add_argument(
        "--mqtt-count-retries",
        type=int,
        default=3,
        help="Retries for lightweight MQTT count retrieval (after validator)",
    )
    p.add_argument(
        "--mqtt-count-retry-delay",
        type=float,
        default=1.0,
        help="Delay seconds between MQTT count retrieval attempts",
    )
    return p.parse_args()


def run_validator(kind: str, args_list: list[str]) -> int:
    script = ROOT / VALIDATORS[kind]
    cmd = [sys.executable, str(script), *args_list]
    print(f"→ Running {kind} validator: {' '.join(cmd)}")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except Exception as e:
        print(f"ERROR: failed invoking {kind} validator: {e}")
        return 2
    if proc.stdout:
        print(proc.stdout.rstrip())
    if proc.stderr:
        print(proc.stderr.rstrip())
    return proc.returncode


def main(argv=None) -> int:  # pragma: no cover
    a = parse_args()
    overall_rc = 0

    if a.scrape_run:
        # Derive output directory from upcoming path
        out_dir = Path(a.upcoming).parent
        print(f"→ Running scrape to refresh artifacts in {out_dir} ...")
        try:
            # Prefer module invocation to avoid dependency on console script being installed
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "twickenham_events",
                    "scrape",
                    "--output",
                    str(out_dir),
                ],
                check=True,
            )
        except Exception as e:  # pragma: no cover
            print(f"ERROR: scrape run failed: {e}")
            return 2

    # ICS
    if not a.no_ics:
        rc = run_validator("ics", ["--file", a.ics])
        if rc != 0:
            overall_rc = rc if overall_rc == 0 else overall_rc

    # Upcoming events
    if not a.no_upcoming:
        upcoming_args = ["--file", a.upcoming]
        if a.allow_empty_upcoming:
            upcoming_args.append("--allow-empty")
        rc = run_validator("upcoming", upcoming_args)
        if rc != 0 and overall_rc == 0:
            overall_rc = rc

    # MQTT (opt-in)
    if a.mqtt:
        # Resolve broker from config if default left in place
        if a.broker == "localhost" and Config is not None:
            try:
                cfg = Config.from_file("config/config.yaml")
                a.broker = cfg.mqtt_broker or a.broker
            except Exception as e:  # pragma: no cover
                print(f"NOTE: unable to load config for broker: {e}")
        if a.broker == "localhost":
            print("ERROR: broker still 'localhost' - specify --broker or set config")
            return 2
        effective_timeout = a.mqtt_timeout if a.mqtt_timeout is not None else a.timeout
        mqtt_args = [
            "--broker",
            a.broker,
            "--port",
            str(a.mqtt_port),
            "--timeout",
            str(effective_timeout),
        ]
        if a.mqtt_username:
            mqtt_args += ["--username", a.mqtt_username]
        if a.mqtt_password:
            mqtt_args += ["--password", a.mqtt_password]
        if a.strict:
            mqtt_args.append("--strict")
        if a.mqtt_run_service:
            mqtt_args.append("--run-service")
        if getattr(a, "mqtt_include_discovery", False):
            mqtt_args.append("--include-discovery")
        if getattr(a, "mqtt_discovery_timeout", 0) and a.mqtt_discovery_timeout > 0:
            mqtt_args += ["--discovery-timeout", str(a.mqtt_discovery_timeout)]
        rc = run_validator("mqtt", mqtt_args)
        if rc != 0 and overall_rc == 0:
            overall_rc = rc
        mqtt_ok = rc == 0
    else:
        mqtt_ok = False

    # Cross-artifact consistency: ICS vs upcoming (and MQTT if ok)
    ics_count = None
    json_count = None
    try:
        if not a.no_ics:
            with open(a.ics, encoding="utf-8") as f:
                ics_count = sum(1 for line in f if line.strip() == "BEGIN:VEVENT")
    except Exception as e:  # pragma: no cover
        print(f"NOTE: failed reading ICS for count: {e}")
    try:
        if not a.no_upcoming:
            with open(a.upcoming, encoding="utf-8") as f:
                data = json.load(f)
                events = data.get("events") if isinstance(data, dict) else None
                if isinstance(events, list):
                    json_count = len(events)
    except Exception as e:  # pragma: no cover
        print(f"NOTE: failed reading upcoming JSON for count: {e}")

    mqtt_count = None
    if mqtt_ok:
        try:
            import os
            import ssl

            import paho.mqtt.client as mqtt  # type: ignore

            try:
                from paho.mqtt.client import CallbackAPIVersion  # type: ignore
            except Exception:  # pragma: no cover
                CallbackAPIVersion = None  # type: ignore

            for attempt in range(1, a.mqtt_count_retries + 1):
                topic = "twickenham_events/events/all_upcoming"
                received: dict[str, int] = {}

                def _on_connect(client, _ud, _flags, _rc, _props=None, _topic=topic):  # type: ignore
                    # Initial subscribe; retained message should arrive quickly.
                    client.subscribe(_topic)

                def _on_message(_client, _ud, msg, _received=received):  # type: ignore
                    try:
                        payload = json.loads(msg.payload.decode("utf-8"))
                    except Exception:  # pragma: no cover
                        return
                    # Prefer top-level count when available (current schema)
                    try:
                        if isinstance(payload, dict):
                            if isinstance(payload.get("count"), int):
                                _received["count"] = int(payload["count"])
                            else:
                                evs = payload.get("events")
                                if isinstance(evs, list):
                                    _received["count"] = len(evs)
                                else:
                                    evj = payload.get("events_json")
                                    if isinstance(evj, dict) and isinstance(
                                        evj.get("count"), int
                                    ):
                                        _received["count"] = int(evj["count"])
                    except Exception:
                        pass
                    _client.disconnect()

                if CallbackAPIVersion is not None:
                    client = mqtt.Client(
                        protocol=mqtt.MQTTv5,
                        callback_api_version=CallbackAPIVersion.VERSION2,
                    )
                else:
                    client = mqtt.Client(protocol=mqtt.MQTTv5)
                client.on_connect = _on_connect
                client.on_message = _on_message

                # Configure auth if provided via args or env
                _user = a.mqtt_username or os.getenv("MQTT_USERNAME")
                _pass = a.mqtt_password or os.getenv("MQTT_PASSWORD")
                if _user and _pass:
                    try:
                        client.username_pw_set(_user, _pass)
                    except Exception:
                        pass

                # Configure TLS if using TLS port or explicitly requested by env
                _force_tls_env = os.getenv("MQTT_USE_TLS")
                _use_tls = a.mqtt_port == 8883 or (
                    _force_tls_env
                    and _force_tls_env.lower() in ("true", "1", "yes", "on")
                )
                if _use_tls:
                    _tls_verify_env = os.getenv("TLS_VERIFY")
                    _verify = True
                    if _tls_verify_env and _tls_verify_env.lower() in (
                        "false",
                        "0",
                        "no",
                        "off",
                    ):
                        _verify = False
                    try:
                        if _verify:
                            client.tls_set()  # default system CA
                        else:
                            client.tls_set(cert_reqs=ssl.CERT_NONE)
                            client.tls_insecure_set(True)
                    except Exception:
                        pass
                try:
                    client.connect(a.broker, a.mqtt_port, 30)
                except Exception as e:  # pragma: no cover
                    if attempt == a.mqtt_count_retries:
                        print(f"NOTE: MQTT count connect failed final attempt: {e}")
                        break
                    print(
                        f"NOTE: MQTT count connect failed attempt {attempt}/{a.mqtt_count_retries}: {e} (retrying)"
                    )
                    time.sleep(a.mqtt_count_retry_delay)
                    continue
                client.loop_start()
                # Grace period to allow retained delivery; slightly longer for some brokers/TLS
                time.sleep(0.25)
                start = time.time()
                # Increase wait window for slower brokers/TLS retained delivery
                while (
                    time.time() - start < 10
                    and "count" not in received
                    and client.is_connected()
                ):
                    time.sleep(0.05)
                    # Mid-wait re-subscribe once (after ~1s) if nothing yet
                    if 1.0 < time.time() - start < 1.1 and "count" not in received:
                        try:
                            client.subscribe(topic)
                        except Exception:
                            pass
                client.loop_stop()
                client.disconnect()
                if "count" in received:
                    mqtt_count = received["count"]
                    break
                if attempt < a.mqtt_count_retries:
                    print(
                        f"NOTE: MQTT count not received attempt {attempt}/{a.mqtt_count_retries} (retrying)"
                    )
                    time.sleep(a.mqtt_count_retry_delay)
        except Exception as e:  # pragma: no cover
            print(f"NOTE: could not retrieve MQTT all_upcoming count: {e}")

    # Evaluate consistency
    counts = {
        k: v
        for k, v in {"ics": ics_count, "json": json_count, "mqtt": mqtt_count}.items()
        if v is not None
    }
    if len(set(counts.values())) > 1:
        print(f"❌ Count mismatch detected: {counts}")
        if overall_rc == 0:
            overall_rc = 1
    elif counts:
        print(f"Counts consistent across artifacts: {counts}")

    if overall_rc == 0:
        print("✅ All selected validators passed")
    else:
        print(f"❌ Validation suite failed (exit={overall_rc})")
    return overall_rc


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
