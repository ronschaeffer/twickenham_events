#!/usr/bin/env python3
"""
Event name shortener using Google Gemini API.

This module provides functionality to shorten event names using AI,
designed to be self-contained with graceful fallback behavior.
"""

import logging
from typing import Tuple, Dict, Any

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    genai = None  # type: ignore # Make genai available for mocking even when not installed
    GENAI_AVAILABLE = False
    logging.warning(
        "google.generativeai not available. Event shortening will be disabled.")


def get_short_name(original_name: str, config) -> Tuple[str, bool]:
    """
    Get a shortened version of an event name using Google Gemini API.

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
