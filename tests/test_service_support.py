from twickenham_events.service_support import (
    AvailabilityPublisher,
    install_global_signal_handler,
)


def test_service_support_exports_exist():
    assert AvailabilityPublisher is not None
    assert callable(install_global_signal_handler)
