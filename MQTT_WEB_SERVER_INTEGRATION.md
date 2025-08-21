# Enhanced MQTT Status with Web Server URLs for Home Assistant

## Overview

The Twickenham Events MQTT client has been enhanced to include web server status and URLs in the status topic. This makes it easy for Home Assistant to automatically discover and use the calendar and webhook endpoints.

## Smart URL Detection

The system now includes intelligent URL detection that automatically determines the best external URL for accessing the web server:

### URL Detection Priority (when `external_url_base` is not set):

1. **Explicit Configuration**: Uses `external_url_base` if provided
2. **Local IP Detection**: Auto-detects the machine's local IPv4 address for LAN access
3. **Docker Support**: Detects Docker container networking automatically
4. **Localhost Fallback**: Falls back to localhost if detection fails

### Docker Deployment Benefits:

- **Container-to-Host**: Other containers can reach the service via detected IP
- **LAN Access**: Devices on the same network can access the service
- **No Manual Config**: Works without specifying external URLs
- **Home Assistant Ready**: URLs are immediately usable by HA on the same network

Example outputs for different environments:

```bash
# Development (localhost binding)
Host: localhost → URL: http://localhost:8080

# Docker (0.0.0.0 binding, auto-detect)
Host: 0.0.0.0 → URL: http://192.168.1.100:8080

# Production (explicit external URL)
Host: 0.0.0.0 + external_url_base → URL: https://twickenham.example.com
```

## Enhanced MQTT Status Payload

When the web server is enabled, the MQTT status topic (`twickenham_events/status`) now includes a `web_server` object:

```json
{
  "status": "active",
  "event_count": 5,
  "ai_error_count": 0,
  "publish_error_count": 0,
  "ai_enabled": true,
  "sw_version": "1.0.0",
  "last_updated": "2024-01-15T10:30:00Z",
  "web_server": {
    "enabled": true,
    "base_url": "http://192.168.1.100:8080",
    "internal_binding": "http://0.0.0.0:8080",
    "external_url_base": null,
    "urls": {
      "calendar": "http://192.168.1.100:8080/calendar",
      "events": "http://192.168.1.100:8080/events",
      "status": "http://192.168.1.100:8080/status",
      "calendar_direct": "http://192.168.1.100:8080/twickenham_events.ics",
      "events_direct": "http://192.168.1.100:8080/upcoming_events.json"
    },
    "home_assistant": {
      "calendar_url": "http://192.168.1.100:8080/calendar",
      "events_json_url": "http://192.168.1.100:8080/events",
      "webhook_ready": true
    }
  }
}
```

## Home Assistant Integration Setup

### 1. Calendar Integration

Add this to your Home Assistant `configuration.yaml`:

```yaml
# Calendar from ICS URL
calendar:
  - platform: caldav
    url: "{{ states.sensor.twickenham_web_server.attributes.calendar_url }}"
    username: ""  # Not required for public calendar
    password: ""  # Not required for public calendar
    calendars:
      - calendar: "Twickenham Events"
        name: "Twickenham Stadium Events"
        search: ".*"

# Alternative: Direct ICS calendar
  - platform: ics
    url: "{{ states.sensor.twickenham_web_server.attributes.calendar_direct_url }}"
    name: "Twickenham Events"
    include_all_day: true
```

### 2. MQTT Sensors for URL Discovery

```yaml
mqtt:
  sensor:
    # Main status sensor
    - name: "Twickenham Events Status"
      state_topic: "twickenham_events/status"
      value_template: "{{ value_json.status }}"
      json_attributes_topic: "twickenham_events/status"
      icon: "mdi:rugby"

    # Web server URL sensor
    - name: "Twickenham Web Server"
      state_topic: "twickenham_events/status"
      value_template: >
        {% if value_json.web_server.enabled %}
          Online
        {% else %}
          Offline
        {% endif %}
      json_attributes_template: >
        {% if value_json.web_server %}
          {
            "base_url": "{{ value_json.web_server.base_url }}",
            "calendar_url": "{{ value_json.web_server.home_assistant.calendar_url }}",
            "calendar_direct_url": "{{ value_json.web_server.urls.calendar_direct }}",
            "events_json_url": "{{ value_json.web_server.home_assistant.events_json_url }}",
            "webhook_ready": {{ value_json.web_server.home_assistant.webhook_ready }}
          }
        {% endif %}
      icon: "mdi:web"

    # Event count sensor
    - name: "Twickenham Event Count"
      state_topic: "twickenham_events/status"
      value_template: "{{ value_json.event_count }}"
      unit_of_measurement: "events"
      icon: "mdi:calendar-multiple"
```

