"""
Web server for Twickenham Events.

Simple HTTP server for serving calendar files and status information.
This module is designed to be extracted into the shared web_host library.
"""

# Import the new FastAPI-based implementation
from .web import TwickenhamWebServer

# For backwards compatibility, expose the class at module level
__all__ = ["TwickenhamWebServer"]
