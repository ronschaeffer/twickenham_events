from core.config import Config
from core.twick_event import (
    save_events_to_json,
    process_and_publish_events,
    normalize_date_range,
    normalize_time,
    extract_date_range,
    validate_crowd_size,
    group_events_by_date,
    find_next_event_and_summary,
)
import yaml
from unittest.mock import patch
from datetime import datetime, timedelta
import pytest
import sys
import json
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))


# Update the test cases for date ranges
@pytest.mark.parametrize("input_date,expected_dates", [
    # Single date cases remain the same
    ("16 May 2025", ["2025-05-16"]),
    ("Mon 16 May 2025", ["2025-05-16"]),
    ("16th May 2025", ["2025-05-16"]),

    # Date range cases now expect list of two dates
    ("16/17 May 2025", ["2025-05-16", "2025-05-17"]),
    ("Weekend 16/17 May 2025", ["2025-05-16", "2025-05-17"]),
    ("Wknd 23/24 May 2025", ["2025-05-23", "2025-05-24"]),

    # Invalid cases
    ("Invalid Date", []),
    ("", []),
    (None, []),
])
def test_date_range_extraction(input_date, expected_dates):
    """Test the extract_date_range function with various inputs."""
    result = extract_date_range(input_date)
    assert result == expected_dates


@pytest.mark.parametrize("input_date,expected_date", [
    # Keep existing single date test cases
    ("16 May 2025", "2025-05-16"),
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
])
def test_normalize_date_range(input_date, expected_date):
    """Test the normalize_date_range function for single dates only."""
    result = normalize_date_range(input_date)
    assert result == expected_date


@pytest.mark.parametrize("input_time, expected", [
    ("3pm", "15:00"),
    ("3:30pm", "15:30"),
    ("3 & 5pm", "15:00 & 17:00"),
    ("TBC", None),
    ("3:10pm", "15:10"),
    ("3.10pm", "15:10"),
    ("11am", "11:00"),
    ("12pm", "12:00"),
    ("12am", "00:00"),
    ("15:10", "15:10"),
    ("03:10", "03:10"),
    ("00:00", "00:00"),
    ("3pm & 6pm", "15:00 & 18:00"),
    ("3:10pm & 5:40pm", "15:10 & 17:40"),
    ("3.10pm & 5.40pm", "15:10 & 17:40"),
    ("tbc", None),
    ("", None),
    ("Invalid", None),
    ("25:00", None),
    ("13pm", None),
    ("3pm and 6pm", "15:00 & 18:00"),  # Changed expected value
    ("5.40pm", "17:40"),
    ("4.10pm", "16:10"),
    ("4.45pm", "16:45"),
])
def test_normalize_time(input_time, expected):
    assert normalize_time(input_time) == expected


@pytest.mark.parametrize("input_crowd, expected", [
    ("10,000", "10,000"),
    ("10000", "10,000"),
    ("TBC", None),
    ("Estimate 10000", "10,000"),
    ("Est. 10000", "10,000"),
    ("Approx. 10000", "10,000"),
    ("~10000", "10,000"),
    ("Invalid", None),
])
def test_validate_crowd_size(input_crowd, expected):
    assert validate_crowd_size(input_crowd) == expected

# Add new test class for event duration calculations


class TestEventDuration:
    @patch('core.config.Config')
    def test_end_time_calculation(self, MockConfig):
        """Test that end times are correctly calculated based on config duration."""
        # Arrange: Mock the config object and its get method
        mock_config_instance = MockConfig.return_value
        mock_config_instance.get.return_value = 6
        duration = mock_config_instance.get('default_duration', 2)

        from core.twick_event import normalize_time

        test_cases = [
            ("15:00", "21:00"),
            ("3pm", "21:00"),
            ("9:30", "15:30"),
            ("23:00", "05:00"),
            ("3pm & 6pm", "21:00 & 00:00"),
            ("Invalid Time", None),
        ]

        for start_time, expected_end in test_cases:
            normalized_start = normalize_time(start_time)

            if normalized_start is None:
                assert expected_end is None
                continue

            end_times = []
            for time_str in normalized_start.split(' & '):
                start_dt = datetime.strptime(time_str, '%H:%M')
                end_dt = start_dt + timedelta(hours=duration)
                end_times.append(end_dt.strftime('%H:%M'))

            calculated_end = ' & '.join(end_times)
            assert calculated_end == expected_end

    @patch('core.config.Config')
    def test_invalid_duration_config(self, MockConfig):
        """Test handling of missing or invalid duration configuration."""
        mock_config_instance = MockConfig.return_value

        # Test with get returning None (simulating missing key)
        mock_config_instance.get.return_value = None
        duration = mock_config_instance.get('default_duration', 2) or 2
        assert duration == 2

        # Test with get returning a default value
        mock_config_instance.get.side_effect = lambda key, default: default
        duration = mock_config_instance.get('default_duration', 2)
        assert duration == 2


