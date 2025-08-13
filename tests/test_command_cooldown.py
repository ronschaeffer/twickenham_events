import json
import time

from twickenham_events.command_processor import CommandProcessor


class FakeClient:
    def __init__(self):
        self.published = []

    def publish(self, topic, payload, qos=0, retain=False):
        self.published.append((topic, payload, qos, retain))

        class R:
            rc = 0

        return R()


def extract_results(published):
    return [json.loads(p[1]) for p in published if p[0] == "result"]


def test_cooldown_enforced():
    client = FakeClient()
    proc = CommandProcessor(client, "ack", "result")
    proc.register("test", lambda ctx: ("success", "ok", {}), cooldown_seconds=2)

    proc.handle_raw('{"command":"test","id":"a"}')
    # allow background thread to finish
    time.sleep(0.05)
    first_results = extract_results(client.published)
    assert any(r["outcome"] == "success" for r in first_results)

    # second invocation immediately should hit cooldown
    proc.handle_raw('{"command":"test","id":"b"}')
    time.sleep(0.01)
    second_results = extract_results(client.published)
    cooldowns = [r for r in second_results if r["id"] == "b"]
    assert cooldowns and cooldowns[0]["outcome"] == "cooldown"
    assert "retry_after_s" in cooldowns[0]

    # After cooldown expiry should succeed again
    time.sleep(2.1)
    proc.handle_raw('{"command":"test","id":"c"}')
    time.sleep(0.05)
    third_results = extract_results(client.published)
    assert any(r["id"] == "c" and r["outcome"] == "success" for r in third_results)

    # Registry should now include last_success_ts
    reg = proc.build_registry_payload()
    cmd_meta = {c["name"]: c for c in reg["commands"]}["test"]
    assert "last_success_ts" in cmd_meta and isinstance(
        cmd_meta["last_success_ts"], int
    )
