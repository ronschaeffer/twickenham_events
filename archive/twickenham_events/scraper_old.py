"""
Event scraping functionality for Twickenham Stadium.
"""

from datetime import datetime
import re
import time
from typing import Any, Optional

from bs4 import BeautifulSoup
import requests


class EventScraper:
    """Handles scraping of events from Twickenham Stadium website."""

    def __init__(self, config):
        """Initialize the scraper with configuration."""
        self.config = config
        self.error_log = []

    def scrape_events(self, url: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """
        Scrape events from the given URL.

        Returns:
            Tuple of (events_list, stats_dict)
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

        max_retries = self.config.get("scraping.max_retries", 3)
        retry_delay = self.config.get("scraping.retry_delay", 5)
        timeout = self.config.get("scraping.timeout", 10)

        return self._fetch_with_retry(url, max_retries, retry_delay, timeout)

    def _fetch_with_retry(
        self, url: str, max_retries: int, delay: int, timeout: int
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Fetch events with retry logic."""
        start_time = time.time()

        for attempt in range(max_retries):
            try:
                print(
                    f"🌐 Fetching events (attempt \033[33m{attempt + 1}\033[0m/\033[33m{max_retries}\033[0m)..."
                )
                events = self._fetch_single_attempt(url, timeout)

                fetch_duration = time.time() - start_time
                stats = {
                    "raw_events_count": len(events) if events else 0,
                    "fetch_duration": round(fetch_duration, 2),
                    "retry_attempts": attempt + 1,
                    "data_source": "live",
                }

                if events:
                    print(
                        f"   \033[32m🎯 Successfully fetched {len(events)} events\033[0m"
                    )
                    print(
                        f"   \033[36m⏱️  Fetch completed in {stats['fetch_duration']}s\033[0m"
                    )
                    return events, stats
                else:
                    print("   \033[33m📭 No events found in response\033[0m")
                    return events, stats

            except requests.RequestException as e:
                error_msg = f"Attempt {attempt + 1} failed: {e}"
                self.error_log.append(error_msg)
                print(f"   \033[31m❌ {error_msg}\033[0m")

                if attempt < max_retries - 1:
                    print(f"   \033[33m⏳ Retrying in {delay} seconds...\033[0m")
                    time.sleep(delay)
                else:
                    print("   \033[31m🚫 All retry attempts failed\033[0m")

        # All attempts failed
        fetch_duration = time.time() - start_time
        failed_stats = {
            "raw_events_count": 0,
            "fetch_duration": round(fetch_duration, 2),
            "retry_attempts": max_retries,
            "data_source": "failed",
        }
        return [], failed_stats

    def _fetch_single_attempt(self, url: str, timeout: int) -> list[dict[str, str]]:
        """
        Single attempt to fetch events from Richmond.gov.uk.

        Returns:
            list[dict[str, str]]: A list of raw event data dictionaries.

        Raises:
            requests.RequestException: If network request fails
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

    def normalize_time(self, time_str: str) -> str:
        """Normalize time string to consistent format."""
        if not time_str or time_str.strip() == "":
            return "Time TBC"

        time_str = time_str.strip()

        # Pattern for times like "19:45" or "7:45 PM"
        time_pattern = r"(\d{1,2}):(\d{2})\s*(AM|PM)?"
        match = re.search(time_pattern, time_str, re.IGNORECASE)

        if match:
            hour, minute, meridiem = match.groups()
            hour = int(hour)
            minute = int(minute)

            if meridiem:
                if meridiem.upper() == "PM" and hour != 12:
                    hour += 12
                elif meridiem.upper() == "AM" and hour == 12:
                    hour = 0

            return f"{hour:02d}:{minute:02d}"

        # If no clear time pattern, return as-is
        return time_str

    def normalize_date_range(self, date_str: str) -> Optional[str]:
        """Normalize date string to YYYY-MM-DD format."""
        if not date_str:
            return None

        date_str = date_str.strip()

        # Try to extract date patterns
        # Common patterns: "Saturday 15 February 2025", "15/02/2025", etc.

        # Pattern for "Saturday 15 February 2025"
        pattern1 = r"\w+\s+(\d{1,2})\s+(\w+)\s+(\d{4})"
        match = re.search(pattern1, date_str)
        if match:
            day, month_name, year = match.groups()
            month_names = {
                "january": 1,
                "february": 2,
                "march": 3,
                "april": 4,
                "may": 5,
                "june": 6,
                "july": 7,
                "august": 8,
                "september": 9,
                "october": 10,
                "november": 11,
                "december": 12,
            }
            month_num = month_names.get(month_name.lower())
            if month_num:
                return f"{year}-{month_num:02d}-{int(day):02d}"

        # Pattern for DD/MM/YYYY
        pattern2 = r"(\d{1,2})/(\d{1,2})/(\d{4})"
        match = re.search(pattern2, date_str)
        if match:
            day, month, year = match.groups()
            return f"{year}-{int(month):02d}-{int(day):02d}"

        # Pattern for YYYY-MM-DD (already normalized)
        pattern3 = r"(\d{4})-(\d{1,2})-(\d{1,2})"
        match = re.search(pattern3, date_str)
        if match:
            year, month, day = match.groups()
            return f"{year}-{int(month):02d}-{int(day):02d}"

        return None

    def validate_crowd_size(self, crowd_str: Optional[str]) -> Optional[str]:
        """Validate and normalize crowd size information."""
        if not crowd_str:
            return None

        crowd_str = crowd_str.strip()
        if not crowd_str or crowd_str.lower() in ("tbc", "tba", "n/a", ""):
            return None

        # Extract numbers and common crowd descriptions
        if re.search(r"\d", crowd_str):
            return crowd_str

        return crowd_str if crowd_str else None

    def summarize_events(
        self, raw_events: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Process and summarize raw events into a structured format."""
        from .ai_processor import AIProcessor

        # Initialize AI processor if enabled
        processor = None
        if self.config.get("ai_processor.shortening.enabled", False):
            try:
                processor = AIProcessor(self.config)
            except Exception as e:
                self.error_log.append(f"AI processor initialization failed: {e}")

        future_events = []
        now = datetime.now()

        for event in raw_events:
            try:
                # Normalize date and time
                normalized_date = self.normalize_date_range(event["date"])
                if not normalized_date:
                    continue

                normalized_time = self.normalize_time(event["time"])
                crowd_size = self.validate_crowd_size(event.get("crowd"))

                # Get short name using AI if available
                short_name = event["title"]
                if processor:
                    try:
                        short_name, _, _ = processor.get_short_name(event["title"])
                    except Exception as e:
                        self.error_log.append(
                            f"AI shortening failed for '{event['title']}': {e}"
                        )

                # Check if event is in the future
                event_date = datetime.strptime(normalized_date.split()[0], "%Y-%m-%d")
                if event_date.date() >= now.date():
                    future_events.append(
                        {
                            "date": normalized_date,
                            "title": event["title"],
                            "short_name": short_name,
                            "time": normalized_time,
                            "crowd_size": crowd_size,
                        }
                    )

            except Exception as e:
                self.error_log.append(
                    f"Error processing event '{event.get('title', 'Unknown')}': {e}"
                )

        return sorted(future_events, key=lambda x: x["date"])

    def find_next_event_and_summary(
        self, events: list[dict[str, Any]]
    ) -> tuple[Optional[dict[str, Any]], Optional[dict[str, Any]]]:
        """Find the next upcoming event and create day summary."""
        if not events:
            return None, None

        # Group events by date
        events_by_date = {}
        for event in events:
            date = event["date"].split()[0]  # Extract date part
            if date not in events_by_date:
                events_by_date[date] = []
            events_by_date[date].append(event)

        # Find next event date
        sorted_dates = sorted(events_by_date.keys())
        if not sorted_dates:
            return None, None

        next_date = sorted_dates[0]
        next_day_events = events_by_date[next_date]

        # Create day summary
        next_day_summary = {
            "date": next_date,
            "event_count": len(next_day_events),
            "events": next_day_events,
        }

        # Return first event of the day as "next event"
        next_event = next_day_events[0] if next_day_events else None

        return next_event, next_day_summary
