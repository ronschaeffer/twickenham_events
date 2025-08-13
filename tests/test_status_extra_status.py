from unittest.mock import MagicMock, patch

from twickenham_events.config import Config


def test_publish_events_extra_status_merge():
    config = Config(
        {
            "mqtt": {
                "enabled": True,
                "broker": "localhost",
                "port": 1883,
                "topics": {"status": "twickenham_events/status"},
            }
        }
    )
    events = []
    mock_pub_instance = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.__enter__.return_value = mock_pub_instance

    with (
        patch("twickenham_events.mqtt_client.MQTTPublisher", return_value=mock_ctx),
        patch("twickenham_events.mqtt_client.MQTT_AVAILABLE", True),
    ):
        from twickenham_events.mqtt_client import MQTTClient  # import after patch

        client = MQTTClient(config)
        client.publish_events(
            events,
            ai_processor=None,
            extra_status={"last_run_ts": 123, "custom_flag": True},
        )

    published = {
        call.args[0]: call.args[1] for call in mock_pub_instance.publish.call_args_list
    }
    status = published["twickenham_events/status"]
    assert status["last_run_ts"] == 123
    assert status["custom_flag"] is True
    assert "status" in status and "event_count" in status
