import time

from twickenham_events.service_cycle import _normalize_errors, build_extra_status


class DummyScraper:
    def __init__(self, errors):
        self.error_log = errors


def test_build_extra_status_no_errors():
    sc = DummyScraper([])
    extra = build_extra_status(
        sc,
        flat_events=[{"fixture": "X"}],
        trigger="interval",
        interval=100,
        run_ts=time.time(),
    )
    assert "errors" not in extra
    assert extra["last_run_trigger"] == "interval"


def test_build_extra_status_errors_and_no_events():
    sc = DummyScraper(["network timeout", "parse failure"])
    extra = build_extra_status(
        sc,
        flat_events=[],
        trigger="manual",
        interval=50,
        run_ts=time.time(),
        reset_cache=True,
    )
    assert extra["status"] == "error"
    assert extra["error_count"] == 2
    assert len(extra["errors"]) == 2
    assert all("message" in e and "ts" in e for e in extra["errors"])


def test_error_truncation():
    errs = [f"e{i}" for i in range(60)]
    sc = DummyScraper(errs)
    extra = build_extra_status(
        sc,
        flat_events=[],
        trigger="manual",
        interval=10,
        run_ts=time.time(),
        max_errors=25,
    )
    assert extra["error_count"] == 25
    first_msg = next(iter(e["message"] for e in extra["errors"]))
    assert first_msg == "e35"  # tail retained


def test_normalize_structured_errors():
    structured = [
        {"message": "m1", "ts": "2025-01-01T00:00:00Z"},
        {"message": "m2"},
    ]
    norm = _normalize_errors(structured, 10)
    assert len(norm) == 2
    assert norm[0]["message"] == "m1"
    assert norm[0]["ts"] == "2025-01-01T00:00:00Z"
    assert norm[1]["message"] == "m2"


def test_max_errors_default():
    sc = DummyScraper(["x"])  # ensure no crash
    extra = build_extra_status(sc, [], "tick", 1, time.time(), reset_cache=True)
    assert extra["error_count"] == 1
