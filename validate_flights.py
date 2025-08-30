#!/usr/bin/env python3
"""
Simple validation script for Flights CLI functionality.

Tests basic functionality without external dependencies.
"""

import json
import sys
import tempfile
from pathlib import Path

# Add the src directory to the path to import flights module
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flights.config import Config
from flights.scraper import FlightScraper
from flights.mqtt_client import FlightMQTTClient


def test_config_defaults():
    """Test that default configuration works."""
    print("Testing default configuration...")
    config = Config.from_defaults()
    
    assert config.get("flights.api_enabled") is True
    assert config.get("flights.tracking_enabled") is True
    assert config.get("mqtt.enabled") is False
    assert config.get("mqtt.broker") == "localhost"
    print("✅ Default configuration test passed")


def test_flight_scraper():
    """Test flight scraper generates mock data."""
    print("Testing flight scraper...")
    config = Config.from_defaults()
    scraper = FlightScraper(config)
    
    flights = scraper.scrape_flights()
    
    assert len(flights) > 0
    assert all("flight_number" in flight for flight in flights)
    assert all("type" in flight for flight in flights)
    assert all(flight["type"] in ["departure", "arrival"] for flight in flights)
    print(f"✅ Flight scraper test passed - found {len(flights)} flights")


def test_flight_summary():
    """Test flight data summarization."""
    print("Testing flight summarization...")
    config = Config.from_defaults()
    scraper = FlightScraper(config)
    
    flights = scraper.scrape_flights()
    summary = scraper.summarize_flights(flights)
    
    assert "total_flights" in summary
    assert "departures" in summary
    assert "arrivals" in summary
    assert "by_status" in summary
    assert summary["total_flights"] == len(flights)
    print("✅ Flight summarization test passed")


def test_next_flight():
    """Test finding the next upcoming flight.""" 
    print("Testing next flight detection...")
    config = Config.from_defaults()
    scraper = FlightScraper(config)
    
    flights = scraper.scrape_flights()
    next_flight = scraper.find_next_flight(flights)
    
    # With mock data, we should always have a next flight
    assert next_flight is not None
    assert "flight_number" in next_flight
    print(f"✅ Next flight test passed - found {next_flight['flight_number']}")


def test_mqtt_client():
    """Test MQTT client when disabled."""
    print("Testing MQTT client (disabled)...")
    config = Config.from_defaults()
    # Ensure MQTT is disabled in test config
    config._data["mqtt"]["enabled"] = False
    
    mqtt_client = FlightMQTTClient(config)
    
    # Should return True (success) when disabled
    result = mqtt_client.publish_flights([])
    assert result is True
    print("✅ MQTT client test passed")


def test_json_serialization():
    """Test JSON serialization of flight data."""
    print("Testing JSON serialization...")
    config = Config.from_defaults()
    scraper = FlightScraper(config)
    
    flights = scraper.scrape_flights()
    
    # Verify JSON serializable
    json_str = json.dumps(flights, indent=2)
    assert json_str is not None
    
    # Verify we can parse it back
    parsed_flights = json.loads(json_str)
    assert len(parsed_flights) == len(flights)
    print("✅ JSON serialization test passed")


def test_config_file():
    """Test loading configuration from file."""
    print("Testing config file loading...")
    
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
    
    import yaml
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_file = f.name
    
    try:
        config = Config.from_file(config_file)
        
        assert config.get("flights.api_enabled") is True
        assert config.get("flights.tracking_enabled") is False
        assert config.get("mqtt.enabled") is True
        assert config.get("mqtt.broker") == "test-broker"
        print("✅ Config file loading test passed")
        
    finally:
        import os
        os.unlink(config_file)


def main():
    """Run all tests."""
    print("🧪 Running Flights CLI validation tests...\n")
    
    try:
        test_config_defaults()
        test_flight_scraper()
        test_flight_summary()
        test_next_flight()
        test_mqtt_client()
        test_json_serialization()
        test_config_file()
        
        print("\n🎉 All tests passed! Flights CLI is working correctly.")
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())