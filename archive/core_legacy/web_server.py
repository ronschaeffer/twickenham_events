#!/usr/bin/env python3
"""
Web server for serving ICS calendar files and status endpoints.

This module is designed to be the foundation for the shared web_host library
that will be used across twickenham_events, hounslow_bin_collection, and other projects.
"""

import json
import logging
from pathlib import Path
import threading
import time
from typing import Any, Optional

try:
    from http.server import HTTPServer, SimpleHTTPRequestHandler
    import urllib.parse

    WEB_SERVER_AVAILABLE = True
except ImportError:
    WEB_SERVER_AVAILABLE = False
    logging.warning("HTTP server modules not available. Web serving will be disabled.")


class ProjectFileHandler(SimpleHTTPRequestHandler):
    """
    HTTP request handler for serving project files with proper MIME types.

    This will be extracted to the shared web_host library.
    """

    def __init__(self, *args, output_dir: Path, config: dict[str, Any], **kwargs):
        self.output_dir = output_dir
        self.config = config
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """Handle GET requests for calendar files and status endpoints."""
        path = urllib.parse.urlparse(self.path).path

        # Route requests
        if path == "/calendar" or path == "/calendar.ics":
            self.serve_calendar()
        elif path == "/status":
            self.serve_status()
        elif path == "/health":
            self.serve_health()
        elif path == "/":
            self.serve_index()
        else:
            self.send_error(404, "File not found")

    def serve_calendar(self):
        """Serve the ICS calendar file."""
        calendar_filename = self.config.get("calendar", {}).get(
            "filename", "twickenham_events.ics"
        )
        calendar_path = self.output_dir / calendar_filename

        if not calendar_path.exists():
            self.send_error(404, "Calendar file not found")
            return

        try:
            with open(calendar_path, "rb") as f:
                content = f.read()

            self.send_response(200)
            self.send_header("Content-Type", "text/calendar; charset=utf-8")
            self.send_header(
                "Content-Disposition", f'attachment; filename="{calendar_filename}"'
            )
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(content)

        except Exception as e:
            logging.error("Error serving calendar: %s", e)
            self.send_error(500, "Internal server error")

    def serve_status(self):
        """Serve JSON status information."""
        try:
            # Load current status from files
            status_data = {
                "service": "twickenham_events",
                "timestamp": time.time(),
                "status": "running",
            }

            # Add events info if available
            events_path = self.output_dir / "upcoming_events.json"
            if events_path.exists():
                with open(events_path) as f:
                    events_data = json.load(f)
                    status_data["events"] = {
                        "count": len(events_data.get("events", [])),
                        "last_updated": events_data.get("last_updated"),
                        "data_source": events_data.get("data_source", "unknown"),
                    }

            # Add calendar info if available
            calendar_filename = self.config.get("calendar", {}).get(
                "filename", "twickenham_events.ics"
            )
            calendar_path = self.output_dir / calendar_filename
            if calendar_path.exists():
                status_data["calendar"] = {
                    "file": calendar_filename,
                    "size": calendar_path.stat().st_size,
                    "modified": calendar_path.stat().st_mtime,
                }

            content = json.dumps(status_data, indent=2).encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(content)

        except Exception as e:
            logging.error("Error serving status: %s", e)
            self.send_error(500, "Internal server error")

    def serve_health(self):
        """Serve health check endpoint."""
        try:
            health_data = {
                "status": "healthy",
                "timestamp": time.time(),
                "service": "twickenham_events",
            }

            content = json.dumps(health_data).encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(content)

        except Exception as e:
            logging.error("Error serving health check: %s", e)
            self.send_error(500, "Internal server error")

    def serve_index(self):
        """Serve a simple index page with available endpoints."""
        html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Twickenham Events Server</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .endpoint { margin: 20px 0; padding: 10px; background: #f5f5f5; border-radius: 5px; }
        a { color: #0066cc; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1>🏉 Twickenham Events Server</h1>
    <p>Available endpoints:</p>

    <div class="endpoint">
        <strong><a href="/calendar">/calendar</a></strong> - Download ICS calendar file
    </div>

    <div class="endpoint">
        <strong><a href="/status">/status</a></strong> - JSON status information
    </div>

    <div class="endpoint">
        <strong><a href="/health">/health</a></strong> - Health check endpoint
    </div>

    <p><em>This server is part of the Twickenham Events project.</em></p>
</body>
</html>""".encode()

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(html_content)

    def log_message(self, format, *args):
        """Override to use proper logging."""
        logging.info("Web Server: %s", format % args)


class TwickenhamWebServer:
    """
    Web server for Twickenham Events.

    This class will be refactored into the shared web_host library.
    """

    def __init__(self, config: dict[str, Any], output_dir: Path):
        self.config = config
        self.output_dir = output_dir
        self.server = None
        self.server_thread = None
        self.running = False

    def start(self, host: str = "0.0.0.0", port: int = 8080) -> bool:
        """Start the web server in a background thread."""
        if not WEB_SERVER_AVAILABLE:
            logging.error("Web server cannot start - HTTP server modules not available")
            return False

        if self.running:
            logging.warning("Web server is already running")
            return True

        try:
            # Create handler with our configuration
            def handler_factory(*args, **kwargs):
                return ProjectFileHandler(
                    *args, output_dir=self.output_dir, config=self.config, **kwargs
                )

            # Create server
            self.server = HTTPServer((host, port), handler_factory)

            # Start in background thread
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.running = True
            self.server_thread.start()

            logging.info("Web server started on http://%s:%s", host, port)
            return True

        except Exception as e:
            logging.error("Failed to start web server: %s", e)
            return False

    def stop(self):
        """Stop the web server."""
        if not self.running:
            return

        if self.server:
            self.server.shutdown()
            self.server.server_close()

        if self.server_thread:
            self.server_thread.join(timeout=5)

        self.running = False
        logging.info("Web server stopped")

    def _run_server(self):
        """Run the server (called in background thread)."""
        try:
            self.server.serve_forever()
        except Exception as e:
            logging.error("Web server error: %s", e)
            self.running = False

    def is_running(self) -> bool:
        """Check if the server is running."""
        return self.running and self.server_thread and self.server_thread.is_alive()

    def get_calendar_url(self, external_host: Optional[str] = None) -> Optional[str]:
        """Get the URL for the calendar endpoint."""
        if not self.is_running():
            return None

        # Use external host if provided (for Docker/proxy scenarios)
        if external_host:
            return f"{external_host}/calendar"

        # Use server host/port
        if self.server:
            host, port = self.server.server_address
            if host == "0.0.0.0":
                host = "localhost"  # Use localhost for local access
            return f"http://{host}:{port}/calendar"

        return None


def start_web_server(
    config: dict[str, Any], output_dir: Path
) -> Optional[TwickenhamWebServer]:
    """
    Start web server if enabled in configuration.

    This function will be part of the shared web_host library interface.
    """
    web_config = config.get("web_server", {})

    if not web_config.get("enabled", False):
        return None

    host = web_config.get("host", "0.0.0.0")
    port = web_config.get("port", 8080)

    server = TwickenhamWebServer(config, output_dir)

    if server.start(host, port):
        return server
    else:
        return None


def get_web_calendar_url(
    config: dict[str, Any], server: Optional[TwickenhamWebServer] = None
) -> Optional[str]:
    """
    Get calendar URL from web server or configuration override.

    This function provides a unified way to get calendar URLs across different deployment scenarios.
    """
    # Check for explicit URL override first (for Docker/proxy scenarios)
    override_url = config.get("calendar", {}).get("calendar_url_override")
    if override_url:
        return override_url

    # Use running web server
    if server and server.is_running():
        external_host = config.get("web_server", {}).get("external_host")
        return server.get_calendar_url(external_host)

    # No web server available
    return None
