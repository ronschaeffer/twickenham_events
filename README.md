# Twickenham Events

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Event scraping & publishing system for Twickenham Stadium that exposes events to Home Assistant over MQTT using a **single unified device-level discovery payload** (compact component map) plus robust availability & Last Will handling.

This project focuses on: deterministic event normalization, resilient MQTT lifecycle handling (LWT + availability), compact Home Assistant discovery, optional AI enrichment, and extensive validation / hygiene tooling to keep retained topics clean.

---

## Table of Contents

1. Features
2. Installation
3. Configuration (Environment + YAML)
4. MQTT Topics & Payload Schemas
5. Unified Discovery Bundle (Structure & Example)
6. Status Payload & Diagnostics Fields
7. Service Modes & CLI Reference
8. AI Processing & Shortening Pipeline
9. Emoji & Icon System (Rules & Priority)
10. Date & Time Normalization
11. Availability & LWT Semantics
12. Legacy Migration (Per-Entity → Unified Bundle)
13. Caching & Error Handling Strategy
14. Validation & Hygiene Tooling
15. Security / Privacy Considerations
16. Performance Characteristics
17. Testing Strategy Overview
18. Roadmap / Future Enhancements
19. FAQ
20. Contributing / Support

---

## Features

- **Unified Device Discovery**: One retained discovery topic (`homeassistant/device/twickenham_events/config`) with an `entities` map; atomic updates & fewer retained topics.
- **Event Scraping**: Normalizes future Twickenham events (dates, times, metadata) from source pages.
- **Structured MQTT Publishing**: Retained JSON topics: `status`, `events/all_upcoming`, `events/next`, `events/today`.
- **Availability + LWT**: Explicit availability topic + MQTT Last Will fallback (auto-offline if process dies).
- **AI Event Processing (optional)**: Gemini-based shortening & type/icon hints with caching & reprocess tooling.
- **Emoji & Icon Enrichment**: Deterministic + AI assisted badges (trophies, rugby ball, calendar, etc.).
- **ICS Calendar Export**: Optionally export/serve ICS (and JSON) calendar artifacts.
- **Dashboard Adaptation Tools**: Backup/patch & YAML export scripts for Lovelace dashboards during migrations.
- **Discovery Hygiene**: Validator + purge script ensures legacy per-entity/button discovery topics removed.
- **Strict Validation Mode**: Enforces expected component set `{status,last_run,upcoming,next,today,refresh,clear_cache}`.
- **Extensive Tests**: 450+ tests spanning scraping, AI, discovery, service loop, and LWT.

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
```

### Configuration File

Copy and modify the configuration template:

```bash
cp config/config.yaml.example config/config.yaml
```

Key configuration sections:

#### MQTT Settings (with Last Will)

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
  topics:
    all_upcoming: "twickenham_events/events/all_upcoming"
    next: "twickenham_events/events/next"
    status: "twickenham_events/status"
    today: "twickenham_events/events/today"
  last_will:
    topic: "twickenham_events/status"
    payload: '{"status": "offline", "reason": "unexpected_disconnect"}'
    qos: 1
    retain: true
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

Discovery is fully programmatic (no static YAML file required). Configure only the prefix:

```yaml
home_assistant:
  enabled: true
  discovery_prefix: "homeassistant"
```

#### Application Identity / Origin URL

# Twickenham Events

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

MQTT publishing of Twickenham Stadium events for Home Assistant. Scrapes public event pages, normalizes data, publishes retained topics, and advertises a device via Home Assistant discovery. Optional AI processing shortens event names and suggests types.

---

## Table of Contents

1. Features
2. Prerequisites
3. Installation
4. Configuration
5. Usage
6. MQTT Topics
7. Home Assistant Discovery
8. AI Processing
9. Testing
10. Development
11. Troubleshooting
12. Deployment (systemd)
13. Contributing
14. License

---

## Features

- Unified device discovery (single retained JSON with entities map)
- Retained topics: status, all_upcoming, next, today
- Availability topic and Last Will support
- Optional AI event processing (shortening, type hints) with on-disk cache
- ICS export of events (optional)
- CLI service loop with command topics (refresh, clear_cache)

## Prerequisites

- Python 3.11+
- Poetry
- MQTT broker (for Home Assistant integration)

## Installation

```bash
git clone https://github.com/ronschaeffer/twickenham_events.git
cd twickenham_events
poetry install
# Optional AI extras
poetry install --with ai
```

## Configuration

Copy the example config and set environment variables in `.env`.

```bash
cp config/config.yaml.example config/config.yaml
```

Environment variables (examples):

```bash
MQTT_BROKER_URL=${MQTT_BROKER_URL}
MQTT_BROKER_PORT=${MQTT_BROKER_PORT}
MQTT_CLIENT_ID=${MQTT_CLIENT_ID}
MQTT_USERNAME=${MQTT_USERNAME}
MQTT_PASSWORD=${MQTT_PASSWORD}
GEMINI_API_KEY=${GEMINI_API_KEY}
```

Key config sections (excerpt):

```yaml
mqtt:
  enabled: true
  broker_url: "${MQTT_BROKER_URL}"
  broker_port: "${MQTT_BROKER_PORT}"
  client_id: "${MQTT_CLIENT_ID}"
  auth:
    username: "${MQTT_USERNAME}"
    password: "${MQTT_PASSWORD}"
  topics:
    status: "twickenham_events/status"
    all_upcoming: "twickenham_events/events/all_upcoming"
    next: "twickenham_events/events/next"
    today: "twickenham_events/events/today"
  last_will:
    topic: "twickenham_events/status"
    payload: '{"status":"offline","reason":"unexpected_disconnect"}'
    qos: 1
    retain: true

