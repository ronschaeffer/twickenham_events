"""
Base FastAPI server module designed for easy extraction into a shared library.

This module provides a generic FastAPI server that can be customized for different
projects. It's designed to be extracted into a separate web_host library.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Union

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
import uvicorn

logger = logging.getLogger(__name__)


class BaseFileServer:
    """
    Generic FastAPI server for serving files with health checks.

    This class is designed to be easily extracted into a shared library
    for use across multiple projects.
    """

    def __init__(
        self,
        title: str = "File Server",
        description: str = "Simple file serving API",
        version: str = "1.0.0",
        base_path: Optional[Union[str, Path]] = None,
    ):
        """
        Initialize the base file server.

        Args:
            title: API title for OpenAPI docs
            description: API description for OpenAPI docs
            version: API version
            base_path: Base directory for file serving (defaults to current directory)
        """
        self.app = FastAPI(
            title=title,
            description=description,
            version=version,
        )
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.server = None
        self.running = False

        # File route registry: path -> (file_path, content_type, description)
        self.file_routes: dict[str, tuple] = {}

        self._setup_default_routes()

    def _setup_default_routes(self):
        """Setup default health and info routes."""

        @self.app.get("/", tags=["info"])
        async def root():
            """Root endpoint with basic API information."""
            return {
                "title": self.app.title,
                "description": self.app.description,
                "version": self.app.version,
                "available_endpoints": [*self.file_routes.keys(), "/health", "/files"],
            }

        @self.app.get("/health", tags=["health"])
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "server_running": self.running,
                "base_path": str(self.base_path),
                "files_available": len(self.file_routes),
            }

        @self.app.get("/files", tags=["info"])
        async def list_files():
            """List all available file endpoints."""
            return {
                "available_files": {
                    path: {
                        "description": info[2],
                        "content_type": info[1],
                        "file_exists": (self.base_path / info[0]).exists(),
                    }
                    for path, info in self.file_routes.items()
                }
            }

    def add_file_route(
        self,
        url_path: str,
        file_path: Union[str, Path],
        content_type: str = "application/octet-stream",
        description: str = "File endpoint",
    ):
        """
        Add a file serving route.

        Args:
            url_path: URL path (e.g., "/calendar")
            file_path: Relative path to file from base_path
            content_type: MIME content type
            description: Description for API docs
        """
        # Store route info
        self.file_routes[url_path] = (str(file_path), content_type, description)

        # Create the route handler
        async def serve_file():
            full_path = self.base_path / file_path

            if not full_path.exists():
                raise HTTPException(
                    status_code=404, detail=f"File not found: {file_path}"
                )

            # For JSON files, parse and return as JSON
            if content_type == "application/json":
                try:
                    with open(full_path, encoding="utf-8") as f:
                        data = json.load(f)
                    return JSONResponse(content=data)
                except json.JSONDecodeError as e:
                    raise HTTPException(
                        status_code=500, detail=f"Invalid JSON file: {e}"
                    ) from e

            # For other files, serve directly
            return FileResponse(
                path=full_path, media_type=content_type, filename=full_path.name
            )

        # Add the route with proper metadata
        self.app.get(
            url_path,
            tags=["files"],
            summary=f"Serve {description}",
            description=f"Download or view {description}",
            response_description=f"{description} content",
        )(serve_file)

    def add_json_route(
        self, url_path: str, file_path: Union[str, Path], description: str = "JSON data"
    ):
        """Convenience method to add a JSON file route."""
        self.add_file_route(url_path, file_path, "application/json", description)

    def add_calendar_route(
        self,
        url_path: str,
        file_path: Union[str, Path],
        description: str = "ICS calendar",
    ):
        """Convenience method to add an ICS calendar route."""
        self.add_file_route(url_path, file_path, "text/calendar", description)

    def add_text_route(
        self, url_path: str, file_path: Union[str, Path], description: str = "Text file"
    ):
        """Convenience method to add a text file route."""
        self.add_file_route(url_path, file_path, "text/plain", description)

    async def start_async(self, host: str = "0.0.0.0", port: int = 8080, **kwargs):
        """
        Start server asynchronously (for use in async contexts).

        Args:
            host: Host to bind to
            port: Port to bind to
            **kwargs: Additional uvicorn configuration
        """
        config = uvicorn.Config(
            self.app, host=host, port=port, log_level="info", **kwargs
        )
        self.server = uvicorn.Server(config)
        self.running = True

        logger.info("Starting server on %s:%d", host, port)
        await self.server.serve()

    def start(self, host: str = "0.0.0.0", port: int = 8080, **kwargs):
        """
        Start server synchronously.

        Args:
            host: Host to bind to
            port: Port to bind to
            **kwargs: Additional uvicorn configuration
        """
        self.running = True
        logger.info("Starting server on %s:%d", host, port)

        uvicorn.run(self.app, host=host, port=port, log_level="info", **kwargs)

    async def stop_async(self):
        """Stop server asynchronously."""
        if self.server:
            self.running = False
            logger.info("Stopping server")
            await self.server.shutdown()

    def stop(self):
        """Stop server synchronously."""
        self.running = False
        logger.info("Server stopped")

    def is_running(self) -> bool:
        """Check if server is running."""
        return self.running
