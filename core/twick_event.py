#!/usr/bin/env python3

from core.mqtt_publisher import MQTTPublisher
from core.ha_discovery.publisher import HADiscoveryPublisher
from core.config import Config
import json
import os
import re
import sys
from datetime import datetime, timedelta
from typing import Optional, Tuple, Any

import requests
from bs4 import BeautifulSoup

# Add project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# --- Global Variables ---
error_log = []


# --- Data Parsing and Normalization Functions ---

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
    weekday_pattern = r'^(Mon|Tue|Wed|Thu|Fri|Sat|Sun|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+'
    cleaned = re.sub(weekday_pattern, '', cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r'(\d+)(st|nd|rd|th)', r'\1',
                     cleaned, flags=re.IGNORECASE)

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
        '%d/%m/%Y', '%d/%m/%y', '%d-%m-%Y', '%d-%m-%y', '%d.%m.%Y', '%d.%m.%y',
        '%d %b %y', '%d %B %y',
    ]
    for fmt in formats:
        try:
            date_obj = datetime.strptime(cleaned, fmt)
            if '%y' in fmt and date_obj.year < 2000:
                date_obj = date_obj.replace(year=date_obj.year + 100)
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            continue

    error_log.append(f"Failed to parse date: '{date_str}'")
    return None


def normalize_time(time_str: str) -> Optional[str]:
    """Normalize time format, handling multiple times separated by '&'."""
    if not time_str or time_str.lower() == 'tbc':
        return None

    time_str = time_str.lower().replace('noon', '12:00pm')
    time_str = re.sub(r'\s*\(tbc\)', '', time_str, flags=re.IGNORECASE)
    time_str = time_str.replace('.', ':')

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


def validate_crowd_size(crowd_str: str) -> Optional[str]:
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


# --- Event Processing Functions ---

def adjust_end_times(events: list) -> list:
    """Adjust end times to prevent overlaps between different events on the same day."""
    if not events:
        return []

    sorted_events = sorted(events, key=lambda x: (
        x['date'], x.get('start_time') or "23:59"))
    adjusted_events = [event.copy() for event in sorted_events]

    for i in range(len(adjusted_events) - 1):
        current_event = adjusted_events[i]
        next_event = adjusted_events[i + 1]

        if (current_event['date'] != next_event['date'] or
            not all(k in current_event and current_event[k] for k in ['start_time', 'end_time']) or
            not next_event.get('start_time') or
                current_event['fixture'] == next_event['fixture']):
            continue

        if current_event['end_time'] > next_event['start_time']:
            current_event['end_time'] = next_event['start_time']

    return adjusted_events


def group_events_by_date(events: list) -> list:
    """Group events by date and create a daily summary."""
    grouped = {}
    for event in events:
        date = event.pop('date')
        if date not in grouped:
            grouped[date] = []
        grouped[date].append(event)

    daily_summaries = []
    for date, daily_events in grouped.items():
        sorted_daily_events = sorted(
            daily_events, key=lambda x: x.get('start_time') or "23:59")
        start_times = [e['start_time']
                       for e in sorted_daily_events if e.get('start_time')]
        end_times = [e['end_time']
                     for e in sorted_daily_events if e.get('end_time')]
        daily_summaries.append({
            'date': date,
            'event_count': len(sorted_daily_events),
            'earliest_start': min(start_times) if start_times else None,
            'latest_end': max(end_times) if end_times else None,
            'events': sorted_daily_events
        })
    return sorted(daily_summaries, key=lambda x: x['date'])


def find_next_event_and_summary(summarized_events: list) -> Tuple[Optional[dict], Optional[dict]]:
    """Finds the very next individual event and its corresponding day summary."""
    now = datetime.now()
    for day_summary in summarized_events:
        for event in day_summary['events']:
            if event.get('start_time'):
                event_datetime = datetime.strptime(
                    f"{day_summary['date']} {event['start_time']}", '%Y-%m-%d %H:%M')
                if event_datetime > now:
                    next_event_payload = event.copy()
                    next_event_payload['date'] = day_summary['date']
                    return next_event_payload, day_summary
    return None, None


