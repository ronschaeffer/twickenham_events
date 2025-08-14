from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional  # noqa: UP035

from dotenv import load_dotenv

from core.config import Config
from core.discovery import publish_twickenham_discovery
from core.twick_event import (
    error_log,
    fetch_events,
    find_next_event_and_summary,
    process_and_publish_events,
    summarise_events,
)
from core.version import get_dynamic_version
from mqtt_publisher.publisher import MQTTPublisher

# Add project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))


def update_dynamic_version():
    """Update ha_entities.yaml with current semantic version from pyproject.toml."""
    try:
        import re

        from core.version import get_project_version

        ha_entities_path = Path(__file__).parent.parent / "config" / "ha_entities.yaml"

        if ha_entities_path.exists():
            current_version = get_project_version()

            with open(ha_entities_path) as f:
                content = f.read()

            # Update sw_version line
            updated_content = re.sub(
                r'(\s*sw_version:"0.1.2")[^"]*(")',
                rf"\g<1>{current_version}\g<2>",
                content,
            )

            with open(ha_entities_path, "w") as f:
                f.write(updated_content)

            print(f"� Updated device version to: \033[32m{current_version}\033[0m")
    except Exception as e:
        print(f"⚠️ Could not update dynamic version: {e}")


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
                publish_twickenham_discovery(config, publisher)

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

    # --- MQTT Publishing ---
    if config.get("mqtt.enabled"):
        print("\n\033[94m📡 MQTT PUBLISHING\033[0m")
        print("\033[94m" + "─" * 20 + "\033[0m")

        try:
            # Get MQTT configuration using best practices from mqtt_publisher
            mqtt_config = config.get_mqtt_config()

            with MQTTPublisher(**mqtt_config) as publisher:
                # Update device version with semantic versioning
                if config.get("home_assistant.enabled"):
                    update_dynamic_version()

                # Publish Home Assistant discovery configs
                if config.get("home_assistant.enabled"):
                    print("🏠 Publishing Home Assistant discovery configs...")
                    publish_twickenham_discovery(config, publisher)
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
            # Support both modern day summary (with 'events' list) and legacy flat event dicts
            events_iter = day.get("events") if isinstance(day, dict) else None  # type: ignore
            if events_iter is None:
                candidate = day if isinstance(day, dict) else {}
                events_iter = (
                    [candidate]
                    if isinstance(candidate, dict) and "fixture" in candidate
                    else []
                )
            for event in events_iter:
                ev = event if isinstance(event, dict) else {}
                print(
                    f"    \033[37m-\033[0m \033[1mFixture:\033[0m      {ev.get('fixture', 'UNKNOWN')}"
                )
                print(
                    f"      \033[37mStart Time:\033[0m   \033[35m{ev.get('start_time', 'TBC')}\033[0m"
                )
                print(
                    f"      \033[37mCrowd:\033[0m        \033[34m{ev.get('crowd', 'TBC')}\033[0m"
                )
    else:
        print("  \033[31mNo upcoming events found.\033[0m")
    print("\n" + "\033[36m" + "=" * 50 + "\033[0m")


if __name__ == "__main__":
    main()
