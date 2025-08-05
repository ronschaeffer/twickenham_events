from datetime import datetime
import json
from pathlib import Path
import sys

from dotenv import load_dotenv
from mqtt_publisher.publisher import MQTTPublisher

from core.config import Config
from core.ha_mqtt_discovery import publish_discovery_configs
from core.twick_event import (
    error_log,
    fetch_events,
    find_next_event_and_summary,
    process_and_publish_events,
    summarise_events,
)
from core.version import get_dynamic_version

# Add project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))


def update_dynamic_version():
    """Update ha_entities.yaml with current Git-based version."""
    try:
        import re

        from core.version import get_dynamic_version

        ha_entities_path = Path(__file__).parent.parent / "config" / "ha_entities.yaml"

        if ha_entities_path.exists():
            current_version = get_dynamic_version()

            with open(ha_entities_path) as f:
                content = f.read()

            # Update sw_version line
            updated_content = re.sub(
                r'(\s*sw_version:"0.1.0"\']?[^"\'\n]*["\']?',
                rf'\1"{current_version}"',
                content,
            )

            with open(ha_entities_path, "w") as f:
                f.write(updated_content)

            print(f"📝 Updated device version to: {current_version}")
    except Exception as e:
        print(f"⚠️ Could not update dynamic version: {e}")


