"""Gateway-path coverage for AIProcessor._ai_generate.

When AI_API_KEY is set, AI calls must route through ai_router (the local-AI
gateway) using the configured gateway model, NOT the native Gemini model.
When unset, the native model is used (dormant — covered by the existing suite).
"""

from unittest.mock import MagicMock

import pytest

from twickenham_events.ai_processor import AIProcessor, _AIResp


def _proc():
    cfg = MagicMock()
    # config.get(key, default) -> return the gateway alias we set, else default
    def _get(key, default=None):
        return {
            "ai_processor.shortening.gateway_model": "assist",
            "ai_processor.type_detection.gateway_model": "local-gemma",
        }.get(key, default)
    cfg.get.side_effect = _get
    # Avoid touching caches on init
    cfg.get.side_effect = _get
    return AIProcessor.__new__(AIProcessor), cfg


def test_gateway_active_reads_env(monkeypatch):
    monkeypatch.delenv("AI_API_KEY", raising=False)
    assert AIProcessor._gateway_active() is False
    monkeypatch.setenv("AI_API_KEY", "sk-x")
    assert AIProcessor._gateway_active() is True


def test_ai_generate_routes_to_gateway_when_active(monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "sk-x")
    proc, cfg = _proc()
    proc.config = cfg

    import ai_router

    called = {}

    def _fake_chat(prompt, *, model=None, **kw):
        called["prompt"] = prompt
        called["model"] = model
        return "SHORT NAME"

    monkeypatch.setattr(ai_router, "chat", _fake_chat)

    native = MagicMock()  # must NOT be used in gateway mode
    out = proc._ai_generate(
        native, "Some Long Event Name", "ai_processor.shortening.gateway_model", "assist"
    )
    assert isinstance(out, _AIResp)
    assert out.text == "SHORT NAME"
    assert called["model"] == "assist"           # used the configured gateway alias
    assert called["prompt"] == "Some Long Event Name"
    native.generate_content.assert_not_called()  # native path skipped


def test_ai_generate_type_detection_uses_local_gemma(monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "sk-x")
    proc, cfg = _proc()
    proc.config = cfg

    import ai_router

    seen = {}

    def _cap(p, *, model=None, **k):
        seen["m"] = model
        return "rugby"

    monkeypatch.setattr(ai_router, "chat", _cap)
    out = proc._ai_generate(MagicMock(), "England v Australia", "ai_processor.type_detection.gateway_model", "local-gemma")
    assert out.text == "rugby"
    assert seen["m"] == "local-gemma"


def test_ai_generate_falls_back_to_native_on_gateway_error(monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "sk-x")
    proc, cfg = _proc()
    proc.config = cfg

    import ai_router

    def _boom(*a, **k):
        raise ai_router.AIRouterError("gateway down")

    monkeypatch.setattr(ai_router, "chat", _boom)

    native = MagicMock()
    native.generate_content.return_value = _AIResp("native result")
    out = proc._ai_generate(native, "X", "ai_processor.shortening.gateway_model", "assist")
    native.generate_content.assert_called_once_with("X")
    assert out.text == "native result"


def test_ai_generate_native_when_dormant(monkeypatch):
    monkeypatch.delenv("AI_API_KEY", raising=False)
    proc, cfg = _proc()
    proc.config = cfg
    native = MagicMock()
    native.generate_content.return_value = _AIResp("native")
    out = proc._ai_generate(native, "X", "ai_processor.shortening.gateway_model", "assist")
    native.generate_content.assert_called_once_with("X")
    assert out.text == "native"
