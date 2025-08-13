import json

from twickenham_events.command_processor import CommandProcessor


class FakeClient:
    def __init__(self):
        self.published = []

    def publish(self, topic, payload, qos=0, retain=False):
        self.published.append((topic, payload, qos, retain))

        class R:
            rc = 0

        return R()


def test_command_registry_payload_and_publish():
    client = FakeClient()
    proc = CommandProcessor(client, "ack", "result")
    proc.register(
        "refresh",
        lambda ctx: ("success", "ok", {}),
        description="Immediate scrape + publish",
        cooldown_seconds=5,
        requires_ai=False,
    )
    proc.register(
        "clear_cache",
        lambda ctx: ("success", "ok", {}),
        description="Clear AI cache",
        requires_ai=True,
    )
    payload = proc.build_registry_payload()
    assert payload["service"] == "twickenham_events"
    cmds = {c["name"]: c for c in payload["commands"]}
    assert "refresh" in cmds and "clear_cache" in cmds
    assert cmds["refresh"].get("cooldown_seconds") == 5
    assert cmds["refresh"].get("requires_ai") is False
    assert cmds["clear_cache"].get("requires_ai") is True
    proc.publish_registry("twickenham_events/commands/registry")
    topics = [t for (t, *_rest) in client.published]
    assert topics[-1] == "twickenham_events/commands/registry"
    reg_payload = json.loads(client.published[-1][1])
    assert {c["name"] for c in reg_payload["commands"]} >= {"refresh", "clear_cache"}
