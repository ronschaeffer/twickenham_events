"""
Comprehensive tests for the Twickenham Events scraper implementation.
Tests all event processing functionality including date/time normalization,
crowd validation, event logic, and edge cases.
"""

from datetime import date, datetime
from pathlib import Path
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add the src directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from twickenham_events.config import Config
from twickenham_events.scraper import EventScraper


@pytest.fixture
def mock_response_success():
    """Fixture for a successful requests.get response."""
    mock = Mock()
    mock.status_code = 200
    mock.content = b"""
    <html><body>
        <table class="table">
            <caption>Events at Twickenham Stadium</caption>
            <tr><th>Date</th><th>Fixture</th><th>Kick off</th><th>Crowd</th></tr>
            <tr><td>Saturday 14 June 2025</td><td>Past Event</td><td>3pm</td><td>10,000</td></tr>
            <tr><td>Saturday 27 September 2025</td><td>Future Event 1</td><td>4pm</td><td>80,000</td></tr>
            <tr><td>Saturday 4 October 2025</td><td>Future Event 2</td><td>TBC</td><td>50,000</td></tr>
        </table>
    </body></html>
    """
    mock.raise_for_status = Mock()
    return mock


@pytest.fixture
def mock_response_no_table():
    """Fixture for a response with no event table."""
    mock = Mock()
    mock.status_code = 200
    mock.content = b"<html><body><p>No events scheduled.</p></body></html>"
    mock.raise_for_status = Mock()
    return mock


@pytest.fixture
def mock_config():
    """Provides a mock Config object for tests."""
    mock = MagicMock(spec=Config)
    mock.get.side_effect = lambda key, default=None: {
        "event_rules.end_of_day_cutoff": "23:00",
        "event_rules.next_event_delay_hours": 1,
        "scraping.max_retries": 3,
        "scraping.retry_delay": 5,
        "scraping.timeout": 10,
        "ai_shortener.enabled": False,  # Disable for most tests
    }.get(key, default)
    return mock


@pytest.fixture
def scraper(mock_config):
    """Provides an EventScraper instance with mock config."""
    return EventScraper(mock_config)


class TestEventScraper:
    """Test the EventScraper class methods."""

    @patch("twickenham_events.scraper.requests.get")
    def test_scrape_events_success(self, mock_get, scraper, mock_response_success):
        """Test successful event fetching and parsing."""
        mock_get.return_value = mock_response_success
        events, stats = scraper.scrape_events("http://fakeurl.com")

        assert len(events) == 3
        assert events[0]["title"] == "Past Event"
        assert events[1]["title"] == "Future Event 1"
        assert events[2]["time"] == "TBC"

        # Test the stats functionality
        assert stats["data_source"] == "live"
        assert stats["raw_events_count"] == 3
        assert stats["retry_attempts"] == 1
        assert "fetch_duration" in stats

    @patch("twickenham_events.scraper.requests.get")
    def test_scrape_events_no_table(self, mock_get, scraper, mock_response_no_table):
        """Test fetching when no event table is present."""
        mock_get.return_value = mock_response_no_table
        events, stats = scraper.scrape_events("http://fakeurl.com")

        assert len(events) == 0
        assert stats["data_source"] == "live"
        assert stats["raw_events_count"] == 0

    def test_scrape_events_no_url(self, scraper):
        """Test scraping with no URL provided."""
        events, stats = scraper.scrape_events("")

        assert len(events) == 0
        assert stats["data_source"] == "config_error"
        assert len(scraper.error_log) > 0

    def test_summarize_events_filters_past_events(self, scraper):
        """Test that summarize_events correctly filters out past events."""
        raw_events = [
            {
                "date": "14 June 2025",
                "title": "Past Event",
                "time": "3pm",
                "crowd": "10,000",
            },
            {
                "date": "27 September 2025",
                "title": "Future Event 1",
                "time": "4pm",
                "crowd": "80,000",
            },
            {
                "date": "04 October 2025",
                "title": "Future Event 2",
                "time": "TBC",
                "crowd": "50,000",
            },
        ]

        # Today's date is July 31, 2025, so June event should be filtered out
        with patch("twickenham_events.scraper.datetime") as mock_datetime:
            mock_datetime.now.return_value.date.return_value = date(2025, 7, 31)
            mock_datetime.strptime = datetime.strptime

            summarized = scraper.summarize_events(raw_events)
            assert len(summarized) == 2
            assert summarized[0]["date"] == "2025-09-27"
            assert summarized[1]["date"] == "2025-10-04"

    def test_find_next_event_and_summary(self, scraper):
        """Test finding the next event from a list of summarized events."""
        summarized_events = [
            {
                "date": "2025-09-27",
                "events": [{"fixture": "Future Event 1", "start_time": "16:00"}],
                "earliest_start": "16:00",
            },
            {
                "date": "2025-10-04",
                "events": [{"fixture": "Future Event 2", "start_time": None}],
                "earliest_start": None,
            },
        ]

        with patch(
            "twickenham_events.scraper.datetime", autospec=True
        ) as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 7, 31, 12, 0, 0)
            mock_datetime.strptime = datetime.strptime
            mock_datetime.combine = datetime.combine

            next_event, next_day_summary = scraper.find_next_event_and_summary(
                summarized_events
            )
            assert next_event is not None
            assert next_event["fixture"] == "Future Event 1"
            assert next_day_summary is not None
            assert next_day_summary["date"] == "2025-09-27"


