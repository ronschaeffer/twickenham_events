# MQTT Publisher Command Message Handler

This module provides a reusable `handle_command_message` function for Home Assistant MQTT automations.

## Features
- Busy/idle ack publishing for command topics
- Retained mirrors for last_ack and last_result
- Button/command mapping for HA
- Defensive error handling for robust automations

## Usage
Import and use `handle_command_message` in your MQTT callback:

```python
from ha_mqtt_publisher.message_handler import handle_command_message

# In your MQTT on_message callback:
handle_command_message(
    client, config, processor, msg,
    ack_topic, last_ack_topic, result_topic, last_result_topic
)
```

## Parameters
- `client`: MQTT client instance
- `config`: Configuration object with .get(key) method
- `processor`: Command processor with .handle_raw(cmd)
- `msg`: MQTT message object
- `ack_topic`, `last_ack_topic`, `result_topic`, `last_result_topic`: topic strings

## Example Topics
- `twickenham_events/cmd/refresh`
- `twickenham_events/commands/ack`
- `twickenham_events/commands/last_ack`
- `twickenham_events/commands/result`
- `twickenham_events/commands/last_result`