def load_previous_events(output_dir: Path) -> list[dict[str, str]]:
    """Load previously successful event data as fallback."""
    try:
        with open(output_dir / "upcoming_events.json") as f:
            previous_data = json.load(f)
            return previous_data.get("events", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def publish_error_status(
    config: Config, timestamp: str, processing_stats: dict | None = None
) -> None:
    """Publish error status when website is unavailable."""
    if not config.get("mqtt.enabled"):
        return

    try:
        mqtt_config = config.get_mqtt_config()
        with MQTTPublisher(**mqtt_config) as publisher:
            # Publish Home Assistant discovery configs first
            if config.get("home_assistant.enabled"):
                publish_discovery_configs(config, publisher)

            # Publish error status with enhanced metrics
            status_payload = {
                "status": "error",
                "last_updated": timestamp,
                "event_count": 0,
                "error_count": len(error_log),
                "errors": error_log,
                "website_status": "unavailable",
            }

            # Add processing metrics if available
            if processing_stats:
                status_payload["metrics"] = {
                    "raw_events_found": processing_stats.get("raw_events_count", 0),
                    "processed_events": 0,
                    "events_filtered": 0,
                    "fetch_duration_seconds": processing_stats.get("fetch_duration", 0),
                    "retry_attempts_used": processing_stats.get("retry_attempts", 0),
                    "data_source": processing_stats.get("data_source", "error"),
                }

            # Publish empty events to clear old data
            empty_events_payload = {"last_updated": timestamp, "events": []}
            publisher.publish(
                config.get("mqtt.topics.all_upcoming"),
                empty_events_payload,
                retain=True,
            )
            publisher.publish(
                config.get("mqtt.topics.next"),
                {"last_updated": timestamp, "event": None, "date": None},
                retain=True,
            )

            # Publish status
            publisher.publish(
                config.get("mqtt.topics.status"), status_payload, retain=True
            )
            print("✅ Published error status to MQTT")

    except Exception as e:
        print(f"❌ Failed to publish error status: {e}")


def load_environment():
    """
    Load environment variables using hierarchical loading pattern.
    Follows mqtt_publisher best practices for multi-project workspaces.
    """
    try:
        # Load shared environment first (if exists)
        parent_env = Path(__file__).parent.parent.parent / ".env"
        if parent_env.exists():
            load_dotenv(parent_env, verbose=False)

        # Load project-specific environment second (overrides shared)
        project_env = Path(__file__).parent.parent / ".env"
        if project_env.exists():
            load_dotenv(project_env, override=True, verbose=False)

    except ImportError:
        print("⚠️  python-dotenv not installed. Install with: poetry add python-dotenv")


def main():
    """
    Main function to run the Twickenham event scraper and publisher.
    """
    # Simple version check without argparse to avoid Poetry script issues
    if len(sys.argv) > 1 and sys.argv[1] == "--version":
        print(get_dynamic_version())
        return 0

    # Load environment variables using best practices
    load_environment()

    # --- Configuration ---
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    config = Config(config_path=str(config_path))
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)

    # --- Timestamp for all files ---
    timestamp = datetime.now().isoformat()

    # --- Fetch and Process Events ---
    raw_events, processing_stats = fetch_events(config.get("scraping.url"), config)

    # Write parsing errors to JSON file immediately after fetch
    errors_path = output_dir / "event_processing_errors.json"
    with open(errors_path, "w") as f:
        json.dump({"last_updated": timestamp, "errors": error_log}, f, indent=4)

    if error_log:
        print(f"Found {len(error_log)} parsing errors. Details in {errors_path}")

    if not raw_events:
        print("❌ No events found or failed to fetch events.")

        # Try to load previous data as fallback
        previous_events = load_previous_events(output_dir)
        if previous_events:
            print(
                f"📁 Using {len(previous_events)} events from previous successful run"
            )
            summarized_events = previous_events

            # Update processing stats for fallback data
            processing_stats["data_source"] = "previous_run"

            # Update JSON with previous data but new timestamp
            upcoming_events_path = output_dir / "upcoming_events.json"
            with open(upcoming_events_path, "w") as f:
                json.dump(
                    {
                        "last_updated": timestamp,
                        "events": summarized_events,
                        "data_source": "previous_run",
                    },
                    f,
                    indent=4,
                )
            print(f"📝 Updated timestamp for {len(summarized_events)} previous events")

        else:
            print("📁 No previous data available")
            summarized_events = []
            processing_stats["data_source"] = "no_data"

        # Always publish status to MQTT, even on failure
        publish_error_status(config, timestamp, processing_stats)

        # If no data at all, exit early
        if not summarized_events:
            return
    else:
        # Successfully fetched fresh events
        print(f"✅ Successfully fetched {len(raw_events)} raw events")
        summarized_events = summarise_events(raw_events, config)

    # --- Output ---
    # Write upcoming events to JSON file (only if we have new data)
    if raw_events:  # Only write if we have fresh data
        upcoming_events_path = output_dir / "upcoming_events.json"
        with open(upcoming_events_path, "w") as f:
            json.dump(
                {"last_updated": timestamp, "events": summarized_events}, f, indent=4
            )
        print(
            f"📝 Successfully wrote {len(summarized_events)} upcoming event days to {upcoming_events_path}"
        )

    # --- MQTT Publishing ---
    if config.get("mqtt.enabled"):
        try:
            # Get MQTT configuration using best practices from mqtt_publisher
            mqtt_config = config.get_mqtt_config()

            with MQTTPublisher(**mqtt_config) as publisher:
                # Update device version with Git-based versioning
                if config.get("home_assistant.enabled"):
                    update_dynamic_version()

                # Publish Home Assistant discovery configs
                if config.get("home_assistant.enabled"):
                    publish_discovery_configs(config, publisher)

                # Publish event data with processing stats
                process_and_publish_events(
                    summarized_events, publisher, config, processing_stats
                )
                print("Successfully published events to MQTT.")

        except ValueError as e:
            # Configuration validation errors
            print(f"MQTT Configuration Error: {e}")
            print("Check your config.yaml and environment variables.")

        except ConnectionError as e:
            # Connection-specific errors with helpful hints
            try:
                mqtt_config = config.get_mqtt_config()
                port = mqtt_config.get("broker_port", 1883)
                tls_enabled = bool(mqtt_config.get("tls"))

                print(f"MQTT Connection Failed: {e}")

                # Provide specific guidance based on configuration
                if tls_enabled and port == 1883:
                    print(
                        "💡 Hint: TLS is enabled but using port 1883. Try port 8883 for TLS."
                    )
                elif not tls_enabled and port == 8883:
                    print(
                        "💡 Hint: Port 8883 is typically for TLS. Try port 1883 or enable TLS."
                    )
                else:
                    print(
                        f"💡 Check: Broker URL, port {port}, and network connectivity."
                    )
            except Exception:
                print(f"MQTT Connection Failed: {e}")

        except Exception as e:
            print(f"Failed to publish to MQTT: {e}")

    # --- Console Output ---
    # Find the next event and summary
    next_event, next_day_summary = find_next_event_and_summary(
        summarized_events, config
    )

    print("\n" + "=" * 30)
    print("    UPCOMING EVENT SUMMARY")
    print("=" * 30 + "\n")

    print("--- Next Event ---")
    if next_event and next_day_summary:
        print(f"  Date:         {next_day_summary.get('date')}")
        print(f"  Fixture:      {next_event.get('fixture')}")
        print(f"  Start Time:   {next_event.get('start_time', 'TBC')}")
        print(f"  Crowd:        {next_event.get('crowd', 'TBC')}")
    else:
        print("  No upcoming events found.")

    print("\n--- All Upcoming Events ---")
    if summarized_events:
        for day in summarized_events:
            print(f"\n  Date: {day['date']}")
            for event in day["events"]:
                # Type: ignore to suppress false positive type checking errors
                print(f"    - Fixture:      {event['fixture']}")  # type: ignore
                print(f"      Start Time:   {event.get('start_time', 'TBC')}")  # type: ignore
                print(f"      Crowd:        {event.get('crowd', 'TBC')}")  # type: ignore
    else:
        print("  No upcoming events found.")
    print("\n" + "=" * 30)


if __name__ == "__main__":
    main()
