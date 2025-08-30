"""
Basic tests for Flights CLI functionality.

Adapted from twickenham_events testing patterns.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from flights.config import Config
from flights.scraper import FlightScraper
from flights.mqtt_client import FlightMQTTClient


def test_config_defaults():
    """Test that default configuration works."""
    config = Config.from_defaults()
    
    assert config.get("flights.api_enabled") is True
    assert config.get("flights.tracking_enabled") is True
    assert config.get("mqtt.enabled") is False
    assert config.get("mqtt.broker") == "localhost"


def test_flight_scraper_mock_data():
    """Test flight scraper generates mock data."""
    config = Config.from_defaults()
    scraper = FlightScraper(config)
    
    flights = scraper.scrape_flights()
    
    assert len(flights) > 0
    assert all("flight_number" in flight for flight in flights)
    assert all("type" in flight for flight in flights)
    assert all(flight["type"] in ["departure", "arrival"] for flight in flights)


def test_flight_summarization():
    """Test flight data summarization."""
    config = Config.from_defaults()
    scraper = FlightScraper(config)
    
    flights = scraper.scrape_flights()
    summary = scraper.summarize_flights(flights)
    
    assert "total_flights" in summary
    assert "departures" in summary
    assert "arrivals" in summary
    assert "by_status" in summary
    assert summary["total_flights"] == len(flights)


def test_next_flight_detection():
    """Test finding the next upcoming flight."""
    config = Config.from_defaults()
    scraper = FlightScraper(config)
    
    flights = scraper.scrape_flights()
    next_flight = scraper.find_next_flight(flights)
    
    # With mock data, we should always have a next flight
    assert next_flight is not None
    assert "flight_number" in next_flight


def test_mqtt_client_disabled():
    """Test MQTT client when MQTT is disabled."""
    config = Config.from_defaults()
    # Ensure MQTT is disabled in test config
    config._data["mqtt"]["enabled"] = False
    
    mqtt_client = FlightMQTTClient(config)
    
    # Should return True (success) when disabled
    result = mqtt_client.publish_flights([])
    assert result is True


@pytest.mark.parametrize("output_format", ["detailed", "simple", "json"])
def test_list_formats(output_format):
    """Test different list output formats."""
    config = Config.from_defaults()
    scraper = FlightScraper(config)
    
    flights = scraper.scrape_flights()
    
    # This would be tested with CLI argument parsing in a full implementation
    # For now, just verify we have the data structure needed
    assert len(flights) > 0
    
    if output_format == "json":
        # Verify JSON serializable
        json_str = json.dumps(flights)
        assert json_str is not None
        
    # For detailed and simple formats, the formatting would happen in CLI layer


def test_config_file_loading():
    """Test loading configuration from file."""
    config_data = {
        "flights": {
            "api_enabled": True,
            "tracking_enabled": False
        },
        "mqtt": {
            "enabled": True,
            "broker": "test-broker"
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        import yaml
        yaml.dump(config_data, f)
        config_file = f.name
    
    try:
        config = Config.from_file(config_file)
        
        assert config.get("flights.api_enabled") is True
        assert config.get("flights.tracking_enabled") is False
        assert config.get("mqtt.enabled") is True
        assert config.get("mqtt.broker") == "test-broker"
        
    finally:
        os.unlink(config_file)


def test_mqtt_config_generation():
    """Test MQTT configuration generation."""
    config = Config.from_defaults()
    config._data["mqtt"]["enabled"] = True
    config._data["mqtt"]["broker"] = "test-broker"
    config._data["mqtt"]["port"] = 8883
    
    mqtt_config = config.get_mqtt_config()
    
    assert mqtt_config["broker_host"] == "test-broker"
    assert mqtt_config["broker_port"] == 8883


if __name__ == "__main__":
    pytest.main([__file__])