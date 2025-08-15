"""
ICS calendar generation for Twickenham Events.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from icalendar import Calendar, Event


class CalendarGenerator:
    """Handles generation of ICS calendar files from event data."""

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
        try:
            if not self.config.get("calendar.enabled", True):
                return None, None

            filename = self.config.get("calendar.filename", "twickenham_events.ics")
            calendar_name = "Twickenham Stadium Events"

            cal = Calendar()
            cal.add("prodid", "-//Twickenham Events//twickenham_events//EN")
            cal.add("version", "2.0")
            cal.add("X-WR-CALNAME", calendar_name)
            cal.add("X-WR-TIMEZONE", "Europe/London")

            total_events = 0
            for event_day in events:
                date_str = event_day.get("date")
                for event in event_day["events"]:
                    summary = event.get("fixture") or event.get("title") or "Event"
                    time_str = event.get("start_time") or event.get("time") or "15:00"
                    venue = event.get(
                        "venue",
                        "Twickenham Stadium, 200 Whitton Rd, Twickenham TW2 7BA, UK",
                    )
                    desc = event.get("description")

                    # Parse date and time
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
                            continue  # Skip event if date is invalid

                    ical_event = Event()
                    ical_event.add("summary", summary)
                    ical_event.add("dtstart", dtstart)
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
        except Exception as e:
            print(f"❌ Error generating ICS calendar: {e}")
            return None, None
            if validation_errors:
                print(f"⚠️  Calendar validation warnings: {validation_errors}")

            # Create output path
            ics_path = output_dir / filename
            ics_path.parent.mkdir(parents=True, exist_ok=True)

            # Generate ICS content and save to file
            generator.generate_ics(processed_events, str(ics_path))

            # Get statistics
            stats = generator.get_ics_stats(processed_events)

            # Return success result
            result = {
                "success": True,
                "stats": {
                    "total_events": stats.get("total_events", len(processed_events)),
                    "calendar_name": calendar_name,
                    "filename": filename,
                    "output_path": str(ics_path),
                },
            }

            return result, ics_path

        except Exception as e:
            print(f"❌ Error generating ICS calendar: {e}")
            return None, None

    def get_calendar_url(self) -> Optional[str]:
        """
        Get the calendar URL for external access.

        Returns:
            Calendar URL if configured, None otherwise
        """
        if not self.config.get("calendar.enabled", True):
            return None

        # Check for URL override in environment
        url_override = self.config.get("calendar_url_override")
        if url_override:
            filename = self.config.get("calendar.filename", "twickenham_events.ics")

            # If URL doesn't end with .ics, append the filename
            if not url_override.endswith(".ics"):
                if not url_override.endswith("/"):
                    url_override += "/"
                url_override += filename

            return url_override

        return None
