import types

import pytest

from twickenham_events.ai_processor import AIProcessor
from twickenham_events.ai_shortener import AIShortener


class DotConfig:
    def __init__(self, data):
        self._data = data

    def get(self, key, default=None):
        cur = self._data
        for part in key.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return default
        return cur


class DummyGenAI:
    def __init__(self, model_behaviour):
        # model_behaviour: callable(prompt) -> response or raises
        self._beh = model_behaviour

    def configure(self, **_):
        return None

    class _Model:
        def __init__(self, beh):
            self._beh = beh

        def generate_content(self, prompt):
            return self._beh(prompt)

    def GenerativeModel(self, *_args, **_kwargs):
        return DummyGenAI._Model(self._beh)


@pytest.fixture
def base_ai_config():
    # Minimal config enabling processor shortening without writing caches
    return DotConfig(
        {
            "ai_processor": {
                "api_key": "test_key",
                "shortening": {
                    "enabled": True,
                    "cache_enabled": False,
                    "model": "gemini-2.5-pro",
                    "max_length": 16,
                    "flags_enabled": False,
                    "standardize_spacing": True,
                    "prompt_template": "Shorten to {char_limit}: {event_name}\n{flag_instructions}\n{flag_examples}",
                },
                "type_detection": {"enabled": False, "cache_enabled": False},
            }
        }
    )


@pytest.fixture
def base_shortener_config():
    return DotConfig(
        {
            "ai_shortener": {
                "api_key": "test_key",
                "enabled": True,
                "cache_enabled": False,
                "model": "gemini-2.5-pro",
                "max_length": 16,
                "flags_enabled": False,
                "standardize_spacing": True,
                "prompt_template": "Shorten to {char_limit}: {event_name}\n{flag_instructions}\n{flag_examples}",
            },
            "ai_type_detection": {"enabled": False, "cache_enabled": False},
        }
    )


def _resp(text):
    r = types.SimpleNamespace()
    r.text = text
    return r


def test_ai_processor_circuit_breaks_on_429(monkeypatch, base_ai_config):
    # Avoid real sleeps
    monkeypatch.setattr("time.sleep", lambda _s: None, raising=True)

    # First call raises quota error; subsequent calls should bypass genai and return original
    calls = {"n": 0}

    def behaviour(_prompt):
        calls["n"] += 1
        raise Exception("429 rate limit")

    dummy = DummyGenAI(behaviour)

    import twickenham_events.ai_processor as mod

    monkeypatch.setattr(mod, "GENAI_AVAILABLE", True, raising=True)
    monkeypatch.setattr(mod, "genai", dummy, raising=True)

    proc = AIProcessor(base_ai_config)
    name = "England vs Australia"

    result, had_error, msg = proc.get_short_name(name)
    assert result == name
    assert had_error is False
    assert msg == ""
    assert calls["n"] == 1

    # Second call should not invoke genai again due to open circuit
    result2, had_error2, _ = proc.get_short_name(name)
    assert result2 == name
    assert had_error2 is False
    assert calls["n"] == 1  # unchanged


def test_ai_processor_circuit_is_per_instance(monkeypatch, base_ai_config):
    monkeypatch.setattr("time.sleep", lambda _s: None, raising=True)

    # New instance should start with closed circuit and allow a successful call
    def behaviour_ok(_prompt):
        return _resp("ENG v AUS")

    dummy = DummyGenAI(behaviour_ok)

    import twickenham_events.ai_processor as mod

    monkeypatch.setattr(mod, "GENAI_AVAILABLE", True, raising=True)
    monkeypatch.setattr(mod, "genai", dummy, raising=True)

    proc = AIProcessor(base_ai_config)
    name = "England vs Australia"
    result, had_error, msg = proc.get_short_name(name)
    assert result == "ENG v AUS"
    assert had_error is False
    assert msg == ""


def test_ai_shortener_circuit_breaks_on_429(monkeypatch, base_shortener_config):
    monkeypatch.setattr("time.sleep", lambda _s: None, raising=True)

    calls = {"n": 0}

    def behaviour(_prompt):
        calls["n"] += 1
        raise Exception("quota exceeded: 429")

    dummy = DummyGenAI(behaviour)

    import twickenham_events.ai_shortener as mod

    monkeypatch.setattr(mod, "GENAI_AVAILABLE", True, raising=True)
    monkeypatch.setattr(mod, "genai", dummy, raising=True)

    shortener = AIShortener(base_shortener_config)
    name = "England vs Australia"
    result, had_error, _ = shortener.get_short_name(name)
    assert result == name
    assert had_error is False
    assert calls["n"] == 1

    # Subsequent call bypasses API
    result2, had_error2, _ = shortener.get_short_name(name)
    assert result2 == name
    assert had_error2 is False
    assert calls["n"] == 1


def test_ai_shortener_circuit_is_per_instance(monkeypatch, base_shortener_config):
    monkeypatch.setattr("time.sleep", lambda _s: None, raising=True)

    def behaviour_ok(_prompt):
        return _resp("ENG v AUS")

    dummy = DummyGenAI(behaviour_ok)

    import twickenham_events.ai_shortener as mod

    monkeypatch.setattr(mod, "GENAI_AVAILABLE", True, raising=True)
    monkeypatch.setattr(mod, "genai", dummy, raising=True)

    shortener = AIShortener(base_shortener_config)
    name = "England vs Australia"
    result, had_error, msg = shortener.get_short_name(name)
    assert result == "ENG v AUS"
    assert had_error is False
    assert msg == ""
