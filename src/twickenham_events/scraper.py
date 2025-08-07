"""
Twickenham Events scraper with complete legacy functionality migration.
Handles sophisticated date/time normalization, event grouping, and processing.
"""

from datetime import date, datetime, time as time_obj, timedelta
import re
import time
from typing import Any, List, Optional, Tuple

from bs4 import BeautifulSoup
import requests


class EventScraper:
    """Handles scraping and processing of Twickenham Stadium events."""

    def __init__(self, config):
        """Initialize the scraper with configuration."""
        self.config = config
        self.error_log = []

    def scrape_events(self, url: str) -> tuple[list[dict[str, str]], dict[str, Any]]:
        """
        Scrape events with retry logic for temporary outages.

        Returns:
            tuple: (raw_events_list, stats_dict) where stats contains retry and timing info
        """
        if not url:
            self.error_log.append(
                "Configuration error: 'scraping.url' is not set in the config file."
            )
            return [], {
                "raw_events_count": 0,
                "fetch_duration": 0,
                "retry_attempts": 0,
                "data_source": "config_error",
            }

        # Get retry settings from config with sensible defaults
        max_retries = self.config.get("scraping.max_retries", 3)
        retry_delay = self.config.get("scraping.retry_delay", 5)
        timeout = self.config.get("scraping.timeout", 10)

        start_time = time.time()

        for attempt in range(max_retries):
            try:
                print(f"🌐 Fetching events (attempt {attempt + 1}/{max_retries})...")
                events = self._fetch_events_single_attempt(url, timeout)

                # Calculate stats
                fetch_duration = time.time() - start_time
                stats = {
                    "raw_events_count": len(events) if events else 0,
                    "fetch_duration": round(fetch_duration, 2),
                    "retry_attempts": attempt + 1,
                    "data_source": "live",
                }

                if events:  # Success with data
                    print(f"   🎯 Successfully fetched {len(events)} events")
                    print(f"   ⏱️  Fetch completed in {stats['fetch_duration']}s")
                    return events, stats
                else:
                    print("   📭 No events found in response")
                    # Even if no events, don't retry - this might be normal
                    return events, stats

            except requests.RequestException as e:
                error_msg = f"Attempt {attempt + 1} failed: {e}"
                self.error_log.append(error_msg)
                print(f"   ❌ {error_msg}")

                if attempt < max_retries - 1:  # Not the last attempt
                    print(f"   ⏳ Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    print("   🚫 All retry attempts failed")

        # All attempts failed
        fetch_duration = time.time() - start_time
        failed_stats = {
            "raw_events_count": 0,
            "fetch_duration": round(fetch_duration, 2),
            "retry_attempts": max_retries,
            "data_source": "failed",
        }
        return [], failed_stats

    def _fetch_events_single_attempt(
        self, url: str, timeout: int = 10
    ) -> list[dict[str, str]]:
        """
        Single attempt to fetch events from the website.

        Returns:
            List of raw event data dictionaries.
        """
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        # Richmond.gov.uk specific parsing
        event_tables = soup.find_all("table", class_="table")
        raw_events = []

        for table in event_tables:
            caption = table.find("caption")
            if (
                not caption
                or "events at twickenham stadium" not in caption.text.lower()
            ):
                continue

            for row in table.find_all("tr")[1:]:  # Skip header row
                cols = row.find_all("td")
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

    def normalize_time(self, time_str: Optional[str]) -> Optional[List[str]]:
        """Normalize time format, returning a list of sorted times - full legacy implementation."""
        if not time_str or time_str.lower() == "tbc":
            return None

        time_str = time_str.lower()
        # Handle specific noon patterns first to avoid duplicates
        time_str = re.sub(r"\b12\s*noon\b", "12:00pm", time_str)
        time_str = re.sub(r"\bnoon\s*12\b", "12:00pm", time_str)
        # Then handle standalone noon
        time_str = time_str.replace("noon", "12:00pm")
        # Handle specific midnight patterns first to avoid duplicates
        time_str = re.sub(r"\b12\s*midnight\b", "12:00am", time_str)
        time_str = re.sub(r"\bmidnight\s*12\b", "12:00am", time_str)
        # Then handle standalone midnight
        time_str = time_str.replace("midnight", "12:00am")
        time_str = re.sub(r"\s*\(tbc\)", "", time_str, flags=re.IGNORECASE)
        time_str = time_str.replace(".", ":")
        time_str = time_str.replace(" and ", " & ")

        time_patterns = re.findall(
            r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm)?\b", time_str, re.IGNORECASE
        )
        if not time_patterns:
            self.error_log.append(f"No valid time patterns found in: '{time_str}'")
            return None

        def is_valid_time(hour, minute):
            return 0 <= hour <= 23 and 0 <= minute <= 59

        def parse_single_time(time, shared_meridian=None):
            time = time.strip().lower()
            meridian = shared_meridian
            if "pm" in time:
                meridian = "pm"
                time = time.replace("pm", "").strip()
            elif "am" in time:
                meridian = "am"
                time = time.replace("am", "").strip()

            try:
                hour, minute = (
                    map(int, time.split(":")) if ":" in time else (int(time), 0)
                )
                if hour > 12 and meridian:
                    return None, None
                if hour > 23:
                    return None, None
                if meridian == "pm" and hour < 12:
                    hour += 12
                elif meridian == "am" and hour == 12:
                    hour = 0
                return (
                    (f"{hour:02d}:{minute:02d}", meridian)
                    if is_valid_time(hour, minute)
                    else (None, None)
                )
            except (ValueError, AttributeError):
                self.error_log.append(f"Failed to parse time component: '{time}'")
                return None, None

        last_meridian = next(
            (
                m
                for t in reversed(time_patterns)
                if (m := ("am" if "am" in t else "pm" if "pm" in t else None))
            ),
            None,
        )
        converted_times = [
            parsed_time
            for time in time_patterns
            if (parsed_time := parse_single_time(time, last_meridian)[0])
        ]
        return sorted(converted_times) if converted_times else None

    def normalize_date_range(self, date_str: Optional[str]) -> Optional[str]:
        """Normalizes a variety of date string formats to 'YYYY-MM-DD' - full legacy implementation."""
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
        cleaned_str = re.sub(
            r"(\d+)(st|nd|rd|th)",
            r"\1",
            cleaned_str,
        )

        # Handle date ranges like '16/17 May 2025' by taking the first day part
        cleaned_str = re.sub(
            r"(\d{1,2})\s*/\s*\d{1,2}(\s+[a-zA-Z]+\s+\d{2,4})",
            r"\1\2",
            cleaned_str,
        )

        # Normalize separators to a single space
        cleaned_str = cleaned_str.replace("-", " ").replace("/", " ").replace(".", " ")
        # Remove extra whitespace
        cleaned_str = re.sub(r"\s+", " ", cleaned_str).strip()

        # List of possible date formats (now with spaces as separator)
        patterns = [
            "%d %B %Y",  # e.g., 16 may 2025
            "%d %b %Y",  # e.g., 16 aug 2025
            "%d %B %y",  # e.g., 16 may 23
            "%d %b %y",  # e.g., 16 aug 23
            "%d %m %Y",  # e.g., 16 05 2025
            "%d %m %y",  # e.g., 16 05 23
            "%Y %m %d",  # ISO format
        ]

        # Try parsing the cleaned string with the defined patterns
        for fmt in patterns:
            try:
                return datetime.strptime(cleaned_str, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue

        return None

    def validate_crowd_size(self, crowd_str: Optional[str]) -> Optional[str]:
        """Validates and formats the crowd size string - full legacy implementation."""
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
                    self.error_log.append(
                        f"Implausible crowd size detected: '{crowd_str}'"
                    )
                    return None
            return f"{crowd:,}"
        except (ValueError, IndexError):
            self.error_log.append(f"Invalid crowd size: '{crowd_str}'")
            return None

    def summarize_events(
        self, raw_events: list[dict[str, str]]
    ) -> list[dict[str, Any]]:
        """
        Summarizes and filters a list of raw event data - full legacy implementation.
        - Normalizes date and time formats.
        - Filters out events that have already passed.
        - Groups events by date with metadata.
        """
        from .ai_processor import AIProcessor

        # Initialize AI processor if enabled
        processor = None
        if self.config.get("ai_processor.shortening.enabled", False):
            try:
                processor = AIProcessor(self.config)
            except Exception as e:
                self.error_log.append(f"AI processor initialization failed: {e}")

        today = datetime.now().date()
        summarized_by_date = {}

        for event in raw_events:
            event_date_str = self.normalize_date_range(event["date"])
            if not event_date_str:
                self.error_log.append(f"Could not parse date: {event['date']}")
                continue

            try:
                event_date = datetime.strptime(event_date_str, "%Y-%m-%d").date()
            except ValueError:
                self.error_log.append(f"Invalid date format: {event_date_str}")
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

            start_times = self.normalize_time(event.get("time"))
            crowd_size = self.validate_crowd_size(event.get("crowd"))

            # Get shortened name for the fixture
            fixture_name = event["title"]
            short_name = fixture_name
            if processor:
                try:
                    short_name, _, _ = processor.get_short_name(fixture_name)
                except Exception as e:
                    self.error_log.append(
                        f"AI shortening failed for '{fixture_name}': {e}"
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
                e.get("start_time")
                for e in date_summary["events"]
                if e.get("start_time")
            ]
            if start_times:
                date_summary["earliest_start"] = min(start_times)

        return sorted(summarized_by_date.values(), key=lambda x: x["date"])

    def find_next_event_and_summary(
        self, summarized_events: list[dict[str, Any]]
    ) -> Tuple[Optional[dict], Optional[dict]]:
        """
        Finds the current or next upcoming event and a summary for that day.
        An event is considered "over" based on rules in the config.
        """
        now = datetime.now()
        today = now.date()

        # Get rules from config, with defaults
        cutoff_str = self.config.get("event_rules.end_of_day_cutoff", "23:00")
        delay_hours = self.config.get("event_rules.next_event_delay_hours", 1)

        try:
            cutoff_time = datetime.strptime(cutoff_str, "%H:%M").time()
        except ValueError:
            cutoff_time = time_obj(23, 0)  # Default fallback
            self.error_log.append(
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
                        start_time = datetime.strptime(
                            earliest_start_str, "%H:%M"
                        ).time()
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