### 3. REST Sensors for Direct Web API Access

```yaml
rest:
  # Events JSON sensor using discovered URL
  - resource_template: "{{ states.sensor.twickenham_web_server.attributes.events_json_url }}"
    name: "Twickenham Events JSON"
    value_template: "{{ value_json.count }}"
    json_attributes:
      - count
      - last_updated
      - by_month
    scan_interval: 300  # 5 minutes

  # Web server health check
  - resource_template: "{{ states.sensor.twickenham_web_server.attributes.base_url }}/health"
    name: "Twickenham Web Health"
    value_template: "{{ value_json.status }}"
    json_attributes:
      - server_running
      - files_available
    scan_interval: 60  # 1 minute
```

### 4. Automation Example: Calendar Import

```yaml
automation:
  # Automatically update calendar when web server comes online
  - alias: "Twickenham Calendar Auto-Import"
    trigger:
      - platform: state
        entity_id: sensor.twickenham_web_server
        to: "Online"
    condition:
      - condition: template
        value_template: "{{ states.sensor.twickenham_web_server.attributes.webhook_ready }}"
    action:
      - service: calendar.reload_config_entry
        data:
          entry_id: "{{ config_entry_id('calendar') }}"
      - service: persistent_notification.create
        data:
          title: "Twickenham Events"
          message: >
            Calendar is now available at:
            {{ states.sensor.twickenham_web_server.attributes.calendar_url }}
          notification_id: "twickenham_calendar_ready"
```

### 5. Dashboard Card Examples

```yaml
# Event overview card
type: entities
title: "Twickenham Stadium Events"
entities:
  - entity: sensor.twickenham_events_status
    name: "Status"
  - entity: sensor.twickenham_event_count
    name: "Upcoming Events"
  - entity: sensor.twickenham_web_server
    name: "Web Server"
  - type: divider
  - entity: calendar.twickenham_events
    name: "Next Event"

# Direct calendar card
type: calendar
entities:
  - calendar.twickenham_events
title: "Twickenham Stadium"

# Custom button card for quick access
type: custom:button-card
entity: sensor.twickenham_web_server
name: "View Calendar"
show_state: false
tap_action:
  action: url
  url_path: "{{ states.sensor.twickenham_web_server.attributes.calendar_url }}"
icon: "mdi:calendar-month"
styles:
  card:
    - background-color: var(--primary-color)
  icon:
    - color: white
  name:
    - color: white
```

## Benefits for Home Assistant Users

1. **Automatic Discovery**: URLs are discovered via MQTT, no manual configuration needed
2. **Dynamic URLs**: Supports both internal and external URL bases automatically
3. **Calendar Integration**: Direct ICS calendar import with autodiscovery
4. **REST API Access**: JSON events API for custom dashboards and automations
5. **Health Monitoring**: Built-in health checks and status monitoring
6. **Webhook Ready**: Prepared for webhook-based integrations

## Configuration Example

To enable this enhancement, ensure your `config.yaml` includes:

```yaml
web_server:
  enabled: true
  host: "0.0.0.0"  # Bind to all interfaces for Docker/LAN access
  port: 8080
  external_url_base: "https://your-domain.com:8080"  # Optional: for external access

mqtt:
  enabled: true
  # ... other MQTT settings
```

### Docker Deployment

For Docker deployments, the smart URL detection provides several advantages:

```yaml
# Minimal configuration - URLs auto-detected
web_server:
  enabled: true
  host: "0.0.0.0"  # Required for container networking
  port: 8080
  # external_url_base: not needed! Auto-detected: http://192.168.1.100:8080

# Docker Compose example
version: '3.8'
services:
  twickenham-events:
    image: twickenham-events:latest
    ports:
      - "8080:8080"  # Expose to host network
    environment:
      - WEB_SERVER_ENABLED=true
      - WEB_SERVER_HOST=0.0.0.0
      - WEB_SERVER_PORT=8080
      # WEB_SERVER_EXTERNAL_URL auto-detected!
```

**Docker Benefits:**
- ✅ **Auto-Discovery**: Host IP automatically detected (e.g., `192.168.1.100:8080`)
- ✅ **LAN Access**: Other devices on network can reach the calendar
- ✅ **Container Networking**: Other containers can access via detected IP
- ✅ **Home Assistant Integration**: Works immediately without URL configuration
- ✅ **Development Friendly**: Same config works in dev and production

The web server URLs will automatically appear in the MQTT status topic, making Home Assistant integration seamless and self-configuring.
