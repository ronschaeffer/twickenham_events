#!/usr/bin/env python3

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import json
from typing import Optional
from core.config import Config  # Changed from 'config' to 'core.config'

# Step 1: Fetch the webpage
url = 'https://www.richmond.gov.uk/services/parking/cpz/twickenham_events'
response = requests.get(url)

# Step 2: Parse the HTML content
soup = BeautifulSoup(response.text, 'html.parser')

# Step 3: Extract the table rows (excluding the header)
rows = soup.select("table.table tr")  # Select all table rows

# Step 4: Initialize a list to store all events
events = []

# Error log for debugging
error_log = []

# Update config loading with config directory path
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'config.yaml')
config = Config(config_path)

# Function to normalize and extract the first date from a range
def extract_date_range(date_str: str) -> list[str]:
    """Extract multiple dates from a range string like '16/17 May 2025' or single date."""
    if not isinstance(date_str, str) or not date_str.strip():
        return []

    cleaned = date_str.strip()
    
    # Remove 'Weekend' or 'Wknd'
    cleaned = re.sub(r'\b(Weekend|Wknd)\b', '', cleaned, flags=re.IGNORECASE).strip()

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
    cleaned = re.sub(r'\b(Weekend|Wknd)\b', '', cleaned, flags=re.IGNORECASE).strip()
    
    # Remove weekday names
    weekday_pattern = (r'^(Mon|Tue|Wed|Thu|Fri|Sat|Sun|'
                       r'Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+')
    cleaned = re.sub(weekday_pattern, '', cleaned, flags=re.IGNORECASE).strip()
    
    # Remove any ordinal suffixes (st, nd, rd, th)
    cleaned = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', cleaned, flags=re.IGNORECASE)

    # Try to match numeric date formats first
    numeric_patterns = [
        (r'(\d{1,2})\s*[-/]\s*(\d{1,2})\s*[-/]\s*(\d{4})', '%d/%m/%Y'),  # 15/08/2023
        (r'(\d{1,2})\s*[-/]\s*(\d{1,2})\s*[-/]\s*(\d{2})', '%d/%m/%y'),  # 15/08/23
    ]

    for pattern, fmt in numeric_patterns:
        match = re.match(pattern, cleaned)
        if match and fmt:
            try:
                groups = match.groups()
                date_str = f"{groups[0]}/{groups[1]}/{groups[2]}"
                date_obj = datetime.strptime(date_str, fmt)
                if '%y' in fmt and date_obj.year < 2000:
                    date_obj = date_obj.replace(year=date_obj.year + 100)  # Fixed missing parenthesis
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
                date_obj = date_obj.replace(year=date_obj.year + 100)  # Fixed missing parenthesis
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            continue

    error_log.append(f"Failed to parse date: '{date_str}'")
    return None

# Function to normalize time format with multiple times using '&'
def normalize_time(time_str):
    if not time_str or time_str.lower() == 'tbc':
        return None

    # Replace all variants of "and" with "&" for consistent processing
    time_str = re.sub(r'\s+(and|&)\s+', ' & ', time_str)

    def is_valid_time(hour, minute):
        return 0 <= hour <= 23 and 0 <= minute <= 59

    def parse_single_time(time, shared_meridian=None):
        """Parse a single time component with optional shared AM/PM"""
        time = time.strip().lower()
        original_time = time
        
        # Handle explicit AM/PM
        meridian = shared_meridian
        if time.endswith('pm'):
            meridian = 'pm'
            time = time[:-2]
        elif time.endswith('am'):
            meridian = 'am'
            time = time[:-2]

        try:
            if ':' in time:
                hour, minute = map(int, time.split(':'))
            else:
                hour = int(time)
                minute = 0

            # Early validation
            if hour > 12 and (meridian or shared_meridian):
                return None
            if hour > 23:
                return None
            
            # Apply meridian adjustments
            if meridian == 'pm' and hour < 12:
                hour += 12
            elif meridian == 'am' and hour == 12:
                hour = 0

            if not is_valid_time(hour, minute):
                return None

            return f"{hour:02d}:{minute:02d}", meridian
        except (ValueError, AttributeError):
            error_log.append(f"Failed to parse time: '{original_time}'")
            return None

    time_str = time_str.replace('.', ':').lower()
    parts = re.split(r'\s*&\s*', time_str)
    
    # Find the last meridian in the string to handle shared AM/PM
    last_meridian = None
    for part in reversed(parts):
        if part.endswith('am') or part.endswith('pm'):
            last_meridian = part[-2:]
            break

    converted_times = []
    for time in parts:
        result = parse_single_time(time, last_meridian)
        if result:
            time_str, _ = result
            converted_times.append(time_str)

    return ' & '.join(converted_times) if converted_times else None

