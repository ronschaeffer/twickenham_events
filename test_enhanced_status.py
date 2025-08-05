#!/usr/bin/env python3
"""
Quick test to verify enhanced status payload structure
"""

import json

from core.config import Config
from core.twick_event import fetch_events, summarise_events

# Load config
config = Config("config/config.yaml")

# Fetch events with stats
raw_events, processing_stats = fetch_events(config.get("scraping.url"), config)

print("🔍 Processing Stats:")
print(json.dumps(processing_stats, indent=2))

if raw_events:
    summarized_events = summarise_events(raw_events, config)
    print(f"\n📊 Events Summary:")
    print(f"  Raw events found: {processing_stats.get('raw_events_count', 0)}")
    print(f"  Processed events: {len(summarized_events)}")
    print(
        f"  Events filtered: {processing_stats.get('raw_events_count', 0) - len(summarized_events)}"
    )
    print(f"  Fetch duration: {processing_stats.get('fetch_duration', 0):.2f}s")
    print(f"  Retry attempts: {processing_stats.get('retry_attempts', 0)}")
    print(f"  Data source: {processing_stats.get('data_source', 'unknown')}")
