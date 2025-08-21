"""
Tests for the combined AI functionality in AIProcessor.
"""

from unittest.mock import MagicMock

from twickenham_events.ai_processor import AIProcessor
from twickenham_events.config import Config


def test_combined_ai_info_fallback_both_disabled():
    """Test combined method when both features are disabled."""
    config = Config(
        {
            "ai_processor": {
                "shortening": {"enabled": False},
                "type_detection": {"enabled": False},
            }
        }
    )

    processor = AIProcessor(config)
    result = processor.get_combined_ai_info("England v Australia")

    assert result["short_name"] == "England v Australia"
    assert result["event_type"] == "rugby"
    assert result["emoji"] == "🏉"
    assert result["mdi_icon"] == "mdi:rugby"
    assert result["had_error"] is False
    assert result["error_message"] == ""


def test_combined_ai_info_shortening_only():
    """Test combined method when only shortening is enabled."""
    config = Config(
        {
            "ai_processor": {
                "shortening": {"enabled": True},
                "type_detection": {"enabled": False},
            }
        }
    )

    processor = AIProcessor(config)

    # Mock the get_short_name method
    processor.get_short_name = MagicMock(return_value=("ENG v AUS", False, ""))
    processor.get_event_type_and_icons = MagicMock(
        return_value=("rugby", "🏉", "mdi:rugby")
    )

    result = processor.get_combined_ai_info("England v Australia")

    assert result["short_name"] == "ENG v AUS"
    assert result["event_type"] == "rugby"
    assert result["emoji"] == "🏉"
    assert result["mdi_icon"] == "mdi:rugby"
    assert result["had_error"] is False

    # Verify individual methods were called
    processor.get_short_name.assert_called_once_with("England v Australia")
    processor.get_event_type_and_icons.assert_called_once_with("England v Australia")


def test_combined_ai_info_type_detection_only():
    """Test combined method when only type detection is enabled."""
    config = Config(
        {
            "ai_processor": {
                "shortening": {"enabled": False},
                "type_detection": {"enabled": True},
            }
        }
    )

    processor = AIProcessor(config)

    # Mock the get_event_type_and_icons method
    processor.get_event_type_and_icons = MagicMock(
        return_value=("rugby", "🏉", "mdi:rugby")
    )

    result = processor.get_combined_ai_info("England v Australia")

    assert result["short_name"] == "England v Australia"  # Original name
    assert result["event_type"] == "rugby"
    assert result["emoji"] == "🏉"
    assert result["mdi_icon"] == "mdi:rugby"
    assert result["had_error"] is False

    # Verify type detection was called
    processor.get_event_type_and_icons.assert_called_once_with("England v Australia")


def test_combined_ai_info_both_enabled_uses_implementation():
    """Test combined method when both features are enabled."""
    config = Config(
        {
            "ai_processor": {
                "shortening": {"enabled": True},
                "type_detection": {"enabled": True},
            }
        }
    )

    processor = AIProcessor(config)

    # Mock the implementation method
    processor._get_combined_ai_info_impl = MagicMock(
        return_value={
            "short_name": "ENG v AUS",
            "event_type": "rugby",
            "emoji": "🏉",
            "mdi_icon": "mdi:rugby",
            "had_error": False,
            "error_message": "",
        }
    )

    result = processor.get_combined_ai_info("England v Australia")

    assert result["short_name"] == "ENG v AUS"
    assert result["event_type"] == "rugby"
    assert result["emoji"] == "🏉"
    assert result["mdi_icon"] == "mdi:rugby"
    assert result["had_error"] is False

    # Verify implementation method was called
    processor._get_combined_ai_info_impl.assert_called_once_with("England v Australia")


def test_combined_ai_info_no_api_key():
    """Test combined method when API key is not provided."""
    config = Config(
        {
            "ai_processor": {
                "shortening": {"enabled": True},
                "type_detection": {"enabled": True},
            }
        }
    )

    processor = AIProcessor(config)

    # Use the implementation method which will handle missing API key
    result = processor._get_combined_ai_info_impl("England v Australia")

    # Should fallback to pattern-based detection
    assert result["short_name"] == "England v Australia"
    assert result["event_type"] == "rugby"
    assert result["emoji"] == "🏉"
    assert result["mdi_icon"] == "mdi:rugby"
    assert result["had_error"] is True
    assert "no API key provided" in result["error_message"]


def test_combined_response_parsing():
    """Test the response parsing logic."""
    config = Config({})
    processor = AIProcessor(config)

    # Test successful parsing
    response_text = """SHORT: ENG v AUS
TYPE: rugby"""

    result = processor._parse_combined_response(
        response_text, "England v Australia", 25, False, True
    )

    assert result["short_name"] == "ENG v AUS"
    assert result["event_type"] == "rugby"
    assert result["emoji"] == "🏉"
    assert result["mdi_icon"] == "mdi:rugby"
    assert result["had_error"] is False


def test_combined_response_parsing_invalid_type():
    """Test parsing with invalid event type."""
    config = Config({})
    processor = AIProcessor(config)

    response_text = """SHORT: ENG v AUS
TYPE: invalid_type"""

    result = processor._parse_combined_response(
        response_text, "England v Australia", 25, False, True
    )

    assert result["short_name"] == "ENG v AUS"
    assert result["event_type"] == "generic"  # Should fallback to generic
    assert result["emoji"] == "🏟️"
    assert result["mdi_icon"] == "mdi:stadium"