class TestDateNormalization:
    """Test date normalization with all edge cases from legacy tests."""

    @pytest.mark.parametrize(
        ("input_date", "expected"),
        [
            ("16 May 2025", "2025-05-16"),
            ("16/17 May 2025", "2025-05-16"),
            ("Mon 16 May 2025", "2025-05-16"),
            ("16th May 2025", "2025-05-16"),
            ("01 January 2023", "2023-01-01"),
            ("31 December 2023", "2023-12-31"),
            ("29 February 2024", "2024-02-29"),  # Leap year
            ("30 Feb 2023", None),  # Invalid date
            ("15-08-2023", "2023-08-15"),
            ("15/08/2023", "2023-08-15"),
            ("15.08.2023", "2023-08-15"),
            ("15-Aug-2023", "2023-08-15"),
            ("15-Aug-23", "2023-08-15"),
            ("15/08/23", "2023-08-15"),
            ("15.08.23", "2023-08-15"),
            ("15-08-23", "2023-08-15"),
            ("15th August 2023", "2023-08-15"),
            ("15th Aug 2023", "2023-08-15"),
            ("15th Aug 23", "2023-08-15"),
            ("15th August 23", "2023-08-15"),
            ("Invalid Date", None),
            ("Monday 1st December 2024", "2024-12-01"),
            ("Tuesday 2nd December 2024", "2024-12-02"),
            ("Wednesday 3rd December 2024", "2024-12-03"),
            ("Thursday 4th December 2024", "2024-12-04"),
            ("Friday 5th December 2024", "2024-12-05"),
            ("Saturday 6th December 2024", "2024-12-06"),
            ("Sunday 7th December 2024", "2024-12-07"),
            ("Mon 8th Dec 2024", "2024-12-08"),
            ("Tue 9th Dec 2024", "2024-12-09"),
            ("Wed 10th Dec 2024", "2024-12-10"),
            ("Thu 11th Dec 2024", "2024-12-11"),
            ("Fri 12th Dec 2024", "2024-12-12"),
            ("Sat 13th Dec 2024", "2024-12-13"),
            ("Sun 14th Dec 2024", "2024-12-14"),
            ("Weekend 16/17 May 2025", "2025-05-16"),
            ("Wknd 23/24 May 2025", "2025-05-23"),
            ("7-Jan-25", "2025-01-07"),
            ("7/1/2025", "2025-01-07"),
            ("07-01-25", "2025-01-07"),
            ("07.01.2025", "2025-01-07"),
            ("7.1.25", "2025-01-07"),
            ("7-May-25", "2025-05-07"),
            ("1st May 2025", "2025-05-01"),
            ("2nd May 2025", "2025-05-02"),
            ("3rd May 2025", "2025-05-03"),
            ("4th May 2025", "2025-05-04"),
            ("21st June 2025", "2025-06-21"),
            ("Mon 7-Jan-25", "2025-01-07"),
            ("Tuesday 07/01/2025", "2025-01-07"),
            ("Wed 7.1.25", "2025-01-07"),
            ("", None),
            ("32/13/25", None),
            ("Weekend", None),
            ("Saturday 2nd November 2024", "2024-11-02"),
            ("Sunday 24th November 2024", "2024-11-24"),
            ("Saturday 28th December 2024", "2024-12-28"),
            ("Saturday 8th February 2025", "2025-02-08"),
            ("Saturday 21st June 2025", "2025-06-21"),
        ],
    )
    def test_normalize_date_range(self, scraper, input_date, expected):
        """Test date normalization with all legacy test cases."""
        assert scraper.normalize_date_range(input_date) == expected


