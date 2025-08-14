from twickenham_events.config import Config


def test_systemd_defaults_present():
    cfg = Config.from_defaults()
    sysd = cfg.get("service.systemd", {})
    assert sysd.get("auto_launch") is False
    assert sysd.get("unit") == "twickenham-events.service"
    assert sysd.get("user") is True
    assert sysd.get("delay_seconds") == 2
