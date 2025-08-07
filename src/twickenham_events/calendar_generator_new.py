"""
ICS calendar generation for Twickenham Events.
Updated to work with proper legacy event structure.
"""

from pathlib import Path
from typing import Any, Optional


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
        try:
            # Check if calendar generation is enabled
            if not self.config.get("calendar.enabled", True):
                return None, None

            # Import here to make it optional
            try:
                from ics_calendar_utils import EventProcessor, ICSGenerator
            except ImportError:
                print(
                    "❌ ics_calendar_utils not available - install with 'poetry install --with calendar'"
                )
                return None, None

            filename = self.config.get("calendar.filename", "twickenham_events.ics")
            calendar_name = "Twickenham Stadium Events"

            # Create field mapping for Twickenham events (updated for legacy structure)
            field_mapping = {
                "fixture": "summary",
                "date": "dtstart_date",
                "start_time": "dtstart_time",
            }

            # Convert our event format to the calendar format
            # Legacy format: events is a list of date groups, each with an "events" array
            calendar_events = []
            for event_day in events:
                for event in event_day["events"]:
                    event_copy = {
                        "fixture": event.get("fixture", "Unknown Event"),
                        "date": event_day["date"],
                        "start_time": event.get("start_time")
                        or "15:00",  # Default 3 PM
                        "location": "Twickenham Stadium, 200 Whitton Rd, Twickenham TW2 7BA, UK",
                    }

                    # Add additional details to description
                    description_parts = []
                    if event.get("fixture_short"):
                        description_parts.append(
                            f"Short name: {event['fixture_short']}"
                        )
                    if event.get("crowd"):
                        description_parts.append(f"Expected crowd: {event['crowd']}")
                    if description_parts:
                        event_copy["description"] = " | ".join(description_parts)

                    calendar_events.append(event_copy)

            # Process events
            processor = EventProcessor()
            processor.add_mapping(field_mapping)
            processed_events = processor.process_events(calendar_events)

            # Generate ICS
            generator = ICSGenerator(
                calendar_name=calendar_name, timezone="Europe/London"
            )

            # Validate events
            validation_errors = generator.validate_events(processed_events)
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
                    "date_range": stats.get("date_range", "N/A"),
                    "file_size": ics_path.stat().st_size if ics_path.exists() else 0,
                },
                "file_path": str(ics_path),
                "calendar_url": self.get_calendar_url(ics_path),
            }

            return result, ics_path

        except Exception as e:
            print(f"❌ Error generating ICS calendar: {e}")
            return None, None

    def get_calendar_url(self, ics_path: Path) -> Optional[str]:
        """
        Get the public URL for the calendar file.

        Args:
            ics_path: Path to the generated ICS file

        Returns:
            Public URL if configured, None otherwise
        """
        base_url = self.config.get("calendar.base_url")
        if base_url and ics_path.exists():
            filename = ics_path.name
            return f"{base_url.rstrip('/')}/{filename}"
        return None
