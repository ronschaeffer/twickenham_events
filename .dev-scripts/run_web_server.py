#!/usr/bin/env python3
"""
Standalone web server launcher for Twickenham Events.

This script can be used to start the FastAPI web server independently
for testing or production use.
"""

import argparse
import logging
from pathlib import Path
import sys

# Add the src directory to the path so we can import our modules
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Import after path setup to avoid import errors
try:
    from twickenham_events.config import Config
    from twickenham_events.web import TwickenhamEventsServer
except ImportError as e:
    print(f"Failed to import required modules: {e}")
    print("Make sure you're running this from the project root directory.")
    sys.exit(1)


def setup_logging(debug: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main():
    """Main entry point for the web server."""
    parser = argparse.ArgumentParser(description="Twickenham Events FastAPI Web Server")
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file (uses defaults if not specified)",
    )
    parser.add_argument(
        "--host", type=str, default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=8080, help="Port to bind to (default: 8080)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Directory containing output files (default: output)",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--reload", action="store_true", help="Enable auto-reload for development"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.debug)
    logger = logging.getLogger(__name__)

    try:
        # Load configuration
        if args.config:
            config = Config.from_file(args.config)
            logger.info("Loaded configuration from %s", args.config)
        else:
            config = Config.from_defaults()
            logger.info("Using default configuration")

        # Setup output directory
        output_dir = Path(args.output_dir)
        if not output_dir.is_absolute():
            output_dir = Path.cwd() / output_dir

        if not output_dir.exists():
            logger.warning("Output directory does not exist: %s", output_dir)
            logger.info("Creating output directory: %s", output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        # Create and start server
        server = TwickenhamEventsServer(config, output_dir)

        logger.info("Starting Twickenham Events API server")
        logger.info("Server will be available at: http://%s:%d", args.host, args.port)
        logger.info("API documentation: http://%s:%d/docs", args.host, args.port)
        logger.info("Press Ctrl+C to stop the server")

        # Start the server
        server.start(
            host=args.host, port=args.port, reload=args.reload, access_log=args.debug
        )

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error("Failed to start server: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
