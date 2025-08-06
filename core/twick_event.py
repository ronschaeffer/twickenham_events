#!/usr/bin/env python3
# codespell:ignore nd,st,rd,th

from datetime import date, datetime, time, timedelta
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple  # noqa: UP035

from bs4 import BeautifulSoup
from mqtt_publisher.publisher import MQTTPublisher
import requests

from core.config import Config
from core.event_shortener import get_short_name
from core.ha_mqtt_discovery import publish_discovery_configs_for_twickenham

# Add project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# --- Global Variables ---
error_log = []


# --- Data Parsing and Normalization Functions ---


def normalize_time(time_str: Optional[str]) -> Optional[List[str]]:  # noqa: UP006
    """Normalize time format, returning a list of sorted times."""
    if not time_str or time_str.lower() == "tbc":
        return None

    time_str = time_str.lower()

    # Handle specific midnight patterns first to avoid duplicates
    time_str = re.sub(r"\b12\s*midnight\b", "12:00am", time_str)
    time_str = re.sub(r"\bmidnight\s*12\b", "12:00am", time_str)
    # Then handle standalone midnight
    time_str = time_str.replace("midnight", "12:00am")

    # Handle specific noon patterns first to avoid duplicates
    time_str = re.sub(r"\b12\s*noon\b", "12:00pm", time_str)
    time_str = re.sub(r"\bnoon\s*12\b", "12:00pm", time_str)
    # Then handle standalone noon
    time_str = time_str.replace("noon", "12:00pm")

    time_str = re.sub(r"\s*\(tbc\)", "", time_str, flags=re.IGNORECASE)
    time_str = time_str.replace(".", ":")
    time_str = time_str.replace(" and ", " & ")

    time_patterns = re.findall(
        r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm)?\b", time_str, re.IGNORECASE
    )
    if not time_patterns:
        error_log.append(f"No valid time patterns found in: '{time_str}'")
        return None

    def is_valid_time(hour: int, minute: int) -> bool:
        return 0 <= hour <= 23 and 0 <= minute <= 59

    def parse_single_time(
        time_part: str, shared_meridian: Optional[str] = None
    ) -> tuple[Optional[str], Optional[str]]:
        time_part = time_part.strip().lower()
        meridian = shared_meridian

        if "pm" in time_part:
            meridian = "pm"
            time_part = time_part.replace("pm", "").strip()
        elif "am" in time_part:
            meridian = "am"
            time_part = time_part.replace("am", "").strip()

        try:
            if ":" in time_part:
                hour_str, minute_str = time_part.split(":")
                hour, minute = int(hour_str), int(minute_str)
            else:
                hour, minute = int(time_part), 0

            # Enhanced validation logic from ICS Utils
            # Convert to 24-hour format
            if meridian == "pm" and hour != 12:
                hour += 12
            elif meridian == "am" and hour == 12:
                hour = 0

            if not is_valid_time(hour, minute):
                return None, None

            return f"{hour:02d}:{minute:02d}", meridian
        except (ValueError, AttributeError):
            error_log.append(f"Failed to parse time component: '{time_part}'")
            return None, None

    # Find the last meridian indicator to use as default (enhanced logic)
    last_meridian = None
    for t in reversed(time_patterns):
        if "am" in t:
            last_meridian = "am"
            break
        elif "pm" in t:
            last_meridian = "pm"
            break

    converted_times = []
    for time_pattern in time_patterns:
        parsed_time, _ = parse_single_time(time_pattern, last_meridian)
        if parsed_time:
            converted_times.append(parsed_time)

    return sorted(converted_times) if converted_times else None


