"""Validation utilities for Twickenham Events payloads (importable by tests)."""

from __future__ import annotations

from typing import Any

EXPECTED_DISCOVERY_COMPONENTS = {
    "status",
    "last_run",
    "upcoming",
    "next",
    "today",
    "refresh",
    "clear_cache",
}


def validate_discovery_payload(payload: Any) -> list[str]:
    """Validate Home Assistant device-level discovery payload structure.

    Returns a list of error strings; empty list means OK.
    Enforces 'cmps' only (rejects legacy 'ents'/'entities') and required component map structure.
    """
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["discovery: payload not dict"]

    if "dev" not in payload:
        errors.append("discovery: missing dev")

    if "ents" in payload:
        errors.append("discovery: unexpected legacy key 'ents' (cmps only)")
    if "entities" in payload:
        errors.append("discovery: unexpected legacy key 'entities' (cmps only)")

    components = payload.get("cmps")
    if not isinstance(components, dict):
        errors.append("discovery: missing or invalid cmps dict (required)")
        return errors

    missing = [c for c in EXPECTED_DISCOVERY_COMPONENTS if c not in components]
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
