# Unraid Docker Template Example

This guide shows how to deploy Twickenham Events on Unraid with optimal Docker networking configuration.

## 🎯 **Recommended Unraid Configuration**

### Template Settings

```xml
<?xml version="1.0"?>
<Container version="2">
  <Name>TwickenhamEvents</Name>
  <Repository>twickenham-events:latest</Repository>
  <Network>bridge</Network>
  <Mode/>
  <Privileged>false</Privileged>
  <Support>https://github.com/ronschaeffer/twickenham_events</Support>
  <Project>https://github.com/ronschaeffer/twickenham_events</Project>
  <Overview>Rugby events scraper with MQTT and Home Assistant integration</Overview>
  <Category>Tools:</Category>
  <WebUI>http://[IP]:[PORT:47476]/</WebUI>
  <TemplateURL/>
  <Icon>https://raw.githubusercontent.com/ronschaeffer/twickenham_events/main/icon.png</Icon>
  <ExtraParams>--add-host=host.docker.internal:host-gateway</ExtraParams>

  <!-- Port Mapping -->
  <Config Name="Web Server Port" Target="47476" Default="47476" Mode="tcp" Description="Web server port" Type="Port" Display="always" Required="true" Mask="false">47476</Config>

  <!-- Environment Variables -->
  <Config Name="External URL" Target="WEB_SERVER_EXTERNAL_URL" Default="" Mode="" Description="Complete external URL (e.g., http://10.10.10.20:47476)" Type="Variable" Display="always" Required="true" Mask="false"/>

  <!-- MQTT Configuration -->
  <Config Name="MQTT Enabled" Target="MQTT_ENABLED" Default="false" Mode="" Description="Enable MQTT integration" Type="Variable" Display="always" Required="false" Mask="false">false</Config>
  <Config Name="MQTT Broker URL" Target="MQTT_BROKER_URL" Default="" Mode="" Description="MQTT broker hostname or IP" Type="Variable" Display="always" Required="false" Mask="false"/>
  <Config Name="MQTT Broker Port" Target="MQTT_BROKER_PORT" Default="1883" Mode="" Description="MQTT broker port" Type="Variable" Display="always" Required="false" Mask="false">1883</Config>
  <Config Name="MQTT Username" Target="MQTT_USERNAME" Default="" Mode="" Description="MQTT username" Type="Variable" Display="always" Required="false" Mask="false"/>
  <Config Name="MQTT Password" Target="MQTT_PASSWORD" Default="" Mode="" Description="MQTT password" Type="Variable" Display="always" Required="false" Mask="true"/>

  <!-- Home Assistant Integration -->
  <Config Name="Home Assistant Enabled" Target="HOME_ASSISTANT_ENABLED" Default="false" Mode="" Description="Enable Home Assistant discovery" Type="Variable" Display="always" Required="false" Mask="false">false</Config>

  <!-- Volume Mappings -->
  <Config Name="Config Directory" Target="/app/config" Default="/mnt/user/appdata/twickenham-events/config" Mode="rw" Description="Configuration files" Type="Path" Display="always" Required="true" Mask="false">/mnt/user/appdata/twickenham-events/config</Config>
  <Config Name="Data Directory" Target="/app/data" Default="/mnt/user/appdata/twickenham-events/data" Mode="rw" Description="Data storage" Type="Path" Display="always" Required="true" Mask="false">/mnt/user/appdata/twickenham-events/data</Config>
</Container>
```

## 🚀 **Quick Setup for Unraid Users**

### Method 1: Using External URL (Recommended)

1. **Set External URL**: In the template, set `WEB_SERVER_EXTERNAL_URL` to:
   ```
   http://YOUR_UNRAID_IP:47476
   ```
   Example: `http://10.10.10.20:47476`

2. **Enable Extra Parameters**: The template includes:
   ```
   --add-host=host.docker.internal:host-gateway
   ```

### Method 2: Automatic Detection (Zero Config)

1. **Leave External URL empty**
2. **Keep Extra Parameters**: The `--add-host` flag enables automatic detection
3. **Auto-detection will find your Unraid server IP**

## 🏠 **Home Assistant Integration**

Once deployed, the container will automatically publish MQTT messages with proper URLs that Home Assistant can reach:

```json
{
  "web_server": {
    "status": "running",
    "url": "http://10.10.10.20:47476",
    "endpoints": {
      "events": "http://10.10.10.20:47476/events",
      "health": "http://10.10.10.20:47476/health"
    }
  }
}
```

## 🔧 **Troubleshooting**

### If URLs show Docker IP (172.x.x.x)

1. **Verify Extra Parameters**: Ensure `--add-host=host.docker.internal:host-gateway` is set
2. **Set External URL**: Manually set `WEB_SERVER_EXTERNAL_URL=http://YOUR_UNRAID_IP:47476`
3. **Check Network**: Ensure your Unraid server has a static IP

### If Container Won't Start

1. **Check Port Conflicts**: Ensure port 47476 is available
2. **Verify Paths**: Make sure appdata directories exist
3. **Check MQTT Settings**: Verify MQTT broker connectivity if enabled

## 📋 **Example Working Configuration**

For a typical Unraid setup on `10.10.10.20`:

```bash
# Environment Variables
WEB_SERVER_EXTERNAL_URL=http://10.10.10.20:47476
MQTT_ENABLED=true
MQTT_BROKER_URL=10.10.10.20
MQTT_BROKER_PORT=1883
HOME_ASSISTANT_ENABLED=true

# Extra Parameters
--add-host=host.docker.internal:host-gateway

# Port Mapping
47476:47476

# Volume Mappings
/mnt/user/appdata/twickenham-events/config:/app/config
/mnt/user/appdata/twickenham-events/data:/app/data
```

This configuration provides:
- ✅ Perfect URL generation for Home Assistant
- ✅ Automatic Docker host detection
- ✅ Clean, single-setting configuration
- ✅ Zero network configuration required
