#!/usr/bin/env python3
"""Integration tests for emoji functionality with the main event processing."""

import unittest

from core.twick_event import get_event_emoji_and_icon


class TestEmojiIntegration(unittest.TestCase):
    """Test emoji functionality integration with main event processing."""

    def test_emoji_function_import_in_main_module(self):
        """Test that the emoji function can be imported from the main module."""
        # This should work because twick_event.py imports it from event_icons
        emoji, icon = get_event_emoji_and_icon("Test Event")
        self.assertEqual(emoji, "📅")
        self.assertEqual(icon, "mdi:calendar")

    def test_rugby_world_cup_final_priority(self):
        """Test that Rugby World Cup Final gets trophy, not rugby emoji."""
        emoji, icon = get_event_emoji_and_icon("Women's Rugby World Cup Final")
        self.assertEqual(emoji, "🏆")
        self.assertEqual(icon, "mdi:trophy")

    def test_harlequins_big_game_gets_rugby(self):
        """Test that Harlequins Big Game gets rugby emoji (real world example)."""
        emoji, icon = get_event_emoji_and_icon("Harlequins Big Game")
        self.assertEqual(emoji, "🏉")
        self.assertEqual(icon, "mdi:rugby")

    def test_international_rugby_match_detection(self):
        """Test international rugby match detection works correctly."""
        test_cases = [
            "England v Australia",
            "Argentina V South Africa",
            "New Zealand vs Wales",
        ]

        for match in test_cases:
            with self.subTest(match=match):
                emoji, icon = get_event_emoji_and_icon(match)
                self.assertEqual(emoji, "🏉")
                self.assertEqual(icon, "mdi:rugby")

    def test_edge_cases_get_appropriate_emojis(self):
        """Test various edge cases get appropriate emojis."""
        test_cases = [
            ("Rugby Semi Final", "🏉", "mdi:rugby"),  # Rugby tournament stage
            ("Football Semi Final", "⚽", "mdi:soccer"),  # Football tournament stage
            ("Concert Live Tour", "🎵", "mdi:music"),  # Music with 'live tour'
            ("Cricket Tournament", "📅", "mdi:calendar"),  # Should NOT match 'tour'
            ("Boxing Match", "📅", "mdi:calendar"),  # General sport
        ]

        for event_name, expected_emoji, expected_icon in test_cases:
            with self.subTest(event_name=event_name):
                emoji, icon = get_event_emoji_and_icon(event_name)
                self.assertEqual(emoji, expected_emoji)
                self.assertEqual(icon, expected_icon)


if __name__ == "__main__":
    unittest.main()
