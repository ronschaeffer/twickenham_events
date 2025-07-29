#!/usr/bin/env python3

from core.mqtt_publisher import MQTTPublisher  # Add this import
from core.config import Config
from typing import Optional, Tuple
import json
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import requests
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Step 1: Fetch the webpage
url = 'https://www.richmond.gov.uk/services/parking/cpz/twickenham_events'
response = requests.get(url)

# Step 2: Parse the HTML content
soup = BeautifulSoup(response.text, 'html.parser')

# Step 3: Extract the table rows (excluding the header)
rows = soup.select("table.table tr")  # Select all table rows

# Step 4: Initialize a list to store all events
events = []

# Generate a timestamp for this run
update_timestamp = {
    'iso': datetime.now().isoformat(),
    'human': datetime.now().strftime('%A, %d %B %Y at %H:%M')
}

# Error log for debugging
error_log = []

# Update config loading with config directory path
config_path = os.path.join(os.path.dirname(
    os.path.dirname(__file__)), 'config', 'config.yaml')
config = Config(config_path)

# Function to normalize and extract the first date from a range


def extract_date_range(date_str: str) -> list[str]:
    """Extract multiple dates from a range string like '16/17 May 2025' or single date."""
    if not isinstance(date_str, str) or not date_str.strip():
        return []

    cleaned = date_str.strip()

    # Remove 'Weekend' or 'Wknd'
    cleaned = re.sub(r'\b(Weekend|Wknd)\b', '', cleaned,
                     flags=re.IGNORECASE).strip()

    # First try to parse as a range
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

    # If not a range, try to parse as single date
    result = normalize_date_range(date_str)
    return [result] if result else []


def normalize_date_range(date_str: str) -> Optional[str]:
    """Normalize date strings to YYYY-MM-DD."""
    if not isinstance(date_str, str) or not date_str.strip():
        return None

    cleaned = date_str.strip()

    # Remove 'Weekend' or 'Wknd'
    cleaned = re.sub(r'\b(Weekend|Wknd)\b', '', cleaned,
                     flags=re.IGNORECASE).strip()

    # Remove weekday names
    weekday_pattern = (r'^(Mon|Tue|Wed|Thu|Fri|Sat|Sun|'
                       r'Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+')
    cleaned = re.sub(weekday_pattern, '', cleaned, flags=re.IGNORECASE).strip()

    # Remove any ordinal suffixes (st, nd, rd, th)
    cleaned = re.sub(r'(\d+)(st|nd|rd|th)', r'\1',
                     cleaned, flags=re.IGNORECASE)

    # Try to match numeric date formats first
    numeric_patterns = [
        (r'(\d{1,2})\s*[-/]\s*(\d{1,2})\s*[-/]\s*(\d{4})',
         '%d/%m/%Y'),  # 15/08/2023
        (r'(\d{1,2})\s*[-/]\s*(\d{1,2})\s*[-/]\s*(\d{2})',
         '%d/%m/%y'),  # 15/08/23
    ]

    for pattern, fmt in numeric_patterns:
        match = re.match(pattern, cleaned)
        if match and fmt:
            try:
                groups = match.groups()
                date_str = f"{groups[0]}/{groups[1]}/{groups[2]}"
                date_obj = datetime.strptime(date_str, fmt)
                if '%y' in fmt and date_obj.year < 2000:
                    # Fixed missing parenthesis
                    date_obj = date_obj.replace(year=date_obj.year + 100)
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                continue

    # Try other date formats
    formats = [
        '%d %B %Y', '%d %b %Y', '%e %B %Y', '%e %b %Y',
        '%d-%b-%Y', '%d-%b-%y', '%d/%m/%Y', '%d/%m/%y',
        '%d-%m-%Y', '%d-%m-%y', '%d.%m.%Y', '%d.%m.%y',
        '%d %b %y', '%d %B %y',
    ]

    for fmt in formats:
        try:
            date_obj = datetime.strptime(cleaned, fmt)
            if '%y' in fmt and date_obj.year < 2000:
                date_obj = date_obj.replace(
                    year=(date_obj.year + 100))  # Fixed parentheses
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            continue

    error_log.append(f"Failed to parse date: '{date_str}'")
    return None

# Function to normalize time format with multiple times using '&'


