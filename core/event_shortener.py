#!/usr/bin/env python3
"""
Event name shortener using Google Gemini API. Model chosen in config.yaml.

This module provides functionality to shorten event names using AI,
designed to be self-contained with graceful fallback behavior.
"""

from datetime import datetime
import json
import logging
import os
from pathlib import Path
from typing import Dict, Tuple  # noqa: UP035

try:
    import google.generativeai as genai

    GENAI_AVAILABLE = True
except ImportError:
    genai = None  # type: ignore # Make genai available for mocking even when not installed
    GENAI_AVAILABLE = False
    logging.warning(
        "google.generativeai not available. Event shortening will be disabled."
    )


# Cache management functions
def get_cache_path() -> Path:
    """Get the path to the cache file."""
    return Path(__file__).parent.parent / "output" / "event_name_cache.json"


def load_cache() -> Dict[str, Dict[str, str]]:  # noqa: UP006
    """Load the event name cache from file."""
    cache_path = get_cache_path()
    if cache_path.exists():
        try:
            with open(cache_path) as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logging.warning("Failed to load cache: %s", e)
    return {}


def save_cache(cache: Dict[str, Dict[str, str]]) -> None:  # noqa: UP006
    """Save the event name cache to file."""
    cache_path = get_cache_path()
    cache_path.parent.mkdir(exist_ok=True)
    try:
        with open(cache_path, "w") as f:
            json.dump(cache, f, indent=2)
    except OSError as e:
        logging.error("Failed to save cache: %s", e)


def standardize_flag_spacing(text: str) -> str:
    """
    Ensure consistent flag + space + country format.
    Fixes AI inconsistencies in flag spacing.

    Args:
        text: AI-generated shortened name

    Returns:
        Text with standardized flag spacing
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


def calculate_visual_width(text: str) -> int:
    """
    Calculate visual display width where each flag emoji counts as 2 units
    and regular characters count as 1 unit each.

    Args:
        text: Text to measure

    Returns:
        Visual width in display units
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


def get_cached_short_name(original_name: str, cache: dict) -> Tuple[str, bool]:  # noqa: UP006
    """
    Get shortened name from cache if available.

    Returns:
        Tuple of (short_name_or_original, is_cached):
        - short_name_or_original: The cached short name or original if not cached
        - is_cached: True if found in cache, False otherwise
    """
    if original_name in cache:
        cached_entry = cache[original_name]
        return cached_entry.get("short", original_name), True
    return original_name, False


def get_short_name(original_name: str, config) -> Tuple[str, bool, str]:  # noqa: UP006
    """
    Get a shortened version of an event name using Google Gemini API.
    Uses caching to avoid repeated API calls for the same event names.

    Args:
        original_name: The original event name to shorten
        config: Configuration object with get() method

    Returns:
        Tuple of (name_to_use, had_error, error_message):
        - name_to_use: Either the shortened name or original name
        - had_error: Boolean indicating if an error occurred during processing
        - error_message: Detailed error message if had_error is True, empty string otherwise
    """
    # Check if feature is disabled
    if not config.get("ai_shortener.enabled", False):
        return original_name, False, ""

    # Load cache and check if we already have this name
    cache_enabled = config.get("ai_shortener.cache_enabled", True)
    cache = load_cache() if cache_enabled else {}

    if cache_enabled:
        cached_result, is_cached = get_cached_short_name(original_name, cache)
        if is_cached:
            # Return cached result - no error since we successfully retrieved it
            return cached_result, False, ""

    # Not in cache, proceed with API call
    # Check if dependencies are available
    if not GENAI_AVAILABLE:
        error_msg = "google.generativeai library not available - install with 'poetry install --with ai'"
        logging.warning("Event shortening requested but %s", error_msg)
        return original_name, True, error_msg

    try:
        # Configure the API
        api_key = config.get("ai_shortener.api_key")

        # Handle environment variable expansion
        if api_key and api_key.startswith("${") and api_key.endswith("}"):
            env_var = api_key[2:-1]  # Remove ${ and }
            api_key = os.environ.get(env_var)

        if not api_key:
            error_msg = "AI shortener enabled but no API key provided - check ai_shortener.api_key in config"
            logging.error(error_msg)
            return original_name, True, error_msg

        genai.configure(api_key=api_key)  # type: ignore

        # Get configuration values
        model_name = config.get("ai_shortener.model", "gemini-2.5-pro")
        char_limit = config.get("ai_shortener.max_length", 16)
        prompt_template = config.get("ai_shortener.prompt_template", "")
        flags_enabled = config.get("ai_shortener.flags_enabled", False)
        standardize_spacing = config.get("ai_shortener.standardize_spacing", True)

        if not prompt_template:
            error_msg = "AI shortener enabled but no prompt template provided - check ai_shortener.prompt_template in config"
            logging.error(error_msg)
            return original_name, True, error_msg

        # Prepare flag-specific content based on configuration
        if flags_enabled:
            flag_instructions = """
    When there's space and the event involves countries, add Unicode flag emojis
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

        model = genai.GenerativeModel(model_name)  # type: ignore

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
                    safe_prompt = final_prompt.replace(original_name, safe_event_name)
                    response = model.generate_content(safe_prompt)
                else:
                    response = model.generate_content(final_prompt)

                if response.text:
                    shortened_name = response.text.strip()

                    # Apply flag spacing standardization if enabled
                    if flags_enabled and standardize_spacing:
                        shortened_name = standardize_flag_spacing(shortened_name)

                    # Visual width validation - count flags as 2 units, characters as 1 unit
                    visual_width = calculate_visual_width(shortened_name)
                    if visual_width <= char_limit and shortened_name:
                        # Save successful result to cache if caching is enabled
                        if cache_enabled:
                            cache[original_name] = {
                                "short": shortened_name,
                                "created": datetime.now().isoformat(),
                                "original": original_name,
                            }
                            save_cache(cache)
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
                    error_msg = "Empty response received from Gemini API after retries"
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
                    error_msg = f"API error while shortening '{original_name}': {e!s}"
                    logging.error(error_msg)
                    return original_name, True, error_msg

        # If we get here, all attempts failed
        error_msg = f"All attempts failed for '{original_name}'"
        logging.error(error_msg)
        return original_name, True, error_msg

    except Exception as e:
        error_msg = f"Unexpected error while shortening '{original_name}': {e!s}"
        logging.error(error_msg)
        return original_name, True, error_msg
