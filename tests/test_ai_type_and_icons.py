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


def test_fallback_type_and_icons_mapping():
    cfg = DotConfig(
        {
            "ai_processor": {
                "type_detection": {"enabled": False, "cache_enabled": False},
                "shortening": {"enabled": False},
            }
        }
    )
    proc = AIProcessor(cfg)

    t1 = proc.get_event_type_and_icons("England v Wales - Six Nations")
    assert t1[0] == "rugby" and t1[1] == "🏉" and t1[2].startswith("mdi:")

    t2 = proc.get_event_type_and_icons("Taylor Swift - The Eras Tour Concert")
    assert t2[0] == "concert" and t2[1] == "🎵"

    t3 = proc.get_event_type_and_icons("World Cup Final")
    assert t3[0] == "trophy" and t3[1] == "🏆"

    t4 = proc.get_event_type_and_icons("Corporate Event at Twickenham")
    assert t4[0] == "generic" and t4[1] == "🏟️"


def test_ai_type_detection_with_cache_and_fallback(monkeypatch):
    # Simulate AI returning an invalid category, forcing fallback
    class Dummy:
        def configure(self, **_):
            return None

        class _Model:
            def generate_content(self, prompt):
                class R:
                    text = "not-a-valid-type"

                return R()

        def GenerativeModel(self, *_a, **_k):
            return Dummy._Model()

    import twickenham_events.ai_processor as mod

    monkeypatch.setattr(mod, "GENAI_AVAILABLE", True, raising=True)
    monkeypatch.setattr(mod, "genai", Dummy(), raising=True)

    cfg = DotConfig(
        {
            "ai_processor": {
                "api_key": "k",
                "type_detection": {
                    "enabled": True,
                    "cache_enabled": True,
                    "cache_dir": "output/cache",
                    "model": "gemini-2.5-pro",
                },
                "shortening": {"enabled": False},
            }
        }
    )
    proc = AIProcessor(cfg)

    etype, emoji, mdi = proc.get_event_type_and_icons("Some Unknown Thing")
    # Falls back to generic when AI gives invalid label
    assert etype == "generic" and emoji == "🏟️" and mdi == "mdi:stadium"
