"""
Web server for Twickenham Events.

Simple HTTP server for serving calendar files and status information.
This module is designed to be extracted into the shared web_host library.
"""

import logging

from .config import Config

logger = logging.getLogger(__name__)


class TwickenhamWebServer:
    """Simple web server for serving event data."""

    def __init__(self, config: Config):
        """Initialize web server with configuration."""
        self.config = config
        self.server = None
        self.running = False

    def start(self) -> bool:
        """Start the web server."""
        if not self.config.web_enabled:
            logger.info("Web server disabled")
            return False

        logger.info(
            "Web server starting on %s:%d", self.config.web_host, self.config.web_port
        )
        # TODO: Implement actual web server
        self.running = True
        return True

    def stop(self) -> None:
        """Stop the web server."""
        if self.running:
            logger.info("Web server stopping")
            self.running = False

    def is_running(self) -> bool:
        """Check if server is running."""
        return self.running
