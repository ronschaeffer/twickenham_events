"""Service support utilities: availability + signal handling.

Designed to make future migration to a library ServiceRunner trivial.
"""

from __future__ import annotations

import signal
import threading
from typing import Callable


class AvailabilityPublisher:
    """Publishes simple online/offline retained states."""

    def __init__(self, mqtt_client, topic: str = "twickenham_events/availability"):
        self._client = mqtt_client
        self.topic = topic
        self._lock = threading.Lock()
        self._state = None

    def online(self):  # pragma: no cover - trivial
        with self._lock:
            self._client.publish(self.topic, "online", retain=True)
            self._state = "online"

    def offline(self):  # pragma: no cover - trivial
        with self._lock:
            # Publish offline only if we previously were online to avoid noise
            if self._state != "offline":
                self._client.publish(self.topic, "offline", retain=True)
                self._state = "offline"


class ServiceSignalController:
    """Registers SIGTERM/SIGINT to invoke a shutdown callback once."""

    def __init__(self, shutdown_cb: Callable[[], None]):
        self._shutdown_cb = shutdown_cb
        self._called = False

    def _handler(self, signum, frame):  # pragma: no cover - real signal path
        if not self._called:
            self._called = True
            self._shutdown_cb()

    def register(self, signals: tuple[int, ...] = (signal.SIGTERM,)):
        for sig in signals:
            signal.signal(sig, self._handler)


_GLOBAL_SIGNAL_CONTROLLER: ServiceSignalController | None = None


def install_global_signal_handler(
    shutdown_cb: Callable[[], None], signals: tuple[int, ...] = (signal.SIGTERM,)
):
    """Install a global signal controller for tests & service runtime."""
    global _GLOBAL_SIGNAL_CONTROLLER
    controller = ServiceSignalController(shutdown_cb)
    controller.register(signals)
    _GLOBAL_SIGNAL_CONTROLLER = controller
    return controller
