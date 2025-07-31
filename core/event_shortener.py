#!/usr/bin/env python3
"""
Event name shortener using Google Gemini API. Model chosen in config.yaml.

This module provides functionality to shorten event names using AI,
designed to be self-contained with graceful fallback behavior.
"""

import logging
import json
import os
from datetime import datetime
from typing import Tuple, Dict, Any
from pathlib import Path

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    genai = None  # type: ignore # Make genai available for mocking even when not installed
    GENAI_AVAILABLE = False
    logging.warning(
        "google.generativeai not available. Event shortening will be disabled.")


# Cache management functions
def get_cache_path() -> Path:
    """Get the path to the cache file."""
    return Path(__file__).parent.parent / 'output' / 'event_name_cache.json'


def load_cache() -> Dict[str, Dict[str, str]]:
    """Load the event name cache from file."""
    cache_path = get_cache_path()
    if cache_path.exists():
        try:
            with open(cache_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logging.warning(f"Failed to load cache: {e}")
    return {}


def save_cache(cache: Dict[str, Dict[str, str]]) -> None:
    """Save the event name cache to file."""
    cache_path = get_cache_path()
    cache_path.parent.mkdir(exist_ok=True)
    try:
        with open(cache_path, 'w') as f:
            json.dump(cache, f, indent=2)
    except IOError as e:
        logging.error(f"Failed to save cache: {e}")


def get_cached_short_name(original_name: str, cache: Dict[str, Dict[str, str]]) -> Tuple[str, bool]:
    """
    Get shortened name from cache if available.
    
    Returns:
        Tuple of (short_name_or_original, is_cached):
        - short_name_or_original: The cached short name or original if not cached
        - is_cached: True if found in cache, False otherwise
    """
    if original_name in cache:
        cached_entry = cache[original_name]
        return cached_entry.get('short', original_name), True
    return original_name, False


def get_short_name(original_name: str, config) -> Tuple[str, bool]:
    """
    Get a shortened version of an event name using Google Gemini API.
    Uses caching to avoid repeated API calls for the same event names.

    Args:
        original_name: The original event name to shorten
        config: Configuration object with get() method

    Returns:
        Tuple of (name_to_use, had_error):
        - name_to_use: Either the shortened name or original name
        - had_error: Boolean indicating if an error occurred during processing
    """
    # Check if feature is disabled
    if not config.get('event_shortener.enabled', False):
        return original_name, False

    # Load cache and check if we already have this name
    cache_enabled = config.get('event_shortener.cache_enabled', True)
    cache = load_cache() if cache_enabled else {}
    
    if cache_enabled:
        cached_result, is_cached = get_cached_short_name(original_name, cache)
        if is_cached:
            # Return cached result - no error since we successfully retrieved it
            return cached_result, False

    # Not in cache, proceed with API call
    # Check if dependencies are available
    if not GENAI_AVAILABLE:
        logging.warning(
            "Event shortening requested but google.generativeai not available")
        return original_name, True

    try:
        # Configure the API
        api_key = config.get('event_shortener.api_key')
        if not api_key:
            logging.error("Event shortening enabled but no API key provided")
            return original_name, True

        genai.configure(api_key=api_key)  # type: ignore

        # Get configuration values
        model_name = config.get(
            'event_shortener.model_name', 'gemini-2.0-flash')
        char_limit = config.get('event_shortener.char_limit', 16)
        prompt_template = config.get('event_shortener.prompt_template', '')

        if not prompt_template:
            logging.error(
                "Event shortening enabled but no prompt template provided")
            return original_name, True

        # Prepare the prompt
        final_prompt = prompt_template.format(
            char_limit=char_limit,
            event_name=original_name
        )

        # Make the API call
        model = genai.GenerativeModel(model_name)  # type: ignore
        response = model.generate_content(final_prompt)

        if response.text:
            shortened_name = response.text.strip()
            # Basic validation - ensure it's not longer than the limit
            if len(shortened_name) <= char_limit and shortened_name:
                # Save successful result to cache if caching is enabled
                if cache_enabled:
                    cache[original_name] = {
                        'short': shortened_name,
                        'created': datetime.now().isoformat(),
                        'original': original_name
                    }
                    save_cache(cache)
                return shortened_name, False
            else:
                logging.warning(
                    f"Generated name '{shortened_name}' exceeds limit or is empty")
                return original_name, True
        else:
            logging.error("Empty response from Gemini API")
            return original_name, True

    except Exception as e:
        logging.error(f"Error shortening event name '{original_name}': {e}")
        return original_name, True
