import signal

from twickenham_events.service_support import (
    AvailabilityPublisher,
    install_global_signal_handler,
)


class StubClient:
    def __init__(self):
        self.published = []

    def publish(self, topic, payload, retain=False):
        self.published.append((topic, payload, retain))


def test_signal_shutdown_triggers_offline():
    client = StubClient()
    avail = AvailabilityPublisher(client)
    avail.online()

    install_global_signal_handler(avail.offline, (signal.SIGUSR1,))
    signal.raise_signal(signal.SIGUSR1)

    assert ("twickenham_events/availability", "offline", True) in client.published