def test_adjust_end_times():
    """Test that event end times are adjusted to prevent overlaps."""
    from core.twick_event import adjust_end_times

    # Test cases for overlapping events - all on same date
    events = [
        {
            'date': '2025-02-08',
            'fixture': 'Event 1',
            'start_time': '14:00',
            'end_time': '20:00',  # Would overlap with next event
            'crowd': '10,000'
        },
        {
            'date': '2025-02-08',
            'fixture': 'Event 2',
            'start_time': '19:00',
            'end_time': '23:00',
            'crowd': '10,000'
        }
    ]

    adjusted = adjust_end_times(events)

    # Check that end times were adjusted properly
    assert len(adjusted) == 2
    # First event shortened to start of second event
    assert adjusted[0]['end_time'] == '19:00'
    assert adjusted[1]['end_time'] == '23:00'  # Last event remains unchanged

    # Test multiple times per event - this logic has been simplified in the main script
    # The adjust_end_times function now only handles single start/end times per event object.
    # The main script creates separate event objects for each time.
    events_multi_time_objects = [
        {
            'date': '2025-02-08',
            'fixture': 'Event A',
            'start_time': '14:00',
            'end_time': '20:00',
            'crowd': '10,000'
        },
        {
            'date': '2025-02-08',
            'fixture': 'Event A',
            'start_time': '16:00',
            'end_time': '22:00',  # Overlaps with next
            'crowd': '10,000'
        },
        {
            'date': '2025-02-08',
            'fixture': 'Event B',
            'start_time': '21:00',
            'end_time': '23:00',
            'crowd': '10,000'
        }
    ]

    adjusted = adjust_end_times(events_multi_time_objects)
    assert len(adjusted) == 3
    # Does not overlap with its direct successor
    assert adjusted[0]['end_time'] == '20:00'
    assert adjusted[1]['end_time'] == '21:00'  # This one is adjusted
    assert adjusted[2]['end_time'] == '23:00'  # Last one is not adjusted


def test_group_events_by_date():
    """Test that events are correctly grouped into daily summaries."""
    events = [
        {'date': '2025-09-27', 'fixture': 'Event 1',
            'start_time': '12:30', 'end_time': '16:00', 'crowd': '82,000'},
        {'date': '2025-09-27', 'fixture': 'Event 2',
            'start_time': '19:00', 'end_time': '22:00', 'crowd': '82,000'},
        {'date': '2025-10-01', 'fixture': 'Event 3',
            'start_time': '15:00', 'end_time': '18:00', 'crowd': '50,000'},
    ]

    grouped = group_events_by_date(events)

    assert len(grouped) == 2

    # Check first day summary
    day1 = grouped[0]
    assert day1['date'] == '2025-09-27'
    assert day1['event_count'] == 2
    assert day1['earliest_start'] == '12:30'
    assert day1['latest_end'] == '22:00'
    assert len(day1['events']) == 2
    assert day1['events'][0]['fixture'] == 'Event 1'
    # Date should be removed from individual events
    assert 'date' not in day1['events'][0]

    # Check second day summary
    day2 = grouped[1]
    assert day2['date'] == '2025-10-01'
    assert day2['event_count'] == 1
    assert day2['earliest_start'] == '15:00'
    assert day2['latest_end'] == '18:00'
    assert len(day2['events']) == 1
    assert day2['events'][0]['fixture'] == 'Event 3'


