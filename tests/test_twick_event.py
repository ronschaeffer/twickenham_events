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


#         publisher_instance = mock_publisher
        calls = publisher_instance.publish.call_args_list
        assert len(calls) == 5

        # Extract payloads
        status_payload = calls[0][0][1]
        attributes_payload = json.loads(calls[1][0][1])
        all_payload = json.loads(calls[2][0][1])
        summary_payload = json.loads(calls[3][0][1])
        next_payload = json.loads(calls[4][0][1])

        # Assert status payloads
        assert status_payload == "OFF"
        assert attributes_payload['error_count'] == 0
        assert attributes_payload['events_found'] is True
        assert attributes_payload['last_updated'] == timestamp['iso']

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

    @patch('core.twick_event.MQTTPublisher')
    @patch('core.twick_event.find_next_event_and_summary')
    def test_payload_structure_no_events(self, mock_find_next, mock_publisher, mock_config):
        """Test that MQTT payloads have the correct structure when no events are found."""
        timestamp = {'iso': '2025-07-29T12:00:00',
                     'human': 'Tuesday, 29 July 2025 at 12:00'}
        mock_find_next.return_value = (None, None)

        process_and_publish_events(
            [], mock_config, timestamp, [], mock_publisher)

        publisher_instance = mock_publisher
        calls = publisher_instance.publish.call_args_list
        assert len(calls) == 5

        # Extract payloads
        status_payload = calls[0][0][1]
        attributes_payload = json.loads(calls[1][0][1])
        all_payload = json.loads(calls[2][0][1])
        summary_payload = json.loads(calls[3][0][1])
        next_payload = json.loads(calls[4][0][1])

        # Assert status payloads
        assert status_payload == "OFF"
        assert attributes_payload['error_count'] == 0
        assert attributes_payload['events_found'] is False
        assert attributes_payload['last_updated'] == timestamp['iso']


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
@patch('core.twick_event.publish_discovery_configs')
@patch('core.twick_event.requests.get')
@patch('core.twick_event.MQTTPublisher')
def test_ha_discovery_is_called_when_enabled(mock_mqtt, mock_requests, mock_publish_discovery, MockConfig):
    """
    Test that the publish_discovery_configs function is called when home_assistant.enabled is true.
    """
    # Arrange: Mock config to enable HA discovery
    mock_config_instance = MockConfig.return_value
    mock_config_instance.get.side_effect = lambda key, default=None: {
        'mqtt.enabled': True,
        'home_assistant.enabled': True
    }.get(key, default)

    # Mock requests to avoid actual web calls
    mock_requests.return_value.status_code = 200
    mock_requests.return_value.text = '<html><body><table>...</table></body></html>'

    # Act
    from core.twick_event import main
    main()

    # Assert: Check that the discovery publisher was called
    mock_publish_discovery.assert_called_once()


# Test for HA Discovery integration
@patch('core.twick_event.Config')
@patch('core.twick_event.publish_discovery_configs')
@patch('core.twick_event.requests.get')
@patch('core.twick_event.MQTTPublisher')
def test_ha_discovery_is_not_called_when_disabled(mock_mqtt, mock_requests, mock_publish_discovery, MockConfig):
    """
    Test that the publish_discovery_configs is NOT called when home_assistant.enabled is false.
    """
    # Arrange: Mock config to disable HA discovery
    mock_config_instance = MockConfig.return_value
    mock_config_instance.get.side_effect = lambda key, default=None: {
        'mqtt.enabled': True,
        'home_assistant.enabled': False
    }.get(key, default)

    # Mock requests to avoid actual web calls
    mock_requests.return_value.status_code = 200
    mock_requests.return_value.text = '<html><body><table>...</table></body></html>'

    # Act
    from core.twick_event import main
    main()

    # Assert: Check that the discovery publisher was NOT called
    mock_publish_discovery.assert_not_called()
