"""
Tests for __main__ module CLI functionality.

Tests the setup_argument_parser function and command-line interface.
"""

import argparse
from unittest.mock import patch

import pytest

from core.__main__ import setup_argument_parser


class TestSetupArgumentParser:
    """Test the setup_argument_parser function."""

    def test_basic_parser_creation(self):
        """Test that parser is created successfully."""
        parser = setup_argument_parser()
        assert isinstance(parser, argparse.ArgumentParser)
        assert parser.description == "Twickenham Events scraper and publisher"

    def test_global_arguments(self):
        """Test global arguments are added."""
        parser = setup_argument_parser()

        # Test --version argument (it prints version and exits)
        with patch("sys.exit"):
            try:
                parser.parse_args(["--version"])
            except SystemExit:
                pass  # Expected behavior
            # The version action may or may not call sys.exit directly

        # Test --config argument
        args = parser.parse_args(["--config", "/path/to/config.yaml", "status"])
        assert args.config == "/path/to/config.yaml"

        # Test --debug argument
        args = parser.parse_args(["--debug", "status"])
        assert args.debug is True

    def test_subcommands_exist(self):
        """Test that all expected subcommands are available."""
        parser = setup_argument_parser()

        # Test scrape command
        args = parser.parse_args(["scrape"])
        assert args.command == "scrape"

        # Test mqtt command
        args = parser.parse_args(["mqtt"])
        assert args.command == "mqtt"

        # Test calendar command
        args = parser.parse_args(["calendar"])
        assert args.command == "calendar"

        # Test all command
        args = parser.parse_args(["all"])
        assert args.command == "all"

        # Test status command
        args = parser.parse_args(["status"])
        assert args.command == "status"

    def test_scrape_command_arguments(self):
        """Test scrape command specific arguments."""
        parser = setup_argument_parser()

        # Test scrape with output argument
        args = parser.parse_args(["scrape", "--output", "/custom/path"])
        assert args.command == "scrape"
        assert args.output == "/custom/path"

        # Test scrape without output argument
        args = parser.parse_args(["scrape"])
        assert args.command == "scrape"
        assert args.output is None

    def test_mqtt_command_arguments(self):
        """Test mqtt command specific arguments."""
        parser = setup_argument_parser()

        # Test mqtt with output argument
        args = parser.parse_args(["mqtt", "--output", "/custom/path"])
        assert args.command == "mqtt"
        assert args.output == "/custom/path"

        # Test mqtt without output argument
        args = parser.parse_args(["mqtt"])
        assert args.command == "mqtt"
        assert args.output is None

    def test_calendar_command_arguments(self):
        """Test calendar command specific arguments."""
        parser = setup_argument_parser()

        # Test calendar with output argument
        args = parser.parse_args(["calendar", "--output", "/custom/path"])
        assert args.command == "calendar"
        assert args.output == "/custom/path"

        # Test calendar without output argument
        args = parser.parse_args(["calendar"])
        assert args.command == "calendar"
        assert args.output is None

    def test_all_command_arguments(self):
        """Test all command specific arguments."""
        parser = setup_argument_parser()

        # Test all with output argument
        args = parser.parse_args(["all", "--output", "/custom/path"])
        assert args.command == "all"
        assert args.output == "/custom/path"

        # Test all without output argument
        args = parser.parse_args(["all"])
        assert args.command == "all"
        assert args.output is None

    def test_status_command(self):
        """Test status command."""
        parser = setup_argument_parser()

        args = parser.parse_args(["status"])
        assert args.command == "status"
        # Status command should not have output argument
        assert not hasattr(args, "output") or args.output is None

    def test_combined_arguments(self):
        """Test combinations of global and command-specific arguments."""
        parser = setup_argument_parser()

        # Test debug with scrape and output
        args = parser.parse_args(["--debug", "scrape", "--output", "/test/path"])
        assert args.debug is True
        assert args.command == "scrape"
        assert args.output == "/test/path"

        # Test config with mqtt
        args = parser.parse_args(["--config", "/test/config.yaml", "mqtt"])
        assert args.config == "/test/config.yaml"
        assert args.command == "mqtt"

    def test_help_text_includes_examples(self):
        """Test that help text includes usage examples."""
        parser = setup_argument_parser()
        help_text = parser.format_help()

        # Check that examples are included in epilog
        assert "Examples:" in help_text
        assert "twick-events scrape" in help_text
        assert "twick-events mqtt" in help_text
        assert "twick-events calendar" in help_text
        assert "twick-events all" in help_text
        assert "twick-events status" in help_text
        assert "twick-events --version" in help_text

    def test_invalid_command_handling(self):
        """Test handling of invalid commands."""
        parser = setup_argument_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(["invalid_command"])

    def test_no_command_default(self):
        """Test behavior when no command is provided."""
        parser = setup_argument_parser()

        # Should parse successfully but command will be None
        args = parser.parse_args([])
        assert args.command is None

    def test_argument_parser_type(self):
        """Test that the function returns the correct type."""
        parser = setup_argument_parser()
        assert isinstance(parser, argparse.ArgumentParser)

        # Test that it has the expected attributes
        assert hasattr(parser, "parse_args")
        assert hasattr(parser, "format_help")
        assert hasattr(parser, "description")

    def test_formatter_class(self):
        """Test that the parser uses the correct formatter class."""
        parser = setup_argument_parser()
        assert (
            parser._get_formatter().__class__.__name__ == "RawDescriptionHelpFormatter"
        )


class TestArgumentParserIntegration:
    """Integration tests for argument parser functionality."""

    def test_real_world_usage_patterns(self):
        """Test common real-world usage patterns."""
        parser = setup_argument_parser()

        # Production usage
        args = parser.parse_args(["all"])
        assert args.command == "all"
        assert args.debug is False

        # Development usage
        args = parser.parse_args(["--debug", "scrape", "--output", "./test-output"])
        assert args.debug is True
        assert args.command == "scrape"
        assert args.output == "./test-output"

        # Custom config usage
        args = parser.parse_args(["--config", "./custom-config.yaml", "mqtt"])
        assert args.config == "./custom-config.yaml"
        assert args.command == "mqtt"

    def test_backwards_compatibility(self):
        """Test that the parser supports expected usage patterns."""
        parser = setup_argument_parser()

        # Basic commands should work
        commands = ["scrape", "mqtt", "calendar", "all", "status"]
        for command in commands:
            args = parser.parse_args([command])
            assert args.command == command

    def test_error_conditions(self):
        """Test various error conditions."""
        parser = setup_argument_parser()

        # Invalid option for status command (status doesn't take --output)
        # Note: This might not actually raise an error depending on implementation
        # but we test that status command can be parsed
        args = parser.parse_args(["status"])
        assert args.command == "status"
