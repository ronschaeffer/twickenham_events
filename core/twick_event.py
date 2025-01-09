#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import json
import os
from typing import Optional

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

# Function to normalize and extract the first date from a range
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
        (r'(\d{1,2})\s*[-/]\s*(\d{1,2})\s+(\w+)\s+(\d{4})', None),  # 16/17 May 2025
    ]

    for pattern, fmt in numeric_patterns:
        match = re.match(pattern, cleaned)
        if match:
            if fmt:
                try:
                    groups = match.groups()
                    date_str = f"{groups[0]}/{groups[1]}/{groups[2]}"
                    date_obj = datetime.strptime(date_str, fmt)
                    if '%y' in fmt and date_obj.year < 2000:
                        date_obj = date_obj.replace(year=date_obj.year + 100)
                    return date_obj.strftime('%Y-%m-%d')
                except ValueError:
                    continue
            else:
                # Handle range dates like "16/17 May 2025"
                month = match.group(3)
                year = match.group(4)
                day = match.group(1)
                try:
                    date_obj = datetime.strptime(f"{day} {month} {year}", '%d %B %Y')
                    return date_obj.strftime('%Y-%m-%d')
                except ValueError:
                    try:
                        date_obj = datetime.strptime(f"{day} {month} {year}", '%d %b %Y')
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
                date_obj = date_obj.replace(year=date_obj.year + 100)
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            continue

    error_log.append(f"Failed to parse date: '{date_str}'")
    return None

# Function to normalize time format with multiple times using '&'
def normalize_time(time_str):
    if not time_str or time_str.lower() == 'tbc':
        return None

    # Replace "and" with "&" for consistent processing
    time_str = time_str.replace(' and ', ' & ')

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
        date_str = normalize_date_range(cols[header_map['date']].text)
        fixture = cols[header_map['fixture']].text.strip()
        time_str = normalize_time(cols[header_map['time']].text.strip())
        crowd_str = validate_crowd_size(cols[header_map['crowd']].text.strip())

        if date_str:
            events.append({
                'date': date_str,
                'fixture': fixture,
                'time': time_str,
                'crowd': crowd_str,
            })
    except Exception as e:
        error_log.append(f"Error processing row: {row} - {str(e)}")

# Filter upcoming events (future events only)
upcoming_events = [event for event in events if datetime.strptime(event['date'], '%Y-%m-%d') >= datetime.now()]

# Write the JSON file to the output directory
output_dir = 'output'
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
    print(f"Time: {next_event['time']}")
    print(f"Crowd: {next_event['crowd']}")

    # Display upcoming events in JSON format
    print("\nAll Upcoming Events:")
    print(json.dumps(upcoming_events, indent=4))
else:
    print("No upcoming events.")

# Log errors
if error_log:
    with open(os.path.join(output_dir, 'error_log.txt'), 'w') as log_file:
        log_file.write('\n'.join(error_log))
    print(f"\nErrors encountered during processing. See '{output_dir}/error_log.txt' for details.")