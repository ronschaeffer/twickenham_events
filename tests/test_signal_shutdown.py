import signal

from twickenham_events.constants import AVAILABILITY_TOPIC
from twickenham_events.service_support import (
    AvailabilityPublisher,
    install_global_signal_handler,
)


class StubClient:
    def __init__(self):
        self.published = []

    def publish(self, topic, payload, qos=0, retain=False):
        self.published.append((topic, payload, retain))


def test_signal_shutdown_triggers_offline():
    client = StubClient()
    avail = AvailabilityPublisher(client, AVAILABILITY_TOPIC)
    avail.online()

    with install_global_signal_handler(avail.offline, (signal.SIGUSR1,)):
        # Instead of raising a real signal (which can interrupt pytest), call the handler
        avail.offline()

    assert ("twickenham_events/availability", "offline", True) in client.published
