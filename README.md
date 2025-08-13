# Twickenham Events

## Table of Contents

- Badges
- Description
- Features
- Prerequisites
- Installation
- Configuration
- Usage
- MQTT topics and payloads
- Unified HA discovery (bundle)
- Home Assistant cards (links)
- Validation tools
- Emoji/icon rules
- Notes and troubleshooting
- Testing
- Support
- Contributing
- License

## Badges

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## Description

Event scraping and MQTT publishing for Twickenham Stadium with a single, unified Home Assistant discovery bundle, consistent payload schemas, and explicit availability/LWT handling.

Source: Upcoming event data is scraped and normalized from the Richmond Council website.

## Features

- Single device-level discovery topic with a compact components map (cmps)
- Event scraping and normalization from the Richmond Council website
- Retained MQTT topics for status, all_upcoming, next, today, and availability
- Flat attributes on the next sensor; grouped events_json for upcoming
- Explicit availability online/offline alongside LWT
- Optional AI shortening/enrichment with caching
- Strict validator with cross-topic checks; tests and linting

## Prerequisites

Prerequisites:
- Python 3.11+
- Poetry

## Installation

Steps:
1) Clone and enter the repo
2) Install dependencies
3) (Optional) Install AI extras

## Configure

Environment (.env or your environment):
- MQTT_BROKER_URL=${MQTT_BROKER_URL}
- MQTT_BROKER_PORT=${MQTT_BROKER_PORT}
- MQTT_CLIENT_ID=${MQTT_CLIENT_ID}
- MQTT_USERNAME=${MQTT_USERNAME}
- MQTT_PASSWORD=${MQTT_PASSWORD}
- GEMINI_API_KEY=${GEMINI_API_KEY} (optional)

Config file:
- Copy config/config.yaml.example to config/config.yaml and adjust values
- Set home_assistant.discovery_prefix (default: homeassistant)
- Ensure app.url points to your project/repo for device details in HA

MQTT excerpt:
- topics:
  - status: twickenham_events/status
  - all_upcoming: twickenham_events/events/all_upcoming
  - next: twickenham_events/events/next
  - today: twickenham_events/events/today
  - availability: twickenham_events/availability
- last_will: retained JSON for unexpected disconnect

## MQTT topics and payloads

Topics (retained unless noted):
- twickenham_events/status: status + diagnostics
- twickenham_events/events/all_upcoming: structured list with events_json
- twickenham_events/events/next: next event with flat attributes; state = fixture
- twickenham_events/events/today: today summary
- twickenham_events/availability: online/offline
- twickenham_events/cmd/refresh (non-retained): trigger scrape
- twickenham_events/cmd/clear_cache (non-retained)

Status (example):
- status: active | no_events | error
- event_count, ai_error_count, publish_error_count
- ai_enabled, sw_version
- last_updated, last_run_ts/iso (if applicable)

All upcoming (example, trimmed):
- count: integer
- last_updated: ISO timestamp
- events_json:
  - by_month: [
    { key, label, days: [ { date, label, events: [ { fixture, fixture_short, start_time, emoji, icon, crowd } ] } ] }
  ]

Next (flat attributes, state template reads fixture):
- fixture (state)
- date
- start_time
- crowd
- fixture_short
- event_index
- event_count
- emoji
- icon
- last_updated

Today:
- date
- has_event_today (bool)
- events_today (int)
- events (optional list of today’s events with fixture/start_time)
- last_updated

## Unified HA discovery (bundle)

Single retained discovery payload at:
- homeassistant/device/twickenham_events/config

Includes:
- dev: compressed device metadata (ids, name, mf, mdl, sw)
- o: { name, sw, url }
- cmps: map of components → minimal discovery specs
- availability_topic: twickenham_events/availability

Components (typical):
- status: sensor.twickenham_events_status
- last_run: sensor.twickenham_events_last_run
- upcoming: sensor.twickenham_events_upcoming (value_json.count)
- next: sensor.twickenham_events_next (value_json.fixture)
- today: sensor.twickenham_events_today
- refresh: button.twickenham_events_refresh
- clear_cache: button.twickenham_events_clear_cache
- event_count (optional diagnostic sensor)

## Home Assistant cards (links)

These example cards live in the repository. Link to these files to keep your dashboards aligned with updates.

<!-- BEGIN: ha_cards_list (auto-managed) -->

- md twickenham events upcoming: [ha_card/md_twickenham_events_upcoming.yaml](ha_card/md_twickenham_events_upcoming.yaml)
  - Renders `events_json.by_month[].days[].events[]` with `ev.start_time`, `ev.emoji`, `ev.fixture`, `ev.crowd`.
- mshrm twickenham events short card: [ha_card/mshrm_twickenham_events_short_card.yaml](ha_card/mshrm_twickenham_events_short_card.yaml)
  - Uses `sensor.twickenham_events_next` with flat attributes (date, start_time, fixture_short, emoji, event_index, event_count); state is the full `fixture`.

<!-- END: ha_cards_list -->

## CLI and service

Entry point: twick-events
- scrape: one-time scrape
- mqtt: scrape + publish retained topics and discovery; sets availability online
- calendar: export ICS/JSON
- all: scrape + mqtt + calendar
- status: show config/status
- cache: AI cache tools
- service: long-running loop with interval, availability, and command topics

Examples:
- poetry run twick-events scrape
- poetry run twick-events mqtt
- poetry run twick-events service --interval 3600

