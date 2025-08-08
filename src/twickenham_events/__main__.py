#!/usr/bin/env python3
"""
Twickenham Events CLI - Modern command-line interface.

Complete restoration of CLI functionality with modern architecture.
"""

import argparse
from datetime import datetime
import json
import logging
from pathlib import Path
import sys

from .ai_processor import AIProcessor
from .calendar_generator import CalendarGenerator
from .config import Config
from .mqtt_client import MQTTClient
from .scraper import EventScraper


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser with all CLI commands."""
    parser = argparse.ArgumentParser(
        prog="twick-events",
        description="Twickenham Events: Rugby event processing with MQTT and calendar integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  twick-events scrape              # Scrape events only
  twick-events next                # Show only the next upcoming event
  twick-events list                # List all upcoming events
  twick-events mqtt                # Scrape and publish to MQTT
  twick-events calendar            # Scrape and generate calendar
  twick-events all                 # Run all integrations (default)
  twick-events status              # Show configuration status
  twick-events --version           # Show version information
  twick-events --dry-run all       # Test mode without side effects
        """,
    )

    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {_get_version()}"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/config.yaml",
        help="path to configuration file",
    )
    parser.add_argument("--output", type=str, help="custom output directory")
    parser.add_argument("--debug", action="store_true", help="enable debug output")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="test mode - no data will be saved or published",
    )

    subparsers = parser.add_subparsers(
        dest="command", help="available commands", required=False
    )

    # Scrape command
    scrape_parser = subparsers.add_parser(
        "scrape", help="scrape events and save to output directory"
    )
    scrape_parser.add_argument(
        "--output",
        help="output directory for results (files will be created within this directory)",
    )

    # MQTT command
    mqtt_parser = subparsers.add_parser(
        "mqtt", help="scrape events and publish to MQTT"
    )
    mqtt_parser.add_argument(
        "--output",
        help="output directory for results (files will be created within this directory)",
    )

    # Calendar command
    calendar_parser = subparsers.add_parser(
        "calendar", help="scrape events and generate calendar"
    )
    calendar_parser.add_argument(
        "--output",
        help="output directory for results (files will be created within this directory)",
    )

    # All command (default behavior)
    all_parser = subparsers.add_parser(
        "all", help="run all integrations (scrape + MQTT + calendar)"
    )
    all_parser.add_argument(
        "--output",
        help="output directory for results (files will be created within this directory)",
    )

    # List command - show all upcoming events
    list_parser = subparsers.add_parser(
        "list", help="list all upcoming events in a readable format"
    )
    list_parser.add_argument(
        "--limit", type=int, default=None, help="maximum number of events to show"
    )
    list_parser.add_argument(
        "--output",
        help="output directory for results (files will be created within this directory)",
    )

    # Next command - show only the next upcoming event
    next_parser = subparsers.add_parser(
        "next", help="show only the next upcoming event"
    )
    next_parser.add_argument(
        "--output",
        help="output directory for results (files will be created within this directory)",
    )

    # Status command
    subparsers.add_parser("status", help="show configuration and system status")

    # Cache command group
    cache_parser = subparsers.add_parser("cache", help="manage AI shortening cache")
    cache_subparsers = cache_parser.add_subparsers(
        dest="cache_command", help="cache operations"
    )
    cache_subparsers.add_parser("clear", help="clear AI shortening cache")
    cache_subparsers.add_parser("stats", help="show cache statistics")
    cache_subparsers.add_parser(
        "reprocess", help="reprocess cached items with current configuration"
    )

    return parser


def _get_version() -> str:
    """Get the package version."""
    try:
        from twickenham_events import __version__

        return __version__
    except ImportError:
        return "0.0.0-dev"


