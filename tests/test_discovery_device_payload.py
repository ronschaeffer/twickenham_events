import json

from twickenham_events.config import Config
from twickenham_events.enhanced_discovery import (
    publish_enhanced_device_discovery as publish_device_level_discovery,
)


class FakeClient:
    def __init__(self):
        self.published = []

    def publish(self, topic, payload, retain=False, qos=0):
        self.published.append((topic, payload, retain, qos))

        class R:
            rc = 0

        return R()


def _extract_device_payload(client: FakeClient):
    msgs = [
        p for p in client.published if p[0].endswith("/device/twickenham_events/config")
    ]
    assert msgs, "Expected device discovery publish"
    return json.loads(msgs[-1][1])


def test_device_level_discovery_includes_expire_after_and_retained_topics():
    cfg = Config.from_defaults()
    client = FakeClient()

    topic = publish_device_level_discovery(client, cfg)
    assert topic.endswith("/device/twickenham_events/config")

    payload = _extract_device_payload(client)
    cmps = payload["cmps"]

    # Ack has expire_after (using abbreviated key)
    assert cmps["cmd_ack"]["expire_after"] == 120

    # Retained mirrors exist with expected topics (abbreviated keys)
    assert cmps["last_ack"]["state_topic"] == "twickenham_events/commands/last_ack"
    assert (
        cmps["last_result"]["state_topic"] == "twickenham_events/commands/last_result"
    )

    # Ack value_template maps 'received' -> busy
    vt = cmps["cmd_ack"]["value_template"]
    assert "received" in vt and "busy" in vt

    # Buttons publish expected command topics and names
    assert cmps["refresh"]["command_topic"].endswith("twickenham_events/cmd/refresh")
    assert cmps["clear_cache"]["command_topic"].endswith(
        "twickenham_events/cmd/clear_cache"
    )
    assert cmps["restart"]["command_topic"].endswith("twickenham_events/cmd/restart")
    assert cmps["clear_cache"]["name"] == "Clear All"
    assert cmps["restart"]["name"].lower().startswith("restart")