# Function to normalize time format with multiple times using '&'
def normalize_time(time_str):
    if not time_str or time_str.lower() == 'tbc':
        return None

    # Handle 'noon' and remove (tbc) and other text noise
    time_str = time_str.lower().replace('noon', '12:00pm')
    time_str = re.sub(r'\s*\(tbc\)', '', time_str, flags=re.IGNORECASE)
    time_str = time_str.replace('.', ':')

    # Regex to find all time-like patterns (e.g., "3:15pm", "10am", "12:00pm")
    time_patterns = re.findall(
        r'\b\d{1,2}(?::\d{2})?\s*(?:am|pm)?\b', time_str, re.IGNORECASE)

    if not time_patterns:
        error_log.append(f"No valid time patterns found in: '{time_str}'")
        return None

    def is_valid_time(hour, minute):
        return 0 <= hour <= 23 and 0 <= minute <= 59

    def parse_single_time(time, shared_meridian=None):
        """Parse a single time component with optional shared AM/PM"""
        time = time.strip().lower()
        original_time = time

        meridian = shared_meridian
        if 'pm' in time:
            meridian = 'pm'
            time = time.replace('pm', '').strip()
        elif 'am' in time:
            meridian = 'am'
            time = time.replace('am', '').strip()

        try:
            if ':' in time:
                hour, minute = map(int, time.split(':'))
            else:
                hour = int(time)
                minute = 0

            if hour > 12 and (meridian or shared_meridian):
                return None, None
            if hour > 23:
                return None, None

            if meridian == 'pm' and hour < 12:
                hour += 12
            elif meridian == 'am' and hour == 12:
                hour = 0

            if not is_valid_time(hour, minute):
                return None, None

            return f"{hour:02d}:{minute:02d}", meridian
        except (ValueError, AttributeError):
            error_log.append(
                f"Failed to parse time component: '{original_time}'")
            return None, None

    # Find the last meridian to handle shared AM/PM cases like "10 & 11am"
    last_meridian = None
    if any('am' in t or 'pm' in t for t in time_patterns):
        for t in reversed(time_patterns):
            if 'am' in t.lower():
                last_meridian = 'am'
                break
            if 'pm' in t.lower():
                last_meridian = 'pm'
                break

    converted_times = []
    for time in time_patterns:
        parsed_time, _ = parse_single_time(time, last_meridian)
        if parsed_time:
            converted_times.append(parsed_time)

    return ' & '.join(sorted(converted_times)) if converted_times else None


def validate_crowd_size(crowd_str):
    if not crowd_str or not isinstance(crowd_str, str):
        return None

    # Remove text like "TBC", "Estimate", "Est", etc.
    cleaned_crowd = re.sub(r'(TBC|Estimate|Est|Approx|~)',
                           '', crowd_str, flags=re.IGNORECASE).strip()

    # Handle ranges like "50-60,000" by taking the upper value.
    range_match = re.search(r'(\d+)\s*-\s*(\d+,\d+)', cleaned_crowd)
    if range_match:
        # Take the second part of the range, e.g., '60,000'
        cleaned_crowd = range_match.group(2)

    # Remove commas before finding numbers
    crowd_no_commas = cleaned_crowd.replace(',', '')
    numbers = re.findall(r'\d+', crowd_no_commas)

    if not numbers:
        return None

    try:
        int_numbers = [int(n) for n in numbers]
        crowd = max(int_numbers)

        # Sanity check for capacity
        if crowd > 100000:
            potential_crowds = [n for n in int_numbers if n <= 100000]
            if potential_crowds:
                crowd = max(potential_crowds)
            else:
                error_log.append(
                    f"Implausible crowd size detected: '{crowd_str}'")
                return None

        return f"{crowd:,}"
    except (ValueError, IndexError):
        error_log.append(f"Invalid crowd size: '{crowd_str}'")
        return None


# Future-proofing: Match columns by header names
headers = [th.text.strip().lower() for th in rows[0].find_all('th')]
header_aliases = {
    'date': ['date'],
    'fixture': ['fixture'],
    'time': ['kick off', 'time'],
    'crowd': ['crowd', 'attendance']
}

header_map = {}
for key, aliases in header_aliases.items():
    for alias in aliases:
        if alias in headers:
            header_map[key] = headers.index(alias)
            break

missing_columns = [col for col in header_aliases if col not in header_map]
if missing_columns:
    raise ValueError(
        f"Missing required columns in table headers: {missing_columns}")

# Loop through rows and process data
for row in rows[1:]:  # Skip the header row
    cols = row.find_all('td')
    if len(cols) < len(headers):
        error_log.append(f"Skipping row due to insufficient columns: {row}")
        continue

    try:
        date_text = cols[header_map['date']].text
        fixture = cols[header_map['fixture']].text.strip()
        time_str = normalize_time(cols[header_map['time']].text.strip())
        crowd_str = validate_crowd_size(cols[header_map['crowd']].text.strip())

        # Check for date range first
        dates = extract_date_range(date_text)
        if not dates:
            # If not a range, use the normal date parser
            single_date = normalize_date_range(date_text)
            if single_date:
                dates = [single_date]
            else:
                continue

        # Create an event for each date found
        for date_str in dates:
            # Get all start times for the current row
            start_times_str = normalize_time(
                cols[header_map['time']].text.strip())

            if start_times_str:
                # If there are multiple times, create a separate event for each
                times = start_times_str.split(' & ')
                for time in times:
                    start = datetime.strptime(time, '%H:%M')
                    end = start + timedelta(hours=config.default_duration)
                    end_time_str = end.strftime('%H:%M')

                    events.append({
                        'date': date_str,
                        'fixture': fixture,
                        'start_time': time,
                        'end_time': end_time_str,
                        'crowd': crowd_str,
                    })
            else:
                # If no time is specified (TBC), create a single event
                events.append({
                    'date': date_str,
                    'fixture': fixture,
                    'start_time': None,
                    'end_time': None,
                    'crowd': crowd_str,
                })
    except Exception as e:
        error_log.append(f"Error processing row: {row} - {str(e)}")


