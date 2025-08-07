"""ICS calendar export functionality for Twickenham Events."""

from pathlib import Path
from typing import Any, Optional

from ics_calendar_utils import EventProcessor, ICSGenerator


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
        # Get calendar configuration
        calendar_config = config.get("calendar", {})
        if not calendar_config.get("enabled", True):
            return None, None

        filename = calendar_config.get("filename", "twickenham_events.ics")
        calendar_name = "Twickenham Stadium Events"

        # Create field mapping for Twickenham events
        field_mapping = {
            "title": "summary",
            "date": "dtstart_date",
            "time": "dtstart_time",  # Will be added with default time
        }

        # Add default time for events that don't have one
        events_with_time = []
        for event in events:
            event_copy = event.copy()
            if "time" not in event_copy or not event_copy["time"]:
                event_copy["time"] = "15:00"  # Default 3 PM start time
            # Add location
            event_copy["location"] = (
                "Twickenham Stadium, 200 Whitton Rd, Twickenham TW2 7BA, UK"
            )
            events_with_time.append(event_copy)

        # Process events
        processor = EventProcessor()
        processor.add_mapping(field_mapping)
        processed_events = processor.process_events(events_with_time)

        # Generate ICS
        generator = ICSGenerator(calendar_name=calendar_name, timezone="Europe/London")

        # Validate events
        validation_errors = generator.validate_events(processed_events)
        if validation_errors:
            print(f"⚠️  Validation warnings: {validation_errors}")

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
