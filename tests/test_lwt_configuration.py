from unittest.mock import MagicMock, patch

from twickenham_events.config import Config
from twickenham_events.mqtt_client import MQTTClient


def test_mqtt_client_passes_last_will():
    """Ensure last_will dict in config is forwarded to MQTTPublisher.

    We intercept the constructor call to confirm kwarg propagation.
    """
    cfg = Config(
        {
            "mqtt": {
                "enabled": True,
                "broker": "localhost",
                "port": 1883,
                "client_id": "test-lwt",
                "topics": {"status": "twickenham_events/status"},
                "last_will": {
                    "topic": "twickenham_events/status",
                    "payload": '{"status":"offline"}',
                    "qos": 1,
                    "retain": True,
                },
            }
        }
    )

    mock_ctx = MagicMock()
    mock_ctx.__enter__.return_value = MagicMock()

    with (
        patch(
            "twickenham_events.mqtt_client.MQTTPublisher", return_value=mock_ctx
        ) as mpub,
        patch("twickenham_events.mqtt_client.MQTT_AVAILABLE", True),
    ):
        cli = MQTTClient(cfg)
        cli.publish_events([])

    # Constructor received last_will kwarg
    called_kwargs = mpub.call_args.kwargs
    assert "last_will" in called_kwargs
    assert called_kwargs["last_will"]["topic"] == "twickenham_events/status"


def test_service_lwt_configuration(monkeypatch):
    """Validate that service mode sets an LWT on paho client.

    We patch paho.mqtt.client.Client to inspect will_set parameters.
    """
    # Ensure mqtt client path dependency is considered 'available'
    from twickenham_events import mqtt_client as mc_mod

    mc_mod.MQTT_AVAILABLE = True

    class DummyPublisher:  # minimal context manager
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def publish(self, *a, **k):
            return True

    mc_mod.MQTTPublisher = DummyPublisher  # type: ignore
    from twickenham_events.__main__ import cmd_service

    cfg = Config(
        {
            "mqtt": {
                "enabled": True,
                "broker": "localhost",
                "port": 1883,
                "client_id": "svc-lwt",
                "topics": {"status": "twickenham_events/status"},
                "last_will": {
                    "topic": "twickenham_events/status",
                    "payload": '{"status":"offline"}',
                    "qos": 1,
                    "retain": True,
                },
            },
            "service": {"interval_seconds": 999999},
        }
    )

    class DummyArgs:
        once = True
        interval = None
        cleanup_discovery = False

    will_calls = {}

    class FakePaho:
        def __init__(self, *a, **kw):
            self._will = None
            self._subs = []

        def username_pw_set(self, *a, **kw):
            pass

        def will_set(self, topic, payload=None, qos=0, retain=False):
            will_calls["topic"] = topic
            will_calls["payload"] = payload
            will_calls["qos"] = qos
            will_calls["retain"] = retain

        def publish(self, *a, **kw):
            pass

        def subscribe(self, *a, **kw):
            self._subs.append(a[0])

        def connect(self, *a, **kw):
            return 0

        def loop_start(self):
            pass

        def loop_stop(self):
            pass

        def disconnect(self):
            pass

    monkeypatch.setattr("paho.mqtt.client.Client", FakePaho)

    rc = cmd_service(cfg, DummyArgs())
    assert rc == 0
    assert (
        will_calls.get("topic") == "twickenham_events/status"
        or will_calls.get("topic") == "twickenham_events/availability"
    )
    assert will_calls.get("payload") is not None
