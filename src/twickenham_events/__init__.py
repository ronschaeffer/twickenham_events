"""
Twickenham Events - Rugby event processing with MQTT and calendar integration.

A modern Python package for scraping Twickenham Stadium events,
processing them with AI-powered summarization, and publishing to
MQTT brokers and calendar formats.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("twickenham_events")
except PackageNotFoundError:
    # Package is not installed
    __version__ = "0.0.0-dev"

__all__ = [
    "__version__",
]
