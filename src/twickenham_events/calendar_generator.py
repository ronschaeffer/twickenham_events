"""
ICS calendar generation for Twickenham Events.
Updated to work with proper legacy event structure.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from icalendar import Calendar, Event


class CalendarGenerator:
    """Handles generation of ICS calendar files from event data."""

    def __init__(self, config):
        """Initialize the calendar generator with configuration."""
        self.config = config

    def generate_ics_calendar(
        self, events: list[dict[str, Any]], output_dir: Path
    ) -> tuple[Optional[dict[str, Any]], Optional[Path]]:
        """
        Generate ICS calendar file from Twickenham events.

        Args:
            events: List of event dictionaries grouped by date (legacy format)
            output_dir: Directory to save the ICS file

        Returns:
            Tuple of (result_dict, ics_file_path)
        """
        # Check if calendar generation is enabled
        if not self.config.get("calendar.enabled", True):
            return None, None

        filename = self.config.get("calendar.filename", "twickenham_events.ics")
        calendar_name = "Twickenham Stadium Events"

        # Use icalendar to generate ICS file
        cal = Calendar()
        cal.add("prodid", "-//Twickenham Events//twickenham_events//EN")
        cal.add("version", "2.0")
        cal.add("X-WR-CALNAME", calendar_name)
        cal.add("X-WR-TIMEZONE", "Europe/London")

        total_events = 0
        for event_day in events:
            date_str = event_day.get("date")
            for event in event_day.get("events", []):
                summary = event.get("fixture") or event.get("title") or "Event"
                time_str = event.get("start_time") or event.get("time") or "15:00"
                venue = event.get(
                    "venue",
                    "Twickenham Stadium, 200 Whitton Rd, Twickenham TW2 7BA, UK",
                )
                desc = event.get("description")

                # Parse date and time - expect YYYY-MM-DD
                dtstart = None
                if date_str:
                    try:
                        dt_parts = [int(x) for x in date_str.split("-")]
                        t_parts = [int(x) for x in time_str.split(":")]
                        dtstart = datetime(
                            dt_parts[0],
                            dt_parts[1],
                            dt_parts[2],
                            t_parts[0],
                            t_parts[1],
                        )
                    except Exception:
                        # Skip event if date is invalid
                        continue

                ical_event = Event()
                ical_event.add("summary", summary)
                # Add a UID for each event to satisfy validator
                ical_event.add("uid", str(uuid4()))
                if dtstart:
                    # Convert to UTC-aware datetime so icalendar serializes with 'Z' and full timestamp
                    dt_utc = dtstart.replace(tzinfo=timezone.utc)
                    ical_event.add("dtstart", dt_utc)
                ical_event.add("location", venue)
                if desc:
                    ical_event.add("description", desc)
                cal.add_component(ical_event)
                total_events += 1

        ics_path = output_dir / filename
        ics_path.parent.mkdir(parents=True, exist_ok=True)
        with open(ics_path, "wb") as f:
            f.write(cal.to_ical())

        result = {
            "success": True,
            "stats": {
                "total_events": total_events,
                "calendar_name": calendar_name,
                "filename": filename,
            },
        }
        return result, ics_path
