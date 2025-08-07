"""Tests for ICS export functionality."""

from pathlib import Path
import tempfile

from core.ics_export import generate_ics_calendar, get_calendar_url


class TestICSExport:
    """Test ICS calendar export functionality."""

    def test_generate_ics_calendar_basic(self):
        """Test basic ICS calendar generation."""
        events = [
            {
                "date": "Saturday, 18 January 2025",
                "title": "England vs France - Six Nations",
            },
            {
                "date": "Sunday, 9 February 2025",
                "title": "England vs Ireland - Six Nations",
            },
        ]

        config = {
            "calendar": {
                "enabled": True,
                "filename": "test_events.ics",
                "duration_estimation": {"default_hours": 2.5},
            }
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            result, ics_path = generate_ics_calendar(events, config, output_dir)

            assert result is not None
            assert result["success"] is True
            assert result["stats"]["total_events"] == 2
            assert ics_path is not None
            assert ics_path.exists()
            assert ics_path.name == "test_events.ics"

            # Check file content
            content = ics_path.read_text(encoding="utf-8")
            assert "BEGIN:VCALENDAR" in content
            assert "England vs France" in content
            assert "England vs Ireland" in content
            assert "Twickenham Stadium" in content

    def test_generate_ics_calendar_disabled(self):
        """Test ICS generation when disabled."""
        events = [{"date": "Saturday, 18 January 2025", "title": "Test Event"}]
        config = {"calendar": {"enabled": False}}

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            result, ics_path = generate_ics_calendar(events, config, output_dir)

            assert result is None
            assert ics_path is None

    def test_generate_ics_calendar_invalid_date(self):
        """Test ICS generation with invalid date format."""
        events = [
            {"date": "Invalid Date", "title": "Test Event"},
            {"date": "Saturday, 18 January 2025", "title": "Valid Event"},
        ]

        config = {"calendar": {"enabled": True, "filename": "test_events.ics"}}

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            result, ics_path = generate_ics_calendar(events, config, output_dir)

            # Should succeed with only the valid event
            assert result is not None
            assert result["stats"]["total_events"] == 1

    def test_get_calendar_url_with_override(self):
        """Test calendar URL generation with override."""
        config = {
            "calendar": {"enabled": True, "filename": "events.ics"},
            "calendar_url_override": "https://example.com/calendars/",
        }

        url = get_calendar_url(config)
        assert url == "https://example.com/calendars/events.ics"

    def test_get_calendar_url_with_full_override(self):
        """Test calendar URL with full file path override."""
        config = {
            "calendar": {"enabled": True},
            "calendar_url_override": "https://example.com/custom/path/events.ics",
        }

        url = get_calendar_url(config)
        assert url == "https://example.com/custom/path/events.ics"

    def test_get_calendar_url_disabled(self):
        """Test calendar URL when calendar is disabled."""
        config = {"calendar": {"enabled": False}}

        url = get_calendar_url(config)
        assert url is None

    def test_get_calendar_url_no_override(self):
        """Test calendar URL without override."""
        config = {"calendar": {"enabled": True}}

        url = get_calendar_url(config)
        assert url is None
