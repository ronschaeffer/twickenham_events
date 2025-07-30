# tests/test_end_to_end.py

import pytest
from unittest.mock import MagicMock, patch, call
from core.twick_event import process_and_publish_events, find_next_event_and_summary
from core.config import Config
from datetime import datetime
import json

# --- Test Data ---

# A timestamp to use for test data, ensuring consistency.
SAMPLE_TIMESTAMP = {'iso': '2025-07-30T10:00:00',
                    'human': 'Wednesday, 30 July 2025 at 10:00'}

# Sample data representing successfully parsed and summarized events.
SAMPLE_SUMMARIZED_EVENTS = [
    {
        'date': '2025-08-15',
        'event_count': 1,
        'earliest_start': '19:00',
        'latest_end': '21:00',
        'events': [
            {
                'fixture': 'Test Event 1',
                'start_time': '19:00',
                'end_time': '21:00',
                'crowd': '10,000'
            }
        ]
    },
    {
        'date': '2025-09-01',
        'event_count': 1,
        'earliest_start': '15:00',
        'latest_end': '17:00',
        'events': [
            {
                'fixture': 'Test Event 2',
                'start_time': '15:00',
                'end_time': '17:00',
                'crowd': '20,000'
            }
        ]
    }
]

# Sample list of parsing errors.
SAMPLE_ERRORS = ["Failed to parse date: 'Invalid Date'",
                 "Invalid crowd size: 'TBC'"]


# --- Fixtures ---

@pytest.fixture
def mock_config():
    """
    Provides a mock Config object for tests, isolating them from the actual
    config.yaml file and ensuring predictable test runs.
    """
    config_data = {
        'mqtt': {
            'broker_url': 'mock_broker',
            'broker_port': 1883,
            'client_id': 'test_client',
            'security': 'none',
            'auth': None,
            'tls': None,
            'topics': {
                'next': 'test/events/next',
                'next_day_summary': 'test/events/next_day_summary',
                'all_upcoming': 'test/events/all_upcoming',
                'status': 'test/events/status'
            }
        }
    }
    # The Config class is initialized with a dictionary directly,
    # bypassing the need to read a file from disk.
    return Config(config_data=config_data)


# --- Tests ---

@patch('core.twick_event.MQTTPublisher')
@patch('core.twick_event.datetime')
def test_process_and_publish_events_successful(mock_datetime, mock_mqtt_publisher, mock_config):
    """
    Verifies that when there are events and no errors, the script publishes
    the correct payloads to all the event-related MQTT topics.
    """
    # Arrange
    # Mock datetime.now() to control the "current" time for the test.
    mock_datetime.now.return_value = datetime(2025, 8, 1)
    # The strptime method needs to be preserved so that the function under
    # test can still parse date strings into datetime objects.
    mock_datetime.strptime = datetime.strptime

    # Create a mock instance of the MQTTPublisher.
    mock_publisher_instance = MagicMock()
    # Configure the mock so that when it's used as a context manager,
    # it returns our mock instance.
    mock_mqtt_publisher.return_value.__enter__.return_value = mock_publisher_instance

    # Act
    # Call the function under test with our sample data.
    process_and_publish_events(
        SAMPLE_SUMMARIZED_EVENTS, mock_config, SAMPLE_TIMESTAMP, [], mock_publisher_instance)

    # Assert
    # The function should publish to 3 event topics, plus the status topic and its attributes.
    assert mock_publisher_instance.publish.call_count == 5

    # Define the expected payloads for each topic.
    next_event, next_day_summary = find_next_event_and_summary(
        SAMPLE_SUMMARIZED_EVENTS)

    # Expected payloads for the event topics
    expected_event_payloads = {
        'test/events/all_upcoming': {'last_updated': SAMPLE_TIMESTAMP, 'events': SAMPLE_SUMMARIZED_EVENTS},
        'test/events/next_day_summary': {'last_updated': SAMPLE_TIMESTAMP, 'summary': next_day_summary},
        'test/events/next': {'last_updated': SAMPLE_TIMESTAMP, 'event': next_event},
    }

    # Expected payloads for the status topic
    expected_status_payload = "OFF"
    expected_attributes_payload = {
        'last_updated': SAMPLE_TIMESTAMP['iso'],
        'error_count': 0,
        'errors': [],
        'events_found': True,
        'last_success': SAMPLE_TIMESTAMP['iso'],
        'last_error': None
    }

    # Create a dictionary of actual published topics and payloads for easy lookup.
    actual_published_data = {
        call.args[0]: call.args[1] for call in mock_publisher_instance.publish.call_args_list
    }

    # Verify that each event topic received the correct JSON payload.
    for topic, payload in expected_event_payloads.items():
        assert topic in actual_published_data
        assert json.loads(actual_published_data[topic]) == payload

    # Verify the status topic payloads
    status_topic = 'test/events/status'
    attributes_topic = f"{status_topic}/attributes"
    assert status_topic in actual_published_data
    assert actual_published_data[status_topic] == expected_status_payload
    assert attributes_topic in actual_published_data
    assert json.loads(
        actual_published_data[attributes_topic]) == expected_attributes_payload


@patch('core.twick_event.MQTTPublisher')
def test_process_and_publish_events_with_errors(mock_mqtt_publisher, mock_config):
    """
    Verifies that when parsing errors are present, the error payload is
    correctly constructed and published to the errors topic, and that
    event-related topics receive empty payloads.
    """
    # Arrange
    mock_publisher_instance = MagicMock()
    mock_mqtt_publisher.return_value.__enter__.return_value = mock_publisher_instance

    # Act
    # Call the function with empty events and a list of sample errors.
    process_and_publish_events(
        [], mock_config, SAMPLE_TIMESTAMP, SAMPLE_ERRORS, mock_publisher_instance)

    # Assert
    # Check that the publisher was called for the 3 event topics, plus the status topic and its attributes.
    assert mock_publisher_instance.publish.call_count == 5

    # Define the expected payloads for event topics in an error scenario.
    expected_event_payloads = {
        'test/events/all_upcoming': {'last_updated': SAMPLE_TIMESTAMP, 'events': []},
        'test/events/next_day_summary': {'last_updated': SAMPLE_TIMESTAMP, 'summary': {}},
        'test/events/next': {'last_updated': SAMPLE_TIMESTAMP, 'event': {}},
    }

    # Define the expected payloads for the status topic in an error scenario.
    expected_status_payload = "ON"
    expected_attributes_payload = {
        'last_updated': SAMPLE_TIMESTAMP['iso'],
        'error_count': len(SAMPLE_ERRORS),
        'errors': SAMPLE_ERRORS,
        'events_found': False,
        'last_success': None,
        'last_error': SAMPLE_TIMESTAMP['iso']
    }

    # Create a dictionary of actual calls for easy lookup.
    actual_published_data = {
        call.args[0]: call.args[1] for call in mock_publisher_instance.publish.call_args_list
    }

    # Verify the payload of all event topics.
    for topic, payload in expected_event_payloads.items():
        assert topic in actual_published_data
        assert json.loads(actual_published_data[topic]) == payload

    # Verify the status topic payloads
    status_topic = 'test/events/status'
    attributes_topic = f"{status_topic}/attributes"
    assert status_topic in actual_published_data
    assert actual_published_data[status_topic] == expected_status_payload
    assert attributes_topic in actual_published_data
    assert json.loads(
        actual_published_data[attributes_topic]) == expected_attributes_payload
