#!/usr/bin/env python3
"""
Flights CLI - Modern command-line interface for flight tracking.

Adapted from Twickenham Events CLI architecture for flight-related functionality.
"""

import argparse
from datetime import datetime
import json
import logging
import os
from pathlib import Path
import sys
from typing import Any

from .config import Config
from .scraper import FlightScraper
from .mqtt_client import FlightMQTTClient


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser with all CLI commands."""
    parser = argparse.ArgumentParser(
        prog="flights-cli",
        description="Flights CLI: Flight tracking and processing with MQTT integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  flights-cli track                # Track flights and save to output
  flights-cli next                 # Show only the next upcoming flight
  flights-cli list                 # List all tracked flights
  flights-cli mqtt                 # Track flights and publish to MQTT
  flights-cli all                  # Run all integrations (track + MQTT)
  flights-cli status               # Show configuration status
  flights-cli --version            # Show version information
  flights-cli --dry-run all        # Test mode without side effects
        """,
    )

    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {_get_version()}"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/flights.yaml",
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

    # Track command
    track_parser = subparsers.add_parser(
        "track", help="track flights and save to output directory"
    )
    track_parser.add_argument(
        "--output",
        help="output directory for results",
    )

    # MQTT command
    mqtt_parser = subparsers.add_parser(
        "mqtt", help="track flights and publish to MQTT"
    )
    mqtt_parser.add_argument(
        "--output",
        help="output directory for results",
    )

    # All command (default behavior)
    all_parser = subparsers.add_parser(
        "all", help="run all integrations (track + MQTT)"
    )
    all_parser.add_argument(
        "--output",
        help="output directory for results",
    )

    # List command - show all tracked flights
    list_parser = subparsers.add_parser(
        "list", help="list all tracked flights in a readable format"
    )
    list_parser.add_argument(
        "--limit", type=int, default=None, help="maximum number of flights to show"
    )
    list_parser.add_argument(
        "--format",
        choices=["detailed", "simple", "json"],
        default="detailed",
        help="output format: detailed (default), simple, or json",
    )
    list_parser.add_argument(
        "--type",
        choices=["all", "departures", "arrivals"],
        default="all",
        help="filter by flight type",
    )

    # Next command - show only the next upcoming flight
    next_parser = subparsers.add_parser(
        "next", help="show only the next upcoming flight"
    )

    # Status command
    subparsers.add_parser("status", help="show configuration and system status")

    return parser


def _get_version() -> str:
    """Get the package version."""
    try:
        from . import __version__
        return __version__
    except ImportError:
        return "unknown"


def _setup_logging(debug: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


def cmd_track(args) -> int:
    """Handle the track command."""
    config = Config.from_file(args.config) if os.path.exists(args.config) else Config.from_defaults()
    scraper = FlightScraper(config)
    
    # Setup output directory
    output_dir = Path(args.output) if args.output else Path("output")
    output_dir.mkdir(exist_ok=True)
    
    if not args.dry_run:
        flights = scraper.scrape_flights()
        summary = scraper.summarize_flights(flights)
        
        # Save flight data
        flights_file = output_dir / "flights.json"
        with open(flights_file, "w") as f:
            json.dump(flights, f, indent=2)
        
        # Save summary
        summary_file = output_dir / "flights_summary.json"
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)
        
        print(f"✅ Flight tracking completed. {len(flights)} flights saved to {output_dir}")
    else:
        print("🔍 Dry run mode - would track flights and save to output")
    
    return 0


def cmd_list(args) -> int:
    """List tracked flights with filtering and formatting options."""
    config = Config.from_file(args.config) if os.path.exists(args.config) else Config.from_defaults()
    scraper = FlightScraper(config)
    
    flights = scraper.scrape_flights()
    
    # Filter by type
    if args.type != "all":
        flights = [f for f in flights if f["type"] == args.type.rstrip("s")]
    
    # Apply limit
    if args.limit:
        flights = flights[:args.limit]
    
    if args.format == "json":
        print(json.dumps(flights, indent=2))
    elif args.format == "simple":
        for flight in flights:
            print(f"{flight['flight_number']} - {flight['status']}")
    else:  # detailed
        for flight in flights:
            print(f"🛫 {flight['flight_number']} ({flight['airline']})")
            if flight['type'] == 'departure':
                print(f"   → {flight['destination']} - Gate {flight['gate']}")
                print(f"   ⏰ Departure: {flight['scheduled_departure']}")
            else:
                print(f"   ← {flight['origin']} - Gate {flight['gate']}")
                print(f"   ⏰ Arrival: {flight['scheduled_arrival']}")
            print(f"   📊 Status: {flight['status']}")
            print()
    
    return 0


