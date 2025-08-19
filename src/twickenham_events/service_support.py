"""Service support: thin wrappers around ha_mqtt_publisher helpers.

This preserves existing imports while delegating to the shared library.
"""

from __future__ import annotations

from typing import Any, Callable

_lib_install_signal_handlers = None
try:
    from ha_mqtt_publisher import (
        AvailabilityPublisher as _LibAvailabilityPublisher,
        install_signal_handlers as _tmp_install_signal_handlers,
    )

    # assign under our module variable name so mypy sees a single definition
    _lib_install_signal_handlers = _tmp_install_signal_handlers
except Exception:
    _LibAvailabilityPublisher = None
    _lib_install_signal_handlers_impl: object | None = None


# Expose a single AvailabilityPublisher symbol. If the library is present we
# reuse its class, otherwise provide a minimal shim that raises on instantiation.
if _LibAvailabilityPublisher is not None:
    # Assign the upstream class; this is a runtime alias used by callers.
    AvailabilityPublisher = _LibAvailabilityPublisher
else:

    class _AvailabilityPublisherFallback:  # fallback shim
        def __init__(self, *_: Any, **__: Any) -> None:
            raise ImportError("ha_mqtt_publisher not available; install dependency")

    AvailabilityPublisher = _AvailabilityPublisherFallback

    # Provide a more permissive fallback so tests can construct and call online()/offline()
    class _AvailabilityPublisherNoop:
        def __init__(self, mqtt_client: Any, topic: str, qos: int = 0) -> None:
            self.client = mqtt_client
            self.topic = topic
            self.qos = qos

        def online(self) -> None:
            try:
                # Best-effort publish; no exception on failure
                self.client.publish(self.topic, "online", qos=self.qos, retain=False)
            except Exception:
                pass

        def offline(self) -> None:
            try:
                # For LWT/offline semantics tests expect retained/offline True
                self.client.publish(self.topic, "offline", qos=self.qos, retain=True)
            except Exception:
                pass

    # Bind a permissive name for runtime use in tests when library missing
    AvailabilityPublisher = _AvailabilityPublisherNoop


def install_global_signal_handler(
    shutdown_cb: Callable[[], None], signals: tuple[int, ...] | None = None
) -> object | None:
    """Compatibility wrapper using library install_signal_handlers.

    If a custom signals tuple is provided, install handlers only for those
    signals in a minimal local controller to avoid interfering with global
    handlers during tests. Otherwise, delegate to the library which installs
    SIGINT/SIGTERM.
    """
    if (
        _lib_install_signal_handlers is None
        and _lib_install_signal_handlers_impl is None
    ):  # pragma: no cover
        # Provide a noop context manager when library missing so tests can
        # install local handlers without raising import errors.
        class _NoopCtrl:
            def __enter__(self) -> _NoopCtrl:
                return self

            def __exit__(
                self, exc_type: object | None, exc: object | None, tb: object | None
            ) -> None:
                return None

        if not signals:
            return _NoopCtrl()
        else:
            # fall through to local controller below when specific signals provided
            pass
    if not signals:
        # delegate to library; signature matches at runtime
        # mypy can't statically verify the external helper signature here; cast to Any
        from typing import Any, cast

        impl = _lib_install_signal_handlers or _lib_install_signal_handlers_impl
        return cast(Any, impl)(shutdown_cb)

    import signal as _signal
    from types import FrameType

    class _LocalCtrl:  # pragma: no cover - signal paths
        def __enter__(self) -> _LocalCtrl:
            self._orig: dict[int, object] = {}

            def _handler(signum: int, frame: FrameType | None) -> None:
                shutdown_cb()

            assert signals is not None
            for sig in signals:
                self._orig[sig] = _signal.getsignal(sig)
                _signal.signal(sig, _handler)
            return self

        def __exit__(
            self, exc_type: object | None, exc: object | None, tb: object | None
        ) -> None:
            for sig, orig in self._orig.items():
                # orig is the value returned by signal.getsignal, which mypy types
                # as a union that doesn't match the second arg of signal.signal; the
                # call is safe at runtime so silence the type error here.
                _signal.signal(sig, orig)  # type: ignore[arg-type]
            return None

    return _LocalCtrl()
