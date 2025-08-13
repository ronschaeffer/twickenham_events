"""Flatten helpers for Twickenham Events.

Creates a canonical flat list of event dicts from the summarized
day-structured representation while ensuring each event carries its
`date` field. Previously the ad-hoc flattening dropped `date`, so MQTT
payloads (next/all_upcoming) lacked event dates even though terminal
output showed them.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def flatten_with_date(
    summarized_events: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return flat list of event dicts, injecting `date` when missing.

    Each summarized entry: {"date": <YYYY-MM-DD>, "events": [ ... ]}
    Event dicts may omit `date`; we copy and add it (non-mutating).
    """
    flat: list[dict[str, Any]] = []
    for day in summarized_events:
        day_date = day.get("date")
        for ev in day.get("events", []):
            e = ev.copy()
            if not e.get("date") and day_date:
                e["date"] = day_date
            flat.append(e)
    return flat


__all__ = ["flatten_with_date"]
