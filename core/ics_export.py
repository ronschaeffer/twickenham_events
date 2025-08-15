"""ICS calendar export functionality for Twickenham Events."""

from pathlib import Path
from typing import Any, Optional

from icalendar import Calendar, Event

# Use the project's canonical date normalizer
from twickenham_events.scraper import EventScraper


def generate_ics_calendar(
    events: list[dict[str, Any]], config: dict[str, Any], output_dir: Path
) -> tuple[Optional[dict[str, Any]], Optional[Path]]:
    """
    Generate ICS calendar file from Twickenham events.

    Args:
        events: List of event dictionaries
        config: Configuration dictionary
        output_dir: Directory to save the ICS file

    Returns:
        Tuple of (result_dict, ics_file_path)
    """
    try:
        calendar_config = config.get("calendar", {})
        if not calendar_config.get("enabled", True):
            return None, None

        filename = calendar_config.get("filename", "twickenham_events.ics")
        calendar_name = "Twickenham Stadium Events"

        cal = Calendar()
        cal.add("prodid", "-//Twickenham Events//twickenham_events//EN")
        cal.add("version", "2.0")
        cal.add("X-WR-CALNAME", calendar_name)
        cal.add("X-WR-TIMEZONE", "Europe/London")

        total_events = 0
        # Leverage the repository's EventScraper.normalize_date_range to canonicalize dates
        normalizer = EventScraper({})

        def _parse_date_using_normalizer(date_str: str, time_str: str):
            """Return a datetime or None using the project's normalizer, falling back to flexible parsing."""
            normalized = normalizer.normalize_date_range(date_str)
            from datetime import datetime as _dt

            if normalized:
                try:
                    y, m, d = [int(x) for x in normalized.split("-")]
                    t_parts = [int(x) for x in (time_str or "15:00").split(":")]
                    return _dt(y, m, d, t_parts[0], t_parts[1])
                except Exception:
                    return None

            # Fallback: try ISO-style YYYY-MM-DD parsing
            try:
                parts = [int(x) for x in date_str.split("-")]
                t_parts = [int(x) for x in (time_str or "15:00").split(":")]
                return _dt(parts[0], parts[1], parts[2], t_parts[0], t_parts[1])
            except Exception:
                pass

            # Fallback: try a few common human-readable formats
            fmts = ["%A, %d %B %Y", "%d %B %Y", "%d %b %Y"]
            for fmt in fmts:
                try:
                    d = _dt.strptime(date_str, fmt)
                    t_parts = [int(x) for x in (time_str or "15:00").split(":")]
                    return _dt(d.year, d.month, d.day, t_parts[0], t_parts[1])
                except Exception:
                    continue

            return None

        for ev in events:
            e = ev.copy()
            # Normalize keys
            summary = e.get("fixture") or e.get("title") or "Event"
            date_str = e.get("date")
            time_str = e.get("start_time") or e.get("time") or "15:00"
            venue = e.get(
                "venue", "Twickenham Stadium, 200 Whitton Rd, Twickenham TW2 7BA, UK"
            )
            description = []
            if e.get("fixture_short"):
                description.append(f"Short name: {e['fixture_short']}")
            if e.get("crowd"):
                description.append(f"Expected crowd: {e['crowd']}")
            desc = " | ".join(description) if description else None

            # Parse date and time using the canonical normalizer
            dtstart = None
            if date_str:
                dtstart = _parse_date_using_normalizer(date_str, time_str)
                if not dtstart:
                    # Skip events with invalid dates entirely
                    continue

            from uuid import uuid4

            event = Event()
            event.add("summary", summary)
            # Add a UID for each event to satisfy validator
            event.add("uid", str(uuid4()))
            if dtstart:
                # Convert to UTC-aware datetime so icalendar serializes with 'Z' and full timestamp
                from datetime import timezone

                dt_utc = dtstart.replace(tzinfo=timezone.utc)
                event.add("dtstart", dt_utc)
            event.add("location", venue)
            if desc:
                event.add("description", desc)
            cal.add_component(event)
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


def get_calendar_url(config: dict[str, Any]) -> Optional[str]:
    """
    Get the calendar URL for external access.

    Args:
        config: Configuration dictionary

    Returns:
        Calendar URL if configured, None otherwise
    """
    calendar_config = config.get("calendar", {})
    if not calendar_config.get("enabled", True):
        return None

    # Check for URL override in environment
    url_override = config.get("calendar_url_override")
    if url_override:
        filename = calendar_config.get("filename", "twickenham_events.ics")

        # If URL doesn't end with .ics, append the filename
        if not url_override.endswith(".ics"):
            if not url_override.endswith("/"):
                url_override += "/"
            url_override += filename

        return url_override

    return None
