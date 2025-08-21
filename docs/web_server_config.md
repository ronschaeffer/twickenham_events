# 🌐 Web Server Configuration Guide

This document outlines the recommended web server configuration settings for the Twickenham Events project, following the existing patterns used for MQTT, Calendar, and AI processor configuration.

## 📋 Configuration Settings

### Core Settings

All web server settings are under the `web_server` section in `config.yaml`:

```yaml
web_server:
  enabled: "${WEB_SERVER_ENABLED}"     # true/false
  host: "${WEB_SERVER_HOST}"           # 0.0.0.0 or 127.0.0.1
  port: "${WEB_SERVER_PORT}"           # 8080, 47476, etc.
```

### Advanced Settings

```yaml
web_server:
  # External access configuration (for Docker/proxy setups)
  external_url_base: "${WEB_SERVER_EXTERNAL_URL}"  # https://your-domain.com/api

  # Development and debugging
  access_log: "${WEB_SERVER_ACCESS_LOG}"    # true/false (default: false)
  reload: false                             # Development auto-reload (not for production)

  # CORS configuration (for browser access)
  cors:
    enabled: "${WEB_SERVER_CORS_ENABLED}"   # true/false
    origins: "${WEB_SERVER_CORS_ORIGINS}"   # "*" or "https://mydomain.com,http://localhost:3000"
```

## 🔧 Environment Variables

Following the project's pattern of using environment variables for sensitive/deployment-specific settings:

### Required Variables

```bash
# Basic web server control
export WEB_SERVER_ENABLED="true"
export WEB_SERVER_HOST="0.0.0.0"      # All interfaces
export WEB_SERVER_PORT="47476"        # Your preferred port

# Optional: External access URL (Docker/proxy scenarios)
export WEB_SERVER_EXTERNAL_URL="https://your-domain.com/twickenham-api"
```

### Optional Variables

```bash
# Development and debugging
export WEB_SERVER_ACCESS_LOG="false"   # Reduces log noise in production
export WEB_SERVER_CORS_ENABLED="true"  # If you need browser access
export WEB_SERVER_CORS_ORIGINS="*"     # Or specific origins
```

## 🚀 Configuration Validation

### Automatic Validation

The system now includes comprehensive validation:

```bash
# Validate all configuration
poetry run python -m src.twickenham_events validate config

# Validate web server specifically (tests connectivity)
poetry run python -m src.twickenham_events validate web

# Test with specific settings
poetry run python -m src.twickenham_events validate web --host 127.0.0.1 --port 8080

# Test external URL
poetry run python -m src.twickenham_events validate web --external-url "https://mydomain.com/api"
```

### What Gets Validated

1. **Configuration Syntax**: Valid YAML and proper data types
2. **Port Validation**: Range 1-65535, warnings for privileged ports (<1024)
3. **Host Validation**: Valid host formats
4. **External URL Validation**: Proper HTTP/HTTPS format
5. **Connectivity Testing**: Actual HTTP requests to endpoints
6. **Endpoint Validation**: Health, status, docs, file serving
7. **File Serving**: Validates calendar and JSON files are served correctly

## 🏗️ Integration Patterns

### Following Existing Patterns

The web server configuration follows the same patterns as other components:

#### 1. Environment Variable Support
- Like MQTT: `MQTT_BROKER_URL`, `MQTT_USERNAME`
- Like Calendar: `CALENDAR_ENABLED`
- Like AI: `GEMINI_API_KEY`, `SHORTENING_ENABLED`

#### 2. Config Properties
```python
# Similar to existing patterns:
config.mqtt_enabled          → config.web_enabled
config.mqtt_broker           → config.web_host
config.mqtt_port             → config.web_port
config.calendar_filename     → config.web_external_url_base
```

#### 3. Validation Integration
```python
# Follows existing validation patterns in mqtt_validate.py
scripts/web_validate.py      # New web server validator
scripts/mqtt_validate.py     # Existing MQTT validator
scripts/validate_all.py      # Comprehensive validator
```

## 📊 Comparison with Other Components

| Component | Enabled Check | Config Section | Validation Script | CLI Integration |
|-----------|---------------|----------------|-------------------|-----------------|
| MQTT | `mqtt.enabled` | `mqtt:` | `mqtt_validate.py` | ✅ |
| Calendar | `calendar.enabled` | `calendar:` | `validate_all.py` | ✅ |
| AI Processor | `ai_processor.shortening.enabled` | `ai_processor:` | Built-in | ✅ |
| **Web Server** | `web_server.enabled` | `web_server:` | `web_validate.py` | ✅ |

## 🎯 Recommended Settings by Environment

### Development
```yaml
web_server:
  enabled: true
  host: "127.0.0.1"  # Localhost only
  port: 8080         # Standard development port
  access_log: true   # Debug requests
  reload: true       # Auto-reload on changes
  cors:
    enabled: true    # For frontend development
    origins: "*"
```

### Production
```yaml
web_server:
  enabled: true
  host: "0.0.0.0"    # All interfaces
  port: 47476        # Your chosen port
  access_log: false  # Reduce log noise
  reload: false      # Stability
  external_url_base: "https://api.yourdomain.com"
  cors:
    enabled: false   # Unless specifically needed
```

### Docker/Container
```yaml
web_server:
  enabled: true
  host: "0.0.0.0"    # Required for container networking
  port: 8080         # Standard container port
  external_url_base: "${WEB_SERVER_EXTERNAL_URL}"  # Set via environment
```

## 🔍 Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   lsof -i :47476  # Check what's using the port
   ```

2. **Permission denied (privileged ports)**
   ```bash
   # Use port > 1024 or run with sudo (not recommended)
   export WEB_SERVER_PORT="8080"
   ```

3. **Cannot connect externally**
   ```bash
   # Check host setting
   export WEB_SERVER_HOST="0.0.0.0"  # Not 127.0.0.1
   ```

4. **Docker/proxy issues**
   ```bash
   export WEB_SERVER_EXTERNAL_URL="https://yourdomain.com/api"
   ```

### Validation Commands

```bash
# Quick health check
curl http://localhost:47476/health

# Full validation
poetry run python -m src.twickenham_events validate web --check-files

# Test with server auto-start
poetry run python -m src.twickenham_events validate web --start-server
```

## 🎖️ Best Practices

### 1. Security
- Use unprivileged ports (>1024) when possible
- Set `host: "127.0.0.1"` for localhost-only access
- Configure CORS origins specifically (not "*") in production
- Use HTTPS in production with proper proxy setup

### 2. Performance
- Disable `access_log` in production
- Never enable `reload` in production
- Use external load balancer/proxy for high availability

### 3. Monitoring
- Enable health checks: `GET /health`
- Monitor status endpoint: `GET /status`
- Use validation commands in deployment pipelines

### 4. Configuration Management
- Use environment variables for deployment-specific settings
- Keep sensitive settings in `.env` files (not in git)
- Validate configuration in CI/CD pipelines