class TestTimeNormalization:
    """Test time normalization with all edge cases from legacy tests."""

    @pytest.mark.parametrize(
        ("input_time", "expected"),
        [
            ("3pm", ["15:00"]),
            ("3:30pm", ["15:30"]),
            ("3 & 5pm", ["15:00", "17:00"]),
            ("TBC", None),
            ("3:10pm", ["15:10"]),
            ("3.10pm", ["15:10"]),
            ("11am", ["11:00"]),
            ("12pm", ["12:00"]),
            ("12am", ["00:00"]),
            ("15:10", ["15:10"]),
            ("03:10", ["03:10"]),
            ("00:00", ["00:00"]),
            ("3pm & 6pm", ["15:00", "18:00"]),
            ("3:10pm & 5:40pm", ["15:10", "17:40"]),
            ("3.10pm & 5.40pm", ["15:10", "17:40"]),
            ("tbc", None),
            ("", None),
            ("Invalid", None),
            ("25:00", None),
            ("13pm", None),
            ("3pm and 6pm", ["15:00", "18:00"]),
            ("5.40pm", ["17:40"]),
            ("4.10pm", ["16:10"]),
            ("4.45pm", ["16:45"]),
            # Midnight handling test cases
            ("midnight", ["00:00"]),
            ("Midnight", ["00:00"]),
            ("12 midnight", ["00:00"]),
            ("midnight 12", ["00:00"]),
            ("Event at midnight", ["00:00"]),
            # Noon handling test cases
            ("noon", ["12:00"]),
            ("Noon", ["12:00"]),
            ("12 noon", ["12:00"]),
            ("12noon", ["12:00"]),  # No space version
            ("noon 12", ["12:00"]),
            ("Event at noon", ["12:00"]),
            # Midnight handling test cases (including no space)
            ("12midnight", ["00:00"]),  # No space version
            # Mixed noon and midnight
            ("noon and midnight", ["00:00", "12:00"]),
        ],
    )
    def test_normalize_time(self, scraper, input_time, expected):
        """Test time normalization with all legacy test cases."""
        assert scraper.normalize_time(input_time) == expected


class TestCrowdValidation:
    """Test crowd size validation with all edge cases from legacy tests."""

    @pytest.mark.parametrize(
        ("input_crowd", "expected"),
        [
            ("10,000", "10,000"),
            ("10000", "10,000"),
            ("TBC", None),
            ("Estimate 10000", "10,000"),
            ("Est. 10000", "10,000"),
            ("Approx. 10000", "10,000"),
            ("~10000", "10,000"),
            ("Invalid", None),
            ("", None),
            (None, None),
            ("50,000-82,000", "82,000"),  # Range handling
            ("150000", None),  # Implausible size
        ],
    )
    def test_validate_crowd_size(self, scraper, input_crowd, expected):
        """Test crowd size validation with all legacy test cases."""
        assert scraper.validate_crowd_size(input_crowd) == expected


class TestEventLogic:
    """Test complex event finding logic from legacy tests."""

    @pytest.fixture
    def mock_summarized_events(self):
        """Mock events for testing event logic."""
        return [
            {
                "date": "2025-08-01",
                "events": [
                    {"fixture": "Concert", "start_time": "15:00", "crowd": "70,000"},
                    {"fixture": "Late Show", "start_time": "20:00", "crowd": "70,000"},
                ],
                "earliest_start": "15:00",
            },
            {
                "date": "2025-08-03",
                "events": [
                    {"fixture": "Rugby Match", "start_time": "14:00", "crowd": "82,000"}
                ],
                "earliest_start": "14:00",
            },
        ]

    @pytest.mark.parametrize(
        ("current_time_str", "expected_fixture"),
        [
            # Before any events have started
            ("2025-08-01 14:00:00", "Concert"),
            # First event has started, but is within the 1-hour delay window
            ("2025-08-01 15:30:00", "Concert"),
            # First event is now over (1 hour past start), so next event is the Late Show
            ("2025-08-01 16:01:00", "Late Show"),
            # Late show is now the current event
            ("2025-08-01 21:00:00", "Late Show"),
            # It's past the 23:00 cutoff, so all of today's events are over. Next event is on Aug 3.
            ("2025-08-01 23:01:00", "Rugby Match"),
            # The next event is still the one on Aug 3.
            ("2025-08-02 10:00:00", "Rugby Match"),
        ],
    )
    def test_find_next_event_logic(
        self, scraper, mock_summarized_events, current_time_str, expected_fixture
    ):
        """Test the find_next_event_and_summary function with various mocked times."""
        mocked_now = datetime.strptime(current_time_str, "%Y-%m-%d %H:%M:%S")

        with patch("twickenham_events.scraper.datetime", autospec=True) as mock_dt:
            mock_dt.now.return_value = mocked_now
            mock_dt.strptime.side_effect = datetime.strptime
            mock_dt.combine.side_effect = datetime.combine

            next_event, _ = scraper.find_next_event_and_summary(mock_summarized_events)

            assert next_event is not None
            assert next_event["fixture"] == expected_fixture

    def test_no_future_events(self, scraper):
        """Test the case where there are no future events left in the list."""
        past_events = [
            {
                "date": "2025-01-01",
                "events": [{"fixture": "Past Event", "start_time": "15:00"}],
                "earliest_start": "15:00",
            }
        ]

        mocked_now = datetime(2025, 9, 1, 12, 0, 0)
        with patch("twickenham_events.scraper.datetime", autospec=True) as mock_dt:
            mock_dt.now.return_value = mocked_now
            mock_dt.strptime.side_effect = datetime.strptime

            next_event, next_day_summary = scraper.find_next_event_and_summary(
                past_events
            )
            assert next_event is None
            assert next_day_summary is None
