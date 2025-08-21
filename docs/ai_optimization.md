# AI Processing Optimization

## Overview

The `get_combined_ai_info()` method combines event shortening, type detection, and icon selection into a single API call, reducing Gemini API quota usage by up to 50%.

## Problem

Previously, each event required separate API calls:
1. `get_short_name()` - for shortening event names
2. `get_event_type_and_icons()` → `_detect_event_type_ai()` - for type detection

For 9 events, this meant **18 API calls** (2 per event), which quickly hits the free tier quota limit of 2 requests/minute.

## Solution

The new `get_combined_ai_info()` method makes **1 API call per event**, reducing quota usage by 50%.

## Usage

### Basic Usage

```python
from twickenham_events.ai_processor import AIProcessor
from twickenham_events.config import Config

config = Config.from_file("config/config.yaml")
ai_processor = AIProcessor(config)

# Single call gets all AI-powered information
result = ai_processor.get_combined_ai_info("England v Australia")

print(f"Short name: {result['short_name']}")     # "🏴󠁧󠁢󠁥󠁮󠁧󠁿 ENG v 🇦🇺 AUS"
print(f"Event type: {result['event_type']}")     # "rugby"
print(f"Emoji: {result['emoji']}")               # "🏉"
print(f"MDI icon: {result['mdi_icon']}")         # "mdi:rugby"
print(f"Had error: {result['had_error']}")       # False
```

### Return Format

```python
{
    "short_name": str,      # Shortened version or original if shortening disabled/failed
    "event_type": str,      # "trophy", "rugby", "concert", or "generic"
    "emoji": str,           # Unicode emoji for display ("🏉", "🏆", "🎵", "🏟️")
    "mdi_icon": str,        # Material Design Icon name ("mdi:rugby", "mdi:trophy", etc.)
    "had_error": bool,      # True if processing failed
    "error_message": str    # Error details if had_error is True, empty string otherwise
}
```

### Configuration Requirements

Both features must be enabled for maximum API optimization:

```yaml
ai_processor:
  api_key: "${GEMINI_API_KEY}"

  shortening:
    enabled: true
    # ... other shortening config

  type_detection:
    enabled: true
    # ... other type detection config
```

## Behavior Matrix

| Shortening | Type Detection | API Calls | Method Used |
|------------|----------------|-----------|-------------|
| ✅ Yes      | ✅ Yes          | 1         | Combined API call |
| ✅ Yes      | ❌ No           | 1         | Individual `get_short_name()` |
| ❌ No       | ✅ Yes          | 1         | Individual `get_event_type_and_icons()` |
| ❌ No       | ❌ No           | 0         | Fallback patterns only |

## Integration Examples

### Scraper Integration

Replace individual shortening calls:

```python
# OLD approach
if processor:
    try:
        short_name, _, _ = processor.get_short_name(fixture_name)
    except Exception as e:
        self.error_log.append(f"AI shortening failed for '{fixture_name}': {e}")

# NEW approach - store all AI info for later use
ai_info = None
if processor:
    try:
        ai_info = processor.get_combined_ai_info(fixture_name)
        short_name = ai_info['short_name']
    except Exception as e:
        self.error_log.append(f"AI processing failed for '{fixture_name}': {e}")
```

### MQTT Client Integration

Replace individual type detection calls:

```python
# OLD approach
if ai_processor and "fixture" in e:
    try:
        _etype, emoji_ai, mdi_icon = ai_processor.get_event_type_and_icons(e["fixture"])
        if emoji_ai:
            e["emoji"] = emoji_ai
        e["icon"] = mdi_icon
    except Exception:
        ai_errors += 1

# NEW approach - use pre-computed AI info if available
if ai_info:  # If we stored AI info during scraping
    e["emoji"] = ai_info["emoji"]
    e["icon"] = ai_info["mdi_icon"]
elif ai_processor and "fixture" in e:
    # Fallback to individual call if needed
    try:
        _etype, emoji_ai, mdi_icon = ai_processor.get_event_type_and_icons(e["fixture"])
        # ... rest of logic
```

## Caching

The combined method uses the same caching mechanisms as individual methods:
- Results are cached with key `f"combined_{event_name}"`
- Cache settings from `ai_processor.shortening.cache_enabled` are respected
- Cache entries include all AI-generated information

## Circuit Breaker

The combined method respects the existing circuit breaker:
- Falls back to individual methods or patterns when quota limits are hit
- Uses the same backoff timing as the shortening feature
- Gracefully degrades without breaking functionality

## Error Handling

- **Network errors**: Falls back to pattern-based detection
- **Quota limits**: Opens circuit breaker, subsequent calls use fallbacks
- **Invalid responses**: Returns original name with pattern-based type detection
- **Missing API key**: Returns original name with pattern-based type detection

## Performance Benefits

For typical Twickenham Events scraping (9 events):

| Metric | Old Approach | New Approach | Improvement |
|--------|--------------|--------------|-------------|
| API calls | 18 | 9 | 50% reduction |
| Network requests | 18 | 9 | 50% faster |
| Quota usage | High | Medium | 2x quota efficiency |
| Rate limit issues | Frequent | Rare | Better compliance |

## Migration Guide

1. **Test first**: Run the demo script to verify functionality
2. **Update scraping**: Modify scraper to use combined method
3. **Update MQTT**: Modify MQTT client to reuse AI info
4. **Monitor**: Check logs for API usage and errors
5. **Optimize**: Adjust caching and circuit breaker settings if needed
