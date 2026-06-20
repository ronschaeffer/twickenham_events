"""Native Anthropic Claude provider for AI event processing.

Mirrors the Ticked/Stopover convention of a single centralised model constant
(cf. ticked internal/ai/claude/claude.go `DefaultModel`). Claude is the
first-priority native model; the AIProcessor falls back to native Gemini when
no ANTHROPIC_API_KEY is configured or a call fails. The local-AI gateway
(ai_router) still takes precedence over both when AI_API_KEY is set.
"""

import logging

# In-use Claude model shared across Ron's apps (Stopover config.py ai_model,
# Ticked claude.go DefaultModel). Keep these aligned when bumping.
DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-6"


def claude_available() -> bool:
    """True when the anthropic SDK is importable."""
    try:
        import anthropic  # noqa: F401

        return True
    except Exception:
        return False


def generate_with_claude(prompt: str, api_key: str, model: str | None = None) -> str | None:
    """Run a single text completion through Claude. Returns text or None.

    Lightweight text task (name shortening / type classification): low
    max_tokens, no system prompt needed. Raises on quota/rate errors so the
    caller's circuit-breaker logic can see the 429 string, matching the native
    Gemini path's behaviour.
    """
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model or DEFAULT_CLAUDE_MODEL,
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    parts = [b.text for b in message.content if getattr(b, "type", None) == "text"]
    text = "".join(parts).strip()
    return text or None