def normalize_date_range(date_str: Optional[str]) -> Optional[str]:
    """Normalizes a variety of date string formats to 'YYYY-MM-DD'.

    Handles date ranges by taking the start date.
    Returns None if the date string is invalid.
    """
    if not date_str or not isinstance(date_str, str):
        return None

    # Pre-process the string to handle various formats
    cleaned_str = date_str.lower()

    # Remove day names, ordinals, and 'weekend' markers
    cleaned_str = re.sub(
        r"\b(mon|tue|wed|thu|fri|sat|sun|monday|tuesday|wednesday|thursday|friday|saturday|sunday|weekend|wknd)\b",
        "",
        cleaned_str,
    ).strip()

    cleaned_str = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", cleaned_str)

    # Handle date ranges like '16/17 May 2025' by taking the first day part
    cleaned_str = re.sub(
        r"(\d{1,2})\s*/\s*\d{1,2}(\s+[a-zA-Z]+\s+\d{2,4})",
        r"\1\2",
        cleaned_str,
    )

    # Normalize separators to a single space, but keep commas for certain patterns
    # First handle dates like "Dec 20, 2024" by converting to "20 Dec 2024"
    comma_match = re.match(r"([a-z]+)\s+(\d{1,2}),\s+(\d{4})", cleaned_str)
    if comma_match:
        month, day, year = comma_match.groups()
        cleaned_str = f"{day} {month} {year}"
    else:
        cleaned_str = cleaned_str.replace(",", "")

    cleaned_str = cleaned_str.replace("-", " ").replace("/", " ").replace(".", " ")
    cleaned_str = re.sub(r"\s+", " ", cleaned_str).strip()

    # Enhanced list of possible date formats from ICS Utils
    patterns = [
        "%Y-%m-%d",  # ISO format: 2024-12-20
        "%d %B %Y",  # e.g., 16 may 2025, 20 December 2024
        "%d %b %Y",  # e.g., 16 aug 2025, 20 Dec 2024
        "%d %B %y",  # e.g., 16 may 23
        "%d %b %y",  # e.g., 16 aug 23
        "%d %m %Y",  # e.g., 16 05 2025, 20 12 2024
        "%d %m %y",  # e.g., 16 05 23
        "%Y %m %d",  # ISO format with spaces
        "%b %d %Y",  # e.g., Dec 20, 2024
        "%B %d %Y",  # e.g., December 20, 2024
        "%m %d %Y",  # e.g., 12 20 2024
    ]

    for fmt in patterns:
        try:
            parsed_date = datetime.strptime(cleaned_str, fmt).date()
            # Handle 2-digit years
            if parsed_date.year < 2000:
                parsed_date = parsed_date.replace(year=parsed_date.year + 2000)
            return parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            continue

    return None


def validate_crowd_size(crowd_str: Optional[str]) -> Optional[str]:
    """Validates and formats the crowd size string."""
    if not crowd_str or not isinstance(crowd_str, str):
        return None

    cleaned_crowd = re.sub(
        r"(TBC|Estimate|Est|Approx|~)", "", crowd_str, flags=re.IGNORECASE
    ).strip()
    range_match = re.search(r"(\d+)\s*-\s*(\d+,\d+)", cleaned_crowd)
    if range_match:
        cleaned_crowd = range_match.group(2)

    crowd_no_commas = cleaned_crowd.replace(",", "")
    numbers = re.findall(r"\d+", crowd_no_commas)
    if not numbers:
        return None

    try:
        int_numbers = [int(n) for n in numbers]
        crowd = max(int_numbers)
        if crowd > 100000:
            potential_crowds = [n for n in int_numbers if n <= 100000]
            crowd = max(potential_crowds) if potential_crowds else None
            if crowd is None:
                error_log.append(f"Implausible crowd size detected: '{crowd_str}'")
                return None
        return f"{crowd:,}"
    except (ValueError, IndexError):
        error_log.append(f"Invalid crowd size: '{crowd_str}'")
        return None


def fetch_events_single_attempt(url: str, timeout: int = 10) -> List[Dict[str, str]]:  # noqa: UP006
    """
    Single attempt to fetch events from the website.

    Args:
        url (str): The URL to scrape for events.
        timeout (int): Request timeout in seconds.

    Returns:
        List[Dict[str, str]]: A list of raw event data dictionaries.

    Raises:
        requests.RequestException: If network request fails
    """
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")

    # --- Richmond.gov.uk specific parsing ---
    event_tables = soup.find_all("table", class_="table")
    raw_events = []

    for table in event_tables:
        caption = table.find("caption")  # type: ignore
        if not caption or "events at twickenham stadium" not in caption.text.lower():  # type: ignore
            continue

        for row in table.find_all("tr")[1:]:  # Skip header row  # type: ignore
            cols = row.find_all("td")  # type: ignore
            if len(cols) >= 3:
                raw_events.append(
                    {
                        "date": cols[0].text.strip(),
                        "title": cols[1].text.strip(),
                        "time": cols[2].text.strip(),
                        "crowd": cols[3].text.strip() if len(cols) > 3 else None,
                    }
                )
    return raw_events


