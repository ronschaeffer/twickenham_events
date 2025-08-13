#!/usr/bin/env python3
"""Validate upcoming_events.json artifact.

Checks:
  * File exists & parses as JSON
  * Root has keys: events(list), generated_ts(str)
  * Each event has: date(str YYYY-MM-DD), title(str), start(str|None), end(str|None) optional fields allowed, id/slug uniqueness optional
  * Dates strictly YYYY-MM-DD; start/end if present HH:MM
  * Events list sorted by date then start time (if present)
  * No duplicate (date,title,start) tuples

Exit codes: 0 ok, 1 validation failures, 2 IO error
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
import re
import sys
from typing import Any

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_RE = re.compile(r"^\d{2}:\d{2}$")

REQUIRED_EVENT_KEYS = {"date"}  # title now derived from fixture if absent


def parse_args() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Validate upcoming_events.json")
    p.add_argument(
        "--file",
        default="output/upcoming_events.json",
        help="Path to upcoming_events.json",
    )
    p.add_argument(
        "--require-generated-ts",
        action="store_true",
        help="Fail if generated_ts field is missing (otherwise it's optional)",
    )
    p.add_argument(
        "--allow-empty",
        action="store_true",
        help="Allow zero events (otherwise empty list fails validation)",
    )
    return p


def load_json(path: str) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate(data: Any, require_generated_ts: bool, allow_empty: bool) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["root JSON must be an object"]
    if "events" not in data or not isinstance(data["events"], list):
        errors.append("missing or invalid 'events' list")
        return errors
    if "generated_ts" in data:
        gt = data["generated_ts"]
        if isinstance(gt, int):
            if gt <= 0:
                errors.append("generated_ts epoch must be positive")
        elif isinstance(gt, str):
            try:
                datetime.fromisoformat(gt.replace("Z", "+00:00"))
            except Exception:
                errors.append("generated_ts not ISO 8601 or epoch int")
        else:
            errors.append("generated_ts must be int epoch or ISO string")
    elif require_generated_ts:
        errors.append("missing generated_ts")
    events = data["events"]
    if not allow_empty and isinstance(events, list) and len(events) == 0:
        errors.append("events list is empty")
    prev_key = None
    seen_keys = set()
    for idx, ev in enumerate(events):
        if not isinstance(ev, dict):
            errors.append(f"event[{idx}] not an object")
            continue
        # Title fallback: accept 'title' or use 'fixture'/'name'
        title = ev.get("title") or ev.get("fixture") or ev.get("name")
        if not title:
            errors.append(f"event[{idx}] missing title/fixture")
        # (title captured via fallback; no need to store explicitly)
        date_val = ev.get("date")
        if not isinstance(date_val, str) or not DATE_RE.match(date_val):
            errors.append(f"event[{idx}] invalid date: {date_val}")
        # Normalize start/end field names (events currently use start_time)
        normalized_start = ev.get("start") or ev.get("start_time")
        if normalized_start is not None and (
            not isinstance(normalized_start, str) or not TIME_RE.match(normalized_start)
        ):
            errors.append(
                f"event[{idx}] invalid start time: {normalized_start} (HH:MM expected)"
            )
        for t_field in ("end",):
            if (
                t_field in ev
                and ev[t_field] is not None
                and (not isinstance(ev[t_field], str) or not TIME_RE.match(ev[t_field]))
            ):
                errors.append(
                    f"event[{idx}] invalid {t_field} time: {ev[t_field]} (HH:MM expected)"
                )
        # ordering key
        start_val = normalized_start if normalized_start is not None else ""
        key = (
            ev.get("date"),
            start_val,
            ev.get("title") or ev.get("fixture") or ev.get("name"),
        )
        if prev_key and key < prev_key:
            errors.append(
                f"events not sorted at index {idx}: {key} comes after {prev_key}"
            )
        prev_key = key
        dup_key = (
            ev.get("date"),
            (ev.get("title") or ev.get("fixture") or ev.get("name")),
            start_val,
        )
        if dup_key in seen_keys:
            errors.append(f"duplicate event triple (date,title,start): {dup_key}")
        else:
            seen_keys.add(dup_key)
    return errors


def main(argv: list[str]) -> int:  # pragma: no cover
    args = parse_args().parse_args(argv)
    if not os.path.exists(args.file):
        print(f"ERROR: file not found: {args.file}")
        return 2
    try:
        data = load_json(args.file)
    except Exception as e:
        print(f"ERROR: failed reading JSON: {e}")
        return 2
    errors = validate(data, args.require_generated_ts, args.allow_empty)
    if errors:
        print("Validation errors (upcoming_events):")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"✅ upcoming_events.json validation passed (events={len(data['events'])})")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
