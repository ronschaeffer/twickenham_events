#!/usr/bin/env python3
# ruff: noqa: E402
"""
Twickenham Events CLI - Modern command-line interface.

Complete restoration of CLI functionality with modern architecture.
"""

import argparse
from datetime import datetime
import importlib
import json
import logging
import os
from pathlib import Path
import signal
import ssl
import sys
import threading
import time
from typing import Any

# Attempt multiple import locations for the MQTTPublisher so the CLI works
# whether the upstream `ha_mqtt_publisher` package is installed, or when
# running from the monorepo where packages may live under different src/ paths.
MQTTPublisher = None
for candidate in (
    "ha_mqtt_publisher.publisher",
    "mqtt_publisher.ha_mqtt_publisher.publisher",
    "mqtt_publisher.publisher",
):
    try:
        mod = importlib.import_module(candidate)
        MQTTPublisher = mod.MQTTPublisher
        break
    except Exception:
        continue
if MQTTPublisher is None:
    # Last resort: provide a lightweight local stub that raises at runtime if used
    class _MissingPublisherStub:
        def __init__(self, *a, **kw):
            raise RuntimeError("No MQTTPublisher implementation available")

    MQTTPublisher = _MissingPublisherStub
import paho.mqtt.client as mqtt

from .ai_processor import AIProcessor
from .calendar_generator import CalendarGenerator
from .config import Config
from .discovery_helper import publish_device_level_discovery
from .mqtt_client import MQTTClient
from .scraper import EventScraper
from .service_support import AvailabilityPublisher, install_global_signal_handler


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
        "--format",
        choices=["detailed", "simple", "json"],
        default="detailed",
        help="output format: detailed (default), simple, or json",
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

    # Service (daemon) command
    service_parser = subparsers.add_parser(
        "service", help="run continuous service (periodic scrape + MQTT)"
    )
    service_parser.add_argument(
        "--once", action="store_true", help="run a single cycle then exit"
    )
    service_parser.add_argument(
        "--interval", type=int, help="override scrape interval seconds"
    )
    service_parser.add_argument(
        "--cleanup-discovery",
        action="store_true",
        help="cleanup legacy/duplicate discovery entities and exit",
    )

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

    # Commands (registry) introspection
    commands_parser = subparsers.add_parser(
        "commands", help="print supported command registry (discovery metadata)"
    )
    commands_parser.add_argument(
        "--json", action="store_true", help="output raw JSON instead of pretty table"
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

    print("🏉 \033[1mTwickenham Events Scraper\033[0m")
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
            if next_day_summary:
                print(f"   📅 Date: {next_day_summary['date']}")
            print(f"   🏆 Event: {next_event['fixture']}")
            if next_event.get("fixture_short"):
                print(f"   📝 Short: {next_event['fixture_short']}")
            if next_event.get("start_time"):
                print(f"   ⏰ Time: {next_event['start_time']}")
            if next_event.get("crowd"):
                print(f"   👥 Crowd: {next_event['crowd']}")

        # Save to file(s) if requested
        if args.output:
            from pathlib import Path

            output_dir = Path(args.output)
            output_dir.mkdir(exist_ok=True)

            # 1. Rich scrape results bundle (diagnostics + summaries)
            results_file = output_dir / "scrape_results.json"
            output_data = {
                "stats": stats,
                "raw_events": raw_events,
                "summarized_events": summarized_events,
                "next_event": next_event,
                "next_day_summary": next_day_summary,
                "errors": scraper.error_log,
            }
            with open(results_file, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, default=str)

            # 2. Flat upcoming events file expected by other commands (e.g. mqtt)
            #    Schema upgraded for parity with MQTT all_upcoming topic:
            #      {
            #         "events": [...],
            #         "count": <int>,
            #         "generated_ts": <epoch>,
            #         "last_updated": <iso8601>
            #      }
            #    summarized_events' inner events already include date (post-refactor),
            #    so we can flatten directly without injection logic.
            flat_events: list[dict[str, Any]] = []
            for day in summarized_events:
                day_date = day.get("date")
                for ev in day.get("events", []):
                    # Ensure date present
                    base_ev = ev
                    if ("date" not in base_ev) and day_date:
                        base_ev = base_ev.copy()
                        base_ev["date"] = day_date
                    # Remove any legacy/display-only title to match MQTT schema
                    if "title" in base_ev:
                        if base_ev is ev:
                            base_ev = base_ev.copy()
                        base_ev.pop("title", None)
                    flat_events.append(base_ev)
            upcoming_file = output_dir / "upcoming_events.json"
            with open(upcoming_file, "w", encoding="utf-8") as f:
                now_epoch = int(time.time())
                now_iso = datetime.now().isoformat()
                json.dump(
                    {
                        "events": flat_events,
                        "count": len(flat_events),
                        "generated_ts": now_epoch,
                        "last_updated": now_iso,
                    },
                    f,
                    indent=2,
                    default=str,
                )

            print(
                f"\n💾 Results saved: {results_file.name} (detailed), {upcoming_file.name} (flat events: {len(flat_events)}) in {output_dir}"
            )

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

    # First scrape (force writing to our resolved output_dir to avoid stale file reads)
    try:
        args.output = str(output_dir)
    except Exception:
        # In case args is a frozen namespace, fall back silently
        pass
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

        # Show effective MQTT configuration (masked password) so user can verify real env/config values
        try:
            eff_cfg = config.get_mqtt_config()
            auth_cfg = eff_cfg.get("auth") or {}
            user_display = auth_cfg.get("username") or "<none>"
            pwd_display = "***" if auth_cfg.get("password") else "<none>"
            print(
                f"Using MQTT config: broker={eff_cfg.get('broker_url')} port={eff_cfg.get('broker_port')} "
                f"security={eff_cfg.get('security')} user={user_display} password={pwd_display} client_id={eff_cfg.get('client_id')}"
            )
        except Exception as _cfg_e:  # pragma: no cover - defensive
            print(f"⚠️  Unable to display MQTT config summary: {_cfg_e}")

        # Publish to MQTT
        mqtt_client = MQTTClient(config)
        mqtt_client.publish_events(events, ai_processor)
        # Publish unified device-level discovery bundle via library helpers
        try:
            AVAILABILITY_TOPIC = "twickenham_events/availability"
            cfg = config.get_mqtt_config()
            with MQTTPublisher(**cfg) as publisher:
                # Publish device-level discovery bundle using status/all_upcoming/next/today topics
                publish_device_level_discovery(
                    mqtt_client=publisher,
                    config=config,
                    availability_topic=AVAILABILITY_TOPIC,
                    include_event_count_component=True,
                    migrate_from_per_entity=True,
                )
                # Immediately mark device online for HA availability
                try:
                    AvailabilityPublisher(publisher, AVAILABILITY_TOPIC).online()
                except Exception:
                    pass
            print("📡 Published device discovery bundle (cmps)")
        except Exception as e:  # pragma: no cover
            if args.dry_run:
                print(f"(dry-run) would publish device discovery: {e}")
            else:
                print(f"⚠️  Device discovery publish skipped: {e}")

        print("✅ Successfully published to MQTT (events + discovery)")
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


def cmd_service(config: Config, args) -> int:
    """Run continuous service loop with periodic scraping and MQTT publishing.

    Command topics:
      twickenham_events/cmd/refresh -> immediate scrape/publish
      twickenham_events/cmd/clear_cache -> clear AI cache (if enabled)
    Interval defaults to config.service_interval_seconds (4h default) unless --interval provided.
    """
    if not config.mqtt_enabled:
        print("❌ MQTT must be enabled for service mode")
        return 1

    # imports moved to module top for linter compliance

    interval = args.interval or config.service_interval_seconds
    scraper = EventScraper(config)
    ai_processor = AIProcessor(config) if config.ai_enabled else None
    mqtt_pub = MQTTClient(config)

    last_run = 0.0
    lock = threading.Lock()
    stop_flag = {"stop": False}

    AVAILABILITY_TOPIC = "twickenham_events/availability"
    availability = AvailabilityPublisher(None, AVAILABILITY_TOPIC)  # client set below

    last_events_count = {"count": None}

    def run_cycle(trigger: str, command_meta: dict | None = None) -> dict[str, Any]:
        nonlocal last_run
        with lock:
            try:
                url = config.scraping_url
                raw_events, stats = scraper.scrape_events(url)
                summarized = scraper.summarize_events(raw_events)
                from .flatten import flatten_with_date

                flat = flatten_with_date(summarized)
                run_ts = time.time()
                last_run = run_ts
                from .service_cycle import build_extra_status

                extra_status = build_extra_status(
                    scraper=scraper,
                    flat_events=flat,
                    trigger=trigger,
                    interval=interval,
                    run_ts=run_ts,
                )
                if command_meta:
                    extra_status["last_command"] = command_meta
                prev = last_events_count["count"]
                # Update last events count (tracking for no-change detection)
                last_events_count["count"] = len(flat)  # type: ignore[assignment]
                no_changes = prev is not None and prev == len(flat)
                mqtt_pub.publish_events(flat, ai_processor, extra_status=extra_status)
                logging.info(
                    "service cycle completed trigger=%s events=%s", trigger, len(flat)
                )
                return {"events": len(flat), "no_changes": no_changes}
            except Exception as e:  # pragma: no cover
                logging.error("service cycle failed: %s", e)
                raise

    client_id = f"{config.mqtt_client_id}-svc"
    # Use Paho MQTT v5 and Callback API v2 to avoid deprecation
    try:
        # Prefer MQTT v5; add callback_api_version V2 if available in this Paho version
        kwargs = {
            "client_id": client_id,
            "protocol": getattr(mqtt, "MQTTv5", mqtt.MQTTv311),
            "userdata": None,
        }
        try:  # import locally to avoid top-level import ordering issues
            from paho.mqtt.client import CallbackAPIVersion as _CBV  # type: ignore

            cbv_v2 = getattr(_CBV, "V2", getattr(_CBV, "VERSION2", None))
            if cbv_v2 is not None:
                kwargs["callback_api_version"] = cbv_v2  # type: ignore[assignment]
        except Exception:
            pass
        paho_client = mqtt.Client(**kwargs)  # type: ignore[arg-type]
    except Exception:
        # Fallback if very old paho
        paho_client = mqtt.Client(client_id=client_id)
    availability._client = paho_client  # inject real client

    # Apply auth if configured (mirrors publisher settings)
    if (
        config.get("mqtt.security") == "username"
        and config.mqtt_username
        and config.mqtt_password
    ):
        try:
            paho_client.username_pw_set(config.mqtt_username, config.mqtt_password)
        except Exception as e:  # pragma: no cover
            logging.warning("Failed setting MQTT auth on command client: %s", e)

    # Configure Last Will and Testament (LWT)
    try:
        lw_cfg = config.get("mqtt.last_will")
        if isinstance(lw_cfg, dict) and lw_cfg.get("topic"):
            will_topic = str(lw_cfg.get("topic"))
            will_payload = lw_cfg.get("payload", '{"status":"offline"}')
            will_qos = int(lw_cfg.get("qos", 1))
            will_retain = bool(lw_cfg.get("retain", True))
        else:
            will_topic = availability.topic
            will_payload = "offline"
            will_qos = 1
            will_retain = True
        paho_client.will_set(will_topic, will_payload, qos=will_qos, retain=will_retain)
        logging.debug(
            "configured_lwt topic=%s qos=%s retain=%s fallback=%s",
            will_topic,
            will_qos,
            will_retain,
            not (isinstance(lw_cfg, dict) and lw_cfg.get("topic")),
        )
    except Exception as e:  # pragma: no cover
        logging.warning("Failed configuring MQTT LWT: %s", e)

    # Configure TLS for the service command client (matches validator behavior)
    try:
        tls_requested = False
        try:
            tls_requested = bool(config.get("mqtt.tls"))
        except Exception:
            tls_requested = False
        _tls_env = os.getenv("MQTT_USE_TLS")
        if _tls_env and _tls_env.lower() in ("true", "1", "yes", "on"):
            tls_requested = True
        # Avoid enabling TLS implicitly on 1883 unless explicitly forced via env
        if int(getattr(config, "mqtt_port", 1883) or 1883) == 1883 and not (
            _tls_env and _tls_env.lower() in ("true", "1", "yes", "on")
        ):
            tls_requested = False
        tls_verify_env = os.getenv("TLS_VERIFY")
        verify_flag: bool | None = None
        if tls_verify_env is not None:
            try:
                verify_flag = tls_verify_env.lower() in ("true", "1", "yes", "on")
            except Exception:
                verify_flag = None
        if tls_requested:
            cfg_tls = None
            try:
                cfg_tls = config.get("mqtt.tls")
            except Exception:
                cfg_tls = None
            try:
                if isinstance(cfg_tls, dict):
                    ca = cfg_tls.get("ca_certs")
                    certfile = cfg_tls.get("certfile")
                    keyfile = cfg_tls.get("keyfile")
                    if ca or certfile:
                        paho_client.tls_set(
                            ca_certs=ca, certfile=certfile, keyfile=keyfile
                        )
                        if verify_flag is False:
                            paho_client.tls_insecure_set(True)
                    else:
                        if verify_flag is True:
                            paho_client.tls_set()
                        else:
                            paho_client.tls_set(cert_reqs=ssl.CERT_NONE)
                            paho_client.tls_insecure_set(True)
                else:
                    if verify_flag is True:
                        paho_client.tls_set()
                    else:
                        paho_client.tls_set(cert_reqs=ssl.CERT_NONE)
                        paho_client.tls_insecure_set(True)
                logging.info(
                    "service mqtt_client tls configured requested=%s verify=%s",
                    tls_requested,
                    verify_flag,
                )
            except Exception as e:
                logging.warning("Failed configuring TLS for service MQTT client: %s", e)
    except Exception:
        pass

    last_connect_code = {"code": None}

    def shutdown_sequence():  # pragma: no cover
        try:
            availability.offline()
        finally:
            stop_flag["stop"] = True

    install_global_signal_handler(shutdown_sequence, (signal.SIGTERM,))

    from .command_processor import CommandProcessor
    from .plugin_loader import load_command_plugins

    ACK_TOPIC = "twickenham_events/commands/ack"
    RESULT_TOPIC = "twickenham_events/commands/result"
    LAST_ACK_TOPIC = "twickenham_events/commands/last_ack"
    LAST_RESULT_TOPIC = "twickenham_events/commands/last_result"
    processor = CommandProcessor(paho_client, ACK_TOPIC, RESULT_TOPIC)  # type: ignore[call-arg]
    # Auto publish registry to retained discovery topic on every registration
    processor.enable_auto_registry_publish("twickenham_events/commands/registry")
    # Load dynamic command plugins (non-fatal if missing)
    try:
        loaded_plugins = load_command_plugins(processor)
        if loaded_plugins:
            logging.info(
                "Loaded %d command plugins: %s",
                len(loaded_plugins),
                ", ".join(loaded_plugins),
            )
    except Exception as e:  # pragma: no cover
        logging.debug("Plugin loading failed: %s", e)

    def refresh_executor(ctx: dict[str, Any]):
        try:
            meta = {
                "id": ctx["id"],
                "name": ctx["command"],
                "requested_ts": ctx.get("requested_ts"),
                "received_ts": ctx.get("received_ts"),
            }
            result = run_cycle("command", command_meta=meta)
            events = result.get("events", 0)
            if result.get("no_changes"):
                details = f"events regenerated: {events} (no changes)"
            else:
                details = f"events regenerated: {events}"
            return "success", details, {"events": events}
        except Exception as e:  # pragma: no cover
            return "fatal_error", f"refresh failed: {e}", {}

    def clear_cache_executor(ctx: dict[str, Any]):
        if not ai_processor:
            return "validation_failed", "AI cache not enabled", {}
        try:
            ai_processor.clear_cache()
            logging.info("AI cache cleared via command")
            meta = {
                "id": ctx["id"],
                "name": ctx["command"],
                "requested_ts": ctx.get("requested_ts"),
                "received_ts": ctx.get("received_ts"),
                "completed_ts": time.time(),
            }
            try:
                mqtt_pub.publish_events(
                    [], ai_processor, extra_status={"last_command": meta}
                )
            except Exception:  # pragma: no cover
                pass
            return "success", "AI cache cleared", {}
        except Exception as e:  # pragma: no cover
            return "fatal_error", f"cache clear failed: {e}", {}

    processor.register(
        "refresh",
        refresh_executor,
        description="Immediate scrape + publish",
        outcome_codes=["success", "fatal_error", "busy"],
        cooldown_seconds=0,
        requires_ai=False,
    )
    processor.register(
        "clear_cache",
        clear_cache_executor,
        description="Clear AI cache entries",
        outcome_codes=["success", "validation_failed", "fatal_error", "busy"],
        cooldown_seconds=0,
        requires_ai=True,
    )

    def restart_executor(ctx: dict[str, Any]):
        try:
            # Publish a quick result and then exit so service manager can restart
            # We let the CommandProcessor handle result publication; here we just signal shutdown.
            # Small delay to allow result/idle ack to flush before exiting.
            logging.info("Restart requested via command")
            time.sleep(0.5)
            # Optional: proactively start/enable systemd service so it comes back
            try:
                sysd = config.get("service.systemd", {}) or {}
                if sysd.get("auto_launch", False):
                    unit = sysd.get("unit", "twickenham-events.service")
                    is_user = bool(sysd.get("user", True))
                    delay = int(sysd.get("delay_seconds", 2))
                    cmd_prefix = ["systemctl", "--user"] if is_user else ["systemctl"]
                    # Start (and optionally enable) the service; best-effort only
                    import subprocess

                    try:
                        subprocess.run([*cmd_prefix, "daemon-reload"], check=False)
                    except Exception:
                        pass
                    # Start the unit after a slight delay; we cannot sleep long here
                    try:
                        subprocess.Popen([*cmd_prefix, "start", unit])
                    except Exception:
                        pass
                    if delay and delay > 0:
                        try:
                            time.sleep(min(delay, 3))
                        except Exception:
                            pass
            except Exception as _e:
                logging.debug("systemd auto_launch skipped: %s", _e)
            shutdown_sequence()
            return "success", "service restarting", {}
        except Exception as e:  # pragma: no cover
            return "fatal_error", f"restart failed: {e}", {}

    processor.register(
        "restart",
        restart_executor,
        description="Restart the running service",
        outcome_codes=["success", "fatal_error", "busy"],
        cooldown_seconds=0,
        requires_ai=False,
    )

    # Use normalized helpers from upstream ha_mqtt_publisher package to avoid
    # duplicate logic and keep behavior consistent with the publisher library.
    try:
        from ha_mqtt_publisher.mqtt_utils import extract_reason_code
    except Exception:

        def extract_reason_code(
            *args, **kwargs
        ):  # robust fallback compatible with paho v1/v2
            # Try to extract an integer-like reason code from common callback signatures
            for a in args:
                try:
                    if isinstance(a, int):
                        return a
                    if hasattr(a, "rc"):
                        return int(a.rc)  # type: ignore[attr-defined]
                    if hasattr(a, "reason_code"):
                        return int(a.reason_code)  # type: ignore[attr-defined]
                except Exception:
                    continue
            for v in kwargs.values():
                try:
                    if isinstance(v, int):
                        return v
                    if hasattr(v, "rc"):
                        return int(v.rc)  # type: ignore[attr-defined]
                    if hasattr(v, "reason_code"):
                        return int(v.reason_code)  # type: ignore[attr-defined]
                except Exception:
                    continue
            return None

    def on_connect(client, userdata, *args, **kwargs):
        # Support both v1 and v2 paho callback signatures. Extract reason_code
        rc_val = extract_reason_code(*args, **kwargs)
        try:
            reason_code = int(rc_val) if rc_val is not None else 0
        except Exception:
            reason_code = 0
        if last_connect_code["code"] == reason_code:
            return
        last_connect_code["code"] = reason_code
        if reason_code == 0:
            logging.info("service connected rc=%s", reason_code)
            base = config.get("app.unique_id_prefix", "twickenham_events")
            client.subscribe(f"{base}/cmd/#")
            # Also listen for our own result messages to publish a final 'idle' ack
            try:
                client.subscribe(RESULT_TOPIC)
            except Exception:  # pragma: no cover
                pass
            try:
                for uid in (
                    "tw_events_refresh",
                    "tw_events_clear_cache",
                    "twickenham_events_refresh",
                    "twickenham_events_clear_cache",
                ):
                    btn_topic = f"{config.service_discovery_prefix}/button/{uid}/config"
                    client.publish(btn_topic, "", retain=True)
                try:
                    publish_device_level_discovery(
                        mqtt_client=client,
                        config=config,
                        availability_topic=AVAILABILITY_TOPIC,
                        include_event_count_component=True,
                        migrate_from_per_entity=True,
                    )
                except Exception as e:
                    logging.warning("Failed to publish device-level discovery: %s", e)
                # Publish command registry discovery (retained)
                try:
                    processor.publish_registry("twickenham_events/commands/registry")
                    logging.info("Published command registry discovery")
                except Exception as e:  # pragma: no cover
                    logging.warning("Failed publishing command registry: %s", e)
                availability.online()
                logging.info(
                    "Published device-level discovery (cmps) and set device online"
                )
            except Exception as e:  # pragma: no cover
                logging.warning("Failed discovery/availability: %s", e)
        else:
            logging.error(
                "service connect failed rc=%s (will not publish discovery)", reason_code
            )

    def on_message(client, userdata, msg, *args, **kwargs):
        try:
            from .message_handler import handle_command_message

            handle_command_message(
                client,
                config,
                processor,
                msg,
                ACK_TOPIC,
                LAST_ACK_TOPIC,
                RESULT_TOPIC,
                LAST_RESULT_TOPIC,
            )
        except Exception as e:  # pragma: no cover
            logging.error("command handling failure: %s", e)

    # Assign v2-compatible callbacks
    paho_client.on_connect = on_connect
    paho_client.on_message = on_message
    try:
        paho_client.connect(config.mqtt_broker, config.mqtt_port, keepalive=60)
        paho_client.loop_start()
    except Exception as e:
        logging.error("cannot start MQTT command client: %s", e)
        return 1

    run_cycle("startup")
    if args.once:
        paho_client.loop_stop()
        paho_client.disconnect()
        return 0

    print(
        f"🚀 Service started interval={interval}s (refresh topic: twickenham_events/cmd/refresh)"
    )
    try:
        while not stop_flag["stop"]:
            if time.time() - last_run >= interval:
                run_cycle("interval")
            time.sleep(5)
    except KeyboardInterrupt:  # pragma: no cover
        print("Stopping service...")
    finally:
        availability.offline()
        paho_client.loop_stop()
        paho_client.disconnect()
    return 0


def cmd_commands(config: Config, args) -> int:
    """Print command registry (mirrors service discovery) without connecting."""
    from .command_processor import CommandProcessor

    class _NoopClient:
        def publish(self, *_, **__):
            return True

    proc = CommandProcessor(_NoopClient(), "", "")  # type: ignore[call-arg]
    proc.register(
        "refresh",
        lambda ctx: ("success", "noop", {}),
        description="Immediate scrape + publish",
        outcome_codes=["success", "fatal_error", "busy"],
        cooldown_seconds=0,
        requires_ai=False,
    )
    proc.register(
        "clear_cache",
        lambda ctx: ("success", "noop", {}),
        description="Clear AI cache entries",
        outcome_codes=["success", "validation_failed", "fatal_error", "busy"],
        cooldown_seconds=0,
        requires_ai=True,
    )
    payload = proc.build_registry_payload()
    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2))
    else:
        print(
            f"\n📋 Supported Commands (registry v{payload.get('registry_version', 1)})"
        )
        for cmd in payload.get("commands", []):
            print(f"  • {cmd['name']}: {cmd.get('description', '')}")
            extras = []
            if "requires_ai" in cmd:
                extras.append(f"requires_ai={cmd['requires_ai']}")
            if "cooldown_seconds" in cmd:
                extras.append(f"cooldown={cmd['cooldown_seconds']}s")
            if extras:
                print("     (" + ", ".join(extras) + ")")
            print(
                "     outcomes="
                + ",".join(cmd.get("outcome_codes", []))
                + f" qos={cmd.get('qos_recommended')}"
            )
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
        elif args.command == "service":
            return cmd_service(config, args)
        elif args.command == "commands":
            return cmd_commands(config, args)
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
