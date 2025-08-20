import pytest

from twickenham_events.__main__ import cmd_cache
from twickenham_events.config import Config


class DummyProc:
    def __init__(self):
        self.cleared = False
        self.stats_called = False
        self.reprocessed = 0

    def clear_cache(self):
        self.cleared = True

    def get_cache_stats(self):
        self.stats_called = True
        return {"count": 0, "file": "output/event_name_cache.json"}

    def reprocess_cache(self):
        self.reprocessed = 3
        return self.reprocessed


@pytest.fixture(autouse=True)
def patch_ai_processor(monkeypatch):
    # Patch AIProcessor used inside cmd_cache to return our dummy
    class DummyFactory:
        def __call__(self, _cfg):
            return DummyProc()

    import twickenham_events.__main__ as mod

    monkeypatch.setattr(mod, "AIProcessor", DummyFactory(), raising=True)
    return None


class Args:
    def __init__(self, subcmd):
        self.cache_command = subcmd


def _cfg_enabled():
    # Enable AI so cmd_cache will proceed
    d = Config.from_defaults()
    # Flip shortening.enabled to True to allow cache commands
    d._data["ai_processor"]["shortening"]["enabled"] = True
    return d


def test_cmd_cache_clear(capsys):
    cfg = _cfg_enabled()
    code = cmd_cache(cfg, Args("clear"))
    assert code == 0
    # Output includes confirmation
    out = capsys.readouterr().out
    assert "Cache cleared" in out


def test_cmd_cache_stats(capsys):
    cfg = _cfg_enabled()
    code = cmd_cache(cfg, Args("stats"))
    assert code == 0
    out = capsys.readouterr().out
    assert "Cache Statistics" in out


def test_cmd_cache_reprocess(capsys):
    cfg = _cfg_enabled()
    code = cmd_cache(cfg, Args("reprocess"))
    assert code == 0
    out = capsys.readouterr().out
    assert "Reprocessed" in out