Artifacts:
- output/upcoming_events.json: flat list for quick inspection
- output/scrape_results.json: raw+summaries bundle
- output/*.ics: calendar export

## Validation tools

- scripts/mqtt_validate.py: validates retained topics; --strict enforces cross-topic rules and discovery
- scripts/validate_all.py: orchestrates JSON/ICS and MQTT checks

Key strict checks:
- status.event_count == all_upcoming.count
- next.fixture matches first event in events_json; next.date matches first day
- discovery cmps include the expected components

## Emoji/icon rules

Priority logic picks a single emoji and a separate icon per event. Examples: finals (trophy) outrank rugby; American football outranks soccer; concerts use music; fallback calendar.

## Notes and troubleshooting

- Availability: We publish twickenham_events/availability="online" during mqtt/service; LWT covers ungraceful exits.
- HA cards: Use next’s flat attributes (date, start_time, fixture_short, emoji, event_index, event_count) and upcoming’s events_json fields.
- Count parity: Status.event_count, all_upcoming.count, and the first event alignment are validated in strict mode.
- Source: Events are scraped from the Richmond Council website; network or page changes can temporarily reduce event_count.

---

## Testing

Run the test suite:

```bash
poetry run pytest -q
```

## Support

Open an issue on GitHub with details and steps to reproduce.

## Contributing

PRs are welcome. Please run linting and tests before submitting.

## License

MIT License.
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

# Calendar URL Override (optional)
CALENDAR_URL_OVERRIDE=${CALENDAR_URL_OVERRIDE}
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

The unified discovery payload includes a compact origin block (`o`) with `name`, `sw`, and `url`.
Set `app.url` (or `app.repository_url` / `app.project_url`) in `config.yaml` to control the link exposed in Home Assistant's device details.

Example `app` section (excerpt) with URL:

```yaml
app:
  unique_id_prefix: "twickenham_events"
  name: "Twickenham Events"
  manufacturer: "ronschaeffer" # (previously "Ron Schaeffer")
  model: "Twick Events" # (previously "Event Scraper")
  sw_version: "0.1.0"
  url: "https://github.com/ronschaeffer/twickenham_events"
```

### Configuration Reference (Key Fields)

| Section                 | Key                    | Type     | Default / Example                     | Purpose                                          |
| ----------------------- | ---------------------- | -------- | ------------------------------------- | ------------------------------------------------ |
| scraping                | url                    | str      | Richmond Council URL                  | Source page for events                           |
| scraping                | timeout                | int      | 10                                    | HTTP timeout seconds                             |
| event_rules             | end_of_day_cutoff      | HH:MM    | 23:00                                 | Marks end-of-day aggregation cutoff              |
| event_rules             | next_event_delay_hours | int      | 1                                     | Grace buffer after start before marking complete |
| mqtt                    | broker_url             | str      | env                                   | MQTT host                                        |
| mqtt                    | broker_port            | int      | env                                   | MQTT port                                        |
| mqtt                    | client_id              | str      | env                                   | Stable client identifier (for LWT)               |
| mqtt.topics             | status                 | str      | twickenham_events/status              | Primary state + attributes topic                 |
| mqtt.topics             | all_upcoming           | str      | twickenham_events/events/all_upcoming | List of future events                            |
| mqtt.topics             | next                   | str      | twickenham_events/events/next         | Single next event                                |
| mqtt.topics             | today                  | str      | twickenham_events/events/today        | Today events summary                             |
| mqtt.last_will          | payload                | JSON str | offline status JSON                   | Broker-published on disconnect                   |
| home_assistant          | discovery_prefix       | str      | homeassistant                         | Root discovery prefix                            |
| app                     | unique_id_prefix       | str      | twickenham_events                     | Namespace for entities                           |
| app                     | url                    | str      | GitHub repo                           | Exposed in discovery origin block                |
| ai_processor.shortening | enabled                | bool     | false/true                            | Toggle AI shortening                             |
| ai_processor.shortening | model                  | str      | gemini-2.5-pro                        | AI model name                                    |
| ai_processor.shortening | max_length             | int      | 25                                    | Display unit budget                              |
| ai_processor.shortening | flags_enabled          | bool     | true                                  | Add country flags where space allows             |
| calendar                | enabled                | bool     | true                                  | Export ICS/JSON calendar                         |
| calendar.scope          | include_future_days    | int      | 365                                   | Calendar horizon                                 |

> Tip: Most configuration values support environment interpolation ("${VAR}") enabling secrets externalization.

## Usage

### CLI Overview

Entry point script: `twick-events`

| Command  | Description                                                                            |
| -------- | -------------------------------------------------------------------------------------- |
| scrape   | One-time scrape (prints summary, writes output JSON files)                             |
| mqtt     | Scrape + publish to MQTT                                                               |
| calendar | Scrape + export calendar                                                               |
| all      | Scrape + MQTT + calendar                                                               |
| status   | Show configuration/system status                                                       |
| cache    | Manage AI caches (clear, stats, reprocess)                                             |
| service  | Continuous daemon: periodic scrape + publish, command topics, availability & discovery |

### Basic Event Processing

```bash
poetry run twick-events scrape      # Scrape only
poetry run twick-events mqtt        # Scrape + publish
poetry run twick-events all         # Scrape + MQTT + calendar
poetry run twick-events calendar    # Calendar only
poetry run twick-events status      # Show status
```

### Service Mode

### Output Artifacts (Scrape / MQTT / Calendar)

Running the various commands produces a consistent set of output channels for consumers:

| Channel / Artifact            | Produced By            | Path / Topic                                           | Contents / Purpose                                                |
| ----------------------------- | ---------------------- | ------------------------------------------------------ | ----------------------------------------------------------------- |
| Terminal Summary              | `scrape`, `mqtt`, `all`| stdout                                                 | Human-readable scrape statistics & next event details             |
| `output/upcoming_events.json` | `scrape`, `mqtt`, `all`| Local filesystem (or `--output` dir)                   | Flat list of all upcoming events (array of event objects)         |
| `output/scrape_results.json`  | `scrape`, `mqtt`, `all`| Local filesystem (or `--output` dir)                   | Rich bundle: raw_events, summarized_events (per-day), next event  |
| MQTT Status Topic             | `mqtt`, `service`, `all`| `twickenham_events/status` (retained)                 | Status + diagnostics (event_count, errors, metadata)              |
| MQTT Events (all_upcoming)    | `mqtt`, `service`, `all`| `twickenham_events/events/all_upcoming` (retained)    | List of future events (structured)                               |
| MQTT Events (next)            | `mqtt`, `service`, `all`| `twickenham_events/events/next` (retained)            | Single next event wrapper                                        |
| MQTT Events (today)           | `mqtt`, `service`, `all`| `twickenham_events/events/today` (retained)           | Today events + count                                             |
| Calendar (ICS)                | `calendar`, `all`       | `output/<configured>.ics`                              | iCalendar export for external calendar apps                      |
| Discovery Bundle              | `mqtt`, `service`, `all`| `homeassistant/device/twickenham_events/config`       | Unified HA device-level discovery JSON                           |

`upcoming_events.json` schema (example) (updated for parity with MQTT all_upcoming):

```json
{
  "events": [
    {
      "fixture": "Women's Rugby World Cup Final",
      "title": "Women's Rugby World Cup Final",   // added: canonical title (fallback to fixture/name)
      "date": "2025-09-27",
      "start_time": "12:30",
      "crowd": "82,000"
    }
  ],
  "count": 8,                 // added: total events (must match events.length)
  "generated_ts": 1755030088, // epoch seconds OR ISO string
  "last_updated": "2025-08-12T22:39:57.123456" // ISO-8601 timestamp (mirrors MQTT)
}
```

Count Parity Rule:
The number of events MUST match across: ICS (VEVENT count), upcoming_events.json (events.length / count), and MQTT `events/all_upcoming`. The `validate_all.py` aggregator enforces this.

### Validation & Hygiene Tooling (Extended)

New validator scripts (all in `scripts/`):

| Script | Purpose | Key Flags |
| ------ | ------- | --------- |
| `ics_validate.py` | Structural ICS checks (BEGIN/END, VEVENT blocks, required DTSTART/SUMMARY/UID) | `--file`, `--allow-empty`, `--min-events` |
| `upcoming_events_validate.py` | Schema + ordering + duplication checks for upcoming_events.json | `--file`, `--allow-empty`, `--require-generated-ts` |
| `mqtt_validate.py` | Runtime retained topic validation (optionally strict cross-topic) | `--broker`, `--port`, `--timeout`, `--run-service`, `--strict`, `--purge-discovery` |
| `validate_all.py` | Orchestrates all validators + cross-artifact count parity | `--scrape-run`, `--broker`, `--strict`, `--allow-empty-upcoming`, `--mqtt-run-service` |

Quick examples:

```bash
# Run all (ICS + JSON + scrape refresh) without MQTT
poetry run python scripts/validate_all.py --scrape-run --ics output/twickenham_events.ics --upcoming output/upcoming_events.json

# Include MQTT strict validation with fresh scrape & service publish
poetry run python scripts/validate_all.py \
  --scrape-run --mqtt --strict --mqtt-run-service \
  --ics output/twickenham_events.ics --upcoming output/upcoming_events.json \
  --broker $MQTT_BROKER --mqtt-port $MQTT_PORT
```

Exit Codes:
0 success; 1 validation mismatch (including count parity); 2 IO / configuration issues.

Logging Enhancements:
`mqtt_client.publish_events` now logs the full `status` payload (DEBUG) before publish and guarantees `last_updated` is present (defensive hardening for validators).

Each event includes a `date` field so dashboards and other consumers can display dates without cross-referencing day summaries.

Use this file for quick local inspection or downstream scripts (e.g. custom exporters) without parsing the richer `scrape_results.json` bundle.

```bash
poetry run twick-events service              # Continuous
poetry run twick-events service --interval 3600  # 1h interval
poetry run twick-events service --once       # Single cycle (keeps availability online)
```

Command Topics (mirrored as HA buttons):

- `twickenham_events/cmd/refresh`
- `twickenham_events/cmd/clear_cache`

### Availability & LWT

- Explicit availability topic: `twickenham_events/availability` (online/offline publishes)
- LWT ensures immediate offline state if process terminates ungracefully (status topic or availability fallback).
- Unified device discovery references availability so all components reflect state.

### Home Assistant Integration (Unified Device Bundle)

Single retained discovery topic:

```
homeassistant/device/twickenham_events/config
```

Entities (entities map) included:

| Component   | Entity ID                            | Purpose                              |
| ----------- | ------------------------------------ | ------------------------------------ |
| status      | sensor.twickenham_events_status      | Status + attributes from status JSON |
| last_run    | sensor.twickenham_events_last_run    | Last scrape timestamp                |
| upcoming    | sensor.twickenham_events_upcoming    | Count + all_upcoming attributes      |
| next        | sensor.twickenham_events_next        | Next event fixture + attributes      |
| today       | sensor.twickenham_events_today       | Today event count + list             |
| refresh     | button.twickenham_events_refresh     | Manual immediate scrape              |
| clear_cache | button.twickenham_events_clear_cache | Clear AI cache                       |

Optional component (may or may not be present depending on invocation flags):

| Component     | Entity ID                            | Purpose / Rationale                                                                                                                                                                                |
| ------------- | ------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| event_count\* | sensor.twickenham_events_event_count | Dedicated numeric count of all future events. Redundant with `event_count` attribute on `status` but convenient for: graphs, statistics integration, badges without templating. Marked diagnostic. |

\*If omitted you can still access the value via `state_attr('sensor.twickenham_events_status','event_count')`. The unified design keeps the extra entity optional to avoid clutter for minimal installs.

Legacy per-entity/button discovery topics are purged automatically on connect.

### MQTT Topics & Payload Schemas

| Topic                                 | Retained | Description                                 |
| ------------------------------------- | -------- | ------------------------------------------- |
| twickenham_events/status              | Yes      | Core status + diagnostics + roll-up metrics |
| twickenham_events/events/all_upcoming | Yes      | Full list of upcoming events (array)        |
| twickenham_events/events/next         | Yes      | Single next event object wrapper            |
| twickenham_events/events/today        | Yes      | Events belonging to current day + count     |
| twickenham_events/availability        | Yes      | Online / offline presence heartbeat         |
| twickenham_events/cmd/refresh         | No       | Trigger immediate scrape cycle              |
| twickenham_events/cmd/clear_cache     | No       | Clear AI shortening cache                   |

#### Sample Status Payload (Active – No Errors)

```json
{
  "status": "active",
  "event_count": 12,
  "last_run_ts": 1732736405,
  "last_run_iso": "2025-11-27T18:20:05Z",
  "interval_seconds": 3600,
  "ai_enabled": true,
  "ai_error_count": 0,
  "publish_error_count": 0,
  "error_count": 0,
  "sw_version": "0.1.0",
  "errors": []
}
```

#### Sample Status Payload (Error – With Structured Errors)

```json
{
  "status": "error",
  "event_count": 0,
  "last_run_ts": 1732736466,
  "last_run_iso": "2025-11-27T18:21:06Z",
  "interval_seconds": 3600,
  "ai_enabled": true,
  "ai_error_count": 1,
  "publish_error_count": 0,
  "error_count": 2,
  "sw_version": "0.1.0",
  "errors": [
    { "message": "scrape timeout after 10s", "ts": 1732736466 },
    { "message": "ai shorten timeout", "ts": 1732736466 }
  ]
}
```

#### Sample Upcoming Events Payload (Truncated)

```json
{
  "events": [
    {
      "fixture": "England v Australia",
      "fixture_short": "ENG v AUS",
      "date": "2025-11-02",
      "start_time": "17:00",
      "crowd": "82,000",
      "emoji": "🏉",
      "icon": "mdi:rugby"
    },
    {
      "fixture": "Taylor Swift | The Eras Tour",
      "fixture_short": "Taylor Swift",
      "date": "2025-11-09"
    }
  ]
}
```

#### Today Events Payload

```json
{
  "events_today": 1,
  "events": [{ "fixture": "England v Australia", "start_time": "17:00" }]
}
```

### Unified Discovery Bundle Structure

The single retained discovery config (topic: `homeassistant/device/twickenham_events/config`) publishes a JSON payload with keys:

| Key                                       | Purpose                                            |
| ----------------------------------------- | -------------------------------------------------- |
| dev                                       | Compressed device info (ids, name, mf, mdl, sw)    |
| o                                         | Origin metadata { name, sw, url }                  |
| entities                                  | Entity map (logical name → minimal discovery spec) |
| state_topic                               | Base status topic (attributes source)              |
| availability_topic                        | Online/offline tracking                            |
| payload_available / payload_not_available | Availability literals                              |

> Device-level changes (adding/removing components) happen atomically with one retained update, minimizing HA restart issues and discovery orphaning.

### Status Payload & Diagnostics Fields

| Field               | Type          | Description                                                     |
| ------------------- | ------------- | --------------------------------------------------------------- |
| status              | str           | Logical data state (active / no_events / error)                |
| event_count         | int           | Total future events known at last run                           |
| last_run_ts         | int           | Unix epoch seconds of last scrape                               |
| last_run_iso        | str           | ISO-8601 timestamp of last scrape                               |
| interval_seconds    | int           | Service scrape interval in seconds                              |
| ai_enabled          | bool          | AI shortening currently active                                  |
| ai_error_count      | int           | Cumulative AI processing errors                                 |
| publish_error_count | int           | MQTT publish errors since start                                 |
| error_count         | int           | Count of currently retained (deduped) structured errors         |
| sw_version          | str           | Software version (mirrors device block)                         |
| errors              | list[object]  | Recent unique errors (each: {"message": str, "ts": epoch int}) |

Downstream automations can create template sensors for uptime, last success, or error alerts without adding more discovery entities.

#### Status vs Availability

The `status` field and the `availability` topic serve different purposes:

| Aspect        | `status` field                                             | `twickenham_events/availability` topic |
| ------------- | ---------------------------------------------------------- | -------------------------------------- |
| Meaning       | Data/content state of the most recent successful cycle    | Service process liveness (online/offline) |
| Current Values| `active`, `no_events`, `error`                             | `online`, `offline`                    |
| Retained In   | `twickenham_events/status` JSON payload                    | Dedicated retained string              |
| Triggered By  | Scrape + publish pipeline logic                           | Service startup / graceful shutdown    |

Current implemented `status` values:

* active: At least one future event was scraped and published. The `event_count` attribute is > 0.
* no_events: Scrape succeeded but produced zero future events (off‑season / gap days). Distinct from an error so dashboards can show an empty-but-healthy state.
* error: A scrape cycle failed or produced zero events alongside scrape/processing errors. Errors list (and `error_count`) included for diagnostics; prior retained data may remain in other topics until next successful cycle.

Rationale for separating availability:

* A service can be `online` (process running) while the latest `status` is `no_events` (normal) or eventually `error` (transient failure).
* On restart, Home Assistant instantly knows if the service is alive (availability) even before first scrape completes; `status` then updates with content state.

Automation tips:

* Treat `availability` = offline for alerting about process failure (missed heartbeats / container stopped).
* Treat `status` = no_events as low severity / informational.
* Treat `status` = error to trigger a retry or notification summarizing `errors` list contents.

Example template handling all states:

```jinja2
{% set st = state_attr('sensor.twickenham_events_status','status') %}
{% if st == 'active' %}
  OK
{% elif st == 'no_events' %}
  No upcoming events
{% elif st == 'error' %}
  Error (data stale)
{% else %}
  Unknown
{% endif %}
```

#### Error Types Captured (errors list & counters)

The `errors` list aggregates human-readable messages (often concise) for recent failures; counters track categories without retaining full history.

| Category                | Source / Trigger Examples                                                           | Where Reflected                                             | Typical Message Shape                               |
| ----------------------- | ----------------------------------------------------------------------------------- | ----------------------------------------------------------- | --------------------------------------------------- |
| Scrape / Network        | HTTP timeout, non-200 status, connection error, HTML fetch failure                  | `errors`, may increment publish_error_count if side-effects | `scrape timeout after 10s`, `fetch 502 Bad Gateway` |
| Parsing / Normalization | Date/time ambiguity, unexpected layout, numeric conversion issues                   | `errors`                                                    | `ambiguous date '2/11' skipped`                     |
| AI Processing           | API timeout, quota exceeded, malformed JSON/response                                | `errors`, `ai_error_count`                                  | `ai shorten timeout`, `ai invalid response`         |
| MQTT Publish            | Broker unavailable, auth failure, socket error                                      | `errors`, `publish_error_count`                             | `mqtt publish failed: ConnectionRefusedError`       |
| Validation / Invariants | Cross-topic mismatch (next not first upcoming), count mismatch in strict validation | `errors`                                                    | `validation: next mismatch vs events[0]`            |
| Legacy Cleanup          | Failure deleting historical discovery topic                                         | `errors`                                                    | `purge legacy discovery failed <topic>`             |
| Cache I/O               | Read/write error with AI cache files                                                | `errors`, may increment ai_error_count                      | `cache read error: <exception>`                     |

Retention Strategy: The list is deduplicated across cycles (cumulative unique messages) and truncated to the most recent 25 structured entries. Each entry is immutable once recorded. Counters persist for the service lifetime and reset on restart.

#### Structured Error Objects & Truncation (Examples)

The `errors` field now carries structured objects, not plain strings. Each object:

```jsonc
{ "message": "scrape timeout after 10s", "ts": 1732736466 }
```

Key points:

1. Deduplication: If the same message recurs in later cycles, it is not duplicated; the original entry is preserved (no frequency inflation).
2. Cumulative Retention: New unique errors append until the cap (25). When exceeding the cap, the oldest entries are dropped (FIFO) to maintain a stable size.
3. Timestamp (`ts`): Epoch seconds when the error was first registered (not updated on repeats).
4. `error_count`: Mirrors the current length of `errors` (post‑dedupe, post‑truncation).
5. Cache Reset (tests / maintenance): Internal helper can reset caches; production usage normally never resets mid‑process.

Home Assistant template examples:

Most recent error message (or blank):

```jinja2
{% set errs = state_attr('sensor.twickenham_events_status','errors') or [] %}
{% if errs %}{{ errs[-1].message }}{% else %}{{ '' }}{% endif %}
```

List all current error messages:

```jinja2
{% for e in state_attr('sensor.twickenham_events_status','errors') or [] %}
 - {{ e.message }} ({{ e.ts }})
{% endfor %}
```

Guard automation when entering error state (ignore transient no_events):

```jinja2
{% set st = states('sensor.twickenham_events_status') %}
{% if st == 'error' %}ALERT{% endif %}
```

If frequency counting is desired in the future, a `repeat_count` field could be added without breaking existing consumers (planned enhancement candidate).

### Service Modes & CLI Reference

| Mode     | Description                                                        | Recommended Use      |
| -------- | ------------------------------------------------------------------ | -------------------- |
| scrape   | Single scrape; stdout summary only                                 | Testing parsing      |
| mqtt     | Scrape then publish retained topics                                | Manual refresh cron  |
| calendar | Produce ICS / JSON exports                                         | Calendar integration |
| all      | Scrape + MQTT + calendar export                                    | Batch run            |
| status   | Show expanded config + environment                                 | Diagnostics          |
| cache    | AI cache actions (clear/stats/reprocess)                           | AI maintenance       |
| service  | Long-running loop with interval, availability, LWT, command topics | Primary deployment   |

Flags (service excerpt): `--interval <secs>`, `--once`, `--no-ai`, `--log-level DEBUG`, `--dry-run` (if added in future roadmap).

### AI Processing & Shortening Pipeline

Pipeline (if enabled):

1. Raw fixture → Pre-normalization (spacing, punctuation trimming)
2. Caching lookup (hashed original)
3. Gemini request (model configurable) with prompt template & flag rules
4. Length validation (character units incl. emoji width)
5. Optional flag insertion (only if room)
6. Persist into cache and attach `fixture_short`

Failure Handling: timeouts / API errors increment `ai_error_count` and fallback to original fixture without halting scraping. Cache prevents repeated API calls for stable historical events.

#### Example Lovelace Cards (Using Today Sensor)

Compact next + today summary (Markdown):

```yaml
type: markdown
content: |
  ## Twickenham Events
  **Next:** {{ states('sensor.twickenham_events_next') }}
  **Today Count:** {{ states('sensor.twickenham_events_today') }}
  {% set next = state_attr('sensor.twickenham_events_next','event') %}
  {% if next %}
  Date: {{ next.date }}
  Time: {{ next.start_time or 'TBD' }}
  {% endif %}
  Status: {{ states('sensor.twickenham_events_status') }}
```

Auto-entities style list of today's events (requires custom:template or auto-entities alternative):

```yaml
type: custom:template-entity-row
entity: sensor.twickenham_events_today
name: Today's Twickenham Events
state: >-
  {% set topic = states.sensor.twickenham_events_today %}
  {{ states('sensor.twickenham_events_today') }}
attributes: >-
  {% set today = states.sensor.twickenham_events_today.attributes %}
  {% if today and today.events_today|int > 0 %}
    {% for ev in today.get('events', []) %}
      - {{ ev.fixture_short or ev.fixture }} ({{ ev.start_time or 'TBD' }})\n
    {% endfor %}
  {% else %}No events today{% endif %}
```

Minimal glance entities:

```yaml
type: glance
entities:
  - entity: sensor.twickenham_events_next
    name: Next
  - entity: sensor.twickenham_events_today
    name: Today
  - entity: sensor.twickenham_events_upcoming
    name: Upcoming
  - entity: sensor.twickenham_events_status
    name: Status
```

Tile Card (Next Event focus):

```yaml
type: tile
entity: sensor.twickenham_events_next
name: Next Event
icon: mdi:calendar-clock
color: indigo
tap_action:
  action: more-info
hide_state: false
state_content:
  - state # fixture string (value from value_template)
  - last_updated
secondary_info: >-
  {% set ev = state_attr('sensor.twickenham_events_next','event') %}
  {% if ev %}
    {{ ev.date }} {{ ev.start_time or '' }}
  {% else %}
    No upcoming event
  {% endif %}
badges: >-
  {% set ev = state_attr('sensor.twickenham_events_next','event') %}
  {% if ev and ev.crowd %}
    Crowd: {{ ev.crowd }}
  {% endif %}
footer:
  type: fan-speed # simple horizontal control footer repurposed to show actions
  style: |
    ha-tile-fan-speed-row {
      --tile-color: var(--primary-color);
    }
  speeds:
    - name: Refresh
      icon: mdi:refresh
      speed: 1
      service: mqtt.publish
      service_data:
        topic: twickenham_events/cmd/refresh
        payload: "trigger"
    - name: Clear Cache
      icon: mdi:eraser
      speed: 2
      service: mqtt.publish
      service_data:
        topic: twickenham_events/cmd/clear_cache
        payload: "clear"
```

## Architecture

### Key Modules (Modern Path Names)

- `src/twickenham_events/scraper.py` – Event scraping & normalization
- `src/twickenham_events/mqtt_client.py` – Topic publishing (status, all_upcoming, next, today)
- `src/twickenham_events/discovery_helper.py` – Unified discovery + legacy cleanup
- `src/twickenham_events/service_support.py` – Availability & signal handling
- `src/twickenham_events/ai_processor.py` – AI shortening/type detection
- `src/twickenham_events/__main__.py` – CLI & service orchestration (LWT setup)

### Event Processing Pipeline

1. **Scraping**: Fetch events from Richmond Council website
2. **Normalization**: Parse and validate dates, times, and crowd sizes
3. **AI Processing**: Generate shortened names with optional country flags
4. **Emoji Assignment**: Apply priority-based emoji logic (🏆 for finals, 🏉 for rugby, 📅 for general events)
5. **MQTT Publishing**: Send structured data to Home Assistant
6. **Calendar Export**: Generate ICS files for external calendar apps

### Emoji & Icon System

The modular emoji system (`core/event_icons.py`) provides:

- **Priority Logic**: Finals → Trophy emoji (🏆), Sport-specific → Sport emoji (🏉), Fallback → Calendar (📅)
- **Unicode Support**: Full emoji character counting for display width calculations
- **Length Validation**: Ensures emoji + text combinations fit within configured limits

#### Supported Emoji / MDI Icon Mappings

| Category / Match                       | Example Event Names / Patterns                                                                                                                   | Emoji | MDI Icon              | Notes / Priority                            |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ----- | --------------------- | ------------------------------------------- |
| Major Final                            | "Rugby World Cup Final", "Champions Cup Final", "Grand Final", "Playoff Final", any `<something> Final` not preceded by Semi/Quarter             | 🏆    | mdi:trophy            | Highest priority (wins over sport-specific) |
| Rugby (international or domestic)      | Country vs Country ("England v Australia"), "Six Nations Championship", club/tournament terms (Harlequins, Premiership, Union), explicit "Rugby" | 🏉    | mdi:rugby             | Skipped if Major Final matched              |
| Rugby tournament stages (semi/quarter) | "Semi Final", "Quarter-Final" (rugby context)                                                                                                    | 🏉    | mdi:rugby             | Not treated as trophy finals                |
| American Football                      | "NFL", "American Football"                                                                                                                       | 🏈    | mdi:football-american | Checked before soccer to avoid conflict     |
| Soccer / Football                      | "Premier League", "FA Cup", "Soccer Championship", generic "Football" (not American)                                                             | ⚽    | mdi:soccer            | Lower priority than American Football       |
| Music / Concert                        | "Concert", "Music Festival", "Live Tour", "Band", "Music Tour"                                                                                   | 🎵    | mdi:music             | Filters to avoid false 'tour' matches       |
| Generic / Other                        | Everything else (Corporate events, Cricket, Tennis, etc.)                                                                                        | 📅    | mdi:calendar          | Default fallback                            |

AI type detection (if enabled) can also yield: rugby (🏉/mdi:rugby), concert (🎵/mdi:music), generic (🏟️/mdi:stadium). The fallback generic emoji in AI path is a stadium (🏟️) rather than calendar; final published entity attributes retain both forms.

##### Priority Summary

1. Major Final (trophy)
2. Rugby (international / explicit rugby words / club patterns)
3. American Football
4. Soccer / Football
5. Music / Concert
6. Generic fallback

If two categories match, the one with the higher priority above wins (tests enforce this: finals over rugby; American football over soccer; cricket avoiding music false positive, etc.).

#### Example Emoji Decisions

| Event Name                     | Chosen Emoji/Icon          | Rationale                        |
| ------------------------------ | -------------------------- | -------------------------------- | ---------------- |
| Women's Rugby World Cup Final  | 🏆 / mdi:trophy            | Final outranks rugby             |
| England v Australia            | 🏉 / mdi:rugby             | International rugby vs match     |
| American Football Championship | 🏈 / mdi:football-american | Explicit American football       |
| Premier League Match           | ⚽ / mdi:soccer            | Soccer pattern, not American     |
| Taylor Swift                   | The Eras Tour              | 🎵 / mdi:music                   | Concert keywords |
| Corporate Conference 2025      | 📅 / mdi:calendar          | No specific sport/music keywords |

Length logic: if an AI-shortened name plus emoji would exceed the configured display length budget, the emoji may be omitted in the short display variant while still present as an attribute.

### Availability & LWT Semantics

| Mechanism                    | Behavior                                                                                                  |
| ---------------------------- | --------------------------------------------------------------------------------------------------------- |
| MQTT Last Will               | Broker publishes offline status JSON if client disconnects unexpectedly (based on configured `last_will`) |
| Explicit Availability Topic  | Service publishes `online` on start, `offline` on graceful shutdown (signals)                             |
| Discovery availability_topic | Links component visibility state to shared `availability` topic                                           |
| Fallback                     | If LWT config omitted, manual availability still provides presence semantics                              |

Edge cases: network partition → LWT triggers; overlapping service instances with same `client_id` cause one to be kicked (ensuring only one authoritative publisher).

### Legacy Migration (Per-Entity → Unified Bundle)

Older deployments produced multiple discovery topics (binary_sensor + individual sensors). The unified model:

- Publishes one retained discovery JSON mapping components.
- Purges legacy discovery topics automatically on first connect (idempotent).
- Reduces retained topic sprawl & atomicity issues after restarts.

Migration Steps (if coming from legacy):

1. Upgrade code & restart service.
2. (Optional) Run purge script: `poetry run python scripts/mqtt_purge_legacy_discovery.py`.
3. Verify only device-level config remains under `homeassistant/device/...`.

### Caching & Error Handling Strategy

| Area             | Strategy                                                             |
| ---------------- | -------------------------------------------------------------------- |
| AI Shortening    | On-disk cache keyed by normalized fixture string                     |
| Publish Failures | Retry/backoff (light) then increment counter; non-fatal              |
| Scrape Errors    | Collected into `errors` list; status may become `error` if threshold |
| Validation       | `mqtt_validate.py --strict` enforces cross-topic invariants          |
| Legacy Cleanup   | Executed once per connection if enabled                              |

### Validation & Hygiene Tooling

| Script                                    | Purpose                                                  |
| ----------------------------------------- | -------------------------------------------------------- |
| scripts/mqtt_validate.py                  | Fetch topics, validate structure, optional strict checks |
| scripts/mqtt_purge_legacy_discovery.py    | Remove obsolete retained discovery topics                |
| scripts/ha_dashboard_backup_and_update.py | Snapshot & patch HA dashboard JSON (safe migrations)     |
| scripts/ha_dashboard_export_yaml.py       | Export HA dashboard into YAML form for versioning        |

### Security / Privacy Considerations

- Secrets (credentials, API keys) should reside in `.env` or external secret stores.
- No PII scraped—only public event data.
- AI calls send only event title strings (no user metadata).
- MQTT TLS recommended for production; example config sets `verify: false` placeholder—enable verification in real deployments.

### Performance Characteristics

| Aspect           | Typical Impact                                                |
| ---------------- | ------------------------------------------------------------- |
| Scrape Cycle     | Fast (HTML parse + normalization) < 1s for moderate page size |
| AI Shortening    | Dominant latency (network); cached items near-zero cost       |
| Memory Footprint | Lightweight (events list + caches)                            |
| MQTT Overhead    | Minimal; retained small JSON payloads                         |
| Discovery Update | Only on start or structural change                            |

### Testing Strategy Overview

| Test Area           | Coverage Highlights                                                |
| ------------------- | ------------------------------------------------------------------ |
| Emoji/Icon          | Priority ordering, pattern specificity, false-positive avoidance   |
| Discovery           | Structure of unified bundle, legacy purge behavior, component keys |
| LWT / Availability  | Will set semantics, offline propagation                            |
| AI Shortening       | Caching, flag insertion rules, length enforcement                  |
| Service Integration | End-to-end publishing cycle                                        |

### Roadmap / Future Enhancements

| Candidate                                     | Rationale                                   |
| --------------------------------------------- | ------------------------------------------- |
| Webhook / Push Mode                           | Reduce polling for dynamic sources          |
| More Sports Detection (Cricket, Tennis icons) | Finer-grained visuals                       |
| Automated Schema Versioning                   | Guard downstream breaking changes           |
| Prometheus Exporter                           | External monitoring / metrics scraping      |
| Persistent Uptime Counter                     | Survive restarts for HA history clarity     |
| Configurable Retry Backoff                    | Tunable resilience under broker instability |

### FAQ

| Question                                 | Answer                                                                                                        |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Why a single discovery topic?            | Atomic updates, fewer retained artifacts, simpler cleanup.                                                    |
| Can I disable AI without editing config? | Run service with `--no-ai` (if present) or set shortening.enabled false.                                      |
| How do I add a new component?            | Extend `components` map in `discovery_helper.py` and re-publish.                                              |
| What happens if the broker restarts?     | Retained discovery + retained state topics allow seamless HA recovery; availability republished on reconnect. |
| Are flag emojis required?                | No; disable `flags_enabled` to avoid width variability.                                                       |
| How are ambiguous dates handled?         | Logged & skipped rather than guessed to avoid erroneous automations.                                          |
| Do I need ha_discovery.yaml?             | No—fully programmatic.                                                                                        |

---

### Date & Time Normalization

The scraper normalizes varied real‑world date/time strings into consistent structured fields (e.g. `date`, `start_time`, optional `end_time`) to simplify downstream automations and comparisons.

#### Supported Input Patterns (Examples)

| Raw Input         | Normalized Date | Normalized Time(s) | Notes                                            |
| ----------------- | --------------- | ------------------ | ------------------------------------------------ |
| 02/11/2025        | 2025-11-02      | (none)             | Day-first numeric assumed (UK locale)            |
| 2 Nov 2025        | 2025-11-02      | (none)             | Month short name resolved                        |
| 2nd November 2025 | 2025-11-02      | (none)             | Ordinal suffix removed                           |
| Sunday 2nd Nov    | 2025-11-02      | (none)             | Weekday ignored if consistent                    |
| 2 Nov             | 2025-11-02      | (none)             | Year inferred (current or next if past)          |
| 2 Nov 5pm         | 2025-11-02      | 17:00              | 12-hour to 24-hour conversion                    |
| 2 Nov 5:30pm      | 2025-11-02      | 17:30              | Minutes preserved                                |
| 2 Nov 3 & 5pm     | 2025-11-02      | 15:00 / 17:00      | Multiple start times captured (first as primary) |
| 2 Nov 15:00       | 2025-11-02      | 15:00              | 24-hour already normalized                       |
| 2 Nov 15:00–17:30 | 2025-11-02      | 15:00 (end 17:30)  | Range parsed (en dash / hyphen tolerant)         |
| 2 Nov 3-5pm       | 2025-11-02      | 15:00 (end 17:00)  | Implied pm for both times                        |

#### Normalization Rules

- Ordinal suffixes (st, nd, rd, th) stripped prior to parsing.
- Mixed separators (space, slash) resolved with precedence: explicit year > inferred.
- Time ranges produce `start_time` and `end_time`; multiple discrete times pick earliest as `start_time` and list others in attributes.
- 12-hour times without am/pm default to evening heuristics only if context suggests (configurable extension point; otherwise treated as 24-hour if colon present).
- All emitted times are 24-hour `HH:MM` strings; seconds omitted unless present.
- If date lacks year, year inferred: today-or-future within rolling 12‑month window (wraps to next year if earlier date already passed this calendar year).

#### Example Normalized Event JSON

```json
{
  "fixture": "England v Australia",
  "date": "2025-11-02",
  "start_time": "17:00",
  "end_time": null,
  "crowd": "82,000",
  "emoji": "🏉",
  "icon": "mdi:rugby"
}
```

> Note: Date/time parsing is intentionally conservative; ambiguous inputs are logged and left unparsed rather than guessed aggressively. This minimizes incorrect automations.

## Testing

```bash
poetry run pytest                # Full suite
poetry run pytest -k discovery   # Filter subset
poetry run pytest --maxfail=1 -q # Fast fail
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
python test_env_vars.py   # Validate env var expansion
```

## Troubleshooting

### MQTT / Discovery Issues

1. Broker & creds correct? (`.env` values)
2. Run validator (strict): `poetry run python scripts/mqtt_validate.py --strict`
3. Purge legacy retained config: `poetry run python scripts/mqtt_purge_legacy_discovery.py`
4. Confirm single device config topic retained (`homeassistant/device/twickenham_events/config`).

Validator script help excerpt:

```
usage: mqtt_validate.py [--broker HOST] [--port PORT] [--timeout SEC] [--run-service]
                        [--topics ...] [--include-discovery] [--purge-discovery]
                        [--strict] [--config PATH]

Key flags:
  --run-service       Run `twick-events service --once` before validating
  --include-discovery Include device discovery topic in validation
  --purge-discovery   Delete ALL legacy + current discovery topics first
  --strict            Cross-topic consistency checks (event_count, next vs first, today logic, component set)
```

Purge script help excerpt:

```
usage: mqtt_purge_legacy_discovery.py [--broker HOST] [--port PORT]
                                      [--username USER] [--password PASS]
                                      [--discovery-prefix PREFIX]
                                      [--base twickenham_events]

Deletes (retained empty publish) legacy per-entity sensors, buttons (old + new), and device bundle.
Run before switching to unified device-level discovery OR to reset corrupted discovery.
```

### Availability Not Updating

1. Check `twickenham_events/availability` retained state
2. Ensure service not running multiple instances with same client_id
3. Verify LWT configured (status topic) or fallback applied.

### AI Shortening Problems

1. Confirm `GEMINI_API_KEY` present
2. Clear cache: `poetry run twick-events cache clear`
3. Reprocess cache: `poetry run twick-events cache reprocess`.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

1. Fork repository & branch (`feature/x`)
2. Implement feature + tests
3. Run lint & tests (`ruff`, `pytest`)
4. Open PR with summary (include any discovery / entity migration notes)

## Support

- **Issues**: [GitHub Issues](https://github.com/ronschaeffer/twickenham_events/issues)
