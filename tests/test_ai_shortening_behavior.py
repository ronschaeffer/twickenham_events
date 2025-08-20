import types

from twickenham_events.ai_processor import AIProcessor


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


def _resp(text):
    r = types.SimpleNamespace()
    r.text = text
    return r


def _base_cfg(**overrides):
    cfg = {
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
    # Merge simple one-level overrides for convenience in tests
    for k, v in overrides.items():
        parts = k.split(".")
        cur = cfg
        for p in parts[:-1]:
            cur = cur.setdefault(p, {})
        cur[parts[-1]] = v
    return DotConfig(cfg)


def test_shortening_success_no_flags(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _s: None, raising=True)

    name = "England vs Australia"

    def behaviour(_prompt):
        return _resp("ENG v AUS")

    dummy = DummyGenAI(behaviour)

    import twickenham_events.ai_processor as mod

    monkeypatch.setattr(mod, "GENAI_AVAILABLE", True, raising=True)
    monkeypatch.setattr(mod, "genai", dummy, raising=True)

    cfg = _base_cfg()
    proc = AIProcessor(cfg)
    result, had_error, msg = proc.get_short_name(name)
    assert result == "ENG v AUS"
    assert had_error is False
    assert msg == ""


def test_shortening_with_flags_spacing_standardized(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _s: None, raising=True)

    name = "England vs Australia"

    def behaviour(_prompt):
        # Return without flags; processor won't add flags on its own
        return _resp("ENG v AUS")

    dummy = DummyGenAI(behaviour)

    import twickenham_events.ai_processor as mod

    monkeypatch.setattr(mod, "GENAI_AVAILABLE", True, raising=True)
    monkeypatch.setattr(mod, "genai", dummy, raising=True)

    cfg = _base_cfg(
        **{
            "ai_processor.shortening.flags_enabled": True,
            "ai_processor.shortening.max_length": 32,
        }
    )
    proc = AIProcessor(cfg)
    result, had_error, msg = proc.get_short_name(name)
    # Since the model didn't include flags, we simply ensure spacing fixer doesn't break output
    assert result == "ENG v AUS"
    assert had_error is False
    assert msg == ""


def test_shortening_disabled_is_noop():
    cfg = _base_cfg(**{"ai_processor.shortening.enabled": False})
    proc = AIProcessor(cfg)
    name = "England vs Australia"
    result, had_error, msg = proc.get_short_name(name)
    assert result == name
    assert had_error is False
    assert msg == ""


def test_shortening_too_long_falls_back(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _s: None, raising=True)

    name = "England vs Australia"

    def behaviour(_prompt):
        # Exceeds limit intentionally
        return _resp("ENGLAND V AUSTRALIA")

    dummy = DummyGenAI(behaviour)

    import twickenham_events.ai_processor as mod

    monkeypatch.setattr(mod, "GENAI_AVAILABLE", True, raising=True)
    monkeypatch.setattr(mod, "genai", dummy, raising=True)

    cfg = _base_cfg(**{"ai_processor.shortening.max_length": 8})
    proc = AIProcessor(cfg)
    result, had_error, msg = proc.get_short_name(name)
    assert result == name
    assert had_error is True
    assert "exceeds visual width" in msg


def test_cache_disabled_invokes_model_every_time(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _s: None, raising=True)
    # Prevent disk cache interference
    monkeypatch.setattr(AIProcessor, "_load_cache", lambda self: {})
    monkeypatch.setattr(AIProcessor, "_save_cache", lambda self: None)

    calls = {"n": 0}

    def behaviour(_prompt):
        calls["n"] += 1
        return _resp("OK")

    dummy = DummyGenAI(behaviour)

    import twickenham_events.ai_processor as mod

    monkeypatch.setattr(mod, "GENAI_AVAILABLE", True, raising=True)
    monkeypatch.setattr(mod, "genai", dummy, raising=True)

    cfg = _base_cfg(**{"ai_processor.shortening.cache_enabled": False})
    proc = AIProcessor(cfg)
    name = "Some Event"

    r1 = proc.get_short_name(name)
    r2 = proc.get_short_name(name)

    assert r1[0] == "OK" and r2[0] == "OK"
    assert calls["n"] == 2  # no caching


def test_cache_enabled_hits_in_memory_cache(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _s: None, raising=True)
    # Prevent disk cache interference; keep in-memory cache behavior
    monkeypatch.setattr(AIProcessor, "_load_cache", lambda self: {})
    monkeypatch.setattr(AIProcessor, "_save_cache", lambda self: None)

    calls = {"n": 0}

    def behaviour(_prompt):
        calls["n"] += 1
        return _resp("OK")

    dummy = DummyGenAI(behaviour)

    import twickenham_events.ai_processor as mod

    monkeypatch.setattr(mod, "GENAI_AVAILABLE", True, raising=True)
    monkeypatch.setattr(mod, "genai", dummy, raising=True)

    cfg = _base_cfg(**{"ai_processor.shortening.cache_enabled": True})
    proc = AIProcessor(cfg)
    name = "Some Event"

    r1 = proc.get_short_name(name)
    r2 = proc.get_short_name(name)

    assert r1[0] == "OK" and r2[0] == "OK"
    assert calls["n"] == 1  # second call served from cache