def _setup_logging(debug: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def cmd_scrape(args):
    """Handle the scrape command."""
    import json

    from .config import Config

    print("�️ \033[1mTwickenham Events Scraper\033[0m")
    print("=" * 50)

    # Load configuration
    config = Config.from_file(args.config)
    url = config.get("scraping.url")

    if not url:
        print("\033[31m❌ Error: No scraping URL configured\033[0m")
        print("   Please set 'scraping.url' in your config file")
        return 1

    # Initialize scraper
    scraper = EventScraper(config)

    if args.dry_run:
        print(f"\033[33m🔍 DRY RUN: Would scrape from: {url}\033[0m")
        print(f"   Max retries: {config.get('scraping.max_retries', 3)}")
        print(f"   Timeout: {config.get('scraping.timeout', 10)}s")
        print(
            f"   AI shortening: {'enabled' if config.get('ai_processor.shortening.enabled', False) else 'disabled'}"
        )
        print(
            f"   AI type detection: {'enabled' if config.get('ai_processor.type_detection.enabled', False) else 'disabled'}"
        )
        return 0

    try:
        # Scrape raw events
        print(f"🌐 Scraping events from: {url}")
        raw_events, stats = scraper.scrape_events(url)

        if not raw_events:
            print("\033[33m📭 No events found\033[0m")
            if scraper.error_log:
                print("\n\033[31mErrors encountered:\033[0m")
                for error in scraper.error_log:
                    print(f"   • {error}")
            return 0

        # Process and summarize events
        print(f"\n📊 Processing {len(raw_events)} raw events...")
        summarized_events = scraper.summarize_events(raw_events)

        # Find next event
        next_event, next_day_summary = scraper.find_next_event_and_summary(
            summarized_events
        )

        # Display results
        print("\n\033[32m✅ Processing complete!\033[0m")
        print(f"   Raw events found: {stats['raw_events_count']}")
        print(f"   Future events: {len(summarized_events)}")
        print(f"   Fetch duration: {stats['fetch_duration']}s")
        print(f"   Retry attempts: {stats['retry_attempts']}")

        if next_event:
            print("\n🎯 \033[1mNext Event:\033[0m")
            print(f"   📅 Date: {next_day_summary['date']}")
            print(f"   🏆 Event: {next_event['fixture']}")
            if next_event.get("fixture_short"):
                print(f"   📝 Short: {next_event['fixture_short']}")
            if next_event.get("start_time"):
                print(f"   ⏰ Time: {next_event['start_time']}")
            if next_event.get("crowd"):
                print(f"   👥 Crowd: {next_event['crowd']}")

        # Save to file if requested
        if args.output:
            from pathlib import Path

            output_dir = Path(args.output)
            output_dir.mkdir(exist_ok=True)
            output_file = output_dir / "scrape_results.json"

            output_data = {
                "stats": stats,
                "raw_events": raw_events,
                "summarized_events": summarized_events,
                "next_event": next_event,
                "next_day_summary": next_day_summary,
                "errors": scraper.error_log,
            }

            with open(output_file, "w") as f:
                json.dump(output_data, f, indent=2, default=str)
            print(f"\n💾 Results saved to: {output_file}")

        # Show errors if any
        if scraper.error_log:
            print(f"\n\033[33m⚠️  {len(scraper.error_log)} warnings/errors:\033[0m")
            for error in scraper.error_log:
                print(f"   • {error}")

        return 0

    except Exception as e:
        print(f"\n\033[31m❌ Scraping failed: {e}\033[0m")
        return 1


def cmd_list(args):
    """List upcoming events with filtering and formatting options."""
    import json

    from .config import Config

    # Load configuration
    config = Config.from_file(args.config)
    url = config.get("scraping.url")

    if not url:
        print("\033[31m❌ Error: No scraping URL configured\033[0m")
        print("   Please set 'scraping.url' in your config file")
        return 1

    # Initialize scraper and AI processor
    scraper = EventScraper(config)
    ai_processor = AIProcessor(config)

    if args.dry_run:
        print(f"\033[33m🔍 DRY RUN: Would scrape from: {url}\033[0m")
        print(f"   Output format: {args.format}")
        if args.output:
            print(f"   Would save to: {args.output}")
        return 0

    # Scrape events
    raw_events, stats = scraper.scrape_events(url)
    if not raw_events:
        print("\033[33m📭 No events found\033[0m")
        return 0

    # Process events
    summarized_events = scraper.summarize_events(raw_events)
    if not summarized_events:
        print("\033[33m📭 No upcoming events found\033[0m")
        return 0

    # Apply date filtering
    if args.limit:
        summarized_events = summarized_events[: args.limit]

    if args.format == "json":
        print(json.dumps(summarized_events, indent=2, default=str))
    elif args.format == "simple":
        for day_summary in summarized_events:
            date_str = day_summary["date"]
            event_count = len(day_summary["events"])
            print(
                f"📅 {date_str} ({event_count} event{'s' if event_count != 1 else ''})"
            )

            for event in day_summary["events"]:
                fixture = event["fixture"]
                # Get dynamic icon based on event type
                event_type, emoji, mdi_icon = ai_processor.get_event_type_and_icons(
                    fixture
                )

                time_str = event.get("start_time") or "TBC"
                print(f"   {emoji} {fixture} ({time_str})")
    else:  # detailed format
        print(f"\033[1m📋 Upcoming Events ({len(summarized_events)} days)\033[0m")
        print()

        for day_summary in summarized_events:
            date_str = day_summary["date"]
            event_count = len(day_summary["events"])
            earliest_time = day_summary.get("earliest_start", "TBC")

            print(
                f"📅 \033[1m{date_str}\033[0m ({event_count} event{'s' if event_count != 1 else ''})"
            )
            if earliest_time != "TBC":
                print(f"   ⏰ Earliest: {earliest_time}")
            print()

            for event in day_summary["events"]:
                fixture = event["fixture"]
                # Get dynamic icon based on event type
                event_type, emoji, mdi_icon = ai_processor.get_event_type_and_icons(
                    fixture
                )

                short_name = event.get("fixture_short")
                time_str = event.get("start_time") or "TBC"
                crowd = event.get("crowd")

                # Event number indicator
                event_num = (
                    f"[{event['event_index']}/{event['event_count']}]"
                    if event["event_count"] > 1
                    else ""
                )

                print(f"   {emoji} {fixture}")
                if short_name and short_name != fixture:
                    print(f"      📝 Short: {short_name}")
                print(f"      ⏰ Time: {time_str}")
                if crowd:
                    print(f"      👥 Crowd: {crowd}")
                if event_num:
                    print(f"      🔢 Event: {event_num}")
                print()

        # Save to file if requested
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    if args.format == "json":
                        json.dump(summarized_events, f, indent=2, default=str)
                    else:
                        # Save detailed format to file
                        f.write(f"Upcoming Events ({len(summarized_events)} days)\n")
                        f.write("=" * 50 + "\n\n")

                        for day_summary in summarized_events:
                            date_str = day_summary["date"]
                            event_count = len(day_summary["events"])
                            f.write(
                                f"{date_str} ({event_count} event{'s' if event_count != 1 else ''})\n"
                            )

                            for event in day_summary["events"]:
                                fixture = event["fixture"]
                                time_str = event.get("start_time") or "TBC"
                                f.write(f"  - {fixture} ({time_str})\n")
                            f.write("\n")

                print(f"\033[32m✅ Events saved to: {args.output}\033[0m")
            except Exception as e:
                print(f"\033[31m❌ Failed to save events: {e}\033[0m")
                return 1

    return 0


def cmd_next(args):
    """Show only the next upcoming event."""
    import json
    from pathlib import Path

    from .config import Config

    try:
        # Load configuration
        config = Config.from_file(args.config)

        if args.dry_run:
            print("🎯 Next Twickenham Event")
            print("==================================================")
            print("🔍 DRY RUN: Would show the next upcoming event")
            return 0

        print("🎯 Next Twickenham Event")
        print("==================================================")

        # Get events
        scraper = EventScraper(config)
        ai_processor = AIProcessor(config)
        url = config.get("scraping.url")
        raw_events, stats = scraper.scrape_events(url)

        if not raw_events:
            print("📭 No events found")
            return 0

        # Process events
        print(f"📊 Processing {len(raw_events)} raw events...")
        summarized_events = scraper.summarize_events(raw_events)

        if not summarized_events:
            print("📭 No upcoming events found")
            return 0

        # Find the next event
        next_event, next_day_summary = scraper.find_next_event_and_summary(
            summarized_events
        )

        if not next_event or not next_day_summary:
            print("📭 No upcoming events found")
            return 0

        print()

        # Display the next event in detail
        date_obj = datetime.strptime(next_day_summary["date"], "%Y-%m-%d")
        print(f"📅 \033[1m{date_obj.strftime('%A, %B %d, %Y')}\033[0m")
        print()

        fixture = next_event["fixture"]
        # Get dynamic icon based on event type
        event_type, emoji, mdi_icon = ai_processor.get_event_type_and_icons(fixture)
        short_name = next_event.get("fixture_short")
        time_str = next_event.get("start_time") or "TBC"
        crowd = next_event.get("crowd")

        # Event number indicator if multiple events that day
        event_num = (
            f"[{next_event['event_index']}/{next_event['event_count']}]"
            if next_event["event_count"] > 1
            else ""
        )

        print(f"{emoji} \033[1m{fixture}\033[0m")
        if short_name and short_name != fixture:
            print(f"   📝 Short: {short_name}")
        print(f"   ⏰ Time: {time_str}")
        if crowd:
            print(f"   👥 Crowd: {crowd}")
        if event_num:
            print(f"   🔢 Event: {event_num}")

        # Show additional context if multiple events that day
        if next_event["event_count"] > 1:
            print("\n📋 Other events this day:")
            for event in next_day_summary["events"]:
                if event != next_event:
                    event_time = event.get("start_time") or "TBC"
                    event_short = event.get("fixture_short", event["fixture"])
                    print(f"   • {event_short} at {event_time}")

        print()

        # Save to file if requested
        if args.output:
            from pathlib import Path

            output_dir = Path(args.output)
            output_dir.mkdir(exist_ok=True)
            output_file = output_dir / "next_event.json"

            output_data = {
                "stats": stats,
                "next_event": next_event,
                "next_day_summary": next_day_summary,
                "all_events": summarized_events,
                "errors": scraper.error_log,
            }

            with open(output_file, "w") as f:
                json.dump(output_data, f, indent=2, default=str)
            print(f"💾 Results saved to: {output_file}")

        # Show errors if any
        if scraper.error_log:
            print(f"\n\033[33m⚠️  {len(scraper.error_log)} warnings/errors:\033[0m")
            for error in scraper.error_log:
                print(f"   • {error}")

        return 0

    except Exception as e:
        print(f"\n\033[31m❌ Failed to get next event: {e}\033[0m")
        return 1


def cmd_mqtt(args) -> int:
    """Scrape events and publish to MQTT."""
    from pathlib import Path

    from .config import Config

    print("\n\033[94m📡 MQTT PUBLISHING\033[0m")
    print("\033[94m" + "─" * 15 + "\033[0m")

    # Load configuration
    config = Config.from_file(args.config)
    output_dir = (
        Path(args.output)
        if hasattr(args, "output") and args.output
        else Path.cwd() / "output"
    )

    if args.dry_run:
        print("🧪 \033[33mDRY RUN MODE\033[0m - Testing MQTT without publishing")

    # First scrape
    scrape_result = cmd_scrape(args)
    if scrape_result != 0:
        return scrape_result

    if not config.mqtt_enabled:
        print("❌ MQTT is not enabled in configuration")
        return 1

    if args.dry_run:
        print("🧪 Would publish to MQTT broker")
        return 0

    try:
        # Load scraped events
        with open(output_dir / "upcoming_events.json") as f:
            data = json.load(f)
        events = data.get("events", [])

        # Initialize AI processor for icon detection
        ai_processor = AIProcessor(config)

        # Publish to MQTT
        mqtt_client = MQTTClient(config)
        mqtt_client.publish_events(events, ai_processor)

        print("✅ Successfully published to MQTT")
        return 0

    except Exception as e:
        print(f"❌ MQTT publishing failed: {e}")
        return 1


def cmd_calendar(args):
    """Handle the calendar command."""
    from pathlib import Path

    from .config import Config

    print("📅 \033[1mTwickenham Events Calendar\033[0m")
    print("=" * 50)

    # Load configuration
    config = Config.from_file(args.config)

    if args.dry_run:
        print("\033[33m🔍 DRY RUN: Would scrape events and generate calendar\033[0m")
        print(f"   Calendar enabled: {config.get('calendar.enabled', True)}")
        print(
            f"   Output filename: {config.get('calendar.filename', 'twickenham_events.ics')}"
        )
        print(f"   Output directory: {args.output or 'output'}")
        return 0

    try:
        # Check if calendar generation is enabled
        if not config.get("calendar.enabled", True):
            print("\033[31m❌ Calendar generation is disabled in configuration\033[0m")
            print("   Set 'calendar.enabled: true' in your config file")
            return 1

        # Scrape events first
        print("🌐 Scraping events...")
        scraper = EventScraper(config)
        url = config.get("scraping.url")

        if not url:
            print("\033[31m❌ Error: No scraping URL configured\033[0m")
            return 1

        raw_events, stats = scraper.scrape_events(url)

        if not raw_events:
            print("\033[33m📭 No events found - cannot generate calendar\033[0m")
            return 0

        # Process events
        print(f"📊 Processing {len(raw_events)} raw events...")
        summarized_events = scraper.summarize_events(raw_events)

        if not summarized_events:
            print("\033[33m📭 No future events found - cannot generate calendar\033[0m")
            return 0

        # Generate calendar
        print(f"\n📅 Generating calendar with {len(summarized_events)} event days...")
        output_dir = Path(args.output) if args.output else Path("output")
        output_dir.mkdir(exist_ok=True)

        generator = CalendarGenerator(config)
        result, ics_path = generator.generate_ics_calendar(
            summarized_events, output_dir
        )

        if result and ics_path:
            print("\n\033[32m✅ Calendar generated successfully!\033[0m")
            print(f"   📁 File: {ics_path}")
            print(f"   📊 Events: {result['stats']['total_events']}")

            # Check for public URL
            if result.get("calendar_url"):
                print(f"   🌐 Public URL: {result['calendar_url']}")

            # Show errors if any
            if scraper.error_log:
                print(
                    f"\n\033[33m⚠️  {len(scraper.error_log)} warnings during processing:\033[0m"
                )
                for error in scraper.error_log:
                    print(f"   • {error}")

            return 0
        else:
            print("\n\033[31m❌ Failed to generate calendar\033[0m")
            return 1

    except Exception as e:
        print(f"\n\033[31m❌ Calendar generation failed: {e}\033[0m")
        return 1


def cmd_all(args) -> int:
    """Run all integrations (scrape + MQTT + calendar)."""
    from .config import Config

    print("\n\033[96m🎯 ALL INTEGRATIONS\033[0m")
    print("\033[96m" + "─" * 18 + "\033[0m")

    # Load configuration
    config = Config.from_file(args.config)

    if args.dry_run:
        print("🧪 \033[33mDRY RUN MODE\033[0m - Testing all integrations")

    results = []

    # 1. Scraping
    scrape_result = cmd_scrape(args)
    results.append(("Scraping", "✅" if scrape_result == 0 else "❌"))

    if scrape_result != 0:
        print("\n❌ Scraping failed - skipping other integrations")
        return scrape_result

    # 2. MQTT (if enabled)
    if config.mqtt_enabled:
        mqtt_result = cmd_mqtt(args)
        results.append(("MQTT", "✅" if mqtt_result == 0 else "❌"))
    else:
        results.append(("MQTT", "⏭️ Disabled"))

    # 3. Calendar (if enabled)
    if config.calendar_enabled:
        calendar_result = cmd_calendar(args)
        results.append(("Calendar", "✅" if calendar_result == 0 else "❌"))
    else:
        results.append(("Calendar", "⏭️ Disabled"))

    # Summary
    print("\n\033[96m📊 SUMMARY\033[0m")
    print("\033[96m" + "─" * 10 + "\033[0m")
    for name, status in results:
        print(f"  {name}: {status}")

    return 0


def cmd_status(config: Config, args) -> int:
    """Show configuration and system status."""
    print("\n\033[96m📊 TWICKENHAM EVENTS STATUS\033[0m")
    print("\033[96m" + "=" * 30 + "\033[0m")

    # Version
    print(f"Version: {_get_version()}")

    # Configuration
    print("\nConfiguration:")
    print(f"  Config file: {config.config_path}")
    print(f"  Scraping URL: {config.scraping_url}")
    print(f"  MQTT enabled: {config.mqtt_enabled}")
    print(f"  Calendar enabled: {config.calendar_enabled}")
    print(f"  AI shortener enabled: {config.ai_enabled}")
    print(f"  Web server enabled: {config.web_enabled}")

    # MQTT details
    if config.mqtt_enabled:
        print("\nMQTT Configuration:")
        print(f"  Broker: {config.mqtt_broker}")
        print(f"  Port: {config.mqtt_port}")
        print(f"  TLS: {config.mqtt_tls}")

    # AI Shortener
    if config.ai_enabled:
        print("\nAI Shortener:")
        print(f"  Model: {config.ai_model}")
        print(f"  Max length: {config.ai_max_length}")

        try:
            processor = AIProcessor(config)
            cache_stats = processor.get_cache_stats()
            print(f"  Cache entries: {cache_stats.get('count', 0)}")
        except Exception:
            print("  Cache: Error loading")

    return 0


def cmd_cache(config: Config, args) -> int:
    """Manage AI shortening cache."""
    if not config.ai_enabled:
        print("❌ AI shortener is not enabled")
        return 1

    try:
        processor = AIProcessor(config)

        if args.cache_command == "clear":
            processor.clear_cache()
            print("✅ Cache cleared")

        elif args.cache_command == "stats":
            stats = processor.get_cache_stats()
            print("\n📊 Cache Statistics:")
            print(f"  Entries: {stats.get('count', 0)}")
            print(f"  File: {stats.get('file', 'Unknown')}")

        elif args.cache_command == "reprocess":
            print("🔄 Reprocessing cache...")
            count = processor.reprocess_cache()
            print(f"✅ Reprocessed {count} entries")

        else:
            print("❌ Unknown cache command")
            return 1

    except Exception as e:
        print(f"❌ Cache operation failed: {e}")
        return 1

    return 0


def main() -> int:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Setup logging
    _setup_logging(args.debug)

    # Show help if no command provided
    if args.command is None:
        parser.print_help()
        return 0

    try:
        # Load configuration
        config_path = args.config or "config/config.yaml"
        config = Config.from_file(config_path)

        # Setup output directory
        output_dir = Path(args.output) if args.output else Path("output")
        output_dir.mkdir(exist_ok=True)

        # Route to command
        if args.command == "scrape":
            return cmd_scrape(args)
        elif args.command == "list":
            return cmd_list(args)
        elif args.command == "next":
            return cmd_next(args)
        elif args.command == "mqtt":
            return cmd_mqtt(args)
        elif args.command == "calendar":
            return cmd_calendar(args)
        elif args.command == "all":
            return cmd_all(args)
        elif args.command == "status":
            return cmd_status(config, args)
        elif args.command == "cache":
            return cmd_cache(config, args)
        else:
            print(f"❌ Unknown command: {args.command}")
            return 1

    except Exception as e:
        print(f"❌ Error: {e}")
        if args.debug:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
