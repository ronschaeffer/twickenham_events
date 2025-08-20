# Twickenham Events FastAPI Web Server

A modular FastAPI-based web server for serving Twickenham Events calendar and JSON data files over HTTP.

## Features

- **Modular Design**: Built with a reusable `BaseFileServer` class that can be extracted into a separate library
- **Multiple Endpoints**: Serves ICS calendar files, JSON event data, and status information
- **Auto-discovery**: Automatically detects and serves available output files
- **Health Checks**: Built-in health and status endpoints for monitoring
- **API Documentation**: Automatic OpenAPI/Swagger documentation
- **Development-friendly**: Hot reload support and comprehensive logging

## Architecture

The web server is built with a two-layer architecture:

### 1. Base Layer (`BaseFileServer`)
Located in `src/twickenham_events/web/base_server.py`, this provides:
- Generic FastAPI server functionality
- File serving capabilities with content-type detection
- Health check endpoints
- Route registration system
- Easy extraction for use in other projects

### 2. Project Layer (`TwickenhamEventsServer`)
Located in `src/twickenham_events/web/twickenham_server.py`, this provides:
- Twickenham-specific endpoints and configuration
- Enhanced status information
- Integration with existing `Config` system
- Backward compatibility with existing `TwickenhamWebServer` interface

## Available Endpoints

### Core Endpoints
- `GET /` - API information and available endpoints
- `GET /health` - Basic health check
- `GET /files` - List all available file endpoints

### Twickenham-Specific Endpoints
- `GET /status` - Enhanced status with file information and configuration
- `GET /calendar` - ICS calendar file (content-type: text/calendar)
- `GET /twickenham_events.ics` - Direct ICS file access
- `GET /events` - JSON events data (content-type: application/json)
- `GET /upcoming_events.json` - Direct JSON file access
- `GET /scrape-results` - Raw scraping results JSON

### Documentation
- `GET /docs` - Interactive Swagger UI documentation
- `GET /redoc` - ReDoc alternative documentation

## Usage

### Standalone Server
```bash
# Basic usage
python run_web_server.py

# Custom configuration
python run_web_server.py --config config/config.yaml --port 8080 --debug

# Development mode with auto-reload
python run_web_server.py --reload --debug
```

### Programmatic Usage
```python
from twickenham_events.config import Config
from twickenham_events.web import TwickenhamEventsServer

config = Config.from_defaults()
server = TwickenhamEventsServer(config)
server.start(host="0.0.0.0", port=8080)
```

### Integration with Existing Code
```python
from twickenham_events.config import Config
from twickenham_events.web_server import TwickenhamWebServer

config = Config.from_defaults()
web_server = TwickenhamWebServer(config)
if web_server.start():
    print("Server started successfully")
```

## Configuration

The web server uses the existing configuration system. Key settings:

```yaml
web_server:
  enabled: true
  host: "0.0.0.0"
  port: 8080
```

Environment variable overrides:
- `TWICK_WEB_SERVER_ENABLED`
- `TWICK_WEB_SERVER_HOST`
- `TWICK_WEB_SERVER_PORT`

## Output Files Served

The server automatically serves files from the `output/` directory:

1. **twickenham_events.ics** - ICS calendar file with all events
2. **upcoming_events.json** - Processed events in JSON format
3. **scrape_results.json** - Raw scraping results

## API Examples

### Get Event Data
```bash
curl http://localhost:8080/events | jq '.events[0]'
```

### Download Calendar
```bash
curl -o twickenham.ics http://localhost:8080/calendar
```

### Check Status
```bash
curl http://localhost:8080/status | jq '.files'
```

## Library Extraction

The `BaseFileServer` class is designed for easy extraction into a separate library. To extract:

1. Copy `src/twickenham_events/web/base_server.py`
2. Update imports to remove project-specific dependencies
3. Package as a standalone module

Example extracted usage:
```python
from web_host import BaseFileServer

server = BaseFileServer(
    title="My API",
    base_path="/path/to/files"
)
server.add_json_route("/data", "data.json")
server.add_calendar_route("/calendar", "events.ics")
server.start()
```

## Dependencies

- **fastapi**: Web framework
- **uvicorn**: ASGI server
- **httpx**: HTTP client for testing

## Testing

Run the test suite:
```bash
python test_web_server.py
```

## Development

Start in development mode:
```bash
python run_web_server.py --reload --debug --port 8081
```

This enables:
- Auto-reload on file changes
- Debug logging
- Development-friendly error messages
