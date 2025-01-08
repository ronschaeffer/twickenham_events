#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
from typing import Optional
import json

# Step 1: Fetch the webpage
url = 'https://www.richmond.gov.uk/services/parking/cpz/twickenham_events'
response = requests.get(url)

# Step 2: Parse the HTML content
soup = BeautifulSoup(response.text, 'html.parser')

# Step 3: Extract the table rows (excluding the header)
rows = soup.select("table.table tr:not(:first-child)")  # Select all table rows except the header

# Step 4: Initialize a list to store all events
events = []

# Function to normalize and extract the first date from a range
def normalize_date_range(date_str: str) -> Optional[str]:
    """Normalize date strings to YYYY-MM-DD."""
    if not isinstance(date_str, str) or not date_str.strip():
        return None

    cleaned = date_str.strip()
    
    # Remove weekday names and 'Weekend' or 'Wknd'
    weekday_pattern = (r'^(Mon|Tue|Wed|Thu|Fri|Sat|Sun|'
                      r'Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|'
                      r'Weekend|Wknd)\s+')
    cleaned = re.sub(weekday_pattern, '', cleaned, flags=re.IGNORECASE).strip()
    
    # Remove any ordinal suffixes (st, nd, rd, th)
    cleaned = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', cleaned, flags=re.IGNORECASE)
    
    # Handle formats like '16/17 May 2025' -> '16 May 2025'
    if '/' in cleaned:
        parts = cleaned.split()
        if len(parts) >= 3:
            day = parts[0].split('/')[0]
            cleaned = f"{day} {' '.join(parts[1:])}"

    formats = [
        '%d %B %Y',      # 16 May 2025
        '%d %b %Y',      # 16 May 2025
        '%e %B %Y',      # single digit day
        '%e %b %Y',      # single digit day abbreviated month
        '%d-%b-%Y',      # 16-May-2025
        '%d-%b-%y',      # 16-May-25
        '%d/%m/%Y',      # 16/05/2025
        '%d/%m/%y',      # 16/05/25
        '%d-%m-%Y',      # 16-05-2025
        '%d-%m-%y',      # 16-05-25
        '%d.%m.%Y',      # 16.05.2025
        '%d.%m.%y',      # 16.05.25
    ]

    for fmt in formats:
        try:
            date_obj = datetime.strptime(cleaned, fmt)
            if '%y' in fmt:  # Handle 2-digit years
                if date_obj.year < 2000:
                    date_obj = date_obj.replace(year=date_obj.year + 100)
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            continue

    return None

# Function to normalize time format with multiple times using '&'
def normalize_time(time_str):
    if not time_str or time_str.lower() == 'tbc':  # Handle empty or "TBC" cases
        return None

    time_str = time_str.replace('.', ':')  # Normalize dots to colons
    time_parts = time_str.split(' & ')
    time_parts = [part.strip() for part in time_parts]

    converted_times = []
    for time in time_parts:
        try:
            # Handle formats like "3pm" (12-hour clock without minutes)
            if len(time) <= 4 and time[-2:].lower() in ['am', 'pm']:
                event_time = datetime.strptime(time, '%I%p').strftime('%H:%M')
            else:
                # Handle formats like "3:10pm"
                event_time = datetime.strptime(time, '%I:%M%p').strftime('%H:%M')
            converted_times.append(event_time)
        except ValueError:
            converted_times.append(None)

    final_time = ' & '.join([time for time in converted_times if time])
    return final_time if final_time else None


# Function to format crowd size with commas
def format_crowd_size(crowd_str):
    try:
        crowd = int(crowd_str.replace(',', '').strip())
        return f"{crowd:,}"
    except ValueError:
        return crowd_str

# Loop through rows and check dates
for row in rows:
    cols = row.find_all('td')
    date_str = cols[0].text.strip()
    fixture = cols[1].text.strip()
    time_str = cols[2].text.strip()
    crowd_str = cols[3].text.strip()

    # Normalize and parse date string
    date_str = normalize_date_range(date_str)

    if date_str:
        try:
            event_date = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            continue

        # Normalize time
        event_time = normalize_time(time_str)

        # Format crowd size
        formatted_crowd = format_crowd_size(crowd_str)

        # Add event to the list
        events.append({
            'date': event_date.strftime('%Y-%m-%d'),
            'fixture': fixture,
            'time': event_time,
            'crowd': formatted_crowd
        })

# Filter upcoming events (future events only)
upcoming_events = [event for event in events if datetime.strptime(event['date'], '%Y-%m-%d') >= datetime.now()]

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
