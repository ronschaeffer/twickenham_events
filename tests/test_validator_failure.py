"""
Validator failure tests (discovery): ensure payloads with legacy keys or missing cmps are rejected.
These tests use an internal utility and do not publish to an external broker.
"""

from twickenham_events.validation_utils import validate_discovery_payload


def test_validator_rejects_ents():
    payload = {
        "dev": {"name": "Test Device"},
        "ents": {"status": {"p": "sensor"}},
    }
    errors = validate_discovery_payload(payload)
    assert any("unexpected legacy key 'ents'" in e for e in errors)


def test_validator_rejects_entities():
    payload = {
        "dev": {"name": "Test Device"},
        "entities": {"status": {"p": "sensor"}},
    }
    errors = validate_discovery_payload(payload)
    assert any("unexpected legacy key 'entities'" in e for e in errors)


def test_validator_missing_cmps():
    payload = {"dev": {"name": "Test Device"}}
    errors = validate_discovery_payload(payload)
    assert any("missing or invalid cmps dict" in e for e in errors)