def test_build_combined_prompt():
    """Test the combined prompt building."""
    config = Config({})
    processor = AIProcessor(config)

    prompt = processor._build_combined_prompt("England v Australia", 25, True)

    assert "England v Australia" in prompt
    assert "Maximum 25 characters" in prompt
    assert "flag emojis" in prompt
    assert "SHORT:" in prompt
    assert "TYPE:" in prompt
    assert "trophy/rugby/concert/generic" in prompt


def test_build_combined_prompt_no_flags():
    """Test the combined prompt building without flags."""
    config = Config({})
    processor = AIProcessor(config)

    prompt = processor._build_combined_prompt("England v Australia", 16, False)

    assert "England v Australia" in prompt
    assert "Maximum 16 characters" in prompt
    assert "text-only format without flag emojis" in prompt
    assert "ENG v AUS" in prompt  # Should have text-only examples
    assert "🏴󠁧󠁢󠁥󠁮󠁧󠁿" not in prompt  # Should not have flag examples


def test_batch_ai_info_fallback_both_disabled():
    """Test batch method when both features are disabled."""
    config = Config(
        {
            "ai_processor": {
                "shortening": {"enabled": False},
                "type_detection": {"enabled": False},
            }
        }
    )

    processor = AIProcessor(config)
    events = ["England v Australia", "Rugby World Cup Final"]
    results = processor.get_batch_ai_info(events)

    assert len(results) == 2
    assert results["England v Australia"]["short_name"] == "England v Australia"
    assert results["England v Australia"]["event_type"] == "rugby"
    assert results["England v Australia"]["emoji"] == "🏉"
    assert results["Rugby World Cup Final"]["event_type"] == "trophy"
    assert results["Rugby World Cup Final"]["emoji"] == "🏆"


def test_batch_ai_info_empty_list():
    """Test batch method with empty event list."""
    config = Config({})
    processor = AIProcessor(config)
    results = processor.get_batch_ai_info([])
    assert results == {}


def test_batch_ai_info_both_enabled_uses_implementation():
    """Test batch method when both features are enabled."""
    config = Config(
        {
            "ai_processor": {
                "shortening": {"enabled": True},
                "type_detection": {"enabled": True},
            }
        }
    )

    processor = AIProcessor(config)
    events = ["England v Australia", "Ed Sheeran Tour"]

    # Mock the implementation method
    expected_results = {
        "England v Australia": {
            "short_name": "ENG v AUS",
            "event_type": "rugby",
            "emoji": "🏉",
            "mdi_icon": "mdi:rugby",
            "had_error": False,
            "error_message": "",
        },
        "Ed Sheeran Tour": {
            "short_name": "Ed Sheeran",
            "event_type": "concert",
            "emoji": "🎵",
            "mdi_icon": "mdi:music",
            "had_error": False,
            "error_message": "",
        },
    }
    processor._get_batch_ai_info_impl = MagicMock(return_value=expected_results)

    results = processor.get_batch_ai_info(events)

    assert results == expected_results
    processor._get_batch_ai_info_impl.assert_called_once_with(events)


def test_build_batch_prompt():
    """Test batch prompt building."""
    config = Config({})
    processor = AIProcessor(config)

    events = ["England v Australia", "Ed Sheeran Tour"]
    prompt = processor._build_batch_prompt(events, 25, True)

    assert "1. England v Australia" in prompt
    assert "2. Ed Sheeran Tour" in prompt
    assert "Maximum 25 characters" in prompt
    assert "flag emojis" in prompt
    assert "EVENT 1:" in prompt
    assert "EVENT 2:" in prompt


def test_parse_batch_response():
    """Test batch response parsing."""
    config = Config({})
    processor = AIProcessor(config)

    events = ["England v Australia", "Ed Sheeran Tour"]
    response_text = """EVENT 1:
SHORT: ENG v AUS
TYPE: rugby

EVENT 2:
SHORT: Ed Sheeran
TYPE: concert"""

    results = processor._parse_batch_response(response_text, events, 25, False, True)

    assert len(results) == 2
    assert results["England v Australia"]["short_name"] == "ENG v AUS"
    assert results["England v Australia"]["event_type"] == "rugby"
    assert results["England v Australia"]["emoji"] == "🏉"
    assert results["Ed Sheeran Tour"]["short_name"] == "Ed Sheeran"
    assert results["Ed Sheeran Tour"]["event_type"] == "concert"
    assert results["Ed Sheeran Tour"]["emoji"] == "🎵"


def test_parse_batch_response_partial():
    """Test batch response parsing with partial data."""
    config = Config({})
    processor = AIProcessor(config)

    events = ["England v Australia", "Unknown Event"]
    response_text = """EVENT 1:
SHORT: ENG v AUS
TYPE: rugby"""

    results = processor._parse_batch_response(response_text, events, 25, False, True)

    assert len(results) == 2
    assert results["England v Australia"]["short_name"] == "ENG v AUS"
    assert results["England v Australia"]["event_type"] == "rugby"
    # Second event should get defaults
    assert results["Unknown Event"]["short_name"] == "Unknown Event"
    assert results["Unknown Event"]["event_type"] == "generic"
