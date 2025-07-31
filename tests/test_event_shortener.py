#!/usr/bin/env python3
"""
Unit tests for the event_shortener module.
"""

from core.event_shortener import get_short_name
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestEventShortener(unittest.TestCase):
    """Test cases for the event shortener functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_config_enabled = Mock()
        self.test_config_enabled.get.side_effect = lambda key, default=None: {
            'event_shortener.enabled': True,
            'event_shortener.api_key': 'test_api_key',
            'event_shortener.model_name': 'gemini-2.0-flash',
            'event_shortener.char_limit': 16,
            'event_shortener.prompt_template': 'Shorten this to {char_limit} chars: {event_name}'
        }.get(key, default)

        self.test_config_disabled = Mock()
        self.test_config_disabled.get.side_effect = lambda key, default=None: {
            'event_shortener.enabled': False,
            'event_shortener.api_key': 'test_api_key',
            'event_shortener.model_name': 'gemini-2.0-flash',
            'event_shortener.char_limit': 16,
            'event_shortener.prompt_template': 'Shorten this to {char_limit} chars: {event_name}'
        }.get(key, default)

    def test_disabled_feature_returns_original_name(self):
        """Test that disabled feature returns original name with no error."""
        original_name = "Women's Rugby World Cup Final"
        result_name, had_error = get_short_name(
            original_name, self.test_config_disabled)

        self.assertEqual(result_name, original_name)
        self.assertFalse(had_error)

    def test_missing_config_returns_original_name(self):
        """Test that missing config returns original name with no error."""
        original_name = "Test Event"
        empty_config = Mock()
        empty_config.get.return_value = None
        result_name, had_error = get_short_name(original_name, empty_config)

        self.assertEqual(result_name, original_name)
        self.assertFalse(had_error)

    @patch('core.event_shortener.GENAI_AVAILABLE', True)
    @patch('core.event_shortener.load_cache')
    @patch('core.event_shortener.save_cache')
    @patch('core.event_shortener.genai')
    def test_successful_api_response(self, mock_genai, mock_save_cache, mock_load_cache):
        """Test successful API response returns shortened name."""
        # Setup mocks
        mock_load_cache.return_value = {}  # Empty cache
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "W RWC Final"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        original_name = "Women's Rugby World Cup Final"
        result_name, had_error = get_short_name(
            original_name, self.test_config_enabled)

        self.assertEqual(result_name, "W RWC Final")
        self.assertFalse(had_error)
        mock_genai.configure.assert_called_once_with(api_key='test_api_key')
        mock_genai.GenerativeModel.assert_called_once_with('gemini-2.0-flash')
        mock_save_cache.assert_called_once()  # Verify cache was saved

    @patch('core.event_shortener.load_cache')
    def test_cached_result_returns_without_api_call(self, mock_load_cache):
        """Test that cached results are returned without making API calls."""
        # Setup cache with existing entry
        mock_load_cache.return_value = {
            "Women's Rugby World Cup Final": {
                "short": "W RWC Final",
                "created": "2025-08-01T10:00:00",
                "original": "Women's Rugby World Cup Final"
            }
        }
        
        original_name = "Women's Rugby World Cup Final"
        result_name, had_error = get_short_name(original_name, self.test_config_enabled)
        
        self.assertEqual(result_name, "W RWC Final")
        self.assertFalse(had_error)
        # Verify cache was loaded but no API call was made
        mock_load_cache.assert_called_once()

    @patch('core.event_shortener.GENAI_AVAILABLE', True)
    @patch('core.event_shortener.load_cache')
    @patch('core.event_shortener.genai')
    def test_api_error_returns_original_name(self, mock_genai, mock_load_cache):
        """Test that API errors return original name with error flag."""
        # Setup mocks
        mock_load_cache.return_value = {}  # Empty cache
        mock_genai.configure.side_effect = Exception("API Error")

        original_name = "Test Event"
        result_name, had_error = get_short_name(
            original_name, self.test_config_enabled)

        self.assertEqual(result_name, original_name)
        self.assertTrue(had_error)

    @patch('core.event_shortener.GENAI_AVAILABLE', False)
    def test_missing_dependency_returns_error(self):
        """Test that missing google.generativeai dependency returns error."""
        original_name = "Test Event"
        result_name, had_error = get_short_name(
            original_name, self.test_config_enabled)

        self.assertEqual(result_name, original_name)
        self.assertTrue(had_error)

    def test_missing_api_key_returns_error(self):
        """Test that missing API key returns error."""
        config_no_key = Mock()
        config_no_key.get.side_effect = lambda key, default=None: {
            'event_shortener.enabled': True,
            'event_shortener.api_key': '',  # Empty API key
            'event_shortener.model_name': 'gemini-2.0-flash',
            'event_shortener.char_limit': 16,
            'event_shortener.prompt_template': 'Test template'
        }.get(key, default)

        original_name = "Test Event"
        result_name, had_error = get_short_name(original_name, config_no_key)

        self.assertEqual(result_name, original_name)
        self.assertTrue(had_error)

    def test_missing_prompt_template_returns_error(self):
        """Test that missing prompt template returns error."""
        config_no_template = Mock()
        config_no_template.get.side_effect = lambda key, default=None: {
            'event_shortener.enabled': True,
            'event_shortener.api_key': 'test_key',
            'event_shortener.model_name': 'gemini-2.0-flash',
            'event_shortener.char_limit': 16,
            'event_shortener.prompt_template': ''  # Empty template
        }.get(key, default)

        original_name = "Test Event"
        result_name, had_error = get_short_name(
            original_name, config_no_template)

        self.assertEqual(result_name, original_name)
        self.assertTrue(had_error)

    @patch('core.event_shortener.GENAI_AVAILABLE', True)
    @patch('core.event_shortener.load_cache')
    @patch('core.event_shortener.save_cache')
    @patch('core.event_shortener.genai')
    def test_empty_api_response_returns_error(self, mock_genai, mock_save_cache, mock_load_cache):
        """Test that empty API response returns error."""
        # Setup mock with empty response
        mock_load_cache.return_value = {}  # Empty cache
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = ""  # Empty response
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        original_name = "Test Event"
        result_name, had_error = get_short_name(
            original_name, self.test_config_enabled)

        self.assertEqual(result_name, original_name)
        self.assertTrue(had_error)

    @patch('core.event_shortener.GENAI_AVAILABLE', True)
    @patch('core.event_shortener.load_cache')
    @patch('core.event_shortener.save_cache')
    @patch('core.event_shortener.genai')
    def test_overlength_response_returns_error(self, mock_genai, mock_save_cache, mock_load_cache):
        """Test that response exceeding character limit returns error."""
        # Setup mock with response that's too long
        mock_load_cache.return_value = {}  # Empty cache
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "This response is way too long for the 16 character limit"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        original_name = "Test Event"
        result_name, had_error = get_short_name(
            original_name, self.test_config_enabled)

        self.assertEqual(result_name, original_name)
        self.assertTrue(had_error)

    @patch('core.event_shortener.GENAI_AVAILABLE', True)
    @patch('core.event_shortener.load_cache')
    @patch('core.event_shortener.save_cache')
    @patch('core.event_shortener.genai')
    def test_prompt_formatting(self, mock_genai, mock_save_cache, mock_load_cache):
        """Test that prompt template is formatted correctly."""
        mock_load_cache.return_value = {}  # Empty cache
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "Short Name"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        original_name = "Long Event Name"
        get_short_name(original_name, self.test_config_enabled)

        # Check that generate_content was called with formatted prompt
        expected_prompt = "Shorten this to 16 chars: Long Event Name"
        mock_model.generate_content.assert_called_once_with(expected_prompt)


if __name__ == '__main__':
    unittest.main()
