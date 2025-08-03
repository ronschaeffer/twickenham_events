from datetime import datetime
import json
from pathlib import Path
import sys

from dotenv import load_dotenv

from core.config import Config
from core.ha_mqtt_discovery import publish_discovery_configs
from core.mqtt_publisher import MQTTPublisher
from core.twick_event import (
    error_log,
    fetch_events,
    find_next_event_and_summary,
    process_and_publish_events,
    summarise_events,
)

# Add project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))


def main():
    """
    Main function to run the Twickenham event scraper and publisher.
    """
    # Load environment variables from .env file
    load_dotenv()

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
            with MQTTPublisher(
                broker_url=config.get("mqtt.broker_url"),
                broker_port=config.get("mqtt.broker_port"),
                client_id=config.get("mqtt.client_id", "twickenham_event_publisher"),
                security=config.get("mqtt.security", "none"),
                auth=config.get("mqtt.auth"),
                tls=config.get("mqtt.tls"),
            ) as publisher:
                # Publish Home Assistant discovery configs
                if config.get("home_assistant.enabled"):
                    publish_discovery_configs(config, publisher)

                # Publish event data
                process_and_publish_events(summarized_events, publisher, config)
                print("Successfully published events to MQTT.")
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
