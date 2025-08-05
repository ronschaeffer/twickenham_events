# Twickenham Events - Cron Job Setup

## Recommended Schedule: Twice Daily

Since the Richmond Council website isn't updated frequently, running twice daily provides good coverage without unnecessary load.

### Suggested Times:
- **Morning**: 9:00 AM (catch any overnight updates)
- **Evening**: 6:00 PM (catch any business-day updates)

## Cron Configuration

### 1. Basic Twice-Daily Schedule
```bash
# Twickenham Events - Morning run
0 9 * * * cd /path/to/twickenham_events && poetry run python -m core

# Twickenham Events - Evening run  
0 18 * * * cd /path/to/twickenham_events && poetry run python -m core
```

### 2. With Logging
```bash
# With output logging
0 9,18 * * * cd /path/to/twickenham_events && poetry run python -m core >> /var/log/twickenham_events.log 2>&1
```

### 3. With Error Handling
```bash
# With timeout and error handling
0 9,18 * * * timeout 60 cd /path/to/twickenham_events && poetry run python -m core || echo "Twickenham Events failed at $(date)" >> /var/log/twickenham_events_errors.log
```

## Retry Configuration Options

### Standard Configuration (config.yaml)
```yaml
scraping:
  url: "https://www.richmond.gov.uk/services/parking/cpz/twickenham_events"
  max_retries: 3        # Number of retry attempts
  retry_delay: 5        # Seconds between retries
  timeout: 10           # Request timeout in seconds
```

### Conservative (for unreliable networks)
```yaml
scraping:
  max_retries: 5
  retry_delay: 10
  timeout: 15
```

### Fast (for reliable networks)
```yaml
scraping:
  max_retries: 2
  retry_delay: 3
  timeout: 8
```

## Runtime Expectations

| Configuration | Normal Run | Max Runtime (all failures) |
|---------------|------------|----------------------------|
| Standard      | 2-5 sec    | ~25 sec                   |
| Conservative  | 2-5 sec    | ~55 sec                   |
| Fast          | 2-5 sec    | ~15 sec                   |

## Monitoring Setup

### MQTT-Based Monitoring
The application publishes status to MQTT topics, allowing Home Assistant to monitor:

```yaml
# Home Assistant automation example
automation:
  - alias: "Twickenham Events Monitor"
    trigger:
      - platform: state
        entity_id: binary_sensor.twickenham_events_status
        to: 'off'
        for:
          minutes: 30
    action:
      - service: notify.mobile_app
        data:
          title: "Twickenham Events Alert"
          message: "Event scraper has been offline for 30+ minutes"
```

### Log-Based Monitoring
```bash
# Check for recent successful runs
tail -n 50 /var/log/twickenham_events.log | grep "Successfully published"

# Check for errors
tail -n 50 /var/log/twickenham_events.log | grep -E "(ERROR|Failed|❌)"
```

## Troubleshooting

### Common Issues:
1. **Network timeouts**: Increase `timeout` and `retry_delay`
2. **Website changes**: Check error logs for parsing failures
3. **MQTT connection**: Verify broker connectivity in logs

### Debug Mode:
Run manually with verbose output:
```bash
cd /path/to/twickenham_events
poetry run python -m core
```

## Security Considerations

1. **File Permissions**: Ensure cron user can read config files
2. **Log Rotation**: Set up logrotate for log files
3. **Environment Variables**: Secure .env file permissions (600)

```bash
# Secure the environment file
chmod 600 /path/to/twickenham_events/.env
chown cron_user:cron_user /path/to/twickenham_events/.env
```