ai_processor:
  api_key: "${GEMINI_API_KEY}"
  shortening:
    enabled: false
    model: "gemini-2.5-pro"
    max_length: 25
    flags_enabled: true
    cache_enabled: true
  type_detection:
    enabled: false
    cache_dir: "output/cache"

home_assistant:
  enabled: true
  discovery_prefix: "homeassistant"
```

## Usage

Entry point: `twick-events`

```bash
poetry run twick-events scrape      # Scrape only
poetry run twick-events mqtt        # Scrape + publish
poetry run twick-events calendar    # Export ICS/JSON
poetry run twick-events all         # Scrape + MQTT + calendar
poetry run twick-events status      # Show configuration/status
poetry run twick-events service     # Long-running loop
```

Command topics (published by Home Assistant buttons):

- twickenham_events/cmd/refresh
- twickenham_events/cmd/clear_cache

Output files are written to `output/` (including `upcoming_events.json`, `scrape_results.json`, optional `twickenham_events.ics`). AI caches are under `output/cache/`.

## MQTT Topics

| Topic                                 | Retained |
| ------------------------------------- | -------- |
| twickenham_events/status              | Yes      |
| twickenham_events/events/all_upcoming | Yes      |
| twickenham_events/events/next         | Yes      |
| twickenham_events/events/today        | Yes      |
| twickenham_events/availability        | Yes      |
| twickenham_events/cmd/refresh         | No       |
| twickenham_events/cmd/clear_cache     | No       |

## Home Assistant Discovery

The service publishes a single device discovery payload to:

```
homeassistant/device/twickenham_events/config
```

Entities include: status, last_run, upcoming, next, today, refresh (button), clear_cache (button).

## AI Processing

AI features are optional and disabled by default. When enabled, the AI processor:

- Shortens event names within a configurable length budget
- Suggests type hints (e.g., rugby, concert)
- Uses an on-disk cache to avoid repeat API calls

Cache management via CLI:

```bash
poetry run twick-events cache clear
poetry run twick-events cache stats
poetry run twick-events cache reprocess
```

See `docs/AI_PROCESSING.md` for details.

## Testing

```bash
poetry run pytest
```

## Development

Common Makefile targets:

- make check        – Lint (no changes)
- make fix          – Lint and auto-fix
- make format       – Format code
- make clean        – Remove caches (`__pycache__`, .pytest_cache, .ruff_cache)
- make test         – Run tests
- make ci-check     – Lint + tests

See `docs/DEVELOPMENT.md` for more.

## Troubleshooting

- Validate MQTT/discovery topics with helper scripts
- Confirm a single running instance per MQTT client_id
- For AI issues, verify `${GEMINI_API_KEY}` and use cache commands above

## Deployment (systemd)

User service unit and steps are documented in `systemd/README.md`.

## Contributing

- Run lint and tests before submitting changes
- Open an issue or PR describing the change and any discovery/entity impacts

## License

MIT License (see `LICENSE`).

---

## Additional documentation

- docs/DEVELOPMENT.md – local development notes and Makefile targets
- docs/GITHUB_ACTIONS.md – CI notes
- systemd/README.md – deployment with systemd
- docs/AI_PROCESSING.md – AI features, configuration, and cache management
  "last_run_iso": "2025-11-27T18:20:05Z",
