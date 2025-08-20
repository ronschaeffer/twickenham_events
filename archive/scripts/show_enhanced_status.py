#!/usr/bin/env python3
"""
Simulate enhanced status payload to see the structure
"""

from datetime import datetime
import json
from pathlib import Path
import sys

# Add to path
sys.path.append(str(Path(__file__).parent))

from core.config import Config
from core.twick_event import error_log, fetch_events, summarise_events

# Load config
config = Config("config/config.yaml")

# Fetch and process events
raw_events, processing_stats = fetch_events(config.get("scraping.url"), config)
summarized_events = summarise_events(raw_events, config) if raw_events else []

# Simulate the enhanced status payload (same logic as in process_and_publish_events)
timestamp = datetime.now().isoformat()
errors = error_log

status_payload = {
    "status": "ok" if not errors else "error",
    "last_updated": timestamp,
    "event_count": len(summarized_events),
    "error_count": len(errors),
    "errors": errors,
}

# Add processing metrics
if processing_stats:
    status_payload["metrics"] = {
        "raw_events_found": processing_stats.get("raw_events_count", 0),
        "processed_events": len(summarized_events),
        "events_filtered": processing_stats.get("raw_events_count", 0)
        - len(summarized_events),
        "fetch_duration_seconds": processing_stats.get("fetch_duration", 0),
        "retry_attempts_used": processing_stats.get("retry_attempts", 0),
        "data_source": processing_stats.get("data_source", "live"),
    }

# Add system info
config_path = getattr(config, "config_path", None)
status_payload["system_info"] = {
    "app_version": "0.1.0",
    "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    "config_source": str(Path(config_path).name) if config_path else "unknown",
}

print("🚀 Enhanced MQTT Status Payload:")
print("=" * 50)
print(json.dumps(status_payload, indent=2))
print("=" * 50)
print(
    f"📊 Summary: {status_payload['event_count']} events, {status_payload['metrics']['retry_attempts_used']} attempts, {status_payload['metrics']['fetch_duration_seconds']:.2f}s"
)
