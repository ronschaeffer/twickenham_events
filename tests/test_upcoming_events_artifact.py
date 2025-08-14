import json
import subprocess
import sys


def test_upcoming_events_regenerated_non_empty(tmp_path):
    """Run scrape command and assert upcoming_events.json exists and has events when raw events > 0.

    Uses actual CLI to exercise end-to-end generation logic.
    """
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    # Run scrape; allow failure to raise for test visibility
    try:
        subprocess.run(
            [
                "twick-events",
                "scrape",
                "--output",
                str(out_dir),
                "--config",
                "config/config.yaml.example",
            ],
            check=True,
        )
    except FileNotFoundError:
        # Fallback to module invocation if console script isn't on PATH in CI
        subprocess.run(
            [
                sys.executable,
                "-m",
                "twickenham_events.__main__",
                "scrape",
                "--output",
                str(out_dir),
                "--config",
                "config/config.yaml.example",
            ],
            check=True,
        )
    up_file = out_dir / "upcoming_events.json"
    assert up_file.exists(), "upcoming_events.json not created"
    data = json.loads(up_file.read_text())
    assert isinstance(data, dict)
    events = data.get("events")
    assert isinstance(events, list), "events not a list"
    # If ICS has events (heuristic: twickenham_events.ics file present & non-empty), expect non-empty events list
    ics_file = out_dir / "twickenham_events.ics"
    if ics_file.exists() and ics_file.read_text().count("BEGIN:VEVENT") > 0:
        assert len(events) > 0, (
            "events list unexpectedly empty despite ICS events present"
        )
    # Ensure each event has date and title
    for ev in events:
        assert "date" in ev
        assert "title" in ev or "fixture" in ev
