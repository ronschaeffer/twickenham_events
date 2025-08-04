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

# Add project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))


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
    raw_events = fetch_events(config.get("scraping.url"))

    # Write parsing errors to JSON file immediately after fetch
    errors_path = output_dir / "event_processing_errors.json"
    with open(errors_path, "w") as f:
        json.dump({"last_updated": timestamp, "errors": error_log}, f, indent=4)

    if error_log:
        print(f"Found {len(error_log)} parsing errors. Details in {errors_path}")

    if not raw_events:
        print("No events found or failed to fetch events.")
        return

    summarized_events = summarise_events(raw_events, config)

    # --- Output ---
    # Write upcoming events to JSON file
    upcoming_events_path = output_dir / "upcoming_events.json"
    with open(upcoming_events_path, "w") as f:
        json.dump({"last_updated": timestamp, "events": summarized_events}, f, indent=4)
    print(
        f"Successfully wrote {len(summarized_events)} upcoming event days to {upcoming_events_path}"
    )

    # --- MQTT Publishing ---
    if config.get("mqtt.enabled"):
        try:
            # Get MQTT configuration using best practices from mqtt_publisher
            mqtt_config = config.get_mqtt_config()

            with MQTTPublisher(**mqtt_config) as publisher:
                # Publish Home Assistant discovery configs
                if config.get("home_assistant.enabled"):
                    publish_discovery_configs(config, publisher)

                # Publish event data
                process_and_publish_events(summarized_events, publisher, config)
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
                print(f"    - Fixture:      {event['fixture']}")
                print(f"      Start Time:   {event.get('start_time', 'TBC')}")
                print(f"      Crowd:        {event.get('crowd', 'TBC')}")
    else:
        print("  No upcoming events found.")
    print("\n" + "=" * 30)


if __name__ == "__main__":
    main()
