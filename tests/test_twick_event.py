from datetime import date, datetime
from pathlib import Path
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

from core.config import Config
from core.twick_event import (
    fetch_events,
    find_next_event_and_summary,
    normalize_date_range,
    normalize_time,
    summarise_events,
    validate_crowd_size,
)

sys.path.append(str(Path(__file__).parent.parent))


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
    }.get(key, default)
    return mock


@patch("requests.get")
def test_fetch_events_success(mock_get, mock_response_success):
    """Test successful event fetching and parsing."""
    mock_get.return_value = mock_response_success
    events, stats = fetch_events("http://fakeurl.com")
    assert len(events) == 3
    assert events[0]["title"] == "Past Event"
    assert events[1]["title"] == "Future Event 1"
    assert events[2]["time"] == "TBC"

    # Test the new stats functionality
    assert stats["data_source"] == "live"
    assert stats["raw_events_count"] == 3
    assert stats["retry_attempts"] == 1
    assert "fetch_duration" in stats


@patch("requests.get")
def test_fetch_events_no_table(mock_get, mock_response_no_table):
    """Test fetching when no event table is present."""
    mock_get.return_value = mock_response_no_table
    events, stats = fetch_events("http://fakeurl.com")
    assert len(events) == 0

    # Test stats for empty response
    assert stats["data_source"] == "live"
    assert stats["raw_events_count"] == 0


def test_summarise_events_filters_past_events(mock_config):
    """Test that summarise_events correctly filters out past events."""
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
    with patch("core.twick_event.datetime") as mock_datetime:
        mock_datetime.now.return_value.date.return_value = date(2025, 7, 31)
        # We need to make sure that strptime is not mocked
        mock_datetime.strptime = datetime.strptime
        with patch("core.twick_event.get_short_name") as mock_shortener:
            # Mock the shortener to return original name (disabled behavior)
            mock_shortener.return_value = ("original_name", False, "")
            summarized = summarise_events(raw_events, mock_config)
            assert len(summarized) == 2
            assert summarized[0]["date"] == "2025-09-27"
            assert summarized[1]["date"] == "2025-10-04"


def test_find_next_event_and_summary(mock_config):
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
    with patch("core.twick_event.datetime", autospec=True) as mock_datetime:
        mock_datetime.now.return_value = datetime(2025, 7, 31, 12, 0, 0)
        # The original strptime needs to be used, not the mock
        mock_datetime.strptime = datetime.strptime
        mock_datetime.combine = datetime.combine

        next_event, next_day_summary = find_next_event_and_summary(
            summarized_events, mock_config
        )
        assert next_event is not None
        assert next_event["fixture"] == "Future Event 1"
        assert next_day_summary is not None
        assert next_day_summary["date"] == "2025-09-27"


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
        # Enhanced US date formats from ICS Utils
        ("Dec 20, 2024", "2024-12-20"),
        ("December 20, 2024", "2024-12-20"),
        ("Jan 15, 2025", "2025-01-15"),
        ("February 28, 2025", "2025-02-28"),
        ("Mar 5, 2024", "2024-03-05"),
        ("November 30, 2023", "2023-11-30"),
    ],
)
def test_normalize_date_range(input_date, expected):
    assert normalize_date_range(input_date) == expected


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
def test_normalize_time(input_time, expected):
    assert normalize_time(input_time) == expected


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
    ],
)
def test_validate_crowd_size(input_crowd, expected):
    assert validate_crowd_size(input_crowd) == expected
