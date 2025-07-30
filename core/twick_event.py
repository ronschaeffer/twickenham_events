#!/usr/bin/env python3

from core.mqtt_publisher import MQTTPublisher
from core.ha_mqtt_discovery import publish_discovery_configs
from core.config import Config
import json
import os
import re
import sys
from datetime import datetime, timedelta, date
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


def find_next_event_and_summary(summarized_events: list, today: Optional[date] = None) -> Tuple[Optional[dict], Optional[dict]]:
    """
    Finds the very next event and a summary of all events on that same day.
    """
    if today is None:
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
    next_event_date = next_event_day['date']

    # Find the very next individual event item
    next_individual_event = None
    for event_item in sorted(next_event_day['events'], key=lambda x: x.get('start_time') or '23:59'):
        # Check if the event's start time is in the future if it's today
        if next_event_date == today.strftime('%Y-%m-%d'):
            if event_item.get('start_time') and datetime.strptime(event_item['start_time'], '%H:%M').time() >= datetime.now().time():
                next_individual_event = event_item
                break
        else:
            next_individual_event = event_item
            break

    # If no specific event is found for today (e.g., all have passed), default to the first one
    if not next_individual_event and next_event_day['events']:
        next_individual_event = next_event_day['events'][0]

    return next_individual_event, next_event_day


def extract_date_range(date_str: str) -> list[str]:
    """Extract multiple dates from a range string like '16/17 May 2025' or single date."""
    if not isinstance(date_str, str) or not date_str.strip():
        return []

    cleaned = date_str.strip()
    cleaned = re.sub(r'\b(Weekend|Wknd)\b', '', cleaned,
                     flags=re.IGNORECASE).strip()

    range_match = re.match(r'(\d{1,2})/(\d{1,2})\s+(\w+)\s+(\d{4})', cleaned)
    if range_match:
        day1, day2, month, year = range_match.groups()
        try:
            date1 = datetime.strptime(f"{day1} {month} {year}", '%d %B %Y')
            date2 = datetime.strptime(f"{day2} {month} {year}", '%d %B %Y')
            return [date1.strftime('%Y-%m-%d'), date2.strftime('%Y-%m-%d')]
        except ValueError:
            try:
                date1 = datetime.strptime(f"{day1} {month} {year}", '%d %b %Y')
                date2 = datetime.strptime(f"{day2} {month} {year}", '%d %b %Y')
                return [date1.strftime('%Y-%m-%d'), date2.strftime('%Y-%m-%d')]
            except ValueError:
                return []

    result = normalize_date_range(date_str)
    return [result] if result else []


def normalize_date_range(date_str: str) -> Optional[str]:
    """Normalize date strings to YYYY-MM-DD."""
    if not isinstance(date_str, str) or not date_str.strip():
        return None

    cleaned = date_str.strip()
    cleaned = re.sub(r'\b(Weekend|Wknd)\b', '', cleaned,
                     flags=re.IGNORECASE).strip()

    # Handle date ranges like '16/17 May 2025' by taking the first day.
    range_match = re.match(r'(\d{1,2})/\d{1,2}\s+(.*)', cleaned)
    if range_match:
        cleaned = f"{range_match.group(1)} {range_match.group(2)}"

    weekday_pattern = r'^(Mon|Tue|Wed|Thu|Fri|Sat|Sun|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+'
    cleaned = re.sub(weekday_pattern, '', cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r'(\d+)(st|nd|rd|th)', r'\1',
                     cleaned, flags=re.IGNORECASE)

    # Replace dots with slashes for numeric patterns
    cleaned = cleaned.replace('.', '/')

    numeric_patterns = [
        (r'(\d{1,2})\s*[-/]\s*(\d{1,2})\s*[-/]\s*(\d{4})', '%d/%m/%Y'),
        (r'(\d{1,2})\s*[-/]\s*(\d{1,2})\s*[-/]\s*(\d{2})', '%d/%m/%y'),
    ]
    for pattern, fmt in numeric_patterns:
        match = re.match(pattern, cleaned)
        if match:
            try:
                groups = match.groups()
                date_obj = datetime.strptime(
                    f"{groups[0]}/{groups[1]}/{groups[2]}", fmt)
                if '%y' in fmt and date_obj.year < 2000:
                    date_obj = date_obj.replace(year=date_obj.year + 100)
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                continue

    formats = [
        '%d %B %Y', '%d %b %Y', '%e %B %Y', '%e %b %Y', '%d-%b-%Y', '%d-%b-%y',
        '%d/%m/%Y', '%d/%m/%y', '%d-%m-%Y', '%d-%m-%y',
        '%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d', '%Y/%m/%d %H:%M:%S',
        '%d %B, %Y', '%d %b, %Y', '%B %d, %Y', '%b %d, %Y',
        '%d %B %Y %H:%M', '%d %b %Y %H:%M', '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M',
        '%d %b %y', '%d %B %y'
    ]
    for fmt in formats:
        try:
            date_obj = datetime.strptime(cleaned, fmt)
            if '%y' in fmt and date_obj.year < 1900:  # Handle 2-digit years
                date_obj = date_obj.replace(year=date_obj.year + 2000)
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            continue

    return None


# --- Event Processing and Publishing Functions ---

def process_and_publish_events(summarized_events: list, publisher: MQTTPublisher, config: Config):
    """
    Processes summarized event data and publishes it to relevant MQTT topics.
    Also publishes status information.
    """
    today = datetime.now().date()
    next_event, next_day_summary = find_next_event_and_summary(
        summarized_events, today)

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


def summarise_events(raw_events: list[dict]) -> list[dict]:
    """Summarises and groups raw event data by date, including only upcoming events."""
    events_by_date = {}
    today = datetime.now().date()

    for event_data in raw_events:
        # Using extract_date_range to handle single and multi-day events
        dates = extract_date_range(event_data.get('date', ''))

        for date_str in dates:
            event_date_str = normalize_date_range(date_str)
            if not event_date_str:
                continue

            try:
                event_date = datetime.strptime(
                    event_date_str, '%Y-%m-%d').date()
                if event_date < today:
                    continue  # Skip past events
            except ValueError:
                error_log.append(f"Could not parse date: {event_date_str}")
                continue

            event_details = {
                'fixture': event_data.get('title', 'N/A'),
                'start_time': normalize_time(event_data.get('time')),
                'crowd': validate_crowd_size(event_data.get('crowd'))
            }

            if event_date_str not in events_by_date:
                events_by_date[event_date_str] = {
                    'date': event_date_str,
                    'events': [],
                    'total_crowd': 0,
                    'earliest_start': None,
                    'latest_end': None
                }

            events_by_date[event_date_str]['events'].append(event_details)

    # Post-process to calculate summaries
    for date, day_summary in events_by_date.items():
        # Calculate total crowd
        total_crowd = 0
        for event in day_summary['events']:
            if event['crowd']:
                total_crowd += int(event['crowd'].replace(',', ''))
        day_summary['total_crowd'] = f"{total_crowd:,}" if total_crowd > 0 else None

        # Find earliest start and latest end times
        start_times = [e['start_time']
                       for e in day_summary['events'] if e.get('start_time')]
        if start_times:
            all_times = []
            for st in start_times:
                all_times.extend(st.split(' & '))

            day_summary['earliest_start'] = min(all_times)
            # Simple assumption for now: duration is 2 hours. This can be refined.
            latest_time = max(all_times)
            latest_dt = datetime.strptime(
                latest_time, '%H:%M') + timedelta(hours=2)
            day_summary['latest_end'] = latest_dt.strftime('%H:%M')

    return sorted(events_by_date.values(), key=lambda x: x['date'])
