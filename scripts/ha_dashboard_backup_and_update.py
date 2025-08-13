#!/usr/bin/env python3
"""Home Assistant Lovelace dashboard backup & entity ID update helper.

Purpose:
  1. Backup current Lovelace dashboard configuration (raw storage API)
  2. Optionally perform safe, mechanical substitutions adapting to new
     twickenham_events entity naming + consolidated attributes.

Usage examples:
  Export only (no changes):
    HA_BASE_URL=https://ha.local:8123 HA_TOKEN="<LLAT>" \
      poetry run python scripts/ha_dashboard_backup_and_update.py --backup-only

  Export then write an updated version with replacements to stdout:
    HA_BASE_URL=https://ha.local:8123 HA_TOKEN=... \
      poetry run python scripts/ha_dashboard_backup_and_update.py --print-updated

  Export and write updated file to backups/updated_<timestamp>.json:
    poetry run python scripts/ha_dashboard_backup_and_update.py --write-updated

Notes:
  - Script NEVER pushes changes back to HA; you must paste edited YAML/JSON
    manually in the Raw Editor (or use HA API yourself) after reviewing.
  - Only simple entity_id string replacements are done. Cards that referenced
    the removed event_count sensor may require manual template adjustment.
  - No external deps (uses urllib.request) so it can run without adding packages.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

LEGACY_TO_NEW_DIRECT: dict[str, str] = {
    # Buttons (short prefix -> full prefix)
    "button.tw_events_refresh": "button.twickenham_events_refresh",
    "button.tw_events_clear_cache": "button.twickenham_events_clear_cache",
    # Old availability binary sensor (removed) -> drop (handled separately)
    "binary_sensor.tw_events_availability": "",  # remove
    # Per-entity sensors replaced by attributes or new sensors
    "sensor.twickenham_events_event_count": "sensor.twickenham_events_status",  # then attribute access needed
}

NEW_ENTITIES = [
    "sensor.twickenham_events_status",
    "sensor.twickenham_events_last_run",
    "sensor.twickenham_events_upcoming",
    "sensor.twickenham_events_next",
    "sensor.twickenham_events_today",
    "button.twickenham_events_refresh",
    "button.twickenham_events_clear_cache",
]

ATTRIBUTE_MIGRATIONS = {
    # old direct sensor -> status attribute guidance
    "sensor.twickenham_events_event_count": {
        "new_entity": "sensor.twickenham_events_status",
        "attribute": "event_count",
    },
}


def fetch_lovelace(base_url: str, token: str) -> dict[str, Any]:
    url = base_url.rstrip("/") + "/api/lovelace/config"
    req = Request(
        url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}
    )
    try:
        with urlopen(req, timeout=15) as resp:  # nosec B310
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:  # pragma: no cover - runtime env
        print(f"ERROR: HTTP {e.code} while fetching lovelace config", file=sys.stderr)
        raise
    except URLError as e:  # pragma: no cover
        print(f"ERROR: URL error {e}", file=sys.stderr)
        raise


def backup_config(cfg: dict[str, Any], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    path = out_dir / f"lovelace_backup_{ts}.json"
    path.write_text(json.dumps(cfg, indent=2, sort_keys=True))
    return path


def mechanical_entity_replacements(raw_json: str) -> tuple[str, list[str], list[str]]:
    """Perform straight string replacements; return (new_json, changed, removed)."""
    changed: list[str] = []
    removed: list[str] = []
    for old, new in LEGACY_TO_NEW_DIRECT.items():
        if old in raw_json:
            if new:
                raw_json = raw_json.replace(old, new)
                changed.append(f"{old} -> {new}")
            else:
                # remove occurrences inside entity arrays (basic regex best-effort)
                pattern = re.compile(rf"['\"]{re.escape(old)}['\"],?\s?")
                raw_json, n = pattern.subn("", raw_json)
                if n:
                    removed.append(old)
    return raw_json, changed, removed


def summarize_manual_actions() -> str:
    return (
        "Manual actions:\n"
        "  - Update any cards that displayed the old event count sensor to use a template "
        "{{ state_attr('sensor.twickenham_events_status','event_count') }}.\n"
        "  - Optionally add upcoming/next/today sensors to dashboards.\n"
        "  - Remove lingering unavailable legacy entities via Entities search 'tw_events_'."
    )


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description="Backup (and optionally update) HA Lovelace config for twickenham_events migration"
    )
    ap.add_argument(
        "--backup-dir", default="ha_backups", help="directory to store backups"
    )
    ap.add_argument(
        "--backup-only", action="store_true", help="only backup, no modifications"
    )
    ap.add_argument(
        "--print-updated",
        action="store_true",
        help="print updated JSON to stdout (no file write unless --write-updated)",
    )
    ap.add_argument(
        "--write-updated",
        action="store_true",
        help="write updated JSON file beside backup",
    )
    args = ap.parse_args(argv)

    base_url = os.environ.get("HA_BASE_URL")
    token = os.environ.get("HA_TOKEN")
    if not base_url or not token:
        print(
            "ERROR: HA_BASE_URL and HA_TOKEN environment variables required",
            file=sys.stderr,
        )
        return 2

    raw_cfg = fetch_lovelace(base_url, token)
    backup_path = backup_config(raw_cfg, Path(args.backup_dir))
    print(f"Backup saved: {backup_path}")

    if args.backup_only:
        return 0

    raw_json = json.dumps(raw_cfg)
    updated_json, changed, removed = mechanical_entity_replacements(raw_json)

    if changed:
        print("Replacements:")
        for c in changed:
            print(f"  - {c}")
    if removed:
        print("Removed obsolete entities:")
        for r in removed:
            print(f"  - {r}")

    if args.print_updated:
        print(updated_json)

    if args.write_updated:
        upd_path = Path(args.backup_dir) / (backup_path.stem + "_updated.json")
        upd_path.write_text(updated_json)
        print(f"Updated file written: {upd_path}")

    print("\n" + summarize_manual_actions())
    print("\nNew entities available:")
    for ent in NEW_ENTITIES:
        print(f"  - {ent}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
