#!/usr/bin/env python3
"""MQTT Validation Script - Test scraping, discovery, and MQTT publishing."""

import json
from pathlib import Path

from ha_mqtt_publisher import MQTTPublisher as LibMQTTPublisher

from src.twickenham_events.ai_processor import AIProcessor
from src.twickenham_events.config import Config
from src.twickenham_events.enhanced_discovery import publish_enhanced_device_discovery
from src.twickenham_events.mqtt_client import MQTTClient
from src.twickenham_events.scraper import EventScraper

print("🔍 MQTT VALIDATION SCRIPT")
print("=" * 50)

# 1. SCRAPING TEST
print("\n1️⃣ SCRAPING TEST")
print("-" * 20)
try:
    config = Config.from_file("config/config.yaml")
    scraper = EventScraper(config)
    url = config.get("scraping.url")

    print(f"Scraping from: {url}")
    raw_events, stats = scraper.scrape_events(url)
    print(f"✅ Raw events found: {len(raw_events)}")

    # Process events
    summarized_events = scraper.summarize_events(raw_events)
    print(f"✅ Future events: {len(summarized_events)}")

    # Save to output for MQTT test
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    # Create flat events list for MQTT
    flat_events = []
    for day_events in summarized_events:
        flat_events.extend(day_events.get("events", []))

    data = {"events": flat_events, "event_count": len(flat_events)}
    with open(output_dir / "upcoming_events.json", "w") as f:
        json.dump(data, f, indent=2)

    print(f"✅ Events saved to output/upcoming_events.json: {len(flat_events)} events")

except Exception as e:
    print(f"❌ Scraping failed: {e}")
    exit(1)

# 2. MQTT PUBLISHING TEST
print("\n2️⃣ MQTT PUBLISHING TEST")
print("-" * 25)
try:
    # Load events from file
    with open(output_dir / "upcoming_events.json") as f:
        data = json.load(f)
    events = data.get("events", [])

    print(f"Publishing {len(events)} events to MQTT...")

    # Initialize AI processor and MQTT client
    ai_processor = AIProcessor(config)
    mqtt_client = MQTTClient(config)

    # Publish events
    mqtt_client.publish_events(events, ai_processor)
    print("✅ Events published to MQTT successfully")

except Exception as e:
    print(f"❌ MQTT publishing failed: {e}")

# 3. DISCOVERY TEST
print("\n3️⃣ DISCOVERY TEST")
print("-" * 18)
try:
    AVAILABILITY_TOPIC = "twickenham_events/availability"
    cfg = config.get_mqtt_config()

    # Clean up undefined TLS certificate paths for ha-mqtt-publisher
    if "tls" in cfg and isinstance(cfg["tls"], dict):
        tls_cfg = cfg["tls"].copy()
        # Remove certificate file paths if they're undefined env vars
        for cert_key in ["ca_cert", "client_cert", "client_key"]:
            if cert_key in tls_cfg:
                cert_path = tls_cfg[cert_key]
                if isinstance(cert_path, str) and cert_path.startswith("${"):
                    # Remove undefined environment variable references
                    del tls_cfg[cert_key]
        cfg = cfg.copy()
        cfg["tls"] = tls_cfg

    publisher = LibMQTTPublisher(**cfg)

    print("Testing device bundle discovery...")
    result = publish_enhanced_device_discovery(
        mqtt_client=publisher,
        config=config,
        availability_topic=AVAILABILITY_TOPIC,
        include_event_count_component=True,
    )
    print(f"✅ Discovery published successfully: {result}")

except Exception as e:
    print(f"❌ Discovery failed: {e}")

print("\n🎯 VALIDATION COMPLETE")
print("=" * 50)
print("Check your MQTT Explorer and Home Assistant for:")
print("- Event topics under twickenham_events/")
print("- Device discovery under homeassistant/device/")
print("- Status and availability topics")
