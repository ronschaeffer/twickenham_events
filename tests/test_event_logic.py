from core.config import Config
from core.twick_event import find_next_event_and_summary
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, date, time, timedelta

# Add project root to the Python path to allow importing from 'core'
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# --- Mock Data ---

MOCK_SUMMARIZED_EVENTS = [
    {
        "date": "2025-08-01",
        "events": [
            {"fixture": "Concert", "start_time": "15:00", "crowd": "70,000"},
            {"fixture": "Late Show", "start_time": "20:00", "crowd": "70,000"}
        ],
        "earliest_start": "15:00"
    },
    {
        "date": "2025-08-03",
        "events": [
            {"fixture": "Rugby Match", "start_time": "14:00", "crowd": "82,000"}
        ],
        "earliest_start": "14:00"
    }
]

# --- Test Cases ---


@pytest.mark.parametrize("current_time_str, expected_fixture", [
    # --- Scenarios for August 1, 2025 ---
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
    # --- Scenarios for August 2, 2025 (a day with no events) ---
    # The next event is still the one on Aug 3.
    ("2025-08-02 10:00:00", "Rugby Match"),
])
def test_find_next_event_logic(current_time_str, expected_fixture):
    """
    Tests the find_next_event_and_summary function with various mocked times.
    """
    # Mock the config object with our rules
    mock_config = MagicMock(spec=Config)
    mock_config.get.side_effect = lambda key, default=None: {
        'event_rules.end_of_day_cutoff': '23:00',
        'event_rules.next_event_delay_hours': 1
    }.get(key, default)

    # Mock datetime.now() to return our specified test time
    mocked_now = datetime.strptime(current_time_str, '%Y-%m-%d %H:%M:%S')
    with patch('core.twick_event.datetime', autospec=True) as mock_dt:
        # Configure the mock to behave like the real datetime object
        mock_dt.now.return_value = mocked_now
        mock_dt.strptime.side_effect = datetime.strptime
        mock_dt.combine.side_effect = datetime.combine

        next_event, _ = find_next_event_and_summary(
            MOCK_SUMMARIZED_EVENTS, mock_config)

        assert next_event is not None
        assert next_event['fixture'] == expected_fixture


def test_no_future_events():
    """
    Tests the case where there are no future events left in the list.
    """
    mock_config = MagicMock(spec=Config)
    mock_config.get.side_effect = lambda key, default=None: {
        'event_rules.end_of_day_cutoff': '23:00',
        'event_rules.next_event_delay_hours': 1
    }.get(key, default)

    mocked_now = datetime(2025, 9, 1, 12, 0, 0)
    with patch('core.twick_event.datetime', autospec=True) as mock_dt:
        mock_dt.now.return_value = mocked_now
        mock_dt.strptime.side_effect = datetime.strptime

        next_event, next_day_summary = find_next_event_and_summary(
            MOCK_SUMMARIZED_EVENTS, mock_config)

        assert next_event is None
        assert next_day_summary is None
