"""
Web server module for Twickenham Events.

This module provides FastAPI-based web server functionality for serving
event calendar files, JSON data, and status information.

The module is designed with modularity in mind - the BaseFileServer can
be easily extracted into a separate library for use across multiple projects.
"""

from .base_server import BaseFileServer
from .twickenham_server import TwickenhamEventsServer, TwickenhamWebServer

__all__ = [
    "BaseFileServer",
    "TwickenhamEventsServer",
    "TwickenhamWebServer",
]
