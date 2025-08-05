# Enhanced Logging Strategy

## Current Issues:

- Mixed print() statements and logging
- No log levels (INFO/WARN/ERROR)
- Console output mixed with structured logs

## Proposed Improvement:

```python
import logging
import structlog

# Setup structured logging
logging.basicConfig(
    format="%(message)s",
    level=logging.INFO,
)

logger = structlog.get_logger()

# Example usage in main():
logger.info("Starting event fetch", url=config.get("scraping.url"))
logger.info("Events fetched", raw_count=len(raw_events), processed_count=len(summarized_events))
logger.warning("Parsing errors found", error_count=len(error_log))
logger.error("Failed to fetch events", error=str(e), retry_attempt=attempt)
```

## Benefits:

- Structured JSON logs for monitoring systems
- Consistent log levels
- Easy to parse and alert on
- Separate console output from logs
