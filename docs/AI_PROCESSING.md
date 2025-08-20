# AI Processing

This document explains the AI processing features used to shorten event names and suggest event types. AI is optional and disabled by default.

## Overview

- Shortening of long event names to a configured maximum length
- Optional country flag insertion when space allows
- Type detection hints (e.g., rugby, concert, generic)
- On-disk caches to reduce repeated API calls

## Configuration

Enable and configure in `config/config.yaml`:

```yaml
ai_processor:
  api_key: "${GEMINI_API_KEY}"
  shortening:
    enabled: false
    model: "gemini-2.5-pro"
    max_length: 25
    flags_enabled: true
    cache_enabled: true
  type_detection:
    enabled: false
    cache_dir: "output/cache"
```

Environment variables should be set in `.env` using `${VAR}` syntax. Do not hardcode secrets.

## Caching

- Event name cache file: `output/event_name_cache.json` (default)
- Type detection cache file: `output/cache/ai_type_cache.json` (default; directory configurable via `ai_processor.type_detection.cache_dir`)
- Caches are JSON objects keyed by original names

The AI processor reads from cache before issuing API calls, and writes successful (or failed) attempts to avoid repeated calls on errors.

## CLI Cache Management

```bash
poetry run twick-events cache clear      # Remove all cached entries
poetry run twick-events cache stats      # Show cache counts
poetry run twick-events cache reprocess  # Recompute entries using current config
```

## Failure Handling

- API timeouts and errors increment `ai_error_count`
- Processing falls back to original fixture string
- Errors are recorded in the status payload `errors` list for diagnostics

## Data Flow (when enabled)

1. Input fixture string (normalized)
2. Cache lookup
3. Request to Gemini API
4. Length validation and flag insertion as configured
5. Save to cache and attach `fixture_short` and type hints

## Security Notes

- Only event titles are sent to the AI API
- Keep API keys in environment variables
- TLS is recommended for MQTT connections
