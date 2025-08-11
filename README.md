# Twickenham Events

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Event scraping and MQTT publishing system for Twickenham Stadium that fetches upcoming events from Richmond Council website and publishes structured data to Home Assistant via MQTT with auto-discovery support.

## Features

- **Event Scraping**: Fetches upcoming events from Richmond Council website with date/time normalization
- **MQTT Publishing**: Publishes structured event data to MQTT topics with retain flags for Home Assistant
- **Home Assistant Integration**: Auto-discovery support with binary sensor status monitoring and dashboard cards
- **AI Event Processing**: Google Gemini API integration for event name shortening with configurable length limits
- **Emoji Classification**: Modular emoji and icon assignment system with priority-based logic (finals get trophies, sport-specific emojis)
- **Flag Integration**: Unicode country flag support for international matches in AI-shortened names
- **ICS Calendar Export**: Generates standard ICS calendar files for external calendar integration
- **Web Server**: Built-in HTTP server for calendar file serving and status endpoints
- **Environment Configuration**: Hierarchical environment variable loading with validation
- **Test Coverage**: 445 tests covering all functionality including emoji logic and AI integration

## Installation

### Prerequisites

- Python 3.11+
- [Poetry](https://python-poetry.org/docs/#installation)

### Setup

1. **Clone the repository:**

   ```bash
   git clone https://github.com/ronschaeffer/twickenham_events.git
   cd twickenham_events
   ```

2. **Install dependencies:**

   ```bash
   poetry install
   ```

3. **Install AI dependencies (optional):**
   ```bash
   poetry install --with ai
   ```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# MQTT Configuration
MQTT_BROKER_URL=${MQTT_BROKER_URL}
MQTT_BROKER_PORT=${MQTT_BROKER_PORT}
MQTT_CLIENT_ID=${MQTT_CLIENT_ID}
MQTT_USERNAME=${MQTT_USERNAME}
MQTT_PASSWORD=${MQTT_PASSWORD}

# AI Processing (optional)
GEMINI_API_KEY=${GEMINI_API_KEY}

# Calendar URL Override (optional)
CALENDAR_URL_OVERRIDE=${CALENDAR_URL_OVERRIDE}
```

### Configuration File

Copy and modify the configuration template:

```bash
cp config/config.yaml.example config/config.yaml
```

Key configuration sections:

#### MQTT Settings

```yaml
mqtt:
  enabled: true
  broker_url: "${MQTT_BROKER_URL}"
  broker_port: "${MQTT_BROKER_PORT}"
  client_id: "${MQTT_CLIENT_ID}"
  security: "username"
  auth:
    username: "${MQTT_USERNAME}"
    password: "${MQTT_PASSWORD}"
```

#### AI Event Processing

```yaml
ai_processor:
  api_key: "${GEMINI_API_KEY}"
  shortening:
    enabled: true
    model: "gemini-2.5-pro"
    max_length: 25
    flags_enabled: true
    cache_enabled: true
```

#### Home Assistant Discovery

```yaml
home_assistant:
  enabled: true
  discovery_prefix: "homeassistant"
  discovery_config: "config/ha_discovery.yaml"
```

## Usage

### Basic Event Processing

```bash
# Dry run (no MQTT publishing)
poetry run python -m core --dry-run

# Full processing with MQTT publishing
poetry run python -m core

# Custom configuration file
poetry run python -m core --config /path/to/config.yaml
```

### Specific Operations

```bash
# Scrape events only
poetry run python -m core scrape

# Publish to MQTT only
poetry run python -m core mqtt

# Generate ICS calendar
poetry run python -m core calendar

# Start web server
poetry run python -m core web-server

# Test all integrations
poetry run python -m core all-integrations
```

### Home Assistant Integration

The system publishes to these MQTT topics:

- `twickenham_events/events/next` - Next upcoming event
- `twickenham_events/events/all_upcoming` - All upcoming events
- `twickenham_events/status` - System status and health

Home Assistant entities are auto-discovered:

- `binary_sensor.twickenham_events_status` - System online/offline status
- `sensor.twickenham_events_next` - Next event details with emoji and short name
- `sensor.twickenham_events_all_upcoming` - Complete events list

## Architecture

### Modular Design

- `core/twick_event.py` - Main event processing pipeline
- `core/event_icons.py` - Emoji and icon assignment logic
- `core/event_shortener.py` - AI-powered name shortening
- `core/discovery.py` - Home Assistant MQTT discovery
- `core/web_server.py` - HTTP server for calendar and status endpoints

### Event Processing Pipeline

1. **Scraping**: Fetch events from Richmond Council website
2. **Normalization**: Parse and validate dates, times, and crowd sizes
3. **AI Processing**: Generate shortened names with optional country flags
4. **Emoji Assignment**: Apply priority-based emoji logic (🏆 for finals, 🏉 for rugby, 📅 for general events)
5. **MQTT Publishing**: Send structured data to Home Assistant
6. **Calendar Export**: Generate ICS files for external calendar apps

### Emoji System

The modular emoji system (`core/event_icons.py`) provides:

- **Priority Logic**: Finals → Trophy emoji (🏆), Sport-specific → Sport emoji (🏉), Fallback → Calendar (📅)
- **Unicode Support**: Full emoji character counting for display width calculations
- **Length Validation**: Ensures emoji + text combinations fit within configured limits

## Testing

Run the test suite:

```bash
# All tests
poetry run pytest

# Specific test categories
poetry run pytest tests/test_event_icons.py      # Emoji functionality
poetry run pytest tests/test_event_shortener.py  # AI shortening
poetry run pytest tests/test_emoji_integration.py # Integration tests

# With coverage
poetry run pytest --cov=core
```

## Development

### Code Quality

```bash
# Linting and formatting
poetry run ruff check .
poetry run ruff format .

# Pre-commit hooks
poetry run pre-commit run --all-files
```

### Environment Testing

```bash
# Test environment variable loading
python test_env_vars.py
```

## Troubleshooting

### MQTT Connection Issues

1. Verify broker URL and credentials in `.env`
2. Check firewall settings for MQTT port
3. Review MQTT logs: `poetry run python -m core mqtt --dry-run`

### AI Shortening Problems

1. Verify `GEMINI_API_KEY` in environment
2. Check API quotas and rate limits
3. Review shortening cache: `output/event_name_cache.json`

### Home Assistant Discovery

1. Ensure `discovery_prefix` matches HA MQTT configuration
2. Check HA logs for discovery message processing
3. Verify MQTT retain flags are enabled

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-functionality`
3. Follow code quality standards: `poetry run pre-commit run --all-files`
4. Ensure tests pass: `poetry run pytest`
5. Submit a pull request

## Support

- **Issues**: [GitHub Issues](https://github.com/ronschaeffer/twickenham_events/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ronschaeffer/twickenham_events/discussions)
