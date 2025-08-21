# Docker Deployment Examples

This guide provides practical examples for deploying Twickenham Events in Docker with proper host IP detection for Home Assistant integration.

## Quick Start Options

### Option 1: Auto-Detection (Easiest)
Let the system automatically detect your host IP:

```bash
docker run -d \
  --name twickenham-events \
  -p 47476:47476 \
  twickenham-events:latest
```

**Pros:** No configuration needed, works in many setups
**Cons:** May find a different IP than expected host IP

### Option 2: host.docker.internal (Recommended)

#### For Docker Desktop (Windows/Mac):
```bash
docker run -d \
  --name twickenham-events \
  -p 47476:47476 \
  twickenham-events:latest
```

#### For Docker on Linux:
```bash
docker run -d \
  --name twickenham-events \
  --add-host=host.docker.internal:host-gateway \
  -p 47476:47476 \
  twickenham-events:latest
```

**Pros:** Official Docker feature, always correct
**Cons:** Requires extra flag on Linux

### Option 3: Environment Variable (Most Reliable)
```bash
# Get your host IP
HOST_IP=$(hostname -I | awk '{print $1}')

# Run with explicit host IP
docker run -d \
  --name twickenham-events \
  -e DOCKER_HOST_IP=${HOST_IP} \
  -p 47476:47476 \
  twickenham-events:latest
```

**Pros:** Guaranteed accuracy, explicit control
**Cons:** Requires knowing/detecting host IP

### Option 4: Host Networking (Simplest)
```bash
docker run -d \
  --name twickenham-events \
  --network host \
  twickenham-events:latest
```

**Pros:** No port mapping, direct host access
**Cons:** Less network isolation, exposes all container ports

## Docker Compose Examples

### Standard Setup with host.docker.internal
```yaml
version: '3.8'
services:
  twickenham-events:
    image: twickenham-events:latest
    container_name: twickenham-events
    ports:
      - "47476:47476"
    extra_hosts:
      - "host.docker.internal:host-gateway"  # For Linux
    restart: unless-stopped
```

### Environment Variable Setup
```yaml
version: '3.8'
services:
  twickenham-events:
    image: twickenham-events:latest
    container_name: twickenham-events
    ports:
      - "47476:47476"
    environment:
      - DOCKER_HOST_IP=${HOST_IP:-192.168.1.100}
    restart: unless-stopped
```

### Host Networking Setup
```yaml
version: '3.8'
services:
  twickenham-events:
    image: twickenham-events:latest
    container_name: twickenham-events
    network_mode: host
    restart: unless-stopped
```

## Testing Your Setup

After starting the container, test the host IP detection:

```bash
# Check what IP was detected
docker exec twickenham-events python -c "
from src.twickenham_events.network_utils import get_docker_host_ip, build_smart_external_url
print(f'Detected Host IP: {get_docker_host_ip()}')
print(f'Generated URL: {build_smart_external_url(\"0.0.0.0\", 47476)}')
"

# Test if the URL is accessible from your host
curl http://DETECTED_IP:47476/status
```

## Home Assistant Integration

Once deployed, the MQTT status payloads will include URLs like:

```json
{
  "web_server": {
    "enabled": true,
    "base_url": "http://10.10.10.20:47476",
    "urls": {
      "calendar": "http://10.10.10.20:47476/calendar",
      "events": "http://10.10.10.20:47476/events",
      "status": "http://10.10.10.20:47476/status"
    }
  }
}
```

These URLs will be accessible from Home Assistant for calendar integration and automation triggers.

## Troubleshooting

### URLs Not Accessible from Home Assistant

1. **Check container detection:**
   ```bash
   docker logs twickenham-events | grep "Docker host"
   ```

2. **Verify host IP is correct:**
   ```bash
   # From Home Assistant host
   curl http://DETECTED_IP:47476/status
   ```

3. **Try explicit configuration:**
   ```bash
   docker run -d \
     -e DOCKER_HOST_IP=YOUR_ACTUAL_HOST_IP \
     -p 47476:47476 \
     twickenham-events:latest
   ```

### Auto-Detection Finds Wrong IP

If auto-detection finds a different IP than expected:

1. **Use environment variable for precision:**
   ```bash
   docker run -d -e DOCKER_HOST_IP=10.10.10.20 -p 47476:47476 twickenham-events
   ```

2. **Use host.docker.internal on Linux:**
   ```bash
   docker run -d --add-host=host.docker.internal:host-gateway -p 47476:47476 twickenham-events
   ```

3. **Check what IPs are reachable:**
   ```bash
   docker exec twickenham-events python -c "
   from src.twickenham_events.network_utils import _probe_for_host_ip
   print(f'Auto-detected IP: {_probe_for_host_ip()}')
   "
   ```

## Summary

**For most users:** Use `--add-host=host.docker.internal:host-gateway` on Linux or let auto-detection work
**For precision:** Set `DOCKER_HOST_IP` environment variable
**For simplicity:** Use `--network host` if network isolation isn't required

All methods will generate Home Assistant-accessible URLs instead of internal Docker bridge IPs.