def fetch_events_with_retry(
    url: str, max_retries: int = 3, delay: int = 5, timeout: int = 10
) -> tuple[List[Dict[str, str]], dict]:  # noqa: UP006
    """
    Fetch events with retry logic for temporary outages.

    Args:
        url (str): The URL to scrape for events.
        max_retries (int): Maximum number of retry attempts
        delay (int): Delay in seconds between retries
        timeout (int): Request timeout in seconds

    Returns:
        tuple: (events_list, stats_dict) where stats contains retry and timing info
    """
    import time as time_module

    start_time = time_module.time()

    for attempt in range(max_retries):
        try:
            print(
                f"🌐 Fetching events (attempt \033[33m{attempt + 1}\033[0m/\033[33m{max_retries}\033[0m)..."
            )
            events = fetch_events_single_attempt(url, timeout)

            # Calculate stats
            fetch_duration = time_module.time() - start_time
            stats = {
                "raw_events_count": len(events) if events else 0,
                "fetch_duration": round(fetch_duration, 2),
                "retry_attempts": attempt + 1,
                "data_source": "live",
            }

            if events:  # Success with data
                print(f"   \033[32m🎯 Successfully fetched {len(events)} events\033[0m")
                print(
                    f"   \033[36m⏱️  Fetch completed in {stats['fetch_duration']}s\033[0m"
                )
                return events, stats
            else:
                print("   \033[33m📭 No events found in response\033[0m")
                # Even if no events, don't retry - this might be normal
                return events, stats

        except requests.RequestException as e:
            error_msg = f"Attempt {attempt + 1} failed: {e}"
            error_log.append(error_msg)
            print(f"   \033[31m❌ {error_msg}\033[0m")

            if attempt < max_retries - 1:  # Not the last attempt
                print(f"   \033[33m⏳ Retrying in {delay} seconds...\033[0m")
                time_module.sleep(delay)
            else:
                print("   \033[31m🚫 All retry attempts failed\033[0m")

    # All attempts failed
    fetch_duration = time_module.time() - start_time
    failed_stats = {
        "raw_events_count": 0,
        "fetch_duration": round(fetch_duration, 2),
        "retry_attempts": max_retries,
        "data_source": "failed",
    }
    return [], failed_stats


def fetch_events(
    url: Optional[str], config: Optional["Config"] = None
) -> tuple[List[Dict[str, str]], dict]:  # noqa: UP006
    """
    Fetches events from the Twickenham Stadium website with configurable retry logic.

    Args:
        url (str): The URL to scrape for events.
        config (Config): Configuration object for retry settings.

    Returns:
        tuple: (events_list, stats_dict) with processing statistics
    """
    if not url:
        error_log.append(
            "Configuration error: 'scraping.url' is not set in the config file."
        )
        return [], {
            "raw_events_count": 0,
            "fetch_duration": 0,
            "retry_attempts": 0,
            "data_source": "config_error",
        }

    # Get retry settings from config with sensible defaults
    if config:
        max_retries = config.get("scraping.max_retries", 3)
        retry_delay = config.get("scraping.retry_delay", 5)
        timeout = config.get("scraping.timeout", 10)
    else:
        max_retries, retry_delay, timeout = 3, 5, 10

    # Use retry logic for better reliability
    return fetch_events_with_retry(url, max_retries, retry_delay, timeout)