def adjust_end_times(events: list) -> list:
    """Adjust end times to prevent overlaps between different events on the same day."""
    if not events:
        return []

    # Sort events by date and start time to process them chronologically
    sorted_events = sorted(events, key=lambda x: (
        x['date'],
        x.get('start_time') or "23:59"  # Handle events with no start time
    ))

    # Create a new list to store the adjusted events
    adjusted_events = [event.copy() for event in sorted_events]

    for i in range(len(adjusted_events) - 1):
        current_event = adjusted_events[i]
        next_event = adjusted_events[i + 1]

        # Conditions for skipping adjustment:
        # 1. Events are not on the same day.
        # 2. Either event is missing time information.
        # 3. Both events are for the same fixture (e.g., multiple kick-offs for one match).
        if (current_event['date'] != next_event['date'] or
            not current_event.get('start_time') or not current_event.get('end_time') or
            not next_event.get('start_time') or
                current_event['fixture'] == next_event['fixture']):
            continue

        # If the current event's end time overlaps with the next event's start time
        if current_event['end_time'] > next_event['start_time']:
            # Adjust the end time of the current event to the start of the next
            current_event['end_time'] = next_event['start_time']

    return adjusted_events


def group_events_by_date(events: list) -> list:
    """Group events by date and create a daily summary."""
    grouped = {}
    for event in events:
        date = event['date']
        if date not in grouped:
            grouped[date] = []
        # Remove redundant date from individual event object
        del event['date']
        grouped[date].append(event)

    daily_summaries = []
    for date, daily_events in grouped.items():
        # Sort events by start time for the day
        sorted_daily_events = sorted(
            daily_events,
            key=lambda x: x['start_time'] or "23:59"
        )

        start_times = [e['start_time']
                       for e in sorted_daily_events if e['start_time']]
        end_times = [e['end_time']
                     for e in sorted_daily_events if e['end_time']]

        daily_summaries.append({
            'date': date,
            'event_count': len(sorted_daily_events),
            'earliest_start': min(start_times) if start_times else None,
            'latest_end': max(end_times) if end_times else None,
            'events': sorted_daily_events
        })

    # Sort the final list of summaries by date
    return sorted(daily_summaries, key=lambda x: x['date'])


def save_events_to_json(events_data: list, timestamp: dict, directory: str) -> None:
    """Saves the processed events to a JSON file with a timestamp."""
    os.makedirs(directory, exist_ok=True)
    output_path = os.path.join(directory, 'upcoming_events.json')
    output_data = {
        'last_updated': timestamp,
        'events': events_data
    }
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=4)


# Filter upcoming events (future events only)
upcoming_events = [event for event in events if datetime.strptime(
    event['date'], '%Y-%m-%d') >= datetime.now()]

# Adjust end times to prevent overlaps
upcoming_events = adjust_end_times(upcoming_events)

# Group events by date for the final output
summarized_events = group_events_by_date(upcoming_events)

# Write the JSON file to the output directory in project root
output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output')
save_events_to_json(summarized_events, update_timestamp, output_dir)


def find_next_event_and_summary(summarized_events: list) -> Tuple[Optional[dict], Optional[dict]]:
    """
    Finds the very next individual event and its corresponding day summary.
    Compares event times against the current time to find the first future event.
    """
    now = datetime.now()
    for day_summary in summarized_events:
        # Create a copy of the events list to avoid modifying it while iterating
        for event in list(day_summary['events']):
            if event.get('start_time'):
                # Combine date and time to create a full datetime object for comparison
                event_datetime_str = f"{day_summary['date']} {event['start_time']}"
                event_datetime = datetime.strptime(
                    event_datetime_str, '%Y-%m-%d %H:%M')

                if event_datetime > now:
                    # This is the first event in the future.
                    # Create a copy and add the date for the 'next' payload.
                    next_event_payload = event.copy()
                    next_event_payload['date'] = day_summary['date']
                    return next_event_payload, day_summary

    # If no future events are found
    return None, None


