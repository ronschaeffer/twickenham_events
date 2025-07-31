# Twickenham Events

This project fetches and processes event data from the Twickenham events page and publishes it via MQTT for use with Home Assistant.

## Features

- **Event Scraping**: Automatically fetches upcoming events from Twickenham Stadium
- **MQTT Publishing**: Publishes event data to MQTT topics with retain flags
- **Home Assistant Integration**: Auto-discovery support with binary status sensor
- **Event Name Shortening**: Optional AI-powered shortening for compact displays
- **Comprehensive Testing**: Full test coverage with pytest

## Setup

1. Install [Poetry](https://python-poetry.org/docs/#installation).
2. Install dependencies:
   ```sh
   poetry install
   ```
3. (Optional) For AI event shortening:
   ```sh
   poetry install --with ai
   ```

## Configuration

Copy `config/config.yaml.example` to `config/config.yaml` and customize:

- MQTT broker settings
- Home Assistant integration options
- Event shortening configuration (optional)

## Usage

Run the script:

```sh
poetry run python -m core
```

## Optional Features

### AI Event Name Shortening

Automatically creates shortened event names suitable for compact displays using Google's Gemini API. See [EVENT_SHORTENING.md](docs/EVENT_SHORTENING.md) for setup instructions.

Example:

- Original: "Women's Rugby World Cup Final"
- Shortened: "W RWC Final"

## Home Assistant Cards

The `ha_card/` directory contains various dashboard card configurations for displaying event data in Home Assistant.

## License

This project is licensed under the MIT License.
