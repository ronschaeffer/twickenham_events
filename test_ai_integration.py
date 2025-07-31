#!/usr/bin/env python3
"""
Quick test script to verify AI event shortening with caching works.
"""

from core.config import Config
from core.event_shortener import get_short_name
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_ai_shortening():
    """Test the AI shortening functionality."""

    # Load config
    config = Config('config/config.yaml')

    # Test with a sample event name
    test_event = "Women's Six Nations Championship Final - England vs France"

    print(f"Testing AI shortening for: '{test_event}'")
    print(
        f"Event shortening enabled: {config.get('event_shortener.enabled', False)}")

    if not config.get('event_shortener.enabled', False):
        print("Event shortening is disabled in config")
        return

    if not config.get('event_shortener.api_key'):
        print("No API key configured - using mock test")
        # Create a mock config for testing

        class MockConfig:
            def get(self, key, default=None):
                return {
                    'event_shortener.enabled': True,
                    'event_shortener.api_key': 'test_key',
                    'event_shortener.model_name': 'gemini-2.0-flash',
                    'event_shortener.char_limit': 20,
                    'event_shortener.prompt_template': 'Shorten this event name to {char_limit} characters or less: {event_name}',
                    'event_shortener.cache_enabled': True
                }.get(key, default)

        mock_config = MockConfig()
        short_name, had_error = get_short_name(test_event, mock_config)
        print(f"Result: '{short_name}' (Error: {had_error})")
        return

    # Test with real config
    short_name, had_error = get_short_name(test_event, config)

    print(f"Shortened: '{short_name}'")
    print(f"Had error: {had_error}")
    print(f"Length: {len(short_name)} characters")

    # Test cache by calling again
    print("\nTesting cache (second call)...")
    short_name2, had_error2 = get_short_name(test_event, config)

    print(f"Shortened: '{short_name2}'")
    print(f"Had error: {had_error2}")
    print(f"Same result: {short_name == short_name2}")


if __name__ == "__main__":
    test_ai_shortening()
