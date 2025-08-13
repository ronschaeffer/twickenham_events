#!/usr/bin/env python3
"""Validate generated Twickenham Events ICS calendar file.

Checks performed:
  * File exists & readable.
  * Begins with BEGIN:VCALENDAR and ends with END:VCALENDAR.
  * Contains at least one VEVENT block (unless --allow-empty specified).
  * Each VEVENT contains at minimum: DTSTART, SUMMARY, UID.
  * Basic DTSTART / DTEND date format sanity (YYYYMMDD or YYYYMMDDTHHMMSSZ).

Exit codes:
  0 = success, validations passed
  1 = validation failures
  2 = file not found / unreadable
"""

from __future__ import annotations

import argparse
import os
import re
import sys

VEVENT_START = re.compile(r"^BEGIN:VEVENT\s*$")
VEVENT_END = re.compile(r"^END:VEVENT\s*$")
DT_VALUE = re.compile(r"^DT(?:START|END)(;[^:]+)?:([0-9]{8}(T[0-9]{6}Z)?)\s*$")


def parse_args() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Validate ICS calendar artifact")
    p.add_argument(
        "--file", default="output/twickenham_events.ics", help="Path to ICS file"
    )
    p.add_argument(
        "--allow-empty",
        action="store_true",
        help="Allow zero VEVENTs (off-season) without failing",
    )
    p.add_argument(
        "--min-events",
        type=int,
        default=1,
        help="Minimum VEVENT blocks required (ignored if --allow-empty)",
    )
    return p


def validate_ics(lines: list[str], allow_empty: bool, min_events: int) -> list[str]:
    errors: list[str] = []
    if not lines:
        return ["file is empty"]
    if not lines[0].startswith("BEGIN:VCALENDAR"):
        errors.append("missing BEGIN:VCALENDAR at start")
    if not any(line.startswith("END:VCALENDAR") for line in lines[-5:]):
        errors.append("missing END:VCALENDAR near end")

    # Collect VEVENT blocks
    events: list[list[str]] = []
    current: list[str] | None = None
    for line in lines:
        if VEVENT_START.match(line):
            if current is not None:  # nested - malformed
                errors.append("nested VEVENT start encountered")
            current = [line]
        elif VEVENT_END.match(line):
            if current is None:
                errors.append("END:VEVENT without BEGIN:VEVENT")
            else:
                current.append(line)
                events.append(current)
                current = None
        elif current is not None:
            current.append(line)
    if current is not None:
        errors.append("unterminated VEVENT block (missing END:VEVENT)")

    if not allow_empty and len(events) < min_events:
        errors.append(
            f"insufficient events: found {len(events)} < required {min_events}"
        )

    for idx, ev in enumerate(events, start=1):
        block = "\n".join(ev)
        if "SUMMARY:" not in block:
            errors.append(f"event {idx}: missing SUMMARY")
        if "UID:" not in block:
            errors.append(f"event {idx}: missing UID")
        if not any(line.startswith("DTSTART") for line in ev):
            errors.append(f"event {idx}: missing DTSTART")
        for line in ev:
            if (
                line.startswith("DTSTART") or line.startswith("DTEND")
            ) and not DT_VALUE.match(line):
                errors.append(f"event {idx}: invalid date line '{line.strip()}'")
    return errors


def main(argv: list[str]) -> int:  # pragma: no cover - CLI glue
    args = parse_args().parse_args(argv)
    path = args.file
    if not os.path.exists(path):
        print(f"ERROR: file not found: {path}")
        return 2
    try:
        with open(path, encoding="utf-8") as f:
            raw_lines = [ln.rstrip("\n") for ln in f]
    except Exception as e:
        print(f"ERROR: could not read file: {e}")
        return 2
    errors = validate_ics(raw_lines, args.allow_empty, args.min_events)
    if errors:
        print("Validation errors (ICS):")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(
        f"✅ ICS validation passed (events={sum(1 for line in raw_lines if line == 'BEGIN:VEVENT')})"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
