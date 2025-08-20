"""
Twickenham Events FastAPI server implementation.

This module extends the base FastAPI server to serve Twickenham Events
specific files (ICS calendar, JSON events, status information).
"""

import logging
from pathlib import Path
from typing import Optional

from ..config import Config
from .base_server import BaseFileServer

logger = logging.getLogger(__name__)


class TwickenhamEventsServer(BaseFileServer):
    """
    FastAPI server for Twickenham Events.

    Serves ICS calendar files, JSON event data, and status information.
    Extends the generic BaseFileServer for project-specific functionality.
    """

    def __init__(self, config: Config, output_dir: Optional[Path] = None):
        """
        Initialize Twickenham Events server.

        Args:
            config: Application configuration
            output_dir: Directory containing output files (defaults to ./output)
        """
        # Initialize base server
        super().__init__(
            title="Twickenham Events API",
            description="API for accessing Twickenham Stadium events calendar and data",
            version="1.0.0",
            base_path=output_dir or Path("output"),
        )

        self.config = config
        self._setup_twickenham_routes()

    def _setup_twickenham_routes(self):
        """Setup Twickenham Events specific routes."""

        # ICS Calendar endpoint
        self.add_calendar_route(
            "/calendar", "twickenham_events.ics", "Twickenham Events ICS Calendar"
        )

        # Alternative calendar endpoint for compatibility
        self.add_calendar_route(
            "/twickenham_events.ics",
            "twickenham_events.ics",
            "Twickenham Events ICS Calendar (direct)",
        )

        # JSON events endpoint
        self.add_json_route(
            "/events", "upcoming_events.json", "Upcoming Events JSON Data"
        )

        # Alternative JSON endpoint for compatibility
        self.add_json_route(
            "/upcoming_events.json",
            "upcoming_events.json",
            "Upcoming Events JSON Data (direct)",
        )

        # Scrape results (raw data)
        self.add_json_route(
            "/scrape-results", "scrape_results.json", "Raw Scraping Results"
        )

        # Add custom status endpoint
        @self.app.get("/status", tags=["twickenham"])
        async def twickenham_status():
            """Enhanced status endpoint with Twickenham-specific information."""
            base_health = await self._get_base_health()

            # Check file availability
            files_status = {}
            for name, file_path in [
                ("calendar", "twickenham_events.ics"),
                ("events", "upcoming_events.json"),
                ("scrape_results", "scrape_results.json"),
            ]:
                full_path = self.base_path / file_path
                files_status[name] = {
                    "exists": full_path.exists(),
                    "size_bytes": full_path.stat().st_size if full_path.exists() else 0,
                    "modified": full_path.stat().st_mtime
                    if full_path.exists()
                    else None,
                }

            return {
                **base_health,
                "service": "twickenham_events",
                "mqtt_enabled": self.config.mqtt_enabled,
                "web_config": {
                    "enabled": self.config.web_enabled,
                    "host": self.config.web_host,
                    "port": self.config.web_port,
                },
                "files": files_status,
            }

    async def _get_base_health(self):
        """Get base health information."""
        return {
            "status": "healthy",
            "server_running": self.running,
            "base_path": str(self.base_path),
            "files_available": len(self.file_routes),
        }


class TwickenhamWebServer:
    """
    Updated web server class that wraps the FastAPI implementation.

    This maintains compatibility with the existing interface while
    using the new FastAPI-based implementation underneath.
    """

    def __init__(self, config: Config):
        """Initialize web server with configuration."""
        self.config = config
        self.server = None
        self.running = False

        # Create the FastAPI server instance
        output_dir = Path("output")
        if not output_dir.is_absolute():
            # Make relative to project root
            project_root = Path(__file__).parent.parent.parent.parent
            output_dir = project_root / output_dir

        self.fastapi_server = TwickenhamEventsServer(config, output_dir)

    def start(self) -> bool:
        """Start the web server."""
        if not self.config.web_enabled:
            logger.info("Web server disabled")
            return False

        try:
            # Start the FastAPI server
            self.fastapi_server.start(
                host=self.config.web_host,
                port=self.config.web_port,
                access_log=False,  # Reduce noise in logs
            )
            self.running = True
            return True
        except Exception as e:
            logger.error("Failed to start web server: %s", e)
            return False

    def stop(self) -> None:
        """Stop the web server."""
        if self.running:
            logger.info("Web server stopping")
            self.fastapi_server.stop()
            self.running = False

    def is_running(self) -> bool:
        """Check if server is running."""
        return self.running and self.fastapi_server.is_running()
