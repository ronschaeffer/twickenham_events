#!/usr/bin/env python3
"""
Test the fresh discovery implementation directly
"""

from core.config import Config
from core.discovery import publish_twickenham_discovery
from mqtt_publisher.publisher import MQTTPublisher

# Load config
config = Config("config/config.yaml")

# Create MQTT publisher for discovery
mqtt_config = config.get_mqtt_config()

print("🧪 Testing fresh discovery implementation...")
print(f"Config loaded: {config.get('app.name', 'Unknown')}")

with MQTTPublisher(**mqtt_config) as publisher:
    print("📡 Connected to MQTT broker")
    publish_twickenham_discovery(config, publisher)
    print("✅ Discovery test completed")