def process_and_publish_events(events: list, config: Config, timestamp: dict) -> None:
    """Process events and publish them via MQTT."""
    mqtt_settings = {
        'broker_url': config.config['mqtt']['broker_url'],
        'broker_port': config.config['mqtt']['broker_port'],
        'client_id': config.config['mqtt']['client_id'],
        'security': config.config['mqtt']['security'],
        'auth': config.config['mqtt'].get('auth'),
        'tls': config.config['mqtt'].get('tls')
    }

    # Find the true next event and its corresponding day summary
    next_individual_event, next_day_summary = find_next_event_and_summary(
        events)

    # Prepare payloads with timestamp
    all_upcoming_payload = {'last_updated': timestamp, 'events': events}
    next_day_summary_payload = {'last_updated': timestamp,
                                'summary': next_day_summary} if next_day_summary else {'last_updated': timestamp, 'summary': {}}
    next_individual_event_payload = {
        'last_updated': timestamp, 'event': next_individual_event} if next_individual_event else {'last_updated': timestamp, 'event': {}}

    with MQTTPublisher(**mqtt_settings) as publisher:
        # Always publish the full list of all upcoming days
        publisher.publish(
            config.config['mqtt']['topics']['all_upcoming'], all_upcoming_payload, retain=True)

        if next_day_summary:
            # Publish the summary for the day of the next event
            publisher.publish(
                config.config['mqtt']['topics']['next_day_summary'], next_day_summary_payload, retain=True)
        else:
            # If no upcoming events, clear the summary topic
            publisher.publish(
                config.config['mqtt']['topics']['next_day_summary'], next_day_summary_payload, retain=True)

        if next_individual_event:
            # Publish the very next individual event
            publisher.publish(
                config.config['mqtt']['topics']['next'], next_individual_event_payload, retain=True)
        else:
            # If no specific next event, clear the topic
            publisher.publish(
                config.config['mqtt']['topics']['next'], next_individual_event_payload, retain=True)


# Publish events via MQTT using the new function
process_and_publish_events(summarized_events, config, update_timestamp)

# Display output
print("\n=== Twickenham Stadium Events ===")
print(f"Last updated: {update_timestamp['human']}")

# Show MQTT connection info
print("\nMQTT Configuration:")
print(
    f"Broker: {config.config['mqtt']['broker_url']}:{config.config['mqtt']['broker_port']}")
print(f"Security: {config.config['mqtt']['security']}")

# Find the true next event again for display purposes
next_event, _ = find_next_event_and_summary(
    summarized_events)

# Display next event with better formatting
if next_event:
    print("\n=== Next Event ===")
    print(f"{'Date:':<12} {next_event['date']}")
    print(f"{'Fixture:':<12} {next_event['fixture']}")
    print(f"{'Start Time:':<12} {next_event['start_time'] or 'TBC'}")
    print(f"{'End Time:':<12} {next_event['end_time'] or 'TBC'}")
    print(f"{'Crowd:':<12} {next_event['crowd'] or 'TBC'}")
else:
    # This branch will be taken if all events are in the past
    if summarized_events:
        print("\nAll scheduled events for the upcoming days have passed.")
    else:
        print("\nNo upcoming events found.")

# Display summary of all events
if summarized_events:
    total_events = sum(day['event_count'] for day in summarized_events)
    print(f"\n=== All Upcoming Events ({total_events} total) ===")
    for day_summary in summarized_events:
        day_info = f"Date: {day_summary['date']} ({day_summary['event_count']} event(s))"

        if day_summary['event_count'] > 1:
            time_window = f"{day_summary['earliest_start'] or 'TBC'} - {day_summary['latest_end'] or 'TBC'}"
            print(f"\n{day_info} | {time_window}")
            for event in day_summary['events']:
                time_info = f"{event['start_time'] or 'TBC'} - {event['end_time'] or 'TBC'}"
                print(
                    f"  - {time_info:<15} | {event['fixture']:<40} | {event['crowd'] or 'TBC'}")
        else:
            event = day_summary['events'][0]
            time_info = f"{event['start_time'] or 'TBC'} - {event['end_time'] or 'TBC'}"
            print(
                f"{day_info} | {time_info:<15} | {event['fixture']:<40} | {event['crowd'] or 'TBC'}")

if not summarized_events:
    print("\nNo upcoming events found.")

# Log errors if any
error_file_path = os.path.join(output_dir, 'parsing_errors.txt')
with open(error_file_path, 'w') as f:
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    f.write(f"Run at: {timestamp}\n\n")
    if error_log:
        print(f"\n=== Errors ({len(error_log)}) ===")
        f.write(f"Found {len(error_log)} parsing errors:\n")
        for error in error_log:
            f.write(f"- {error}\n")
        print(f"Details written to: {error_file_path}")
    else:
        print("\nNo parsing errors found.")
        f.write("No parsing errors found during this run.\n")

print("\n=== Processing Complete ===")
