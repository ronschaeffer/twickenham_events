#!/usr/bin/env python3
"""
MQTT Status Inspector - Check what enhanced status looks like
"""

import json

from mqtt_publisher.publisher import MQTTPublisher

from core.config import Config
from core.twick_event import fetch_events, process_and_publish_events, summarise_events

# Load config
config = Config("config/config.yaml")


# Create a custom publisher that captures what we send
class DebugMQTTPublisher(MQTTPublisher):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.published_messages = []

    def publish(self, topic, payload, qos=0, retain=False):
        self.published_messages.append(
            {"topic": topic, "payload": payload, "retain": retain}
        )
        return super().publish(topic, payload, qos, retain)


# Fetch and process events
raw_events, processing_stats = fetch_events(config.get("scraping.url"), config)
summarized_events = summarise_events(raw_events, config) if raw_events else []

# Create debug publisher
mqtt_config = config.get_mqtt_config()
with DebugMQTTPublisher(**mqtt_config) as publisher:
    process_and_publish_events(summarized_events, publisher, config, processing_stats)

    # Show what was published to status topic
    for msg in publisher.published_messages:
        if "status" in msg["topic"]:
            print("🚀 Enhanced Status Payload:")
            print(json.dumps(msg["payload"], indent=2))
            break