# --- I/O and Publishing Functions ---

def save_events_to_json(events_data: list, timestamp: dict, directory: str) -> None:
    """Saves the processed events to a JSON file with a timestamp."""
    os.makedirs(directory, exist_ok=True)
    output_path = os.path.join(directory, 'upcoming_events.json')
    with open(output_path, 'w') as f:
        json.dump({'last_updated': timestamp,
                  'events': events_data}, f, indent=4)


def process_and_publish_events(summarized_events: list, config: Config, timestamp: dict, errors: list) -> None:
    """Process events and publish them via MQTT."""
    mqtt_settings = {
        'broker_url': str(config.get('mqtt.broker_url')),
        'broker_port': int(config.get('mqtt.broker_port')),
        'client_id': str(config.get('mqtt.client_id', 'twickenham_events_publisher')),
        'security': str(config.get('mqtt.security', 'none')),
        'auth': config.get('mqtt.auth'),
        'tls': config.get('mqtt.tls')
    }

    next_individual_event, next_day_summary = find_next_event_and_summary(
        summarized_events)
    all_upcoming_payload = {
        'last_updated': timestamp, 'events': summarized_events}
    next_day_summary_payload = {
        'last_updated': timestamp, 'summary': next_day_summary or {}}
    next_individual_event_payload = {
        'last_updated': timestamp, 'event': next_individual_event or {}}
    error_payload = {'last_updated': timestamp,
                     'error_count': len(errors), 'errors': errors}

    print("\nPublishing event topics to MQTT...")
    with MQTTPublisher(**mqtt_settings) as publisher:
        publisher.publish(
            str(config.get('mqtt.topics.all_upcoming')), all_upcoming_payload, retain=True)
        publisher.publish(str(config.get('mqtt.topics.next_day_summary')),
                          next_day_summary_payload, retain=True)
        publisher.publish(str(config.get('mqtt.topics.next')),
                          next_individual_event_payload, retain=True)
        publisher.publish(str(config.get('mqtt.topics.errors')),
                          error_payload, retain=True)


def display_summary(summarized_events: list, timestamp: dict, config: Config, errors: list) -> None:
    """Displays the final summary to the console."""
    print("\n=== Event Summary ===")
    print(f"Last updated: {timestamp['human']}")

    next_event, _ = find_next_event_and_summary(summarized_events)
    if next_event:
        print("\n=== Next Event ===")
        print(f"{'Date:':<12} {next_event['date']}")
        print(f"{'Fixture:':<12} {next_event['fixture']}")
        print(f"{'Start Time:':<12} {next_event.get('start_time', 'TBC')}")
        print(f"{'End Time:':<12} {next_event.get('end_time', 'TBC')}")
        print(f"{'Crowd:':<12} {next_event.get('crowd', 'TBC')}")
    else:
        print("\nNo upcoming events found or all have passed.")

    if summarized_events:
        total_events = sum(day['event_count'] for day in summarized_events)
        print(f"\n=== All Upcoming Events ({total_events} total) ===")
        for day in summarized_events:
            day_info = f"Date: {day['date']} ({day['event_count']} event(s))"
            if day['event_count'] > 1:
                time_window = f"{day.get('earliest_start', 'TBC')} - {day.get('latest_end', 'TBC')}"
                print(f"\n{day_info} | {time_window}")
                for event in day['events']:
                    time_info = f"{event.get('start_time', 'TBC')} - {event.get('end_time', 'TBC')}"
                    print(
                        f"  - {time_info:<15} | {event['fixture']:<40} | {event.get('crowd', 'TBC')}")
            else:
                event = day['events'][0]
                time_info = f"{event.get('start_time', 'TBC')} - {event.get('end_time', 'TBC')}"
                print(
                    f"{day_info} | {time_info:<15} | {event['fixture']:<40} | {event.get('crowd', 'TBC')}")

    if errors:
        print(f"\n=== Errors ({len(errors)}) ===")
        for error in errors:
            print(f"- {error}")
    else:
        print("\nNo parsing errors found.")

    print("\n=== Processing Complete ===")


# --- Main Execution ---

