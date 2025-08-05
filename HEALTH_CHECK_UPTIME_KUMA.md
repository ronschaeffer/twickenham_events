# Health Check & Uptime Kuma Integration

The Twickenham Events project includes a comprehensive health check system perfect for monitoring with Uptime Kuma or other monitoring solutions.

## Quick Start

```bash
# Run health check manually
poetry run python -m core.health_check

# Or using the new command (after poetry install)
poetry run twick-health
```

## Health Check Response

The health check returns JSON with comprehensive status information:

```json
{
  "timestamp": "2025-08-05T18:54:45.802338",
  "status": "healthy",
  "checks": {
    "config": "ok",
    "data_freshness": "ok",
    "error_log": "ok",
    "mqtt_config": "ok"
  },
  "warnings": [],
  "errors": []
}
```

## Exit Codes

- **0**: Healthy (all checks pass)
- **1**: Unhealthy (critical errors)
- **2**: Warning (non-critical issues)

## Health Checks Performed

### 1. Configuration Validity

- ✅ Verifies `config/config.yaml` can be loaded
- ✅ Validates configuration structure

### 2. Data Freshness

- ✅ **< 24 hours**: Healthy
- ⚠️ **24-48 hours**: Warning
- ❌ **> 48 hours**: Error

### 3. Error Log Status

- ✅ Checks for processing errors
- ⚠️ Reports error counts as warnings

### 4. MQTT Configuration

- ✅ Verifies MQTT settings are valid
- ✅ Reports if MQTT is disabled

## Uptime Kuma Setup

### HTTP Monitor Configuration

1. **Monitor Type**: HTTP(s)
2. **URL**: `http://your-server/health` (see web setup below)
3. **Method**: GET
4. **Expected Status**: 200
5. **Keyword**: `"status": "healthy"`

### Script Monitor Configuration (Recommended)

1. **Monitor Type**: Script
2. **Script**:
   ```bash
   cd /home/ron/projects/twickenham_events && poetry run python -m core.health_check
   ```
3. **Expected Exit Code**: 0

### Advanced Script with Details

```bash
#!/bin/bash
cd /home/ron/projects/twickenham_events
HEALTH_OUTPUT=$(poetry run python -m core.health_check 2>&1)
EXIT_CODE=$?

echo "Twickenham Events Health Check"
echo "Exit Code: $EXIT_CODE"
echo "Output: $HEALTH_OUTPUT"

# Parse JSON for additional context
if command -v jq &> /dev/null; then
    echo "Event Count: $(echo "$HEALTH_OUTPUT" | jq -r '.event_count // "N/A"')"
    echo "Warnings: $(echo "$HEALTH_OUTPUT" | jq -r '.warnings | length')"
    echo "Errors: $(echo "$HEALTH_OUTPUT" | jq -r '.errors | length')"
fi

exit $EXIT_CODE
```

## Web Endpoint Setup (Optional)

For HTTP monitoring, create a simple web endpoint:

```python
#!/usr/bin/env python3
# health_web.py - Simple Flask health endpoint
from flask import Flask, jsonify
import subprocess
import json

app = Flask(__name__)

@app.route('/health')
def health():
    try:
        result = subprocess.run([
            'poetry', 'run', 'python', '-m', 'core.health_check'
        ], capture_output=True, text=True, cwd='/home/ron/projects/twickenham_events')

        health_data = json.loads(result.stdout)

        if result.returncode == 0:
            return jsonify(health_data), 200
        elif result.returncode == 2:
            return jsonify(health_data), 200  # Warning but still OK
        else:
            return jsonify(health_data), 503  # Service unavailable

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
```

## Cron Integration

Run health checks on a schedule:

```bash
# Check every 30 minutes and log results
*/30 * * * * cd /home/ron/projects/twickenham_events && poetry run python -m core.health_check >> /var/log/twick-health.log 2>&1
```

## Monitoring Best Practices

### Alert Thresholds

- **Critical**: Exit code 1 (unhealthy)
- **Warning**: Exit code 2 (warnings present)
- **Data Age**: Alert if data > 24 hours old

### Notification Rules

```yaml
# Uptime Kuma notification example
webhook_url: "https://your-webhook-url"
conditions:
  - status_change: true
  - consecutive_failures: 3
  - data_age_warning: true
```

### Dashboard Metrics

Monitor these key indicators:

- Health check success rate
- Data freshness (hours since last update)
- Processing error count
- MQTT connectivity status

## Troubleshooting

### Common Issues

**Health check fails with config error:**

```bash
# Check config file exists and is valid
cat config/config.yaml
poetry run python -c "from core.config import Config; Config('config/config.yaml')"
```

**Data freshness warnings:**

```bash
# Check when data was last updated
cat output/upcoming_events.json | jq '.last_updated'

# Force a data refresh
poetry run python -m core
```

**MQTT connectivity issues:**

```bash
# Test MQTT connection
poetry run python -c "
from core.config import Config
config = Config('config/config.yaml')
print(config.get_mqtt_config())
"
```

## Integration Examples

### Home Assistant

Use the health check with Home Assistant's command line sensor:

```yaml
sensor:
  - platform: command_line
    name: "Twickenham Events Health"
    command: "cd /home/ron/projects/twickenham_events && poetry run python -m core.health_check"
    value_template: "{{ value_json.status }}"
    json_attributes:
      - checks
      - warnings
      - errors
    scan_interval: 300
```

### Prometheus/Grafana

Export health metrics:

```python
# health_metrics.py
from prometheus_client import start_http_server, Gauge, Info
import time
import json
import subprocess

health_status = Gauge('twickenham_health_status', 'Health status (1=healthy, 0=unhealthy)')
data_age_hours = Gauge('twickenham_data_age_hours', 'Age of data in hours')
error_count = Gauge('twickenham_error_count', 'Number of errors')

def collect_metrics():
    result = subprocess.run(['poetry', 'run', 'python', '-m', 'core.health_check'],
                          capture_output=True, text=True)
    data = json.loads(result.stdout)

    health_status.set(1 if data['status'] == 'healthy' else 0)
    error_count.set(len(data['errors']))

if __name__ == '__main__':
    start_http_server(8000)
    while True:
        collect_metrics()
        time.sleep(60)
```

The health check system provides comprehensive monitoring capabilities that integrate seamlessly with Uptime Kuma and other monitoring solutions.