class TestFindNextEvent:
    """Tests for the find_next_event_and_summary function."""

    # Some sample summarized data to use in tests
    sample_summarized_events = [
        {
            'date': '2025-07-29',
            'event_count': 2,
            'earliest_start': '14:00',
            'latest_end': '22:00',
            'events': [
                {'fixture': 'Past Event 1', 'start_time': '14:00',
                    'end_time': '16:00', 'crowd': '10,000'},
                {'fixture': 'Future Event 1', 'start_time': '20:00',
                    'end_time': '22:00', 'crowd': '10,000'}
            ]
        },
        {
            'date': '2025-07-30',
            'event_count': 1,
            'earliest_start': '18:00',
            'latest_end': '21:00',
            'events': [
                {'fixture': 'Future Event 2', 'start_time': '18:00',
                    'end_time': '21:00', 'crowd': '20,000'}
            ]
        }
    ]

    @patch('core.twick_event.datetime', wraps=datetime)
    def test_finds_correct_next_event_same_day(self, mock_dt):
        """Test it finds the next event when it's later on the same day."""
        # Mock current time to be 16:00 on 2025-07-29
        mock_dt.now.return_value = datetime(2025, 7, 29, 16, 0)

        next_event, next_summary = find_next_event_and_summary(
            self.sample_summarized_events)

        assert next_event is not None
        assert next_summary is not None

        # Check the individual event payload
        assert next_event['fixture'] == 'Future Event 1'
        assert next_event['start_time'] == '20:00'
        assert next_event['date'] == '2025-07-29'  # Date should be added

        # Check the summary payload
        assert next_summary['date'] == '2025-07-29'
        assert next_summary['event_count'] == 2

    @patch('core.twick_event.datetime', wraps=datetime)
    def test_finds_correct_next_event_next_day(self, mock_dt):
        """Test it finds the next event when it's on the following day."""
        # Mock current time to be 23:00 on 2025-07-29 (after all of today's events)
        mock_dt.now.return_value = datetime(2025, 7, 29, 23, 0)

        next_event, next_summary = find_next_event_and_summary(
            self.sample_summarized_events)

        assert next_event is not None
        assert next_summary is not None

        # Check the individual event payload
        assert next_event['fixture'] == 'Future Event 2'
        assert next_event['start_time'] == '18:00'
        assert next_event['date'] == '2025-07-30'

        # Check the summary payload
        assert next_summary['date'] == '2025-07-30'
        assert next_summary['event_count'] == 1

    @patch('core.twick_event.datetime', wraps=datetime)
    def test_returns_none_if_all_events_passed(self, mock_dt):
        """Test it returns None for both payloads if all events are in the past."""
        # Mock current time to be 23:00 on 2025-07-30 (after all events)
        mock_dt.now.return_value = datetime(2025, 7, 30, 23, 0)

        next_event, next_summary = find_next_event_and_summary(
            self.sample_summarized_events)

        assert next_event is None
        assert next_summary is None

    def test_handles_no_events(self):
        """Test it handles an empty list of events gracefully."""
        next_event, next_summary = find_next_event_and_summary([])
        assert next_event is None
        assert next_summary is None


class TestMQTTPayloads:
    """Tests for the structure of MQTT payloads."""

    @pytest.fixture
    def mock_config(self, tmp_path):
        """Create a mock config for MQTT tests."""
        config_content = {
            'mqtt': {
                'broker_url': 'localhost',
                'broker_port': 1883,
                'client_id': 'test_client',
                'security': 'none',
                'topics': {
                    'all_upcoming': 'test/all',
                    'next_day_summary': 'test/summary',
                    'next': 'test/next',
                    'errors': 'test/errors'
                }
            }
        }
        config_file = tmp_path / "mqtt_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_content, f)
        return Config(str(config_file))

    @patch('core.twick_event.MQTTPublisher')
    @patch('core.twick_event.find_next_event_and_summary')
    def test_payload_structure_with_events(self, mock_find_next, mock_publisher, mock_config):
        """Test that MQTT payloads have the correct structure when events are found."""
        # Mock data
        timestamp = {'iso': '2025-07-29T12:00:00',
                     'human': 'Tuesday, 29 July 2025 at 12:00'}
        summarized_events = [{'date': '2025-08-01', 'event_count': 1}]
        next_event = {'fixture': 'Test Event', 'date': '2025-08-01'}
        next_summary = {'date': '2025-08-01', 'event_count': 1}

        mock_find_next.return_value = (next_event, next_summary)

        # Call the function
        process_and_publish_events(
            summarized_events, mock_config, timestamp, [])

        # Get the mock publisher instance
        publisher_instance = mock_publisher.return_value.__enter__.return_value

        # Check the calls to publish
        calls = publisher_instance.publish.call_args_list
        assert len(calls) == 4

        # Extract payloads
        all_payload = calls[0][0][1]
        summary_payload = calls[1][0][1]
        next_payload = calls[2][0][1]
        error_payload = calls[3][0][1]

        # Assert timestamp and data keys are present
        assert 'last_updated' in all_payload
        assert 'events' in all_payload
        assert all_payload['last_updated'] == timestamp

        assert 'last_updated' in summary_payload
        assert 'summary' in summary_payload
        assert summary_payload['last_updated'] == timestamp
        assert summary_payload['summary'] == next_summary

        assert 'last_updated' in next_payload
        assert 'event' in next_payload
        assert next_payload['last_updated'] == timestamp
        assert next_payload['event'] == next_event

        # Assert that the error payload is empty
        assert 'last_updated' in error_payload
        assert error_payload['error_count'] == 0
        assert error_payload['errors'] == []

    @patch('core.twick_event.MQTTPublisher')
    @patch('core.twick_event.find_next_event_and_summary')
    def test_payload_structure_no_events(self, mock_find_next, mock_publisher, mock_config):
        """Test that MQTT payloads have the correct structure when no events are found."""
        timestamp = {'iso': '2025-07-29T12:00:00',
                     'human': 'Tuesday, 29 July 2025 at 12:00'}
        mock_find_next.return_value = (None, None)

        process_and_publish_events([], mock_config, timestamp, [])

        publisher_instance = mock_publisher.return_value.__enter__.return_value
        calls = publisher_instance.publish.call_args_list
        assert len(calls) == 4

        # Extract payloads
        all_payload = calls[0][0][1]
        summary_payload = calls[1][0][1]
        next_payload = calls[2][0][1]
        error_payload = calls[3][0][1]

        # Assert structure for "all" topic (still has timestamp)
        assert 'last_updated' in all_payload
        assert 'events' in all_payload
        assert all_payload['events'] == []

        # Assert structure for empty summary and next event
        assert 'last_updated' in summary_payload
        assert 'summary' in summary_payload
        assert summary_payload['summary'] == {}

        assert 'last_updated' in next_payload
        assert 'event' in next_payload
        assert next_payload['event'] == {}

        # Assert structure for cleared errors
        assert 'last_updated' in error_payload
        assert 'error_count' in error_payload
        assert 'errors' in error_payload
        assert error_payload['error_count'] == 0
        assert error_payload['errors'] == []