# Function to validate and format crowd size
def validate_crowd_size(crowd_str):
    if not crowd_str or not isinstance(crowd_str, str):
        return None

    # Remove text like "TBC", "Estimate", "Est", etc.
    cleaned_crowd = re.sub(r'(TBC|Estimate|Est|Approx|~)', '', crowd_str, flags=re.IGNORECASE).strip()

    try:
        crowd = int(re.sub(r'[^\d]', '', cleaned_crowd))
        return f"{crowd:,}"  # Format with commas
    except ValueError:
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
    raise ValueError(f"Missing required columns in table headers: {missing_columns}")

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

        # Create an event for each date
        for date_str in dates:
            start_time_str = normalize_time(cols[header_map['time']].text.strip())
            
            # Calculate end time if start time exists
            end_time_str = None
            if start_time_str:
                # Handle multiple start times (e.g., "14:00 & 16:00")
                times = start_time_str.split(' & ')
                end_times = []
                for time in times:
                    start = datetime.strptime(time, '%H:%M')
                    end = start + timedelta(hours=config.default_duration)  # Changed from event_duration to default_duration
                    end_times.append(end.strftime('%H:%M'))
                end_time_str = ' & '.join(end_times)

            events.append({
                'date': date_str,
                'fixture': fixture,
                'start_time': start_time_str,
                'end_time': end_time_str,
                'crowd': crowd_str,
            })
    except Exception as e:
        error_log.append(f"Error processing row: {row} - {str(e)}")

def adjust_end_times(events):
    """Adjust end times to prevent overlaps between events."""
    # Sort events by date and start time
    sorted_events = sorted(events, key=lambda x: (
        x['date'],
        x['start_time'] if x['start_time'] else "23:59"  # Put events with no start time at end of day
    ))
    
    for i in range(len(sorted_events) - 1):
        current = sorted_events[i]
        next_event = sorted_events[i + 1]
        
        # Skip if either event has no times
        if not current['start_time'] or not current['end_time'] or not next_event['start_time']:
            continue
            
        # If events are on different dates, no need to adjust
        if current['date'] != next_event['date']:
            continue
            
        # For events with multiple times, use the last end time and first start time
        current_end_times = current['end_time'].split(' & ')
        next_start_times = next_event['start_time'].split(' & ')
        
        current_last_end = current_end_times[-1]
        next_first_start = next_start_times[0]
        
        # If current event would overlap with next event
        if current_last_end > next_first_start:
            # Adjust all end times of current event if needed
            adjusted_end_times = []
            for idx, end_time in enumerate(current_end_times):
                if end_time > next_first_start:
                    adjusted_end_times.append(next_first_start)
                else:
                    adjusted_end_times.append(end_time)
            current['end_time'] = ' & '.join(adjusted_end_times)
    
    return sorted_events

# Filter upcoming events (future events only)
upcoming_events = [event for event in events if datetime.strptime(event['date'], '%Y-%m-%d') >= datetime.now()]

# Adjust end times to prevent overlaps
upcoming_events = adjust_end_times(upcoming_events)

# Write the JSON file to the output directory in project root
output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output')
os.makedirs(output_dir, exist_ok=True)

output_path = os.path.join(output_dir, 'upcoming_events.json')
with open(output_path, 'w') as f:
    json.dump(upcoming_events, f, indent=4)

# Display next event
if upcoming_events:
    next_event = upcoming_events[0]
    print("Next Event:")
    print(f"Date: {next_event['date']}")
    print(f"Fixture: {next_event['fixture']}")
    print(f"Start Time: {next_event['start_time']}")
    print(f"End Time: {next_event['end_time']}")
    print(f"Crowd: {next_event['crowd']}")

    # Display upcoming events in JSON format
    print("\nAll Upcoming Events:")
    print(json.dumps(upcoming_events, indent=4))
else:
    print("No upcoming events.")

# Log errors
if error_log:
    with open(os.path.join(output_dir, 'parsing_errors.txt'), 'w') as log_file:  # Changed from error_log.txt
        log_file.write('\n'.join(error_log))
    print(f"\nErrors encountered during processing. See '{output_dir}/parsing_errors.txt' for details.")  # Updated message