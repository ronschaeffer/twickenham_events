import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional  # noqa: UP035

from dotenv import load_dotenv
from mqtt_publisher.publisher import MQTTPublisher

from core.config import Config
from core.ha_mqtt_discovery import publish_discovery_configs_for_twickenham
from core.ics_export import generate_ics_calendar, get_calendar_url
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


def load_previous_events(output_dir: Path) -> List[Dict[str, str]]:  # noqa: UP006
    """Load previously successful event data as fallback."""
    try:
        with open(output_dir / "upcoming_events.json") as f:
            previous_data = json.load(f)
            return previous_data.get("events", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def publish_error_status(
    config: Config,
    timestamp: str,
    processing_stats: Optional[Dict[str, Any]] = None,  # noqa: UP006
) -> None:
    """Publish error status when website is unavailable."""
    if not config.get("mqtt.enabled"):
        return

    try:
        mqtt_config = config.get_mqtt_config()
        with MQTTPublisher(**mqtt_config) as publisher:
            # Publish Home Assistant discovery configs first
            if config.get("home_assistant.enabled"):
                publish_discovery_configs_for_twickenham(config, publisher)

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


def setup_argument_parser() -> argparse.ArgumentParser:
    """Set up command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Twickenham Events scraper and publisher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  twick-events scrape              # Scrape events only
  twick-events mqtt               # Scrape and publish to MQTT
  twick-events calendar           # Scrape and generate calendar
  twick-events all                # Run all integrations (default)
  twick-events status             # Show configuration status
  twick-events --version          # Show version information
        """,
    )

    parser.add_argument("--version", action="version", version=get_dynamic_version())
    parser.add_argument("--config", type=str, help="path to configuration file")
    parser.add_argument("--debug", action="store_true", help="enable debug output")

    subparsers = parser.add_subparsers(dest="command", help="available commands")

    # Scrape command
    scrape_parser = subparsers.add_parser(
        "scrape", help="scrape events and save to output directory"
    )
    scrape_parser.add_argument("--output", help="custom output directory")

    # MQTT command
    mqtt_parser = subparsers.add_parser(
        "mqtt", help="scrape events and publish to MQTT"
    )
    mqtt_parser.add_argument("--output", help="custom output directory")

    # Calendar command
    calendar_parser = subparsers.add_parser(
        "calendar", help="scrape events and generate calendar"
    )
    calendar_parser.add_argument("--output", help="custom output directory")

    # All command (default behavior)
    all_parser = subparsers.add_parser(
        "all", help="run all integrations (scrape + MQTT + calendar)"
    )
    all_parser.add_argument("--output", help="custom output directory")

    # Status command
    subparsers.add_parser("status", help="show configuration and system status")

    return parser


def main():
    """
    Main function to run the Twickenham event scraper and publisher.
    """
    # Parse command line arguments
    parser = setup_argument_parser()
    args = parser.parse_args()

    # If no command specified, default to 'all'
    if args.command is None:
        args.command = "all"

    # Load environment variables using best practices
    load_environment()

    try:
        # Setup configuration
        if args.config:
            config_path = Path(args.config)
        else:
            config_path = Path(__file__).parent.parent / "config" / "config.yaml"

        config = Config(config_path=str(config_path))

        # Setup output directory
        if args.output:
            output_dir = Path(args.output)
        else:
            output_dir = Path(__file__).parent.parent / "output"
        output_dir.mkdir(exist_ok=True)

        # Route to appropriate command
        if args.command == "scrape":
            return cmd_scrape(config, output_dir, args)
        elif args.command == "mqtt":
            return cmd_mqtt(config, output_dir, args)
        elif args.command == "calendar":
            return cmd_calendar(config, output_dir, args)
        elif args.command == "all":
            return cmd_all(config, output_dir, args)
        elif args.command == "status":
            return cmd_status(config, args)
        else:
            parser.print_help()
            return 1

    except Exception as e:
        print(f"❌ Command failed: {e}")
        if args.debug:
            import traceback

            traceback.print_exc()
        return 1


