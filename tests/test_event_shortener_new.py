#!/usr/bin/env python3
"""
Additional unit tests for the new event_shortener functionality.
Tests for flag support, visual width calculation, and environment variable expansion.
"""

from core.event_shortener import (
    standardize_flag_spacing,
    calculate_visual_width,
    get_short_name
)
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestEventShortenerNewFeatures(unittest.TestCase):
    """Test cases for the new event shortener functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_config_flags_enabled = Mock()
        self.test_config_flags_enabled.get.side_effect = lambda key, default=None: {
            'ai_shortener.enabled': True,
            'ai_shortener.api_key': '${GEMINI_API_KEY}',
            'ai_shortener.model': 'gemini-2.5-pro',
            'ai_shortener.max_length': 25,
            'ai_shortener.flags_enabled': True,
            'ai_shortener.standardize_spacing': True,
            'ai_shortener.prompt_template': 'Shorten this to {char_limit} chars: {event_name}\n{flag_instructions}\n{flag_examples}'
        }.get(key, default)

        self.test_config_flags_disabled = Mock()
        self.test_config_flags_disabled.get.side_effect = lambda key, default=None: {
            'ai_shortener.enabled': True,
            'ai_shortener.api_key': 'test_api_key',
            'ai_shortener.model': 'gemini-2.5-pro',
            'ai_shortener.max_length': 25,
            'ai_shortener.flags_enabled': False,
            'ai_shortener.standardize_spacing': True,
            'ai_shortener.prompt_template': 'Shorten this to {char_limit} chars: {event_name}\n{flag_instructions}\n{flag_examples}'
        }.get(key, default)

    def test_standardize_flag_spacing_england(self):
        """Test standardizing England flag spacing."""
        # Test various spacing issues
        test_cases = [
            ('🏴󠁧󠁢󠁥󠁮󠁧󠁿ENG', '🏴󠁧󠁢󠁥󠁮󠁧󠁿 ENG'),  # No space
            ('🏴󠁧󠁢󠁥󠁮󠁧󠁿  ENG', '🏴󠁧󠁢󠁥󠁮󠁧󠁿 ENG'),  # Multiple spaces
            ('🏴󠁧󠁢󠁥󠁮󠁧󠁿 ENG', '🏴󠁧󠁢󠁥󠁮󠁧󠁿 ENG'),  # Already correct
        ]

        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = standardize_flag_spacing(input_text)
                self.assertEqual(result, expected)

    def test_standardize_flag_spacing_multiple_countries(self):
        """Test standardizing spacing for multiple countries."""
        input_text = '🇦🇷ARG V 🇿🇦  RSA'
        expected = '🇦🇷 ARG V 🇿🇦 RSA'
        result = standardize_flag_spacing(input_text)
        self.assertEqual(result, expected)

    def test_standardize_flag_spacing_all_flags(self):
        """Test standardizing spacing for all supported flags."""
        test_cases = [
            ('🇦🇺AUS', '🇦🇺 AUS'),  # Australia
            ('🇳🇿NZ', '🇳🇿 NZ'),    # New Zealand
            ('🇦🇷ARG', '🇦🇷 ARG'),  # Argentina
            ('🇿🇦RSA', '🇿🇦 RSA'),  # South Africa
            ('🇫🇷FRA', '🇫🇷 FRA'),  # France
            ('🇮🇹ITA', '🇮🇹 ITA'),  # Italy
            ('🇮🇪IRE', '🇮🇪 IRE'),  # Ireland
            ('🇫🇯FIJ', '🇫🇯 FIJ'),  # Fiji
            ('🏴󠁧󠁢󠁳󠁣󠁴󠁿SCO', '🏴󠁧󠁢󠁳󠁣󠁴󠁿 SCO'),  # Scotland
            ('🏴󠁧󠁢󠁷󠁬󠁳󠁿WAL', '🏴󠁧󠁢󠁷󠁬󠁳󠁿 WAL'),  # Wales
        ]

        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = standardize_flag_spacing(input_text)
                self.assertEqual(result, expected)

    def test_standardize_flag_spacing_no_flags(self):
        """Test that text without flags is unchanged."""
        input_text = 'ENG v AUS'
        result = standardize_flag_spacing(input_text)
        self.assertEqual(result, input_text)

    def test_calculate_visual_width_no_flags(self):
        """Test visual width calculation for text without flags."""
        test_cases = [
            ('ENG v AUS', 9),       # 9 characters
            ('W RWC Final', 11),    # 11 characters
            ('Test', 4),            # 4 characters
            ('', 0),                # Empty string
        ]

        for text, expected_width in test_cases:
            with self.subTest(text=text):
                result = calculate_visual_width(text)
                self.assertEqual(result, expected_width)

    def test_calculate_visual_width_with_flags(self):
        """Test visual width calculation for text with flags."""
        test_cases = [
            ('🇦🇷 ARG V 🇿🇦 RSA', 15),  # 2 flags (4 units) + 11 chars = 15 units
            # 2 flags (4 units) + 11 chars = 15 units
            ('🏴󠁧󠁢󠁥󠁮󠁧󠁿 ENG v 🇦🇺 AUS', 15),
            ('🇫🇯 FIJ', 6),               # 1 flag (2 units) + 4 chars = 6 units
            ('🇳🇿 NZ v 🇦🇺 AUS', 14),     # 2 flags (4 units) + 10 chars = 14 units
        ]

        for text, expected_width in test_cases:
            with self.subTest(text=text):
                result = calculate_visual_width(text)
                self.assertEqual(result, expected_width)

    def test_calculate_visual_width_complex_flags(self):
        """Test visual width calculation with complex flag sequences."""
        # England flag has a complex Unicode sequence
        text = '🏴󠁧󠁢󠁥󠁮󠁧󠁿 ENG'
        result = calculate_visual_width(text)
        # Should be 1 flag (2 units) + 4 chars = 6 units
        self.assertEqual(result, 6)

    @patch.dict(os.environ, {'GEMINI_API_KEY': 'actual_api_key'})
    def test_environment_variable_expansion(self):
        """Test that environment variables are expanded correctly."""
        with patch('core.event_shortener.GENAI_AVAILABLE', True), \
                patch('core.event_shortener.load_cache', return_value={}), \
                patch('core.event_shortener.genai') as mock_genai:

            # Setup mock
            mock_model = Mock()
            mock_response = Mock()
            mock_response.text = "Test Result"
            mock_model.generate_content.return_value = mock_response
            mock_genai.GenerativeModel.return_value = mock_model

            original_name = "Test Event"
            get_short_name(original_name, self.test_config_flags_enabled)

            # Verify that genai.configure was called with the expanded environment variable
            mock_genai.configure.assert_called_once_with(
                api_key='actual_api_key')

    @patch.dict(os.environ, {}, clear=True)  # Clear environment variables
    def test_environment_variable_missing(self):
        """Test handling when environment variable is missing."""
        with patch('core.event_shortener.GENAI_AVAILABLE', True), \
                patch('core.event_shortener.load_cache', return_value={}):

            original_name = "Test Event"
            result, had_error = get_short_name(
                original_name, self.test_config_flags_enabled)

            # Should return original name and have error due to missing API key
            self.assertEqual(result, original_name)
            self.assertTrue(had_error)

    @patch('core.event_shortener.GENAI_AVAILABLE', True)
    @patch('core.event_shortener.load_cache')
    @patch('core.event_shortener.save_cache')
    @patch('core.event_shortener.genai')
    @patch('time.sleep')  # Mock sleep to speed up tests
    def test_rate_limiting_applied(self, mock_sleep, mock_genai, mock_save_cache, mock_load_cache):
        """Test that rate limiting delay is applied."""
        # Setup mocks
        mock_load_cache.return_value = {}
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "Short Name"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        original_name = "Test Event"
        get_short_name(original_name, self.test_config_flags_disabled)

        # Verify that sleep was called with 2 seconds
        mock_sleep.assert_called_once_with(2)

    @patch('core.event_shortener.GENAI_AVAILABLE', True)
    @patch('core.event_shortener.load_cache')
    @patch('core.event_shortener.save_cache')
    @patch('core.event_shortener.genai')
    @patch('time.sleep')
    # Set environment variable
    @patch.dict(os.environ, {'GEMINI_API_KEY': 'test_api_key'})
    def test_flag_standardization_applied(self, mock_sleep, mock_genai, mock_save_cache, mock_load_cache):
        """Test that flag standardization is applied when enabled."""
        # Setup mocks
        mock_load_cache.return_value = {}
        mock_model = Mock()
        mock_response = Mock()
        # AI returns inconsistent spacing
        mock_response.text = "🇦🇷ARG V 🇿🇦  RSA"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        original_name = "Argentina vs South Africa"
        result, had_error = get_short_name(
            original_name, self.test_config_flags_enabled)

        # Should be standardized to consistent spacing
        self.assertEqual(result, "🇦🇷 ARG V 🇿🇦 RSA")
        self.assertFalse(had_error)

    @patch('core.event_shortener.GENAI_AVAILABLE', True)
    @patch('core.event_shortener.load_cache')
    @patch('core.event_shortener.save_cache')
    @patch('core.event_shortener.genai')
    @patch('time.sleep')
    # Set environment variable
    @patch.dict(os.environ, {'GEMINI_API_KEY': 'test_api_key'})
    def test_visual_width_validation(self, mock_sleep, mock_genai, mock_save_cache, mock_load_cache):
        """Test that visual width validation rejects oversized results."""
        # Setup mocks
        mock_load_cache.return_value = {}
        mock_model = Mock()
        mock_response = Mock()
        # AI returns result that exceeds visual width limit (25)
        mock_response.text = "🇦🇷 ARG V 🇿🇦 RSA AND MUCH MORE TEXT HERE"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        original_name = "Argentina vs South Africa"
        result, had_error = get_short_name(
            original_name, self.test_config_flags_enabled)

        # Should return original name due to width limit exceeded
        self.assertEqual(result, original_name)
        self.assertTrue(had_error)

    def test_new_config_keys_used(self):
        """Test that new ai_shortener.* config keys are used correctly."""
        # This is tested implicitly in other tests, but let's be explicit
        config = Mock()
        config.get.side_effect = lambda key, default=None: {
            'ai_shortener.enabled': False,  # Disabled
        }.get(key, default)

        original_name = "Test Event"
        result, had_error = get_short_name(original_name, config)

        # Should return original name when disabled
        self.assertEqual(result, original_name)
        self.assertFalse(had_error)

        # Verify the correct config key was checked
        config.get.assert_called_with('ai_shortener.enabled', False)

    @patch('core.event_shortener.GENAI_AVAILABLE', True)
    @patch('core.event_shortener.load_cache')
    @patch('core.event_shortener.save_cache')
    @patch('core.event_shortener.genai')
    # Set environment variable
    @patch.dict(os.environ, {'GEMINI_API_KEY': 'test_api_key'})
    def test_prompt_includes_flag_instructions(self, mock_genai, mock_save_cache, mock_load_cache):
        """Test that prompt includes flag instructions when flags are enabled."""
        mock_load_cache.return_value = {}
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "🇦🇷 ARG V 🇿🇦 RSA"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        original_name = "Argentina vs South Africa"
        get_short_name(original_name, self.test_config_flags_enabled)

        # Get the prompt that was passed to the model
        call_args = mock_model.generate_content.call_args[0][0]

        # Verify flag instructions are included
        self.assertIn("Unicode flag emojis", call_args)
        self.assertIn("🏴󠁧󠁢󠁥󠁮󠁧󠁿 ENG", call_args)
        self.assertIn("🇦🇺 AUS", call_args)

    @patch('core.event_shortener.GENAI_AVAILABLE', True)
    @patch('core.event_shortener.load_cache')
    @patch('core.event_shortener.save_cache')
    @patch('core.event_shortener.genai')
    def test_prompt_excludes_flags_when_disabled(self, mock_genai, mock_save_cache, mock_load_cache):
        """Test that prompt excludes flag instructions when flags are disabled."""
        mock_load_cache.return_value = {}
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "ARG V RSA"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        original_name = "Argentina vs South Africa"
        get_short_name(original_name, self.test_config_flags_disabled)

        # Get the prompt that was passed to the model
        call_args = mock_model.generate_content.call_args[0][0]

        # Verify flag instructions are excluded
        self.assertIn("Keep text-only format", call_args)
        self.assertNotIn("Unicode flag emojis", call_args)


if __name__ == '__main__':
    unittest.main()