def summarise_events(
    raw_events: List[Dict[str, str]],  # noqa: UP006
    config: Config,
) -> List[Dict[str, Any]]:  # noqa: UP006
    """
    Summarises and filters a list of raw event data.
    - Normalizes date and time formats.
    - Filters out events that have already passed.
    - Groups events by date.
    """
    today = datetime.now().date()
    summarized_by_date = {}

    for event in raw_events:
        event_date_str = normalize_date_range(event["date"])
        if not event_date_str:
            error_log.append(f"Could not parse date: {event['date']}")
            continue

        try:
            event_date = datetime.strptime(event_date_str, "%Y-%m-%d").date()
        except ValueError:
            error_log.append(f"Invalid date format: {event_date_str}")
            continue

        if event_date < today:
            continue

        event_date_iso = event_date.isoformat()
        if event_date_iso not in summarized_by_date:
            summarized_by_date[event_date_iso] = {
                "date": event_date_iso,
                "events": [],
                "earliest_start": None,
            }

        start_times = normalize_time(event.get("time"))
        crowd_size = validate_crowd_size(event.get("crowd"))

        # Get shortened name for the fixture
        fixture_name = event["title"]
        short_name, shortening_error, error_message = get_short_name(
            fixture_name, config
        )
        if shortening_error:
            error_log.append(
                f"AI shortening failed for '{fixture_name}': {error_message}"
            )

        if start_times:
            for time in start_times:
                event_data = {
                    "fixture": fixture_name,
                    "start_time": time,
                    "crowd": crowd_size,
                }
                # Add short name if different from original
                if short_name != fixture_name:
                    event_data["fixture_short"] = short_name
                summarized_by_date[event_date_iso]["events"].append(event_data)
        else:
            # Handle events with no specific start time (TBC)
            event_data = {
                "fixture": fixture_name,
                "start_time": None,
                "crowd": crowd_size,
            }
            # Add short name if different from original
            if short_name != fixture_name:
                event_data["fixture_short"] = short_name
            summarized_by_date[event_date_iso]["events"].append(event_data)

    # Determine the earliest start time for each day and add event counts
    for date_summary in summarized_by_date.values():
        # Sort events within the day by start_time
        date_summary["events"].sort(key=lambda x: x.get("start_time") or "23:59")

        # Add event_index and event_count to each event
        total_events = len(date_summary["events"])
        for i, event in enumerate(date_summary["events"]):
            event["event_index"] = i + 1
            event["event_count"] = total_events

        start_times = [
            e.get("start_time") for e in date_summary["events"] if e.get("start_time")
        ]
        if start_times:
            date_summary["earliest_start"] = min(start_times)

    return sorted(summarized_by_date.values(), key=lambda x: x["date"])


def find_next_event_and_summary(
    summarized_events: list, config: Config
) -> Tuple[Optional[dict], Optional[dict]]:  # noqa: UP006
    """
    Finds the current or next upcoming event and a summary for that day.
    An event is considered "over" based on rules in the config.
    """
    now = datetime.now()
    today = now.date()

    # Get rules from config, with defaults
    cutoff_str = config.get("event_rules.end_of_day_cutoff", "23:00")
    delay_hours = config.get("event_rules.next_event_delay_hours", 1)

    try:
        cutoff_time = datetime.strptime(cutoff_str, "%H:%M").time()
    except ValueError:
        cutoff_time = time(23, 0)  # Default fallback
        error_log.append(
            f"Invalid cutoff time format '{cutoff_str}', defaulting to 23:00."
        )

    # Filter for events that are not definitively in the past
    future_or_current_events = [
        event
        for event in summarized_events
        if datetime.strptime(event["date"], "%Y-%m-%d").date() >= today
    ]

    if not future_or_current_events:
        return None, None

    # Sort by date, then by earliest start time
    future_or_current_events.sort(
        key=lambda x: (x["date"], x.get("earliest_start") or "23:59")
    )

    for _i, event_day in enumerate(future_or_current_events):
        event_date = datetime.strptime(event_day["date"], "%Y-%m-%d").date()

        # If the event day is in the future, it's the one we want
        if event_date > today:
            return event_day["events"][0], event_day

        # If the event day is today, we need to apply the new logic
        if event_date == today:
            # Sort today's individual events by start time
            sorted_events_today = event_day["events"]

            # Check if we are past the end-of-day cutoff time
            if now.time() >= cutoff_time:
                # If so, all of today's events are over. Look for the next day's event.
                continue

            for j, event_item in enumerate(sorted_events_today):
                start_time_str = event_item.get("start_time")
                if not start_time_str:
                    # If no start time, it can't be determined to be "over" until cutoff, so it's the next one
                    return event_item, event_day

                # Handle multiple times, e.g., "15:00 & 18:00", take the earliest
                earliest_start_str = start_time_str
                try:
                    start_time = datetime.strptime(earliest_start_str, "%H:%M").time()
                except ValueError:
                    continue  # Skip if time is invalid

                # Check if the event is over
                is_over = False
                # Rule 1: Is there a subsequent event on the same day?
                if j + 1 < len(sorted_events_today) and (
                    now.time()
                    >= (
                        datetime.combine(date.today(), start_time)
                        + timedelta(hours=delay_hours)
                    ).time()
                ):
                    is_over = True

                # If not over by the delay rule, it's our current/next event
                if not is_over:
                    return event_item, event_day

            # If all of today's events are considered over by the delay rule, check the next day
            continue

    # If the loop completes, no future events were found
    return None, None


