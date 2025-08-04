# 🏉 Twick- **🧪 Testing Coverage**: Test coverage with pytest and error handling

- **🔒 Secure Configuration**: Environment variable support with hierarchical loading
- **📊 Detailed Logging**: Logging with configurable levelsam Events

An event scraping and MQTT publishing system that fetches upcoming events from Twickenham Stadium and publishes them to Home Assistant via MQTT with auto-discovery support.

## ✨ Features

<<<<<<< HEAD
- **🕸️ Event Scraping**: Fetches upcoming events from Twickenham Stadium website
=======
- **🕸️ Event Scraping**: Automatically fetches upcoming events from Richmond Council website
>>>>>>> f411fdeed1d4412e9b61551c04ad52cab7ad6216
- **📡 MQTT Publishing**: Publishes structured event data to MQTT topics with retain flags
- **🏠 Home Assistant Integration**: Auto-discovery support with status monitoring
- **🤖 AI Event Shortening**: Optional AI-powered event name shortening for compact displays
- **🧪 Testing Coverage**: Test coverage with pytest and error handling
- **🔒 Secure Configuration**: Environment variable support with hierarchical loading
- **📊 Detailed Logging**: Logging with configurable levels

## 📦 Installation

### Prerequisites

- Python 3.11+
- [Poetry](https://python-poetry.org/docs/#installation)

### Setup Steps

1. **Clone the repository:**

   ```bash
   git clone https://github.com/ronschaeffer/twickenham_events.git
   cd twickenham_events
   ```

2. **Install dependencies:**

   ```bash
   poetry install
   ```

3. **Optional - For AI event shortening:**
   ```bash
   poetry install --with ai
   ```

## ⚙️ Configuration

### MQTT Configuration

This project uses the [`mqtt_publisher`](https://github.com/ronschaeffer/mqtt_publisher) library for MQTT functionality.

📖 **For detailed MQTT configuration instructions**, see the [MQTT Publisher README](../mqtt_publisher/README.md#-configuration)

### Quick Setup

<<<<<<< HEAD
1. **Copy the configuration template:**
=======
```bash
# MQTT Broker Configuration (shared across projects)
MQTT_BROKER_URL=your-broker.example.com
MQTT_BROKER_PORT=you-broke-port
MQTT_USERNAME=your_mqtt_username
MQTT_PASSWORD=your_mqtt_password
MQTT_USE_TLS=false

# Google Gemini API (for AI event shortening)
GEMINI_API_KEY=your_gemini_api_key_here
```
>>>>>>> f411fdeed1d4412e9b61551c04ad52cab7ad6216

   ```bash
   cp config/config.yaml.example config/config.yaml
   ```

2. **Set your MQTT credentials** (choose one method):

   **Option A: Environment Variables** (recommended)

   ```bash
   # Create .env file in project root
   MQTT_BROKER_URL=your-broker.example.com
   MQTT_BROKER_PORT=8883
   MQTT_CLIENT_ID=twickenham_events_client
   MQTT_USERNAME=your_mqtt_username
   MQTT_PASSWORD=your_mqtt_password

   # Optional: Google Gemini API for AI event shortening
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

   **Option B: Direct Configuration**

   ```bash
   # Edit config/config.yaml directly with your values
   ```

3. **The configuration uses environment variable substitution:**

### Configuration File

1. **Copy the example configuration:**

   ```bash
   cp config/config.yaml.example config/config.yaml
   ```

2. **The configuration automatically uses environment variables:**

   ```yaml
   # MQTT Configuration with environment variable substitution
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

## 🚀 Usage

### Basic Usage

```bash
poetry run python -m core
```

### With Dry Run (testing)

```bash
poetry run python -m core --dry-run
```

### Example Output

```
2024-01-01 12:00:00 INFO - Starting Twickenham Events scraper
2024-01-01 12:00:01 INFO - Found 3 upcoming events
2024-01-01 12:00:02 INFO - Connected to MQTT broker
2024-01-01 12:00:03 INFO - Published discovery configurations
2024-01-01 12:00:04 INFO - Published event data to Home Assistant
```

## 🏠 Home Assistant Integration

### Auto-Discovery Features

- **📊 Event Sensors**: Next event, all upcoming events, daily summaries
- **🔴 Status Sensor**: Online/offline status monitoring
- **📅 Event Attributes**: Event details with metadata
- **🏷️ Device Grouping**: All sensors grouped under "Twickenham Events" device

### Available Sensors

| Sensor           | Entity ID                                   | Description                        |
| ---------------- | ------------------------------------------- | ---------------------------------- |
| Next Event       | `sensor.twickenham_events_next`             | Details of the next upcoming event |
| All Upcoming     | `sensor.twickenham_events_all_upcoming`     | JSON list of all future events     |
| Next Day Summary | `sensor.twickenham_events_next_day_summary` | Summary for next event day         |
| Status           | `binary_sensor.twickenham_events_status`    | System online/offline status       |

### Sample Home Assistant Card

```yaml
type: markdown
content: |
  ## 🏉 Next Twickenham Event
  **{{ states('sensor.twickenham_events_next') }}**

  📅 {{ state_attr('sensor.twickenham_events_next', 'date') }}
  🕐 {{ state_attr('sensor.twickenham_events_next', 'time') }}

  Status: {{ states('binary_sensor.twickenham_events_status') }}
```

## 🤖 AI Event Shortening (Optional)

Creates shortened event names using Google's Gemini API:

- **Original**: "Guinness Six Nations Championship - England vs Wales"
- **Shortened**: "6N: ENG vs WAL"

### Setup:

1. Get a [Google Gemini API key](https://aistudio.google.com/app/apikey)
2. Add to your environment: `GEMINI_API_KEY=your_api_key`
3. Enable in config: `ai_shortener.enabled: true`

See [docs/EVENT_SHORTENING.md](docs/EVENT_SHORTENING.md) for detailed setup.

## 🧪 Testing

### Run Tests

```bash
poetry run pytest
```

### Run with Coverage

```bash
poetry run pytest --cov=core --cov-report=html
```

### Test Environment Connection

```bash
poetry run python -c "
from core.config import Config
from dotenv import load_dotenv
load_dotenv()  # Load environment variables
config = Config('config/config.yaml')
print(f'MQTT: {config.get(\"mqtt.broker_url\")}:{config.get(\"mqtt.broker_port\")}')
"
```

## 📂 Project Structure

```
twickenham_events/
├── core/                    # Main application code
│   ├── __main__.py         # Entry point with optional env loading
│   ├── config.py           # Configuration with ${VAR} substitution
│   ├── twick_event.py      # Event data structures
│   └── mqtt_publisher.py   # MQTT publishing logic
├── config/                 # Configuration files
│   ├── config.yaml.example # Template with environment variables
│   └── ha_entities.yaml    # Home Assistant entity definitions
├── tests/                  # Test suite
├── docs/                   # Documentation
├── ha_card/               # Home Assistant dashboard cards
└── .env.example           # Environment template
```

## 🔧 Development

### Code Quality

```bash
# Format code
poetry run ruff format

# Check linting
poetry run ruff check

# Type checking
poetry run mypy core/
```

### Dependencies

- **Core**: `requests`, `pyyaml`, `python-dotenv`
- **MQTT**: Uses [`mqtt_publisher`](https://github.com/ronschaeffer/mqtt_publisher) as Git dependency
- **AI (Optional)**: `google-generativeai`
- **Testing**: `pytest`, `pytest-cov`

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests: `poetry run pytest`
4. Commit changes (`git commit -m 'Add amazing feature'`)
5. Push to branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

## 📞 Support

For questions, issues, or contributions, please open an issue on GitHub.

---