def main():
    """Main function to fetch, process, and publish Twickenham event data."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, 'config', 'config.yaml')
    config = Config(config_path)
    http_error = None
    events = []
    summarized_events = []

    # --- Home Assistant Discovery ---
    if config.get('home_assistant.enabled', False):
        print("Home Assistant integration enabled. Publishing discovery topics...")
        entities_config_path = os.path.join(
            base_dir, 'config', 'ha_entities.yaml')
        ha_publisher = HADiscoveryPublisher(config, entities_config_path)
        ha_publisher.publish_discovery_topics()
        print("Discovery topics published.")

    # --- Web Scraping ---
    url = 'https://www.richmond.gov.uk/services/parking/cpz/twickenham_events'
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        table_rows = soup.select("table.table tr")
        if not table_rows:
            error_log.append("No event table found on the webpage.")
        else:
            # --- Data Processing ---
            headers = [th.text.strip().lower()
                       for th in table_rows[0].find_all('th')]
            header_aliases = {'date': ['date'], 'fixture': ['fixture'], 'time': [
                'kick off', 'time'], 'crowd': ['crowd', 'attendance']}
            header_map = {key: next((headers.index(alias) for alias in aliases if alias in headers), -1)
                          for key, aliases in header_aliases.items()}

            if any(idx == -1 for idx in header_map.values()):
                missing = [key for key, idx in header_map.items() if idx == -1]
                error_log.append(
                    f"Missing required columns in table headers: {missing}")
            else:
                for row in table_rows[1:]:
                    cols = row.find_all('td')
                    if len(cols) < len(headers):
                        error_log.append(
                            f"Skipping row due to insufficient columns: {row}")
                        continue

                    try:
                        date_text = cols[header_map['date']].text
                        fixture = cols[header_map['fixture']].text.strip()
                        time_str = cols[header_map['time']].text.strip()
                        crowd_str = cols[header_map['crowd']].text.strip()

                        dates = extract_date_range(date_text)
                        if not dates:
                            dates = [d for d in [
                                normalize_date_range(date_text)] if d]

                        for date in dates:
                            start_times = normalize_time(time_str)
                            if start_times:
                                for time in start_times.split(' & '):
                                    start = datetime.strptime(time, '%H:%M')
                                    duration = int(str(config.get(
                                        'default_duration', 2)))
                                    end = start + timedelta(hours=duration)
                                    events.append({
                                        'date': date, 'fixture': fixture, 'start_time': time,
                                        'end_time': end.strftime('%H:%M'), 'crowd': validate_crowd_size(crowd_str)
                                    })
                            else:
                                events.append({
                                    'date': date, 'fixture': fixture, 'start_time': None,
                                    'end_time': None, 'crowd': validate_crowd_size(crowd_str)
                                })
                    except Exception as e:
                        error_log.append(
                            f"Error processing row: {row} - {str(e)}")
    except requests.RequestException as e:
        http_error = f"Error fetching webpage: {e}"
        error_log.append(http_error)

    update_timestamp = {
        'iso': datetime.now().isoformat(),
        'human': datetime.now().strftime('%A, %d %B %Y at %H:%M')
    }

    # --- Final Processing and Publishing ---
    if events:
        upcoming_events = [e for e in events if datetime.strptime(
            e['date'], '%Y-%m-%d') >= datetime.now()]
        adjusted_events = adjust_end_times(upcoming_events)
        summarized_events = group_events_by_date(adjusted_events)

    output_dir = os.path.join(base_dir, 'output')
    save_events_to_json(summarized_events, update_timestamp, output_dir)

    if config.get('mqtt.enabled', False):
        process_and_publish_events(
            summarized_events, config, update_timestamp, error_log)

    display_summary(summarized_events, update_timestamp, config, error_log)

    error_file_path = os.path.join(output_dir, 'parsing_errors.txt')
    with open(error_file_path, 'w') as f:
        f.write(f"Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        if error_log:
            f.write(f"Found {len(error_log)} parsing errors:\n")
            for error in error_log:
                f.write(f"- {error}\n")
        else:
            f.write("No parsing errors found during this run.\n")


if __name__ == "__main__":
    main()