def cmd_scrape(config: Config, output_dir: Path, args) -> int:
    """Scrape events and save to output directory."""
    print("\n\033[93m🌐 EVENT SCRAPING\033[0m")
    print("\033[93m" + "─" * 15 + "\033[0m")

    # Timestamp for all files
    timestamp = datetime.now().isoformat()

    # Fetch and process events
    raw_events, processing_stats = fetch_events(config.get("scraping.url"), config)

    # Write parsing errors
    errors_path = output_dir / "event_processing_errors.json"
    with open(errors_path, "w") as f:
        json.dump({"last_updated": timestamp, "errors": error_log}, f, indent=4)

    if error_log:
        print(
            f"\033[33m⚠️  Found {len(error_log)} parsing errors. Details in \033[36m{errors_path}\033[0m"
        )

    if not raw_events:
        print("\033[31m❌ No events found or failed to fetch events.\033[0m")

        # Try fallback
        previous_events = load_previous_events(output_dir)
        if previous_events:
            print(
                f"📁 Using \033[33m{len(previous_events)}\033[0m events from previous successful run"
            )
            summarized_events = previous_events
        else:
            print("📁 No previous data available")
            return 1
    else:
        print(f"✅ Successfully fetched \033[32m{len(raw_events)}\033[0m raw events")
        summarized_events = summarise_events(raw_events, config)

    # Save to JSON
    upcoming_events_path = output_dir / "upcoming_events.json"
    with open(upcoming_events_path, "w") as f:
        json.dump({"last_updated": timestamp, "events": summarized_events}, f, indent=4)

    print(
        f"📝 Successfully wrote \033[36m{len(summarized_events)}\033[0m upcoming event days to \033[33m{upcoming_events_path}\033[0m"
    )
    return 0


def cmd_mqtt(config: Config, output_dir: Path, args) -> int:
    """Scrape events and publish to MQTT."""
    # First scrape the data
    scrape_result = cmd_scrape(config, output_dir, args)
    if scrape_result != 0:
        return scrape_result

    # Load the scraped data
    upcoming_events_path = output_dir / "upcoming_events.json"
    try:
        with open(upcoming_events_path) as f:
            event_data = json.load(f)
        summarized_events = event_data.get("events", [])
    except Exception as e:
        print(f"❌ Failed to load scraped data: {e}")
        return 1

    if not config.get("mqtt.enabled"):
        print("❌ MQTT is not enabled in configuration")
        return 1

    print("\n\033[94m📡 MQTT PUBLISHING\033[0m")
    print("\033[94m" + "─" * 15 + "\033[0m")

    try:
        mqtt_config = config.get_mqtt_config()
        with MQTTPublisher(**mqtt_config) as publisher:
            # Publish Home Assistant discovery configs
            if config.get("home_assistant.enabled"):
                publish_discovery_configs_for_twickenham(config, publisher)
                print("✅ Published Home Assistant discovery configs")

            # Process and publish events
            processing_stats = {"data_source": "live"}
            process_and_publish_events(
                summarized_events, publisher, config, processing_stats
            )
            print("✅ Successfully published events to MQTT")

        return 0
    except Exception as e:
        print(f"❌ MQTT publishing failed: {e}")
        return 1


def cmd_calendar(config: Config, output_dir: Path, args) -> int:
    """Scrape events and generate calendar."""
    # First scrape the data
    scrape_result = cmd_scrape(config, output_dir, args)
    if scrape_result != 0:
        return scrape_result

    # Load the scraped data
    upcoming_events_path = output_dir / "upcoming_events.json"
    try:
        with open(upcoming_events_path) as f:
            event_data = json.load(f)
        summarized_events = event_data.get("events", [])
    except Exception as e:
        print(f"❌ Failed to load scraped data: {e}")
        return 1

    if not config.get("calendar.enabled"):
        print("❌ Calendar generation is not enabled in configuration")
        return 1

    print("\n\033[95m📅 CALENDAR GENERATION\033[0m")
    print("\033[95m" + "─" * 20 + "\033[0m")

    try:
        ics_result, ics_path = generate_ics_calendar(
            summarized_events, config, output_dir
        )

        if ics_result and ics_path:
            event_count = ics_result.get("stats", {}).get("total_events", 0)
            print(
                f"✅ Generated ICS calendar with {event_count} events: \033[33m{ics_path}\033[0m"
            )

            # Show calendar URL if available
            calendar_url = get_calendar_url(config)
            if calendar_url:
                print(f"🔗 Calendar URL: {calendar_url}")

            return 0
        else:
            print("❌ Failed to generate calendar")
            return 1
    except Exception as e:
        print(f"❌ Calendar generation failed: {e}")
        return 1


