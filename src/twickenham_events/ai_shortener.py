"""
AI-powered event name shortening and type detection using Google Gemini API.
"""

from datetime import datetime
import json
import logging
from pathlib import Path
import re
from typing import Any

# Load generative AI client dynamically. genai is Any so attribute access is permitted
genai: Any = None
try:
    import importlib

    _gen_mod = importlib.import_module("google.generativeai")
    genai = _gen_mod
    GENAI_AVAILABLE = True
except Exception:
    genai = None
    GENAI_AVAILABLE = False
    logging.warning(
        "google.generativeai not available. Event shortening will be disabled."
    )


class AIShortener:
    """Handles AI-powered shortening of event names and event type detection."""

    def __init__(self, config: Any):
        """Initialize the AI shortener with configuration."""
        self.config = config
        self.cache = (
            self._load_cache() if config.get("ai_shortener.cache_enabled", True) else {}
        )
        self.type_cache = (
            self._load_type_cache()
            if config.get("ai_type_detection.cache_enabled", True)
            else {}
        )
        # Circuit breaker with timed backoff on quota/rate limit
        self._shortener_circuit_open = False
        self._shortener_circuit_open_ts: float | None = None

    def shortener_circuit_open(self) -> bool:
        """Return True if circuit is open and backoff window hasn't elapsed.

        Uses ai_shortener.retry_minutes_on_quota when available, else defaults to 10.
        """
        if not self._shortener_circuit_open:
            return False
        try:
            backoff_min = int(
                self.config.get("ai_shortener.retry_minutes_on_quota", 10)
            )
        except Exception:
            backoff_min = 10
        if self._shortener_circuit_open_ts is None:
            return True
        import time as _t

        return (_t.time() - self._shortener_circuit_open_ts) < (backoff_min * 60)

    def get_event_type_and_icons(self, event_name: str) -> tuple[str, str, str]:
        """
        Determine the event type and return appropriate icons.

        Args:
            event_name: The event name to analyze

        Returns:
            Tuple of (event_type, emoji, mdi_icon):
            - event_type: "rugby", "concert", or "generic"
            - emoji: Unicode emoji for CLI display
            - mdi_icon: Material Design Icon name for MQTT
        """
        # Check if AI type detection is enabled
        if self.config.get("ai_type_detection.enabled", False):
            event_type = self._detect_event_type_ai(event_name)
        else:
            event_type = self._detect_event_type_fallback(event_name)

        # Map event type to icons
        return self._get_icons_for_type(event_type)

    def _detect_event_type_ai(self, event_name: str) -> str:
        """Use AI to detect event type with caching."""
        # Check if feature is disabled or API not available
        if not self.config.get("ai_type_detection.enabled", False):
            return self._detect_event_type_fallback(event_name)

        if not GENAI_AVAILABLE:
            return self._detect_event_type_fallback(event_name)

        # Check cache first
        if (
            self.config.get("ai_type_detection.cache_enabled", True)
            and event_name in self.type_cache
        ):
            cached_entry = self.type_cache[event_name]
            if not cached_entry.get("error"):
                return cached_entry.get("type", "generic")

        try:
            api_key = self.config.get(
                "ai_shortener.api_key"
            )  # Reuse same API key - config handles ${} expansion
            if not api_key:
                return self._detect_event_type_fallback(event_name)

            assert GENAI_AVAILABLE
            genai.configure(api_key=api_key)
            model_name = self.config.get("ai_type_detection.model", "gemini-2.5-pro")

            prompt = f"""Analyze this event name and classify it into one of these categories:
- "rugby" - for rugby matches, internationals, Six Nations, World Cup, etc.
- "concert" - for musical performances, artists, bands, tours, etc.
- "generic" - for anything else (conferences, corporate events, other sports, etc.)

Event name: "{event_name}"

Respond with ONLY the category word (rugby, concert, or generic), nothing else."""

            assert GENAI_AVAILABLE
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)

            if response and response.text:
                detected_type = response.text.strip().lower()
                if detected_type in ["rugby", "concert", "generic"]:
                    # Cache the result
                    if self.config.get("ai_type_detection.cache_enabled", True):
                        self.type_cache[event_name] = {
                            "type": detected_type,
                            "timestamp": datetime.now().isoformat(),
                            "error": False,
                        }
                        self._save_type_cache()
                    return detected_type

            # AI response was unclear, use fallback
            return self._detect_event_type_fallback(event_name)

        except Exception as e:
            logging.warning("AI type detection failed for '%s': %s", event_name, e)
            # Cache the failure to avoid repeated API calls
            if self.config.get("ai_type_detection.cache_enabled", True):
                self.type_cache[event_name] = {
                    "type": "generic",
                    "timestamp": datetime.now().isoformat(),
                    "error": True,
                    "error_message": str(e),
                }
                self._save_type_cache()
            return self._detect_event_type_fallback(event_name)

    def _detect_event_type_fallback(self, event_name: str) -> str:
        """Fallback method using regex patterns to detect event type."""
        event_lower = event_name.lower()

        # Rugby keywords
        rugby_patterns = [
            r"\b(rugby|rfu|six nations|world cup|nations cup|autumn international|spring international)\b",
            r"\b(england|wales|scotland|ireland|france|italy|australia|new zealand|south africa|argentina|fiji)\s+(v|vs|versus)\s+",
            r"\b(lions|all blacks|wallabies|springboks|pumas)\b",
            r"\b(internationals?|test match|championship)\b",
            r"\b(guinness|championship|premiership).*rugby\b",
            r"\b(harlequins|leicester|saracens|northampton|bath|gloucester|exeter|bristol|sale|wasps)\b.*\b(v|vs|versus)\b",
            r"\b(quins|tigers|saints|chiefs|sharks)\b.*\b(v|vs|versus)\b",
        ]

        # Concert keywords
        concert_patterns = [
            r"\b(concert|tour|live|music|band|artist|singer|orchestra|symphony)\b",
            r"\b(gig|show|performance|acoustic|jazz|rock|pop|classical)\b",
            r"\b(festival|music festival)\b",
        ]

        # Check for rugby first
        for pattern in rugby_patterns:
            if re.search(pattern, event_lower):
                return "rugby"

        # Check for concert
        for pattern in concert_patterns:
            if re.search(pattern, event_lower):
                return "concert"

        # Default to generic
        return "generic"

    def _get_icons_for_type(self, event_type: str) -> tuple[str, str, str]:
        """Map event type to emoji and MDI icon."""
        icon_mapping = {
            "rugby": ("🏉", "mdi:rugby"),
            "concert": ("🎵", "mdi:music"),
            "generic": ("🏟️", "mdi:stadium"),
        }

        if event_type in icon_mapping:
            emoji, mdi_icon = icon_mapping[event_type]
            return event_type, emoji, mdi_icon
        else:
            # Fallback to generic
            return "generic", "🏟️", "mdi:stadium"

    def get_short_name(self, original_name: str) -> tuple[str, bool, str]:
        """
        Get a shortened version of an event name using Google Gemini API.
        Uses caching to avoid repeated API calls for the same event names.

        Args:
            original_name: The original event name to shorten

        Returns:
            Tuple of (name_to_use, had_error, error_message):
            - name_to_use: Either the shortened name or original name
            - had_error: Boolean indicating if an error occurred during processing
            - error_message: Detailed error message if had_error is True, empty string otherwise
        """
        # Check if feature is disabled
        if not self.config.get("ai_shortener.enabled", False):
            return original_name, False, ""

        # Check cache first
        if (
            self.config.get("ai_shortener.cache_enabled", True)
            and original_name in self.cache
        ):
            cached_entry = self.cache[original_name]
            return cached_entry.get("short", original_name), False, ""

        # Check if dependencies are available
        if not GENAI_AVAILABLE:
            error_msg = "google.generativeai library not available - install with 'poetry install --with ai'"
            logging.warning("Event shortening requested but %s", error_msg)
            return original_name, True, error_msg

        # Fast exit if we've previously hit quota/rate limiting (respect timed backoff)
        if self.shortener_circuit_open():
            return original_name, False, ""

        try:
            # Configure the API - config handles ${VARIABLE} expansion
            api_key = self.config.get("ai_shortener.api_key")

            if not api_key:
                error_msg = "AI shortener enabled but no API key provided - check ai_shortener.api_key in config"
                logging.error(error_msg)
                return original_name, True, error_msg

            assert GENAI_AVAILABLE
            genai.configure(api_key=api_key)  # type: ignore[attr-defined]

            # Get configuration values
            model_name = self.config.get("ai_shortener.model", "gemini-2.5-pro")
            char_limit = self.config.get("ai_shortener.max_length", 16)
            prompt_template = self.config.get("ai_shortener.prompt_template", "")
            flags_enabled = self.config.get("ai_shortener.flags_enabled", False)
            standardize_spacing = self.config.get(
                "ai_shortener.standardize_spacing", True
            )

            if not prompt_template:
                error_msg = "AI shortener enabled but no prompt template provided - check ai_shortener.prompt_template in config"
                logging.error(error_msg)
                return original_name, True, error_msg

            # Prepare flag-specific content based on configuration
            if flags_enabled:
                flag_instructions = """When there's space and the event involves countries, add Unicode flag emojis
        with EXACTLY ONE SPACE between flag and country code.

        Flag examples: 🏴󠁧󠁢󠁥󠁮󠁧󠁿 ENG (St George's Cross), 🇦🇺 AUS, 🇳🇿 NZ, 🇦🇷 ARG, 🇿🇦 RSA,
        🇫🇷 FRA, 🇮🇹 ITA, 🏴󠁧󠁢󠁷󠁬󠁳󠁿 WAL, 🏴󠁧󠁢󠁳󠁣󠁴󠁿 SCO, 🇮🇪 IRE, 🇫🇯 FIJ"""

                flag_examples = """fixture: England v Australia
        fixture_short: 🏴󠁧󠁢󠁥󠁮󠁧󠁿 ENG v 🇦🇺 AUS

        fixture: Argentina V South Africa
        fixture_short: 🇦🇷 ARG V 🇿🇦 RSA"""
            else:
                flag_instructions = "Keep text-only format without flag emojis."
                flag_examples = """fixture: England v Australia
        fixture_short: ENG v AUS

        fixture: Argentina V South Africa
        fixture_short: ARG V RSA"""

            # Prepare the prompt
            final_prompt = prompt_template.format(
                char_limit=char_limit,
                event_name=original_name,
                flag_instructions=flag_instructions,
                flag_examples=flag_examples,
            )

            # Make the API call with rate limiting and retry for safety filters
            import time

            assert GENAI_AVAILABLE
            model = genai.GenerativeModel(model_name)

            # Try the request, with retry for safety filter issues
            max_attempts = 2
            for attempt in range(max_attempts):
                try:
                    # Add delay to prevent rate limiting
                    if attempt > 0:
                        time.sleep(3)  # Longer delay for retries
                    else:
                        time.sleep(2)  # Normal delay

                    # For retry attempts, try alternative phrasing
                    if attempt > 0:
                        # Replace potentially problematic words
                        safe_event_name = original_name.replace(" vs ", " v ").replace(
                            " VS ", " V "
                        )
                        safe_prompt = final_prompt.replace(
                            original_name, safe_event_name
                        )
                        response = model.generate_content(safe_prompt)
                    else:
                        response = model.generate_content(final_prompt)

                    if response.text:
                        shortened_name = response.text.strip()

                        # Apply flag spacing standardization if enabled
                        if flags_enabled and standardize_spacing:
                            shortened_name = self._standardize_flag_spacing(
                                shortened_name
                            )

                        # Visual width validation - count flags as 2 units, characters as 1 unit
                        visual_width = self._calculate_visual_width(shortened_name)
                        if visual_width <= char_limit and shortened_name:
                            # Save successful result to cache if caching is enabled
                            if self.config.get("ai_shortener.cache_enabled", True):
                                self.cache[original_name] = {
                                    "short": shortened_name,
                                    "created": datetime.now().isoformat(),
                                    "original": original_name,
                                }
                                self._save_cache()
                            return shortened_name, False, ""
                        else:
                            error_msg = f"Generated name '{shortened_name}' exceeds visual width limit ({visual_width} > {char_limit}) or is empty"
                            logging.warning(error_msg)
                            return original_name, True, error_msg
                    # Empty response - likely safety filter
                    elif attempt < max_attempts - 1:
                        logging.warning(
                            "Empty response for '%s' (attempt %d), retrying with alternative phrasing...",
                            original_name,
                            attempt + 1,
                        )
                        continue
                    else:
                        error_msg = (
                            "Empty response received from Gemini API after retries"
                        )
                        logging.error(error_msg)
                        return original_name, True, error_msg

                except Exception as e:
                    error_str = str(e)
                    # Check if it's a safety filter issue
                    if "finish_reason" in error_str and (
                        "1" in error_str or "SAFETY" in error_str.upper()
                    ):
                        if attempt < max_attempts - 1:
                            logging.warning(
                                "Safety filter triggered for '%s' (attempt %d), retrying with alternative phrasing...",
                                original_name,
                                attempt + 1,
                            )
                            continue
                        else:
                            error_msg = f"Content safety filter triggered for '{original_name}' after retries"
                            logging.warning(error_msg)
                            return original_name, True, error_msg
                    else:
                        # Different error, don't retry
                        quota_hit = (
                            "429" in error_str
                            or "quota" in error_str.lower()
                            or "rate" in error_str.lower()
                        )
                        if quota_hit:
                            if not self._shortener_circuit_open:
                                self._shortener_circuit_open = True
                                import time as _time

                                self._shortener_circuit_open_ts = _time.time()
                                logging.warning(
                                    "AI quota/rate limit encountered; backing off further shortening"
                                )
                            return original_name, False, ""
                        error_msg = (
                            f"API error while shortening '{original_name}': {e!s}"
                        )
                        logging.error(error_msg)
                        return original_name, True, error_msg

            # If we get here, all attempts failed
            error_msg = f"All attempts failed for '{original_name}'"
            logging.error(error_msg)
            return original_name, True, error_msg

        except Exception as e:
            error_str = str(e)
            if (
                "429" in error_str
                or "quota" in error_str.lower()
                or "rate" in error_str.lower()
            ):
                if not self._shortener_circuit_open:
                    self._shortener_circuit_open = True
                    import time as _time

                    self._shortener_circuit_open_ts = _time.time()
                    logging.warning(
                        "AI quota/rate limit encountered (outer); backing off further shortening"
                    )
                return original_name, False, ""
            error_msg = f"Unexpected error while shortening '{original_name}': {e!s}"
            logging.error(error_msg)
            return original_name, True, error_msg

    def _get_cache_path(self) -> Path:
        """Get the path to the cache file."""
        return Path(__file__).parent.parent.parent / "output" / "event_name_cache.json"

    def _load_cache(self) -> dict[str, dict[str, str]]:
        """Load the event name cache from file."""
        cache_path = self._get_cache_path()
        if cache_path.exists():
            try:
                with open(cache_path) as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                logging.warning("Failed to load cache: %s", e)
        return {}

    def _save_cache(self) -> None:
        """Save the event name cache to file."""
        cache_path = self._get_cache_path()
        cache_path.parent.mkdir(exist_ok=True)
        try:
            with open(cache_path, "w") as f:
                json.dump(self.cache, f, indent=2)
        except OSError as e:
            logging.error("Failed to save cache: %s", e)

    def _standardize_flag_spacing(self, text: str) -> str:
        """
        Ensure consistent flag + space + country format.
        Fixes AI inconsistencies in flag spacing.
        """
        import re

        # Flag-to-country mappings with consistent spacing
        flag_patterns = [
            (r"🏴󠁧󠁢󠁥󠁮󠁧󠁿\s*ENG", "🏴󠁧󠁢󠁥󠁮󠁧󠁿 ENG"),  # England
            (r"🏴󠁧󠁢󠁳󠁣󠁴󠁿\s*SCO", "🏴󠁧󠁢󠁳󠁣󠁴󠁿 SCO"),  # Scotland
            (r"🏴󠁧󠁢󠁷󠁬󠁳󠁿\s*WAL", "🏴󠁧󠁢󠁷󠁬󠁳󠁿 WAL"),  # Wales
            (r"🇦🇺\s*AUS", "🇦🇺 AUS"),  # Australia
            (r"🇳🇿\s*NZ", "🇳🇿 NZ"),  # New Zealand
            (r"🇦🇷\s*ARG", "🇦🇷 ARG"),  # Argentina
            (r"🇿🇦\s*RSA", "🇿🇦 RSA"),  # South Africa
            (r"🇫🇷\s*FRA", "🇫🇷 FRA"),  # France
            (r"🇮🇹\s*ITA", "🇮🇹 ITA"),  # Italy
            (r"🇮🇪\s*IRE", "🇮🇪 IRE"),  # Ireland
            (r"🇫🇯\s*FIJ", "🇫🇯 FIJ"),  # Fiji
        ]

        result = text
        for pattern, replacement in flag_patterns:
            result = re.sub(pattern, replacement, result)

        return result

    def _calculate_visual_width(self, text: str) -> int:
        """
        Calculate visual display width where each flag emoji counts as 2 units
        and regular characters count as 1 unit each.
        """
        import re

        # Count flag emojis (they start with regional indicator symbols or black flag)
        flag_pattern = r"[\U0001F1E6-\U0001F1FF][\U0001F1E6-\U0001F1FF]|\U0001F3F4[\U000E0060-\U000E007F]+"
        flag_count = len(re.findall(flag_pattern, text))

        # Remove flags to count remaining characters
        text_without_flags = re.sub(flag_pattern, "", text)
        char_count = len(text_without_flags)

        # Each flag = 2 units, each character = 1 unit
        return char_count + (flag_count * 2)

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        if not self.config.get("ai_shortener.cache_enabled", True):
            return {"cache_enabled": False}

        total_entries = len(self.cache)
        successful_entries = sum(
            1 for entry in self.cache.values() if entry.get("short")
        )
        failed_entries = total_entries - successful_entries

        return {
            "cache_enabled": True,
            "total_entries": total_entries,
            "successful_entries": successful_entries,
            "failed_entries": failed_entries,
            "cache_file": str(self._get_cache_path()),
        }

    def clear_cache(self) -> None:
        """Clear the cache completely."""
        self.cache = {}
        self._save_cache()

    def reprocess_cache(self) -> int:
        """Reprocess all cached entries and return count of updated entries."""
        if not self.config.get("ai_shortener.cache_enabled", True):
            return 0

        count = 0
        for original_name in list(self.cache.keys()):
            # Remove from cache and re-process
            del self.cache[original_name]
            try:
                self.get_short_name(original_name)
                count += 1
            except Exception:
                pass  # Ignore errors during reprocessing

        return count

    def _get_type_cache_path(self) -> Path:
        """Get the path for the type detection cache file."""
        cache_dir = Path(self.config.get("ai_type_detection.cache_dir", "output/cache"))
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / "ai_type_cache.json"

    def _load_type_cache(self) -> dict[str, Any]:
        """Load the type detection cache from disk."""
        cache_path = self._get_type_cache_path()
        if cache_path.exists():
            try:
                with open(cache_path, encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                logging.warning("Failed to load type cache, starting fresh")
        return {}

    def _save_type_cache(self) -> None:
        """Save the type detection cache to disk."""
        cache_path = self._get_type_cache_path()
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(self.type_cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.warning("Failed to save type cache: %s", e)

    def get_type_cache_stats(self) -> dict:
        """Get type detection cache statistics."""
        if not self.config.get("ai_type_detection.cache_enabled", True):
            return {"type_cache_enabled": False}

        total_entries = len(self.type_cache)
        successful_entries = sum(
            1 for entry in self.type_cache.values() if not entry.get("error", True)
        )
        failed_entries = total_entries - successful_entries

        return {
            "type_cache_enabled": True,
            "total_entries": total_entries,
            "successful_entries": successful_entries,
            "failed_entries": failed_entries,
            "cache_file": str(self._get_type_cache_path()),
        }

    def clear_type_cache(self) -> None:
        """Clear the type detection cache completely."""
        self.type_cache = {}
        self._save_type_cache()
