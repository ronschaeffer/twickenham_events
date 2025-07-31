# tests/test_end_to_end.py

import pytest
from unittest.mock import MagicMock, patch, call
import json
from core.twick_event import process_and_publish_events, find_next_event_and_summary
from core.config import Config
from datetime import datetime

# --- Test Data ---

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
        'home_assistant': {'enabled': False},
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
def test_process_and_publish_events_successful(mock_mqtt_publisher, mock_config):
    """
    Verifies that when there are events and no errors, the script publishes
    the correct payloads to all the event-related MQTT topics.
    """
    # Arrange
    mock_publisher_instance = MagicMock()
    mock_mqtt_publisher.return_value.__enter__.return_value = mock_publisher_instance

    # Act
    process_and_publish_events(
        SAMPLE_SUMMARIZED_EVENTS, mock_publisher_instance, mock_config)

    # Assert
    assert mock_publisher_instance.publish.call_count == 5

    next_event, next_day_summary = find_next_event_and_summary(
        SAMPLE_SUMMARIZED_EVENTS, mock_config)

    # Create a dictionary of actual published topics and payloads
    actual_published_data = {}
    for call_args in mock_publisher_instance.publish.call_args_list:
        topic = call_args.args[0]
        payload_str = call_args.args[1]
        try:
            actual_published_data[topic] = json.loads(payload_str)
        except (json.JSONDecodeError, TypeError):
            actual_published_data[topic] = payload_str

    # Verify event payloads (checking structure and content, ignoring timestamp)
    assert actual_published_data['test/events/all_upcoming']['events'] == SAMPLE_SUMMARIZED_EVENTS
    assert actual_published_data['test/events/next_day_summary']['summary'] == next_day_summary
    assert actual_published_data['test/events/next']['event'] == next_event

    # Verify status payloads
    status_topic = 'test/events/status'
    attributes_topic = f"{status_topic}/attributes"
    assert actual_published_data[status_topic] == 'ok'
    attributes = actual_published_data[attributes_topic]
    assert attributes['status'] == 'ok'
    assert attributes['event_count'] == 2
    assert attributes['error_count'] == 0
    assert attributes['errors'] == []
    # Check for timestamp existence and basic format
    assert 'last_updated' in attributes
    assert isinstance(attributes['last_updated'], str)


@patch('core.twick_event.MQTTPublisher')
def test_process_and_publish_events_with_errors(mock_mqtt_publisher, mock_config):
    """
    Verifies that when parsing errors are present, the error payload is
    correctly constructed and published to the status topic, and that
    event-related topics receive empty payloads.
    """
    # Arrange
    mock_publisher_instance = MagicMock()
    mock_mqtt_publisher.return_value.__enter__.return_value = mock_publisher_instance

    # Make a copy of the global error_log to avoid modifying it directly
    with patch('core.twick_event.error_log', list(SAMPLE_ERRORS)):
        # Act
        process_and_publish_events(
            [], mock_publisher_instance, mock_config)

    # Assert
    assert mock_publisher_instance.publish.call_count == 5

    # Create a dictionary of actual published topics and payloads
    actual_published_data = {}
    for call_args in mock_publisher_instance.publish.call_args_list:
        topic = call_args.args[0]
        payload_str = call_args.args[1]
        try:
            actual_published_data[topic] = json.loads(payload_str)
        except (json.JSONDecodeError, TypeError):
            actual_published_data[topic] = payload_str

    # Verify event payloads
    assert actual_published_data['test/events/all_upcoming']['events'] == []
    assert actual_published_data['test/events/next_day_summary']['summary'] is None
    assert actual_published_data['test/events/next']['event'] is None

    # Verify status payloads
    status_topic = 'test/events/status'
    attributes_topic = f"{status_topic}/attributes"
    assert actual_published_data[status_topic] == 'error'
    attributes = actual_published_data[attributes_topic]
    assert attributes['status'] == 'error'
    assert attributes['event_count'] == 0
    assert attributes['error_count'] == 2
    assert attributes['errors'] == SAMPLE_ERRORS
    assert 'last_updated' in attributes
    assert isinstance(attributes['last_updated'], str)


@patch('core.twick_event.MQTTPublisher')
def test_process_and_publish_events_no_upcoming_events(mock_mqtt_publisher, mock_config):
    """
    Verifies that when there are no upcoming events, the correct payloads
    are published, indicating no events are scheduled.
    """
    # Arrange
    mock_publisher_instance = MagicMock()
    mock_mqtt_publisher.return_value.__enter__.return_value = mock_publisher_instance

    # Act
    process_and_publish_events(
        [], mock_publisher_instance, mock_config)

    # Assert
    assert mock_publisher_instance.publish.call_count == 5

    # Create a dictionary of actual published topics and payloads
    actual_published_data = {}
    for call_args in mock_publisher_instance.publish.call_args_list:
        topic = call_args.args[0]
        payload_str = call_args.args[1]
        try:
            actual_published_data[topic] = json.loads(payload_str)
        except (json.JSONDecodeError, TypeError):
            actual_published_data[topic] = payload_str

    # Verify event payloads
    assert actual_published_data['test/events/all_upcoming']['events'] == []
    assert actual_published_data['test/events/next_day_summary']['summary'] is None
    assert actual_published_data['test/events/next']['event'] is None

    # Verify status payloads
    status_topic = 'test/events/status'
    attributes_topic = f"{status_topic}/attributes"
    assert actual_published_data[status_topic] == 'ok'
    attributes = actual_published_data[attributes_topic]
    assert attributes['status'] == 'ok'
    assert attributes['event_count'] == 0
    assert attributes['error_count'] == 0
    assert attributes['errors'] == []
    assert 'last_updated' in attributes
    assert isinstance(attributes['last_updated'], str)