def process_and_publish_events(
    summarized_events: list,
    publisher: MQTTPublisher,
    config: Config,
    processing_stats: Optional[Dict[str, Any]] = None,  # noqa: UP006
):
    """
    Processes summarized event data and publishes it to relevant MQTT topics.
    Also publishes enhanced status information with metrics.
    """
    from pathlib import Path
    import sys

    next_event, next_day_summary = find_next_event_and_summary(
        summarized_events, config
    )

    timestamp = datetime.now().isoformat()

    # Publish to event topics
    publisher.publish(
        config.get("mqtt.topics.all_upcoming"),
        {"last_updated": timestamp, "events": summarized_events},
        retain=True,
    )
    publisher.publish(
        config.get("mqtt.topics.next"),
        {
            "last_updated": timestamp,
            "event": next_event,
            "date": next_day_summary["date"] if next_day_summary else None,
        },
        retain=True,
    )

    # Enhanced status payload with processing metrics
    errors = error_log
    status_payload = {
        "status": "ok" if not errors else "error",
        "last_updated": timestamp,
        "event_count": len(summarized_events),
        "error_count": len(errors),
        "errors": errors,
    }

    # Add processing metrics if available
    if processing_stats:
        status_payload["metrics"] = {
            "raw_events_found": processing_stats.get("raw_events_count", 0),
            "processed_events": len(summarized_events),
            "events_filtered": processing_stats.get("raw_events_count", 0)
            - len(summarized_events),
            "fetch_duration_seconds": processing_stats.get("fetch_duration", 0),
            "retry_attempts_used": processing_stats.get("retry_attempts", 0),
            "data_source": processing_stats.get(
                "data_source", "live"
            ),  # live, previous_run, fallback
        }

    # Add system info for transparency
    config_path = getattr(config, "config_path", None)
    status_payload["system_info"] = {
        "app_version": "0.1.0",  # Could read from pyproject.toml
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "config_source": str(Path(config_path).name) if config_path else "unknown",
    }

    status_topic = config.get("mqtt.topics.status")
    publisher.publish(status_topic, status_payload, retain=True)


def main():
    """
    Main function to run the event scraper and publisher.
    """
    config = Config()
    # Publisher for Home Assistant discovery
    ha_discovery_publisher = MQTTPublisher(
        broker_url=config.get("mqtt.broker.url"),
        broker_port=config.get("mqtt.broker.port"),
        client_id=config.get("mqtt.client.id_discovery", "twick_event_discovery"),
        security=config.get("mqtt.security.type"),
        auth=config.get("mqtt.security.auth"),
        tls=config.get("mqtt.security.tls"),
    )
    publish_discovery_configs_for_twickenham(config, ha_discovery_publisher)
    ha_discovery_publisher.disconnect()

    # Main publisher for event data
    publisher = MQTTPublisher(
        broker_url=config.get("mqtt.broker.url"),
        broker_port=config.get("mqtt.broker.port"),
        client_id=config.get("mqtt.client.id_main", "twick_event_main"),
        security=config.get("mqtt.security.type"),
        auth=config.get("mqtt.security.auth"),
        tls=config.get("mqtt.security.tls"),
    )
    raw_events, processing_stats = fetch_events(config.get("scraping.url"), config)

    if raw_events:
        summarized_events = summarise_events(raw_events, config)
        process_and_publish_events(
            summarized_events, publisher, config, processing_stats
        )
    else:
        # Publish error status even if no events fetched
        process_and_publish_events([], publisher, config, processing_stats)

    # Save errors to a file
    if error_log:
        error_file_path = os.path.join(
            config.get("logging.log_dir", "output"), "parsing_errors.json"
        )
        os.makedirs(os.path.dirname(error_file_path), exist_ok=True)
        with open(error_file_path, "w") as f:
            json.dump(error_log, f, indent=4)
        print(f"Completed with {len(error_log)} errors. See {error_file_path}")
    else:
        print("Completed successfully.")


if __name__ == "__main__":
    main()
