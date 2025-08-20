from pathlib import Path

from twickenham_events.calendar_generator import CalendarGenerator
from twickenham_events.config import Config


def test_generate_ics_creates_file(tmp_path: Path):
    # Minimal config enables calendar by default
    cfg = Config.from_defaults()

    # Sample legacy-shaped events structure: list of days with events list
    events = [
        {
            "date": "2025-03-15",
            "events": [
                {"fixture": "England v France", "start_time": "16:45"},
                {"fixture": "Taylor Swift", "start_time": "20:00"},
            ],
        }
    ]

    gen = CalendarGenerator(cfg)
    result, ics_path = gen.generate_ics_calendar(events, tmp_path)

    assert result and result.get("success") is True
    assert ics_path and ics_path.exists()

    # Basic content sanity: ICS should contain VEVENT
    content = ics_path.read_text()
    assert "BEGIN:VEVENT" in content and "END:VEVENT" in content