def cmd_next(args) -> int:
    """Show only the next upcoming flight."""
    config = Config.from_file(args.config) if os.path.exists(args.config) else Config.from_defaults()
    scraper = FlightScraper(config)
    
    flights = scraper.scrape_flights()
    next_flight = scraper.find_next_flight(flights)
    
    if next_flight:
        print("🛫 Next Flight:")
        print(f"   Flight: {next_flight['flight_number']} ({next_flight['airline']})")
        if next_flight['type'] == 'departure':
            print(f"   → {next_flight['destination']} - Gate {next_flight['gate']}")
            print(f"   ⏰ Departure: {next_flight['scheduled_departure']}")
        else:
            print(f"   ← {next_flight['origin']} - Gate {next_flight['gate']}")
            print(f"   ⏰ Arrival: {next_flight['scheduled_arrival']}")
        print(f"   📊 Status: {next_flight['status']}")
    else:
        print("❌ No upcoming flights found.")
    
    return 0


def cmd_mqtt(args) -> int:
    """Track flights and publish to MQTT."""
    config = Config.from_file(args.config) if os.path.exists(args.config) else Config.from_defaults()
    scraper = FlightScraper(config)
    mqtt_client = FlightMQTTClient(config)
    
    if not args.dry_run:
        flights = scraper.scrape_flights()
        
        if mqtt_client.publish_flights(flights):
            print(f"✅ Flight data published to MQTT. {len(flights)} flights processed.")
        else:
            print("❌ Failed to publish flight data to MQTT.")
            return 1
    else:
        print("🔍 Dry run mode - would track flights and publish to MQTT")
    
    return 0


def cmd_all(args) -> int:
    """Run all integrations (track + MQTT)."""
    print("🚀 Running all flight integrations...")
    
    # Run tracking
    result = cmd_track(args)
    if result != 0:
        return result
    
    # Run MQTT publishing
    result = cmd_mqtt(args)
    if result != 0:
        return result
    
    print("🎉 All flight integrations completed successfully!")
    return 0


def cmd_status(config: Config, args) -> int:
    """Show configuration and system status."""
    print("📊 Flights CLI Status")
    print("=" * 50)
    
    print(f"✅ Configuration loaded from: {args.config}")
    print(f"✅ Flights API enabled: {config.get('flights.api_enabled', False)}")
    print(f"✅ Flight tracking enabled: {config.get('flights.tracking_enabled', False)}")
    print(f"✅ MQTT enabled: {config.get('mqtt.enabled', False)}")
    
    if config.get('mqtt.enabled', False):
        print(f"   📡 MQTT Broker: {config.get('mqtt.broker', 'localhost')}:{config.get('mqtt.port', 1883)}")
        topics = config.get('mqtt.topics', {})
        for topic_name, topic_path in topics.items():
            print(f"   📝 {topic_name}: {topic_path}")
    
    print("\n🔧 System Information:")
    print(f"   Python version: {sys.version.split()[0]}")
    print(f"   Working directory: {os.getcwd()}")
    
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
        config_path = args.config or "config/flights.yaml"
        config = Config.from_file(config_path) if os.path.exists(config_path) else Config.from_defaults()

        # Setup output directory
        output_dir = Path(args.output) if args.output else Path("output")
        output_dir.mkdir(exist_ok=True)

        # Route to command
        if args.command == "track":
            return cmd_track(args)
        elif args.command == "list":
            return cmd_list(args)
        elif args.command == "next":
            return cmd_next(args)
        elif args.command == "mqtt":
            return cmd_mqtt(args)
        elif args.command == "all":
            return cmd_all(args)
        elif args.command == "status":
            return cmd_status(config, args)
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