def cmd_all(config: Config, output_dir: Path, args) -> int:
    """Run all integrations (scrape + MQTT + calendar)."""
    results = []

    # 1. Scrape events
    scrape_result = cmd_scrape(config, output_dir, args)
    results.append(("Scraping", "✅" if scrape_result == 0 else "❌"))

    if scrape_result != 0:
        print("\n\033[31m❌ Scraping failed - skipping other integrations\033[0m")
        return scrape_result

    # 2. MQTT publishing (if enabled)
    if config.get("mqtt.enabled"):
        mqtt_result = cmd_mqtt(config, output_dir, args)
        results.append(("MQTT", "✅" if mqtt_result == 0 else "❌"))
    else:
        results.append(("MQTT", "Disabled"))

    # 3. Calendar generation (if enabled)
    if config.get("calendar.enabled"):
        calendar_result = cmd_calendar(config, output_dir, args)
        results.append(("Calendar", "✅" if calendar_result == 0 else "❌"))
    else:
        results.append(("Calendar", "Disabled"))

    # Show summary
    print("\n\033[96m📊 INTEGRATION SUMMARY\033[0m")
    print("\033[96m" + "─" * 20 + "\033[0m")
    for integration, status in results:
        print(f"  {integration}: {status}")

    return 0


def cmd_status(config: Config, args) -> int:
    """Show configuration and system status."""
    print("\n\033[96m📊 TWICKENHAM EVENTS STATUS\033[0m")
    print("\033[96m" + "=" * 30 + "\033[0m")

    # Version info
    print(f"Version: {get_dynamic_version()}")

    # Configuration status
    print("\nConfiguration:")
    print(f"  Scraping URL: {config.get('scraping.url', 'Not configured')}")
    print(f"  MQTT Enabled: {config.get('mqtt.enabled', False)}")
    print(f"  Calendar Enabled: {config.get('calendar.enabled', False)}")
    print(f"  Home Assistant Enabled: {config.get('home_assistant.enabled', False)}")

    # MQTT details
    if config.get("mqtt.enabled"):
        print("\nMQTT Configuration:")
        print(f"  Broker: {config.get('mqtt.broker_url', 'Not configured')}")
        print(f"  Port: {config.get('mqtt.broker_port', 'Not configured')}")
        print(f"  Client ID: {config.get('mqtt.client_id', 'Not configured')}")

    # Check output directory
    output_dir = Path(__file__).parent.parent / "output"
    print(f"\nOutput Directory: {output_dir}")
    print(f"  Exists: {output_dir.exists()}")
    if output_dir.exists():
        files = list(output_dir.glob("*"))
        print(f"  Files: {len(files)}")
        for file in files:
            print(f"    - {file.name}")

    return 0


