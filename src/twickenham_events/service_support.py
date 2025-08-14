"""Service support: thin wrappers around ha_mqtt_publisher helpers.

This preserves existing imports while delegating to the shared library.
"""

from __future__ import annotations

from typing import Callable

try:
    from ha_mqtt_publisher import (
        AvailabilityPublisher as _LibAvailabilityPublisher,
        install_signal_handlers as _lib_install_signal_handlers,
    )

    # Re-export the library AvailabilityPublisher for drop-in use in callers
    class AvailabilityPublisher(_LibAvailabilityPublisher):  # type: ignore[misc]
        pass

except Exception as _e:  # pragma: no cover - defensive fallback
    _LibAvailabilityPublisher = None  # type: ignore
    _lib_install_signal_handlers = None  # type: ignore

    class AvailabilityPublisher:  # type: ignore[no-redef]
        def __init__(self, *_, **__):
            raise ImportError("ha_mqtt_publisher not available; install dependency")


def install_global_signal_handler(
    shutdown_cb: Callable[[], None], signals: tuple[int, ...] | None = None
):
    """Compatibility wrapper using library install_signal_handlers.

    If a custom signals tuple is provided, install handlers only for those
    signals in a minimal local controller to avoid interfering with global
    handlers during tests. Otherwise, delegate to the library which installs
    SIGINT/SIGTERM.
    """
    if _lib_install_signal_handlers is None:  # pragma: no cover
        raise ImportError("ha_mqtt_publisher not available; install dependency")
    if not signals:
        return _lib_install_signal_handlers(shutdown_cb)

    from contextlib import AbstractContextManager
    import signal as _signal
    from types import FrameType

    class _LocalCtrl(AbstractContextManager):  # pragma: no cover - signal paths
        def __enter__(self):
            self._orig = {}

            def _handler(signum: int, frame: FrameType | None):
                shutdown_cb()

            for sig in signals:
                self._orig[sig] = _signal.getsignal(sig)
                _signal.signal(sig, _handler)
            return self

        def __exit__(self, exc_type, exc, tb):
            for sig, orig in self._orig.items():
                _signal.signal(sig, orig)
            return False

    return _LocalCtrl()