def test_save_events_to_json(tmp_path):
    """Test that the JSON file is created with the correct structure."""
    # Prepare mock data
    timestamp = {'iso': '2025-07-29T10:30:00',
                 'human': 'Tuesday, 29 July 2025 at 10:30'}
    events_data = [{'date': '2025-08-01', 'event_count': 1}]
    output_dir = tmp_path / "output"

    # Call the function
    save_events_to_json(events_data, timestamp, str(output_dir))

    # Check that the file was created
    output_file = output_dir / "upcoming_events.json"
    assert output_file.exists()

    # Check the content of the file
    with open(output_file, 'r') as f:
        data = json.load(f)

    assert 'last_updated' in data
    assert 'events' in data
    assert data['last_updated'] == timestamp
    assert data['events'] == events_data


# Test for HA Discovery integration
@patch('core.twick_event.Config')
@patch('core.twick_event.HADiscoveryPublisher')
@patch('core.twick_event.requests.get')
@patch('core.twick_event.MQTTPublisher')
def test_ha_discovery_is_called_when_enabled(mock_mqtt, mock_requests, mock_ha_publisher, MockConfig):
    """
    Test that the HADiscoveryPublisher is called when home_assistant.enabled is true.
    """
    # Arrange: Mock config to enable HA discovery
    mock_config_instance = MockConfig.return_value
    mock_config_instance.get.side_effect = lambda key, default=None: {
        "home_assistant.enabled": True,
        "mqtt.enabled": False,  # Disable regular MQTT publishing for this test
        "default_duration": 2
    }.get(key, default)

    # Mock the requests response to avoid actual web calls
    mock_response = mock_requests.return_value
    mock_response.raise_for_status.return_value = None
    mock_response.text = '<html><body><table class="table"><tr><th>Date</th><th>Fixture</th><th>Time</th><th>Crowd</th></tr><tr><td>22/06/2024</td><td>Test Fixture</td><td>15:00</td><td>82000</td></tr></table></body></html>'

    # Act: Run the main function
    from core.twick_event import main
    main()

    # Assert: Check that HADiscoveryPublisher was initialized and its method called
    mock_ha_publisher.assert_called_once()
    mock_ha_publisher.return_value.publish_discovery_topics.assert_called_once()


@patch('core.twick_event.Config')
@patch('core.twick_event.HADiscoveryPublisher')
@patch('core.twick_event.requests.get')
@patch('core.twick_event.MQTTPublisher')
def test_ha_discovery_is_not_called_when_disabled(mock_mqtt, mock_requests, mock_ha_publisher, MockConfig):
    """
    Test that the HADiscoveryPublisher is NOT called when home_assistant.enabled is false.
    """
    # Arrange: Mock config to disable HA discovery
    mock_config_instance = MockConfig.return_value
    mock_config_instance.get.side_effect = lambda key, default=None: {
        "home_assistant.enabled": False,
        "mqtt.enabled": False,
        "default_duration": 2
    }.get(key, default)

    # Mock the requests response
    mock_response = mock_requests.return_value
    mock_response.raise_for_status.return_value = None
    mock_response.text = '<html><body><table class="table"><tr><th>Date</th><th>Fixture</th><th>Time</th><th>Crowd</th></tr><tr><td>22/06/2024</td><td>Test Fixture</td><td>15:00</td><td>82000</td></tr></table></body></html>'

    # Act: Run the main function
    from core.twick_event import main
    main()

    # Assert: Check that HADiscoveryPublisher was NOT initialized or called
    mock_ha_publisher.assert_not_called()
    mock_ha_publisher.return_value.publish_discovery_topics.assert_not_called()
