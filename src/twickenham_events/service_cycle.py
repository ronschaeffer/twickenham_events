"""Service cycle helpers (testable extraction from cmd_service).

Provides logic for building the extra_status dict passed to MQTT publish,
including:
  - Adding last run timestamps / trigger / interval
  - Attaching recent errors (capped length)
  - Converting plain string errors into structured entries with timestamps
  - Setting status="error" when there are no events and errors exist (if not overridden)
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any

MAX_ERRORS_DEFAULT = 25


def _normalize_errors(errors: Iterable[Any], max_errors: int) -> list[dict[str, str]]:
    """Normalize an iterable of errors to structured entries.

    Each entry becomes {"message": <str>, "ts": <UTC ISO>}. Existing dict entries
    are preserved; missing "message" coerces via str(); missing "ts" filled with now.
    Length is truncated to the most recent max_errors (tail semantics).
    """
    errs_list = list(errors)
    # Keep only the tail
    if len(errs_list) > max_errors:
        errs_list = errs_list[-max_errors:]
    now = datetime.utcnow().isoformat() + "Z"
    normalized: list[dict[str, str]] = []
    for e in errs_list:
        if isinstance(e, dict):
            msg = str(e.get("message") or e)
            ts = e.get("ts") or now
            normalized.append({"message": msg, "ts": ts})
        else:
            normalized.append({"message": str(e), "ts": now})
    return normalized


_LAST_ERRORS_CACHE: list[str] = []  # unique message list in insertion order (bounded)
_LAST_ERRORS_STRUCT: list[dict[str, str]] = []  # structured cumulative list (bounded)


def build_extra_status(
    scraper,  # object having error_log list
    flat_events: list[dict[str, Any]],
    trigger: str,
    interval: int,
    run_ts: float,
    max_errors: int | None = None,
    reset_cache: bool = False,
) -> dict[str, Any]:
    """Create the extra_status dict consumed by MQTTClient.publish_events.

    Returns dict including last_run_ts, last_run_iso, trigger, interval, and
    optionally errors + status override.
    """
    from datetime import datetime as _dt

    max_errors = max_errors or MAX_ERRORS_DEFAULT
    global _LAST_ERRORS_CACHE, _LAST_ERRORS_STRUCT
    if reset_cache:
        _LAST_ERRORS_CACHE = []
        _LAST_ERRORS_STRUCT = []
    iso = _dt.utcfromtimestamp(run_ts).isoformat() + "Z"
    extra: dict[str, Any] = {
        "last_run_ts": int(run_ts),
        "last_run_iso": iso,
        "last_run_trigger": trigger,
        "interval_seconds": interval,
    }
    errors_raw = getattr(scraper, "error_log", []) or []
    if errors_raw:
        new_raw: list[Any] = []
        for entry in errors_raw:
            msg = entry.get("message") if isinstance(entry, dict) else str(entry)
            if msg not in _LAST_ERRORS_CACHE:
                new_raw.append(entry)

        published_struct: list[dict[str, str]] = []
        if new_raw:
            # Normalize only the new entries first (with fresh timestamps)
            new_struct = _normalize_errors(new_raw, max_errors)
            # Append preserving prior order
            for s in new_struct:
                if s["message"] not in _LAST_ERRORS_CACHE:
                    _LAST_ERRORS_CACHE.append(s["message"])
                    _LAST_ERRORS_STRUCT.append(s)
            # Enforce bounds on cumulative structures
            if len(_LAST_ERRORS_CACHE) > max_errors:
                overflow = len(_LAST_ERRORS_CACHE) - max_errors
                _LAST_ERRORS_CACHE = _LAST_ERRORS_CACHE[overflow:]
                _LAST_ERRORS_STRUCT = _LAST_ERRORS_STRUCT[overflow:]
        # If no new_raw but we already have previous, reuse cumulative struct
        if _LAST_ERRORS_STRUCT:
            published_struct = list(_LAST_ERRORS_STRUCT)
            extra["errors"] = published_struct
            extra["error_count"] = len(published_struct)
            if not flat_events:
                extra["status"] = "error"
    return extra


__all__ = ["MAX_ERRORS_DEFAULT", "_normalize_errors", "build_extra_status"]
