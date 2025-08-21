# Docker Networking Configuration

## Overview

When running Twickenham Events in a Docker container, proper network configuration is essential for Home Assistant integration and web server accessibility.

## Network Detection Behavior

The smart URL building system automatically detects the environment and chooses the best IP address:

1. **Non-Docker Environment**: Uses local LAN IP (e.g., `192.168.1.100`)
2. **Docker Environment**: Uses Docker host detection methods
3. **Explicit Configuration**: Respects `external_url_base` configuration

## Docker Host IP Detection Methods

The system tries multiple methods to determine the Docker host IP:

1. **DOCKER_HOST_IP Environment Variable** (Most Reliable)
2. **host.docker.internal** (Docker Desktop)
3. **Auto-Detection** (NEW: Network range probing)
4. **Default Gateway** (Standard Docker bridge - usually `172.17.0.1`)

### Auto-Detection Feature

The enhanced system now automatically probes common private network ranges to find the actual host IP:

- **10.10.10.x** - Enterprise/lab networks
- **192.168.1.x** - Common home networks
- **192.168.0.x** - Alternative home networks
- **10.0.0.x** - Docker Desktop/enterprise
- **172.16.0.x** - Docker custom networks

**Benefits:**
- ✅ Finds actual host LAN IP (e.g., `10.10.10.20`) instead of Docker bridge IP (`172.17.0.1`)
- ✅ Works automatically without configuration in many setups
- ✅ Fast scanning with threading (typically completes in 1-2 seconds)
- ✅ Falls back gracefully to gateway detection if auto-detection fails

**Limitations:**
- May find the first reachable IP rather than the exact host IP
- Requires host ports (SSH/22) to be reachable from container
- Environment variable still recommended for guaranteed accuracy

## Recommended Docker Deployment Options

### Option 1: Unified External URL Configuration (Recommended)

Set your complete external URL - this handles both URL generation and host IP detection:

```bash
# Single configuration that serves both purposes
docker run -d \
  -e WEB_SERVER_EXTERNAL_URL=http://10.10.10.20:47476 \
  -p 47476:47476 \
  twickenham-events

# For Unraid users - add to template's environment variables:
# WEB_SERVER_EXTERNAL_URL=http://10.10.10.20:47476
```

**Benefits:**
- ✅ **Unified Configuration**: One setting for both URL generation and Docker networking
- ✅ **Unraid Compatible**: Perfect for Unraid templates
- ✅ **Flexible**: Supports custom protocols, ports, reverse proxies
- ✅ **Future Proof**: Handles complex deployment scenarios

### Option 2: host.docker.internal (Automatic, No Environment Variables)

Use Docker's built-in DNS name that resolves to the host IP:

#### Docker Desktop (Windows/Mac)
```bash
# Works out-of-the-box on Docker Desktop
docker run -d \
  -p 47476:47476 \
  twickenham-events

# host.docker.internal automatically resolves to host IP
```

#### Docker on Linux
```bash
# Add host-gateway mapping to enable host.docker.internal
docker run -d \
  --add-host=host.docker.internal:host-gateway \
  -p 47476:47476 \
  twickenham-events

# Or using docker-compose:
# extra_hosts:
#   - "host.docker.internal:host-gateway"
```

**Benefits:**
- ✅ Official Docker feature
- ✅ Always resolves to the correct host IP
- ✅ No environment variables needed
- ✅ Works consistently across different host networks

**Docker Compose Example:**
```yaml
version: '3.8'
services:
  twickenham-events:
    image: twickenham-events
    ports:
      - "47476:47476"
    extra_hosts:
      - "host.docker.internal:host-gateway"  # Enable on Linux
```

### Option 3: Host Network Mode

Use Docker's host networking to share the host's network stack:

```bash
docker run -d \
  --network host \
  twickenham-events
```

**Note**: With `--network host`, the container shares the host's IP address directly.

### Option 4: Docker Compose

```yaml
version: '3.8'
services:
  twickenham-events:
    image: twickenham-events
    ports:
      - "47476:47476"
    environment:
      - DOCKER_HOST_IP=${HOST_IP}
    # Alternative: Enable host.docker.internal on Linux
    extra_hosts:
      - "host.docker.internal:host-gateway"
    # Or use host networking:
    # network_mode: host
```

### Option 5: Configuration File

Set the external URL base in your configuration:

```yaml
# config.yaml
web_server:
  host: "0.0.0.0"
  port: 47476
  external_url_base: "http://192.168.1.100"  # Your host's LAN IP
```

## URL Examples

### Container with Auto-Detection

- **Container IP**: `172.17.0.21` (not accessible from host network)
- **Docker Gateway**: `172.17.0.1` (accessible from container, may work from host)
- **Generated URL**: `http://172.17.0.1:47476`

### Container with DOCKER_HOST_IP

- **Environment**: `DOCKER_HOST_IP=192.168.1.100`
- **Generated URL**: `http://192.168.1.100:47476` (accessible from Home Assistant)

### Container with Host Networking

- **Network Mode**: `--network host`
- **Generated URL**: `http://192.168.1.100:47476` (uses host's actual IP)

## Home Assistant Integration

For Home Assistant to access the calendar and webhook URLs, they must be reachable from the Home Assistant network context:

1. **Same Host**: If HA runs on the same host, Docker bridge IPs may work
2. **Different Host**: Requires host's LAN IP (192.168.x.x range)
3. **Docker Compose**: Consider using the same Docker network

## Troubleshooting

### URLs Not Accessible from Home Assistant

1. Check if Home Assistant can reach the URL:
   ```bash
   # From Home Assistant host/container
   curl http://172.17.0.1:47476/status
   ```

2. If not accessible, set `DOCKER_HOST_IP`:
   ```bash
   export DOCKER_HOST_IP=$(hostname -I | awk '{print $1}')
   ```

3. Or use explicit configuration:
   ```yaml
   web_server:
     external_url_base: "http://192.168.1.100"
   ```

### Checking Current Detection

Run this command in your container to see what URLs are being generated:

```python
from src.twickenham_events.network_utils import build_smart_external_url
print("Calendar URL:", build_smart_external_url("0.0.0.0", 47476))
```

## Security Considerations

- **Host Networking**: Exposes all container ports to the host
- **Bridge Networking**: Only exposed ports are accessible
- **Firewall**: Ensure port 47476 is accessible if needed

## Summary

For reliable Home Assistant integration:

1. **Preferred**: Set `DOCKER_HOST_IP` environment variable
2. **Alternative**: Use `--network host` for simpler networking
3. **Fallback**: Configure `external_url_base` explicitly
