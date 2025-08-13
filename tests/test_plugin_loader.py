from pathlib import Path

from twickenham_events.command_processor import CommandProcessor
from twickenham_events.plugin_loader import load_command_plugins


class FakeClient:
    def publish(self, *a, **k):
        class R:
            rc = 0

        return R()


def test_plugin_loader_registers_commands(tmp_path: Path, monkeypatch):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    plugin_file = plugins_dir / "cmd_sample.py"
    plugin_file.write_text(
        """def register_commands(proc):\n    proc.register("sample", lambda ctx:("success","ok",{}))\n"""
    )

    # Monkeypatch Path to point to our temp plugins dir
    loaded = load_command_plugins(
        CommandProcessor(FakeClient(), "ack", "result"), str(plugins_dir)
    )
    assert "cmd_sample" in loaded