# Keep the original main logic for backwards compatibility (renamed)
def run_legacy_main():
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
    print("\n\033[93m🌐 EVENT FETCHING & PROCESSING\033[0m")
    print("\033[93m" + "─" * 30 + "\033[0m")

    raw_events, processing_stats = fetch_events(config.get("scraping.url"), config)

    # Write parsing errors to JSON file immediately after fetch
    errors_path = output_dir / "event_processing_errors.json"
    with open(errors_path, "w") as f:
        json.dump({"last_updated": timestamp, "errors": error_log}, f, indent=4)

    if error_log:
        print(
            f"\033[33m⚠️  Found {len(error_log)} parsing errors. Details in \033[36m{errors_path}\033[0m"
        )

    if not raw_events:
        print("\033[31m❌ No events found or failed to fetch events.\033[0m")

        # Try to load previous data as fallback
        previous_events = load_previous_events(output_dir)
        if previous_events:
            print(
                f"📁 Using \033[33m{len(previous_events)}\033[0m events from previous successful run"
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
            print(
                f"📝 Updated timestamp for \033[33m{len(summarized_events)}\033[0m previous events"
            )

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
        print(f"✅ Successfully fetched \033[32m{len(raw_events)}\033[0m raw events")
        summarized_events = summarise_events(raw_events, config)

    # --- Output ---
    print("\n\033[95m💾 FILE OUTPUT\033[0m")
    print("\033[95m" + "─" * 15 + "\033[0m")

    # Write upcoming events to JSON file (only if we have new data)
    if raw_events:  # Only write if we have fresh data
        upcoming_events_path = output_dir / "upcoming_events.json"
        with open(upcoming_events_path, "w") as f:
            json.dump(
                {"last_updated": timestamp, "events": summarized_events}, f, indent=4
            )
        print(
            f"📝 Successfully wrote \033[36m{len(summarized_events)}\033[0m upcoming event days to \033[33m{upcoming_events_path}\033[0m"
        )

    # Generate ICS calendar file
    print("📅 Generating ICS calendar...")
    ics_result, ics_path = generate_ics_calendar(summarized_events, config, output_dir)

    if ics_result and ics_path:
        event_count = ics_result.get("stats", {}).get("total_events", 0)
        print(
            f"   \033[32m✅ Generated ICS calendar with {event_count} events: \033[33m{ics_path}\033[0m"
        )

        # Show calendar URL if web serving is configured
        calendar_url = get_calendar_url(config)
        if calendar_url:
            print(f"   \033[36m🔗 Calendar URL: {calendar_url}\033[0m")
    elif config.get("calendar.enabled", False):
        print("   \033[33m⚠️  ICS generation skipped - no events in scope\033[0m")
    else:
        print("   \033[90m📅 ICS generation disabled in config\033[0m")

    # --- MQTT Publishing ---
    if config.get("mqtt.enabled"):
        print("\n\033[94m📡 MQTT PUBLISHING\033[0m")
        print("\033[94m" + "─" * 20 + "\033[0m")

        try:
            # Get MQTT configuration using best practices from mqtt_publisher
            mqtt_config = config.get_mqtt_config()

            with MQTTPublisher(**mqtt_config) as publisher:
                # Publish Home Assistant discovery configs
                if config.get("home_assistant.enabled"):
                    print("🏠 Publishing Home Assistant discovery configs...")
                    publish_discovery_configs_for_twickenham(config, publisher)
                    print("   \033[32m✅ Discovery configs published\033[0m")

                # Publish event data with processing stats
                print("📤 Publishing event data to MQTT topics...")
                process_and_publish_events(
                    summarized_events, publisher, config, processing_stats
                )
                print("   \033[32m✅ Event data published successfully\033[0m")

            print("\033[32m🎉 MQTT publishing completed successfully!\033[0m")

        except ValueError as e:
            # Configuration validation errors
            print(f"\033[31m❌ MQTT Configuration Error:\033[0m {e}")
            print("💡 Check your config.yaml and environment variables.")

        except ConnectionError as e:
            # Connection-specific errors with helpful hints
            print(f"\033[31m🔌 MQTT Connection Failed:\033[0m {e}")
            try:
                mqtt_config = config.get_mqtt_config()
                port = mqtt_config.get("broker_port", 1883)
                tls_enabled = bool(mqtt_config.get("tls"))

                # Provide specific guidance based on configuration
                if tls_enabled and port == 1883:
                    print(
                        "💡 \033[33mHint:\033[0m TLS is enabled but using port 1883. Try port 8883 for TLS."
                    )
                elif not tls_enabled and port == 8883:
                    print(
                        "💡 \033[33mHint:\033[0m Port 8883 is typically for TLS. Try port 1883 or enable TLS."
                    )
                else:
                    print(
                        f"💡 \033[33mCheck:\033[0m Broker URL, port {port}, and network connectivity."
                    )
            except Exception:
                pass

        except Exception as e:
            print(f"\033[31m❌ Failed to publish to MQTT:\033[0m {e}")

    # --- Console Output ---
    # Find the next event and summary
    next_event, next_day_summary = find_next_event_and_summary(
        summarized_events, config
    )

    print("\n" + "\033[36m" + "=" * 50)
    print("    🏟️  UPCOMING EVENT SUMMARY  🏟️")
    print("=" * 50 + "\033[0m\n")

    print("\033[33m--- Next Event ---\033[0m")
    if next_event and next_day_summary:
        print(
            f"  \033[37mDate:\033[0m         \033[32m{next_day_summary.get('date')}\033[0m"
        )
        print(
            f"  \033[37mFixture:\033[0m      \033[1m{next_event.get('fixture')}\033[0m"
        )
        print(
            f"  \033[37mStart Time:\033[0m   \033[35m{next_event.get('start_time', 'TBC')}\033[0m"
        )
        print(
            f"  \033[37mCrowd:\033[0m        \033[34m{next_event.get('crowd', 'TBC')}\033[0m"
        )
    else:
        print("  \033[31mNo upcoming events found.\033[0m")

    print("\n\033[33m--- All Upcoming Events ---\033[0m")
    if summarized_events:
        for day in summarized_events:
            print(f"\n  \033[36m📅 Date: {day['date']}\033[0m")
            for event in day["events"]:
                # Type: ignore to suppress false positive type checking errors
                print(
                    f"    \033[37m-\033[0m \033[1mFixture:\033[0m      {event['fixture']}"
                )  # type: ignore
                print(
                    f"      \033[37mStart Time:\033[0m   \033[35m{event.get('start_time', 'TBC')}\033[0m"
                )  # type: ignore
                print(
                    f"      \033[37mCrowd:\033[0m        \033[34m{event.get('crowd', 'TBC')}\033[0m"
                )  # type: ignore
    else:
        print("  \033[31mNo upcoming events found.\033[0m")
    print("\n" + "\033[36m" + "=" * 50 + "\033[0m")


if __name__ == "__main__":
    main()
