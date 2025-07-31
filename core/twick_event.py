#!/usr/bin/env python3

from core.mqtt_publisher import MQTTPublisher
from core.ha_mqtt_discovery import publish_discovery_configs
from core.config import Config
import json
import os
import re
import sys
from datetime import datetime, date
from typing import Optional, Tuple

import requests
from bs4 import BeautifulSoup

# Add project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# --- Global Variables ---
error_log = []


# --- Data Parsing and Normalization Functions ---

def normalize_time(time_str: Optional[str]) -> Optional[str]:
    """Normalize time format, handling multiple times separated by '&'."""
    if not time_str or time_str.lower() == 'tbc':
        return None

    time_str = time_str.lower().replace('noon', '12:00pm')
    time_str = re.sub(r'\s*\(tbc\)', '', time_str, flags=re.IGNORECASE)
    time_str = time_str.replace('.', ':')
    time_str = time_str.replace(' and ', ' & ')

    time_patterns = re.findall(
        r'\b\d{1,2}(?::\d{2})?\s*(?:am|pm)?\b', time_str, re.IGNORECASE)
    if not time_patterns:
        error_log.append(f"No valid time patterns found in: '{time_str}'")
        return None

    def is_valid_time(hour, minute):
        return 0 <= hour <= 23 and 0 <= minute <= 59

    def parse_single_time(time, shared_meridian=None):
        time = time.strip().lower()
        meridian = shared_meridian
        if 'pm' in time:
            meridian = 'pm'
            time = time.replace('pm', '').strip()
        elif 'am' in time:
            meridian = 'am'
            time = time.replace('am', '').strip()

        try:
            hour, minute = (map(int, time.split(':'))
                            if ':' in time else (int(time), 0))
            if hour > 12 and meridian:
                return None, None
            if hour > 23:
                return None, None
            if meridian == 'pm' and hour < 12:
                hour += 12
            elif meridian == 'am' and hour == 12:
                hour = 0
            return (f"{hour:02d}:{minute:02d}", meridian) if is_valid_time(hour, minute) else (None, None)
        except (ValueError, AttributeError):
            error_log.append(f"Failed to parse time component: '{time}'")
            return None, None

    last_meridian = next((m for t in reversed(time_patterns) if (
        m := ('am' if 'am' in t else 'pm' if 'pm' in t else None))), None)
    converted_times = [parsed_time for time in time_patterns if (
        parsed_time := parse_single_time(time, last_meridian)[0])]
    return ' & '.join(sorted(converted_times)) if converted_times else None


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
        r'\b(mon|tue|wed|thu|fri|sat|sun|monday|tuesday|wednesday|thursday|friday|saturday|sunday|weekend|wknd)\b', '', cleaned_str).strip()
    cleaned_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', cleaned_str)

    # Handle date ranges like '16/17 May 2025' by taking the first day part
    cleaned_str = re.sub(
        r'(\d{1,2})\s*/\s*\d{1,2}(\s+[a-zA-Z]+\s+\d{2,4})', r'\1\2', cleaned_str)

    # Normalize separators to a single space
    cleaned_str = cleaned_str.replace(
        '-', ' ').replace('/', ' ').replace('.', ' ')
    # Remove extra whitespace
    cleaned_str = re.sub(r'\s+', ' ', cleaned_str).strip()

    # List of possible date formats (now with spaces as separator)
    patterns = [
        '%d %B %Y',   # e.g., 16 may 2025
        '%d %b %Y',   # e.g., 16 aug 2025
        '%d %B %y',   # e.g., 16 may 23
        '%d %b %y',   # e.g., 16 aug 23
        '%d %m %Y',   # e.g., 16 05 2025
        '%d %m %y',   # e.g., 16 05 23
        '%Y %m %d'    # ISO format
    ]

    # Try parsing the cleaned string with the defined patterns
    for fmt in patterns:
        try:
            return datetime.strptime(cleaned_str, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue

    return None


def validate_crowd_size(crowd_str: Optional[str]) -> Optional[str]:
    """Validates and formats the crowd size string."""
    if not crowd_str or not isinstance(crowd_str, str):
        return None

    cleaned_crowd = re.sub(r'(TBC|Estimate|Est|Approx|~)',
                           '', crowd_str, flags=re.IGNORECASE).strip()
    range_match = re.search(r'(\d+)\s*-\s*(\d+,\d+)', cleaned_crowd)
    if range_match:
        cleaned_crowd = range_match.group(2)

    crowd_no_commas = cleaned_crowd.replace(',', '')
    numbers = re.findall(r'\d+', crowd_no_commas)
    if not numbers:
        return None

    try:
        int_numbers = [int(n) for n in numbers]
        crowd = max(int_numbers)
        if crowd > 100000:
            potential_crowds = [n for n in int_numbers if n <= 100000]
            crowd = max(potential_crowds) if potential_crowds else None
            if crowd is None:
                error_log.append(
                    f"Implausible crowd size detected: '{crowd_str}'")
                return None
        return f"{crowd:,}"
    except (ValueError, IndexError):
        error_log.append(f"Invalid crowd size: '{crowd_str}'")
        return None


def fetch_events(url: Optional[str]) -> list[dict]:
    """
    Fetches events from the Twickenham Stadium website.

    Args:
        url (str): The URL to scrape for events.

    Returns:
        list[dict]: A list of raw event data dictionaries.
    """
    if not url:
        error_log.append(
            "Configuration error: 'scraping.url' is not set in the config file.")
        return []
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        error_log.append(f"Failed to fetch URL {url}: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')

    # --- Richmond.gov.uk specific parsing ---
    event_tables = soup.find_all('table', class_='table')
    raw_events = []

    for table in event_tables:
        caption = table.find('caption')
        if not caption or 'events at twickenham stadium' not in caption.text.lower():
            continue

        for row in table.find_all('tr')[1:]:  # Skip header row
            cols = row.find_all('td')
            if len(cols) >= 3:
                raw_events.append({
                    'date': cols[0].text.strip(),
                    'title': cols[1].text.strip(),
                    'time': cols[2].text.strip(),
                    'crowd': cols[3].text.strip() if len(cols) > 3 else None
                })
    return raw_events


def summarise_events(raw_events: list[dict]) -> list[dict]:
    """
    Summarises and filters a list of raw event data.
    - Normalizes date and time formats.
    - Filters out events that have already passed.
    - Groups events by date.
    """
    today = datetime.now().date()
    summarized_by_date = {}

    for event in raw_events:
        event_date_str = normalize_date_range(event['date'])
        if not event_date_str:
            error_log.append(f"Could not parse date: {event['date']}")
            continue

        try:
            event_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()
        except ValueError:
            error_log.append(f"Invalid date format: {event_date_str}")
            continue

        if event_date < today:
            continue

        event_date_iso = event_date.isoformat()
        if event_date_iso not in summarized_by_date:
            summarized_by_date[event_date_iso] = {
                'date': event_date_iso,
                'events': [],
                'earliest_start': None
            }

        start_time = normalize_time(event.get('time'))
        crowd_size = validate_crowd_size(event.get('crowd'))

        summarized_by_date[event_date_iso]['events'].append({
            'fixture': event['title'],
            'start_time': start_time,
            'crowd': crowd_size
        })

    # Determine the earliest start time for each day
    for date_summary in summarized_by_date.values():
        start_times = [
            t for e in date_summary['events']
            if (t := e.get('start_time'))
        ]
        if start_times:
            # Handle multiple times like "15:00 & 18:00"
            all_times = [t.strip()
                         for times in start_times for t in times.split('&')]
            date_summary['earliest_start'] = min(all_times)

    return sorted(summarized_by_date.values(), key=lambda x: x['date'])


def find_next_event_and_summary(summarized_events: list) -> Tuple[Optional[dict], Optional[dict]]:
    """
    Finds the very next event and a summary of all events on that same day.
    """
    today = datetime.now().date()

    future_events = [
        event for event in summarized_events
        if datetime.strptime(event['date'], '%Y-%m-%d').date() >= today
    ]

    if not future_events:
        return None, None

    # Sort by date, then by start time (handling None)
    future_events.sort(key=lambda x: (
        x['date'], x.get('earliest_start') or '23:59'))

    next_event_day = future_events[0]
    next_event_date = datetime.strptime(
        next_event_day['date'], '%Y-%m-%d').date()

    # Find the very next individual event item
    next_individual_event = None
    # Sort events within the day by start time
    sorted_events_today = sorted(
        next_event_day['events'], key=lambda x: x.get('start_time') or '23:59')

    for event_item in sorted_events_today:
        # If the event is today, check if the start time is in the future
        if next_event_date == today:
            start_time_str = event_item.get('start_time')
            if start_time_str:
                # Handle multiple times, e.g., "15:00 & 18:00"
                times = [t.strip() for t in start_time_str.split('&')]
                future_times = [
                    t for t in times if datetime.strptime(t, '%H:%M').time() >= datetime.now().time()]
                if future_times:
                    # We found an event today that hasn't started yet
                    next_individual_event = event_item
                    break
            else:
                if next_individual_event is None:
                    next_individual_event = event_item
        else:
            # If the event is on a future date, it's the next one
            next_individual_event = event_item
            break

    if not next_individual_event and sorted_events_today:
        next_individual_event = sorted_events_today[0]

    return next_individual_event, next_event_day


def process_and_publish_events(summarized_events: list, publisher: MQTTPublisher, config: Config):
    """
    Processes summarized event data and publishes it to relevant MQTT topics.
    Also publishes status information.
    """
    next_event, next_day_summary = find_next_event_and_summary(
        summarized_events)

    timestamp = {'iso': datetime.now().isoformat(
    ), 'human': datetime.now().strftime('%A, %d %B %Y at %H:%M')}

    # Publish to event topics
    publisher.publish(
        config.get('mqtt.topics.all_upcoming'),
        json.dumps({'last_updated': timestamp, 'events': summarized_events})
    )
    publisher.publish(
        config.get('mqtt.topics.next_day_summary'),
        json.dumps({'last_updated': timestamp, 'summary': next_day_summary})
    )
    publisher.publish(
        config.get('mqtt.topics.next'),
        json.dumps({'last_updated': timestamp, 'event': next_event})
    )

    # Publish to status topic
    errors = error_log
    status_payload = {
        'status': 'ok' if not errors else 'error',
        'last_updated': timestamp['iso'],
        'event_count': len(summarized_events),
        'error_count': len(errors),
        'errors': errors
    }

    status_topic = config.get('mqtt.topics.status')
    attributes_topic = f"{status_topic}/attributes"

    publisher.publish(status_topic, status_payload['status'])
    publisher.publish(attributes_topic, json.dumps(status_payload))


def main():
    """
    Main function to run the event scraper and publisher.
    """
    config = Config()
    # Load HA entities from a separate YAML file
    ha_entities_config_path = os.path.join(
        config.config_dir, 'ha_entities.yaml')
    # Publisher for Home Assistant discovery
    ha_discovery_publisher = MQTTPublisher(
        broker_url=config.get('mqtt.broker.url'),
        broker_port=config.get('mqtt.broker.port'),
        client_id=config.get('mqtt.client.id_discovery',
                             'twick_event_discovery'),
        security=config.get('mqtt.security.type'),
        auth=config.get('mqtt.security.auth'),
        tls=config.get('mqtt.security.tls')
    )
    publish_discovery_configs(config, ha_discovery_publisher)
    ha_discovery_publisher.disconnect()

    # Main publisher for event data
    publisher = MQTTPublisher(
        broker_url=config.get('mqtt.broker.url'),
        broker_port=config.get('mqtt.broker.port'),
        client_id=config.get('mqtt.client.id_main', 'twick_event_main'),
        security=config.get('mqtt.security.type'),
        auth=config.get('mqtt.security.auth'),
        tls=config.get('mqtt.security.tls')
    )
    raw_events = fetch_events(config.get('scraping.url'))

    if raw_events:
        summarized_events = summarise_events(raw_events)
        process_and_publish_events(summarized_events, publisher, config)

    publisher.disconnect()

    # Save errors to a file
    if error_log:
        error_file_path = os.path.join(
            config.get('logging.log_dir', 'output'), 'parsing_errors.json')
        os.makedirs(os.path.dirname(error_file_path), exist_ok=True)
        with open(error_file_path, 'w') as f:
            json.dump(error_log, f, indent=4)
        print(f"Completed with {len(error_log)} errors. See {error_file_path}")
    else:
        print("Completed successfully.")


if __name__ == "__main__":
    main()
