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

        # Create field mapping for Twickenham events. The installed library already
        # maps common fields like 'fixture'->'summary', 'date'->'dtstart_date',
        # and 'start_time'->'dtstart_time'. We'll normalize our input accordingly
        # and only rely on defaults to minimize API coupling.

        # Add default time for events that don't have one
        events_normalized: list[dict[str, Any]] = []
        for ev in events:
            e = ev.copy()
            # Normalize keys expected by the processor defaults
            if "title" in e and "fixture" not in e:
                e["fixture"] = e.get("title")
            if "time" in e and "start_time" not in e:
                e["start_time"] = e.get("time")
            if not e.get("start_time"):
                e["start_time"] = "15:00"  # Default 3 PM start time
            # Ensure location present
            e["venue"] = e.get(
                "venue",
                "Twickenham Stadium, 200 Whitton Rd, Twickenham TW2 7BA, UK",
            )
            events_normalized.append(e)

        # Process events
        processor = EventProcessor()
        # Newer library exposes process_events; older fallback may expose 'process'.
        if hasattr(processor, "process_events"):
            processed_events = processor.process_events(events_normalized)  # type: ignore[attr-defined]
        else:  # pragma: no cover - legacy shim
            processed_events = processor.process(events_normalized)  # type: ignore[call-arg]

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
