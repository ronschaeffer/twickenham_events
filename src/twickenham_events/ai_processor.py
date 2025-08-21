"""
AI-powered event processing including type detection, icon mapping, and name shortening using Google Gemini API.
"""

from datetime import datetime, timezone
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


class AIProcessor:
    """Handles AI-powered event processing including type detection, icon mapping, and name shortening."""

    def __init__(self, config: Any):
        """Initialize the AI processor with configuration."""
        self.config = config
        self.cache = (
            self._load_cache() if config.get("ai_processor.cache_enabled", True) else {}
        )
        self.type_cache = (
            self._load_type_cache()
            if config.get("ai_processor.type_detection.cache_enabled", True)
            else {}
        )
        # Circuit breaker: on quota/rate limit, skip further shortening until backoff window elapses.
        self._shortener_circuit_open = False
        self._shortener_circuit_open_ts: float | None = None

    def shortener_circuit_open(self) -> bool:
        """Return True if circuit is open and backoff window hasn't elapsed."""
        if not self._shortener_circuit_open:
            return False
        try:
            backoff_min = int(
                self.config.get("ai_processor.shortening.retry_minutes_on_quota", 10)
            )
        except Exception:
            backoff_min = 10
        if self._shortener_circuit_open_ts is None:
            return True
        import time as _t

        return (_t.time() - self._shortener_circuit_open_ts) < (backoff_min * 60)

    def get_shortener_backoff_info(self) -> dict:
        """Return backoff state info for AI shortener circuit breaker.

        Returns a dict like:
          {"open": bool, "retry_at": iso_str|None, "retry_in_seconds": int|None}
        """
        info: dict[str, Any] = {
            "open": False,
            "retry_at": None,
            "retry_in_seconds": None,
        }
        if not self._shortener_circuit_open:
            return info
        try:
            backoff_min = int(
                self.config.get("ai_processor.shortening.retry_minutes_on_quota", 10)
            )
        except Exception:
            backoff_min = 10
        if self._shortener_circuit_open_ts is None:
            info["open"] = True
            return info
        import time as _t

        retry_at_epoch = self._shortener_circuit_open_ts + (backoff_min * 60)
        now = _t.time()
        remaining = int(max(0, retry_at_epoch - now))
        # still open if remaining > 0
        info["open"] = remaining > 0
        if remaining > 0:
            dt = datetime.fromtimestamp(retry_at_epoch, tz=timezone.utc).replace(
                microsecond=0
            )
            info["retry_at"] = dt.isoformat().replace("+00:00", "Z")
            info["retry_in_seconds"] = remaining
        return info

    def get_combined_ai_info(self, event_name: str) -> dict:
        """
        Get shortened name, event type, and icons in a single AI API call.

        This method combines shortening, type detection, and flag generation
        into one request to reduce API quota usage.

        Args:
            event_name: The event name to process

        Returns:
            Dict containing:
            - short_name: Shortened version or original if shortening disabled/failed
            - event_type: "trophy", "rugby", "concert", or "generic"
            - emoji: Unicode emoji for display
            - mdi_icon: Material Design Icon name for MQTT
            - had_error: Boolean indicating if processing failed
            - error_message: Error details if had_error is True
        """
        # Check if AI features are enabled
        shortening_enabled = self.config.get("ai_processor.shortening.enabled", False)
        type_detection_enabled = self.config.get(
            "ai_processor.type_detection.enabled", False
        )

        # If neither is enabled, use fallback methods
        if not shortening_enabled and not type_detection_enabled:
            event_type, emoji, mdi_icon = self.get_event_type_and_icons(event_name)
            return {
                "short_name": event_name,
                "event_type": event_type,
                "emoji": emoji,
                "mdi_icon": mdi_icon,
                "had_error": False,
                "error_message": "",
            }

        # Check if only one feature is enabled - use individual methods
        if shortening_enabled and not type_detection_enabled:
            short_name, had_error, error_msg = self.get_short_name(event_name)
            event_type, emoji, mdi_icon = self.get_event_type_and_icons(event_name)
            return {
                "short_name": short_name,
                "event_type": event_type,
                "emoji": emoji,
                "mdi_icon": mdi_icon,
                "had_error": had_error,
                "error_message": error_msg,
            }

        if type_detection_enabled and not shortening_enabled:
            event_type, emoji, mdi_icon = self.get_event_type_and_icons(event_name)
            return {
                "short_name": event_name,
                "event_type": event_type,
                "emoji": emoji,
                "mdi_icon": mdi_icon,
                "had_error": False,
                "error_message": "",
            }

        # Both features enabled - use combined AI call
        return self._get_combined_ai_info_impl(event_name)

    def _get_combined_ai_info_impl(self, event_name: str) -> dict:
        """Implementation of combined AI processing."""
        # Check cache first for both shortening and type detection
        cache_key = f"combined_{event_name}"
        if (
            self.config.get("ai_processor.shortening.cache_enabled", True)
            and cache_key in self.cache
        ):
            cached_entry = self.cache[cache_key]
            return {
                "short_name": cached_entry.get("short_name", event_name),
                "event_type": cached_entry.get("event_type", "generic"),
                "emoji": cached_entry.get("emoji", "🏟️"),
                "mdi_icon": cached_entry.get("mdi_icon", "mdi:stadium"),
                "had_error": False,
                "error_message": "",
            }

        # Check if dependencies are available
        if not GENAI_AVAILABLE:
            event_type, emoji, mdi_icon = self._get_icons_for_type(
                self._detect_event_type_fallback(event_name)
            )
            return {
                "short_name": event_name,
                "event_type": event_type,
                "emoji": emoji,
                "mdi_icon": mdi_icon,
                "had_error": True,
                "error_message": "google.generativeai library not available - install with 'poetry install --with ai'",
            }

        # Check circuit breaker
        if self.shortener_circuit_open():
            event_type, emoji, mdi_icon = self.get_event_type_and_icons(event_name)
            return {
                "short_name": event_name,
                "event_type": event_type,
                "emoji": emoji,
                "mdi_icon": mdi_icon,
                "had_error": False,
                "error_message": "",
            }

        try:
            # Configure the API
            api_key = self.config.get("ai_processor.api_key")
            if not api_key:
                event_type, emoji, mdi_icon = self._get_icons_for_type(
                    self._detect_event_type_fallback(event_name)
                )
                return {
                    "short_name": event_name,
                    "event_type": event_type,
                    "emoji": emoji,
                    "mdi_icon": mdi_icon,
                    "had_error": True,
                    "error_message": "AI processor enabled but no API key provided - check ai_processor.api_key in config",
                }

            assert GENAI_AVAILABLE
            genai.configure(api_key=api_key)

            # Get configuration values
            model_name = self.config.get(
                "ai_processor.shortening.model", "gemini-2.5-pro"
            )
            char_limit = self.config.get("ai_processor.shortening.max_length", 16)
            flags_enabled = self.config.get(
                "ai_processor.shortening.flags_enabled", False
            )
            standardize_spacing = self.config.get(
                "ai_processor.shortening.standardize_spacing", True
            )

            # Create combined prompt
            combined_prompt = self._build_combined_prompt(
                event_name, char_limit, flags_enabled
            )

            # Make the API call
            import time

            model = genai.GenerativeModel(model_name)
            time.sleep(2)  # Rate limiting

            response = model.generate_content(combined_prompt)

            if response and response.text:
                # Parse the response
                result = self._parse_combined_response(
                    response.text.strip(),
                    event_name,
                    char_limit,
                    flags_enabled,
                    standardize_spacing,
                )

                # Cache the result
                if self.config.get("ai_processor.shortening.cache_enabled", True):
                    self.cache[cache_key] = {
                        "short_name": result["short_name"],
                        "event_type": result["event_type"],
                        "emoji": result["emoji"],
                        "mdi_icon": result["mdi_icon"],
                        "created": datetime.now().isoformat(),
                        "original": event_name,
                    }
                    self._save_cache()

                return result
            else:
                # Empty response - fallback
                event_type, emoji, mdi_icon = self._get_icons_for_type(
                    self._detect_event_type_fallback(event_name)
                )
                return {
                    "short_name": event_name,
                    "event_type": event_type,
                    "emoji": emoji,
                    "mdi_icon": mdi_icon,
                    "had_error": True,
                    "error_message": "Empty response received from Gemini API",
                }

        except Exception as e:
            error_str = str(e)
            # Check for quota/rate limit
            quota_hit = (
                "429" in error_str
                or "quota" in error_str.lower()
                or "rate" in error_str.lower()
            )
            if quota_hit and not self._shortener_circuit_open:
                self._shortener_circuit_open = True
                import time as _time

                self._shortener_circuit_open_ts = _time.time()
                logging.warning(
                    "AI quota/rate limit encountered; backing off further AI processing"
                )

            # Use fallback
            event_type, emoji, mdi_icon = self._get_icons_for_type(
                self._detect_event_type_fallback(event_name)
            )
            return {
                "short_name": event_name,
                "event_type": event_type,
                "emoji": emoji,
                "mdi_icon": mdi_icon,
                "had_error": not quota_hit,  # quota hit is not an error, just a limitation
                "error_message": "" if quota_hit else f"API error: {e}",
            }

    def _build_combined_prompt(
        self, event_name: str, char_limit: int, flags_enabled: bool
    ) -> str:
        """Build a combined prompt for shortening and type detection."""
        flag_instructions = ""
        flag_examples = ""

        if flags_enabled:
            flag_instructions = """When there's space and the event involves countries, add Unicode flag emojis
        with EXACTLY ONE SPACE between flag and country code.

        Flag examples: 🏴󠁧󠁢󠁥󠁮󠁧󠁿 ENG (St George's Cross), 🇦🇺 AUS, 🇳🇿 NZ, 🇦🇷 ARG, 🇿🇦 RSA,
        🇫🇷 FRA, 🇮🇹 ITA, 🏴󠁧󠁢󠁷󠁬󠁳󠁿 WAL, 🏴󠁧󠁢󠁳󠁣󠁴󠁿 SCO, 🇮🇪 IRE, 🇫🇯 FIJ"""
            flag_examples = """England v Australia -> 🏴󠁧󠁢󠁥󠁮󠁧󠁿 ENG v 🇦🇺 AUS
        Argentina V South Africa -> 🇦🇷 ARG V 🇿🇦 RSA"""
        else:
            flag_instructions = "Keep text-only format without flag emojis."
            flag_examples = """England v Australia -> ENG v AUS
        Argentina V South Africa -> ARG V RSA"""

        return f"""Analyze this event and provide both a shortened name and event classification.

Event: "{event_name}"

Task 1 - Shorten the name:
- Maximum {char_limit} characters (count flag emojis as 2 characters each)
- Keep essential information like team names, key words
- Use standard abbreviations (England->ENG, Australia->AUS, etc.)
- {flag_instructions}

Task 2 - Classify the event type:
- "trophy" - for finals, championships, cup finals, major tournament finals, or other prestigious competitions
- "rugby" - for regular rugby matches, internationals, Six Nations, World Cup (non-final), etc.
- "concert" - for musical performances, artists, bands, tours, etc.
- "generic" - for anything else (conferences, corporate events, other sports, etc.)

Examples:
{flag_examples}
World Cup Final -> World Cup Final (trophy)
Ed Sheeran Tour -> Ed Sheeran (concert)

Format your response as:
SHORT: [shortened name]
TYPE: [trophy/rugby/concert/generic]

Response:"""

    def _parse_combined_response(
        self,
        response_text: str,
        original_name: str,
        char_limit: int,
        flags_enabled: bool,
        standardize_spacing: bool,
    ) -> dict:
        """Parse the combined AI response."""
        lines = [line.strip() for line in response_text.split("\n") if line.strip()]

        short_name = original_name
        event_type = "generic"

        for line in lines:
            if line.startswith("SHORT:"):
                potential_short = line[6:].strip()
                if flags_enabled and standardize_spacing:
                    potential_short = self._standardize_flag_spacing(potential_short)

                visual_width = self._calculate_visual_width(potential_short)
                if visual_width <= char_limit and potential_short:
                    short_name = potential_short
            elif line.startswith("TYPE:"):
                potential_type = line[5:].strip().lower()
                if potential_type in ["trophy", "rugby", "concert", "generic"]:
                    event_type = potential_type

        # Get icons for the detected type
        event_type, emoji, mdi_icon = self._get_icons_for_type(event_type)

        return {
            "short_name": short_name,
            "event_type": event_type,
            "emoji": emoji,
            "mdi_icon": mdi_icon,
            "had_error": False,
            "error_message": "",
        }

    def get_batch_ai_info(self, event_names: list[str]) -> dict[str, dict]:
        """
        Process multiple events in a single AI API call for maximum quota efficiency.

        This is the ultimate optimization - processes ALL events with just 1 API call
        instead of 1 call per event.

        Args:
            event_names: List of event names to process

        Returns:
            Dict mapping event names to their AI info:
            {
                "event_name": {
                    "short_name": str,
                    "event_type": str,
                    "emoji": str,
                    "mdi_icon": str,
                    "had_error": bool,
                    "error_message": str
                },
                ...
            }
        """
        if not event_names:
            return {}

        # Check if AI features are enabled
        shortening_enabled = self.config.get("ai_processor.shortening.enabled", False)
        type_detection_enabled = self.config.get(
            "ai_processor.type_detection.enabled", False
        )

        # If neither is enabled, use fallback methods for all
        if not shortening_enabled and not type_detection_enabled:
            results = {}
            for event_name in event_names:
                event_type, emoji, mdi_icon = self.get_event_type_and_icons(event_name)
                results[event_name] = {
                    "short_name": event_name,
                    "event_type": event_type,
                    "emoji": emoji,
                    "mdi_icon": mdi_icon,
                    "had_error": False,
                    "error_message": "",
                }
            return results

        # If only one feature is enabled, use individual methods
        if shortening_enabled and not type_detection_enabled:
            results = {}
            for event_name in event_names:
                short_name, had_error, error_msg = self.get_short_name(event_name)
                event_type, emoji, mdi_icon = self.get_event_type_and_icons(event_name)
                results[event_name] = {
                    "short_name": short_name,
                    "event_type": event_type,
                    "emoji": emoji,
                    "mdi_icon": mdi_icon,
                    "had_error": had_error,
                    "error_message": error_msg,
                }
            return results

        if type_detection_enabled and not shortening_enabled:
            results = {}
            for event_name in event_names:
                event_type, emoji, mdi_icon = self.get_event_type_and_icons(event_name)
                results[event_name] = {
                    "short_name": event_name,
                    "event_type": event_type,
                    "emoji": emoji,
                    "mdi_icon": mdi_icon,
                    "had_error": False,
                    "error_message": "",
                }
            return results

        # Both features enabled - use batch AI call
        return self._get_batch_ai_info_impl(event_names)

    def _get_batch_ai_info_impl(self, event_names: list[str]) -> dict[str, dict]:
        """Implementation of batch AI processing."""
        # Check batch cache first
        cache_key = f"batch_{hash(tuple(sorted(event_names)))}"
        if (
            self.config.get("ai_processor.shortening.cache_enabled", True)
            and cache_key in self.cache
        ):
            cached_entry = self.cache[cache_key]
            return cached_entry.get("results", {})

        # Check if dependencies are available
        if not GENAI_AVAILABLE:
            results = {}
            for event_name in event_names:
                event_type, emoji, mdi_icon = self._get_icons_for_type(
                    self._detect_event_type_fallback(event_name)
                )
                results[event_name] = {
                    "short_name": event_name,
                    "event_type": event_type,
                    "emoji": emoji,
                    "mdi_icon": mdi_icon,
                    "had_error": True,
                    "error_message": "google.generativeai library not available - install with 'poetry install --with ai'",
                }
            return results

        # Check circuit breaker
        if self.shortener_circuit_open():
            results = {}
            for event_name in event_names:
                event_type, emoji, mdi_icon = self.get_event_type_and_icons(event_name)
                results[event_name] = {
                    "short_name": event_name,
                    "event_type": event_type,
                    "emoji": emoji,
                    "mdi_icon": mdi_icon,
                    "had_error": False,
                    "error_message": "",
                }
            return results

        try:
            # Configure the API
            api_key = self.config.get("ai_processor.api_key")
            if not api_key:
                results = {}
                for event_name in event_names:
                    event_type, emoji, mdi_icon = self._get_icons_for_type(
                        self._detect_event_type_fallback(event_name)
                    )
                    results[event_name] = {
                        "short_name": event_name,
                        "event_type": event_type,
                        "emoji": emoji,
                        "mdi_icon": mdi_icon,
                        "had_error": True,
                        "error_message": "AI processor enabled but no API key provided - check ai_processor.api_key in config",
                    }
                return results

            assert GENAI_AVAILABLE
            genai.configure(api_key=api_key)

            # Get configuration values
            model_name = self.config.get(
                "ai_processor.shortening.model", "gemini-2.5-pro"
            )
            char_limit = self.config.get("ai_processor.shortening.max_length", 16)
            flags_enabled = self.config.get(
                "ai_processor.shortening.flags_enabled", False
            )
            standardize_spacing = self.config.get(
                "ai_processor.shortening.standardize_spacing", True
            )

            # Create batch prompt
            batch_prompt = self._build_batch_prompt(
                event_names, char_limit, flags_enabled
            )

            # Make the API call
            import time

            model = genai.GenerativeModel(model_name)
            time.sleep(2)  # Rate limiting

            response = model.generate_content(batch_prompt)

            if response and response.text:
                # Parse the batch response
                results = self._parse_batch_response(
                    response.text.strip(),
                    event_names,
                    char_limit,
                    flags_enabled,
                    standardize_spacing,
                )

                # Cache the results
                if self.config.get("ai_processor.shortening.cache_enabled", True):
                    self.cache[cache_key] = {
                        "results": results,
                        "created": datetime.now().isoformat(),
                        "event_count": len(event_names),
                    }
                    self._save_cache()

                return results
            else:
                # Empty response - fallback
                results = {}
                for event_name in event_names:
                    event_type, emoji, mdi_icon = self._get_icons_for_type(
                        self._detect_event_type_fallback(event_name)
                    )
                    results[event_name] = {
                        "short_name": event_name,
                        "event_type": event_type,
                        "emoji": emoji,
                        "mdi_icon": mdi_icon,
                        "had_error": True,
                        "error_message": "Empty response received from Gemini API",
                    }
                return results

        except Exception as e:
            error_str = str(e)
            # Check for quota/rate limit
            quota_hit = (
                "429" in error_str
                or "quota" in error_str.lower()
                or "rate" in error_str.lower()
            )
            if quota_hit and not self._shortener_circuit_open:
                self._shortener_circuit_open = True
                import time as _time

                self._shortener_circuit_open_ts = _time.time()
                logging.warning(
                    "AI quota/rate limit encountered; backing off further AI processing"
                )

            # Use fallback for all events
            results = {}
            for event_name in event_names:
                event_type, emoji, mdi_icon = self._get_icons_for_type(
                    self._detect_event_type_fallback(event_name)
                )
                results[event_name] = {
                    "short_name": event_name,
                    "event_type": event_type,
                    "emoji": emoji,
                    "mdi_icon": mdi_icon,
                    "had_error": not quota_hit,  # quota hit is not an error, just a limitation
                    "error_message": "" if quota_hit else f"API error: {e}",
                }
            return results

    def _build_batch_prompt(
        self, event_names: list[str], char_limit: int, flags_enabled: bool
    ) -> str:
        """Build a batch prompt for processing multiple events."""
        flag_instructions = ""
        flag_examples = ""

        if flags_enabled:
            flag_instructions = """When there's space and the event involves countries, add Unicode flag emojis
        with EXACTLY ONE SPACE between flag and country code.

        Flag examples: 🏴󠁧󠁢󠁥󠁮󠁧󠁿 ENG (St George's Cross), 🇦🇺 AUS, 🇳🇿 NZ, 🇦🇷 ARG, 🇿🇦 RSA,
        🇫🇷 FRA, 🇮🇹 ITA, 🏴󠁧󠁢󠁷󠁬󠁳󠁿 WAL, 🏴󠁧󠁢󠁳󠁣󠁴󠁿 SCO, 🇮🇪 IRE, 🇫🇯 FIJ"""
            flag_examples = """England v Australia -> 🏴󠁧󠁢󠁥󠁮󠁧󠁿 ENG v 🇦🇺 AUS
        Argentina V South Africa -> 🇦🇷 ARG V 🇿🇦 RSA"""
        else:
            flag_instructions = "Keep text-only format without flag emojis."
            flag_examples = """England v Australia -> ENG v AUS
        Argentina V South Africa -> ARG V RSA"""

        events_list = "\n".join(
            f"{i + 1}. {event}" for i, event in enumerate(event_names)
        )

        return f"""Analyze these events and provide both shortened names and event classifications for ALL events.

Events to process:
{events_list}

Task 1 - Shorten each event name:
- Maximum {char_limit} characters (count flag emojis as 2 characters each)
- Keep essential information like team names, key words
- Use standard abbreviations (England->ENG, Australia->AUS, etc.)
- {flag_instructions}

Task 2 - Classify each event type:
- "trophy" - for finals, championships, cup finals, major tournament finals, or other prestigious competitions
- "rugby" - for regular rugby matches, internationals, Six Nations, World Cup (non-final), etc.
- "concert" - for musical performances, artists, bands, tours, etc.
- "generic" - for anything else (conferences, corporate events, other sports, etc.)

Examples:
{flag_examples}
World Cup Final -> World Cup Final (trophy)
Ed Sheeran Tour -> Ed Sheeran (concert)

Format your response EXACTLY like this for each event:
EVENT 1:
SHORT: [shortened name]
TYPE: [trophy/rugby/concert/generic]

EVENT 2:
SHORT: [shortened name]
TYPE: [trophy/rugby/concert/generic]

[Continue for all events...]

Response:"""

    def _parse_batch_response(
        self,
        response_text: str,
        event_names: list[str],
        char_limit: int,
        flags_enabled: bool,
        standardize_spacing: bool,
    ) -> dict[str, dict]:
        """Parse the batch AI response."""
        results = {}

        # Initialize all events with defaults
        for event_name in event_names:
            event_type, emoji, mdi_icon = self._get_icons_for_type("generic")
            results[event_name] = {
                "short_name": event_name,
                "event_type": event_type,
                "emoji": emoji,
                "mdi_icon": mdi_icon,
                "had_error": False,
                "error_message": "",
            }

        # Parse the response
        lines = [line.strip() for line in response_text.split("\n") if line.strip()]
        current_event_index = None
        current_short = None
        current_type = None

        for line in lines:
            if line.startswith("EVENT "):
                # Save previous event if we have data
                if current_event_index is not None and current_event_index < len(
                    event_names
                ):
                    event_name = event_names[current_event_index]
                    if current_short:
                        if flags_enabled and standardize_spacing:
                            current_short = self._standardize_flag_spacing(
                                current_short
                            )
                        visual_width = self._calculate_visual_width(current_short)
                        if visual_width <= char_limit:
                            results[event_name]["short_name"] = current_short
                    if current_type and current_type in [
                        "trophy",
                        "rugby",
                        "concert",
                        "generic",
                    ]:
                        event_type, emoji, mdi_icon = self._get_icons_for_type(
                            current_type
                        )
                        results[event_name]["event_type"] = event_type
                        results[event_name]["emoji"] = emoji
                        results[event_name]["mdi_icon"] = mdi_icon

                # Start new event
                try:
                    current_event_index = int(line.split()[1].rstrip(":")) - 1
                    current_short = None
                    current_type = None
                except (ValueError, IndexError):
                    continue

            elif line.startswith("SHORT:"):
                current_short = line[6:].strip()
            elif line.startswith("TYPE:"):
                current_type = line[5:].strip().lower()

        # Save the last event
        if current_event_index is not None and current_event_index < len(event_names):
            event_name = event_names[current_event_index]
            if current_short:
                if flags_enabled and standardize_spacing:
                    current_short = self._standardize_flag_spacing(current_short)
                visual_width = self._calculate_visual_width(current_short)
                if visual_width <= char_limit:
                    results[event_name]["short_name"] = current_short
            if current_type and current_type in [
                "trophy",
                "rugby",
                "concert",
                "generic",
            ]:
                event_type, emoji, mdi_icon = self._get_icons_for_type(current_type)
                results[event_name]["event_type"] = event_type
                results[event_name]["emoji"] = emoji
                results[event_name]["mdi_icon"] = mdi_icon

        return results

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
        if self.config.get("ai_processor.type_detection.enabled", False):
            event_type = self._detect_event_type_ai(event_name)
        else:
            event_type = self._detect_event_type_fallback(event_name)

        # Map event type to icons
        return self._get_icons_for_type(event_type)

    def _detect_event_type_ai(self, event_name: str) -> str:
        """Use AI to detect event type with caching."""
        # Check if feature is disabled or API not available
        if not self.config.get("ai_processor.type_detection.enabled", False):
            return self._detect_event_type_fallback(event_name)

        if not GENAI_AVAILABLE:
            return self._detect_event_type_fallback(event_name)

        # Check cache first
        if (
            self.config.get("ai_processor.type_detection.cache_enabled", True)
            and event_name in self.type_cache
        ):
            cached_entry = self.type_cache[event_name]
            if not cached_entry.get("error"):
                return cached_entry.get("type", "generic")

        try:
            api_key = self.config.get(
                "ai_processor.api_key"
            )  # Reuse same API key - config handles ${} expansion
            if not api_key:
                return self._detect_event_type_fallback(event_name)

            assert GENAI_AVAILABLE
            genai.configure(api_key=api_key)
            model_name = self.config.get(
                "ai_processor.type_detection.model", "gemini-2.5-pro"
            )

            prompt = f"""Analyze this event name and classify it into one of these categories:
- "trophy" - for finals, championships, cup finals, major tournament finals, or other prestigious competitions
- "rugby" - for regular rugby matches, internationals, Six Nations, World Cup (non-final), etc.
- "concert" - for musical performances, artists, bands, tours, etc.
- "generic" - for anything else (conferences, corporate events, other sports, etc.)

Event name: "{event_name}"

Respond with ONLY the category word (trophy, rugby, concert, or generic), nothing else."""

            assert GENAI_AVAILABLE
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)

            if response and response.text:
                detected_type = response.text.strip().lower()
                if detected_type in ["trophy", "rugby", "concert", "generic"]:
                    # Cache the result
                    if self.config.get(
                        "ai_processor.type_detection.cache_enabled", True
                    ):
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
            if self.config.get("ai_processor.type_detection.cache_enabled", True):
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

        # Trophy/Championship keywords - check these first as they're most specific
        trophy_patterns = [
            r"\b(grand final|cup final|title match|championship decider|title decider)\b",
            r"\b(world cup final|six nations final|premiership final|championship final)\b",
            r"\b(champions cup final|european cup final|heineken cup final)\b",
            r"\b(grand slam final|triple crown final)\b",
            r"\b(playoff final)\b",
            r"\b(winner takes all)\b",
            r"\b(champions league final|europa league final)\b",
        ]

        # Rugby keywords
        rugby_patterns = [
            r"\b(rugby|rfu|six nations|world cup|nations cup|autumn international|spring international)\b",
            r"\b(england|wales|scotland|ireland|france|italy|australia|new zealand|south africa|argentina|fiji)\s+(v|vs|versus)\s+",
            r"\b(lions|all blacks|wallabies|springboks|pumas)\b",
            r"\b(internationals?|test match|championship)\b",
            r"\b(guinness|championship|premiership).*rugby\b",
            r"\b(quins|harlequins|leicester|saracens|northampton|bath|gloucester|exeter|bristol|sale|wasps)\b.*\b(v|vs|versus)\b",
            r"\b(tigers|saints|chiefs|sharks)\b.*\b(v|vs|versus)\b",
        ]

        # Concert keywords
        concert_patterns = [
            r"\b(concert|tour|live|music|band|artist|singer|orchestra|symphony)\b",
            r"\b(gig|show|performance|acoustic|jazz|rock|pop|classical)\b",
            r"\b(festival|music festival)\b",
        ]

        # Check for trophy events first (most specific)
        for pattern in trophy_patterns:
            if re.search(pattern, event_lower):
                return "trophy"

        # Check for rugby next
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
            "trophy": ("🏆", "mdi:trophy"),
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
        if not self.config.get("ai_processor.shortening.enabled", False):
            return original_name, False, ""

        # Check cache first
        if (
            self.config.get("ai_processor.shortening.cache_enabled", True)
            and original_name in self.cache
        ):
            cached_entry = self.cache[original_name]
            return cached_entry.get("short", original_name), False, ""

        # Check if dependencies are available
        if not GENAI_AVAILABLE:
            error_msg = "google.generativeai library not available - install with 'poetry install --with ai'"
            logging.warning("Event shortening requested but %s", error_msg)
            return original_name, True, error_msg

        # Fast-path: if a prior call detected quota/rate-limit, skip AI and fall back
        if self.shortener_circuit_open():
            return original_name, False, ""

        try:
            # Configure the API - config handles ${VARIABLE} expansion
            api_key = self.config.get("ai_processor.api_key")

            if not api_key:
                error_msg = "AI processor enabled but no API key provided - check ai_processor.api_key in config"
                logging.error(error_msg)
                return original_name, True, error_msg

            assert GENAI_AVAILABLE
            genai.configure(api_key=api_key)

            # Get configuration values
            model_name = self.config.get(
                "ai_processor.shortening.model", "gemini-2.5-pro"
            )
            char_limit = self.config.get("ai_processor.shortening.max_length", 16)
            prompt_template = self.config.get(
                "ai_processor.shortening.prompt_template", ""
            )
            flags_enabled = self.config.get(
                "ai_processor.shortening.flags_enabled", False
            )
            standardize_spacing = self.config.get(
                "ai_processor.shortening.standardize_spacing", True
            )

            if not prompt_template:
                error_msg = "AI processor enabled but no prompt template provided - check ai_processor.shortening.prompt_template in config"
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
                            if self.config.get(
                                "ai_processor.shortening.cache_enabled", True
                            ):
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
                        # If this looks like a quota/rate-limit (e.g. 429), open circuit
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
                            # Treat as non-fatal and silently fall back to original
                            return original_name, False, ""
                        else:
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
            # If global/outer failure smells like a quota issue, open circuit quietly
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

    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        if not self.config.get("ai_processor.shortening.cache_enabled", True):
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
        if not self.config.get("ai_processor.shortening.cache_enabled", True):
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
        cache_dir = Path(
            self.config.get("ai_processor.type_detection.cache_dir", "output/cache")
        )
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / "ai_type_cache.json"

    def _load_type_cache(self) -> dict:
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
        if not self.config.get("ai_processor.type_detection.cache_enabled", True):
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
