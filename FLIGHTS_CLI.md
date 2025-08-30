# Flights CLI

A command-line interface for flight tracking and processing, adapted from the Twickenham Events CLI architecture.

## Overview

The Flights CLI provides a modern, extensible interface for flight data tracking, processing, and integration with external systems like MQTT for real-time updates.

## Architecture

This CLI mirrors the successful patterns from the Twickenham Events project:

- **Modular Design**: Separate modules for configuration, scraping, MQTT, etc.
- **Command-driven Interface**: Multiple subcommands for different operations
- **Configuration Management**: YAML-based configuration with environment variable support
- **Output Flexibility**: Multiple output formats (JSON, detailed, simple)
- **Integration Ready**: MQTT support for real-time publishing

## Installation

The Flights CLI is installed alongside the main project:

```bash
pip install -e .
```

This creates a `flights-cli` command entry point.

## Usage

### Basic Commands

```bash
# Show help
flights-cli --help

# Show version
flights-cli --version

# Track flights and save to output directory
flights-cli track

# List all tracked flights
flights-cli list

# Show next upcoming flight
flights-cli next

# Show system status
flights-cli status

# Publish to MQTT (if configured)
flights-cli mqtt

# Run all integrations
flights-cli all
```

### Advanced Usage

```bash
# List only departures in simple format
flights-cli list --type departures --format simple

# Limit results
flights-cli list --limit 5

# JSON output
flights-cli list --format json

# Dry run mode
flights-cli --dry-run all

# Custom configuration file
flights-cli --config custom_config.yaml status

# Debug mode
flights-cli --debug track
```

## Configuration

Configuration is managed via `config/flights.yaml`:

```yaml
flights:
  api_enabled: true
  tracking_enabled: true
  alerts_enabled: false

mqtt:
  enabled: false
  broker: "localhost"
  port: 1883
  topics:
    status: "flights/status"
    departures: "flights/departures"
    arrivals: "flights/arrivals"
    next: "flights/next"

output:
  directory: "output"
  formats:
    - "json"
    - "csv"
```

## Features

### Current Implementation

- **Mock Data Generation**: Provides sample flight data for testing
- **Flight Tracking**: Basic departure and arrival tracking
- **Multiple Output Formats**: Detailed, simple, and JSON formats
- **Status Filtering**: Filter by flight type (departures/arrivals)
- **MQTT Integration**: Ready for real-time publishing (when configured)
- **Configuration Management**: Flexible YAML-based configuration

### Future Enhancements

- **Real API Integration**: Connect to live flight data APIs
- **Calendar Integration**: Generate flight schedules in calendar format
- **Alert System**: Real-time notifications for flight changes
- **Web Interface**: Optional web dashboard for flight monitoring
- **Database Support**: Persistent storage for historical data

## File Structure

```
src/flights/
├── __init__.py          # Package initialization
├── __main__.py          # Main CLI entry point
├── config.py            # Configuration management
├── scraper.py           # Flight data scraping
└── mqtt_client.py       # MQTT publishing
```

## Testing

Run the validation tests:

```bash
python validate_flights.py
```

Or run the basic test suite:

```bash
python tests/test_flights_cli.py
```

## Adaptation Notes

This CLI was adapted from the Twickenham Events project with the following changes:

1. **Domain-Specific Terms**: Events → Flights, Rugby → Airlines, etc.
2. **Data Structure**: Adapted for flight-specific fields (departure/arrival times, gates, airlines)
3. **Mock Data**: Flight-appropriate sample data instead of rugby events
4. **Configuration**: Flight-specific configuration options
5. **Entry Point**: New `flights-cli` command separate from `twick-events`

The core architectural patterns remain the same to maintain consistency and leverage proven design decisions.

## Integration

The Flights CLI can be integrated with:

- **MQTT Brokers**: For real-time data publishing
- **Home Assistant**: Via MQTT discovery
- **Flight APIs**: FlightAware, AviationStack, etc.
- **Monitoring Systems**: Via status endpoints
- **Automation**: Via command-line scripting

## Contributing

Follow the same patterns as the main Twickenham Events project:

1. Maintain the modular architecture
2. Use consistent error handling
3. Add appropriate logging
4. Update tests for new functionality
5. Document configuration options