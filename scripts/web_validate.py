#!/usr/bin/env python3
"""
Web server validation for Twickenham Events.

This script validates the web server configuration and tests connectivity.
Similar to mqtt_validate.py but for the FastAPI web server.
"""

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Any, Optional

try:
    import httpx  # type: ignore[import-not-found]

    WEB_VALIDATION_AVAILABLE = True
except ImportError:
    httpx = None  # type: ignore[assignment]
    WEB_VALIDATION_AVAILABLE = False

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from twickenham_events.config import Config
except ImportError:
    Config = None  # type: ignore


def parse_args() -> argparse.ArgumentParser:
    """Parse command line arguments."""
    p = argparse.ArgumentParser(description="Validate Twickenham Events web server")
    p.add_argument("--host", default="localhost", help="Web server host to test")
    p.add_argument("--port", type=int, default=8080, help="Web server port to test")
    p.add_argument("--config", default="config/config.yaml", help="Config file path")
    p.add_argument(
        "--timeout", type=float, default=10.0, help="Request timeout in seconds"
    )
    p.add_argument(
        "--start-server",
        action="store_true",
        help="Start the web server before validation (for testing)",
    )
    p.add_argument(
        "--endpoints",
        nargs="*",
        default=[
            "/",
            "/health",
            "/status",
            "/files",
            "/events",
            "/calendar",
            "/docs",
        ],
        help="Endpoints to validate",
    )
    p.add_argument(
        "--check-files",
        action="store_true",
        help="Validate that expected output files are served correctly",
    )
    p.add_argument(
        "--external-url",
        help="External URL base to test (overrides host:port, useful for Docker/proxy)",
    )
    return p


class WebServerValidator:
    """Web server validation helper."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 10.0,
        config: Optional[Any] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.config = config
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def validate_endpoint(
        self,
        endpoint: str,
        expected_status: int = 200,
        content_checks: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Validate a single endpoint."""
        url = f"{self.base_url}{endpoint}"

        try:
            assert (
                httpx is not None
            )  # For type checkers; guarded by WEB_VALIDATION_AVAILABLE
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url)

                # Check status code
                if response.status_code != expected_status:
                    self.errors.append(
                        f"{endpoint}: Expected status {expected_status}, got {response.status_code}"
                    )
                    return False

                # Check content if specified
                if content_checks:
                    content_type = response.headers.get("content-type", "").lower()

                    # JSON content validation
                    if (
                        content_checks.get("json")
                        and "application/json" in content_type
                    ):
                        try:
                            data = response.json()
                            required_fields = content_checks.get("required_fields", [])
                            for field in required_fields:
                                if "." in field:
                                    # Nested field check (e.g., "status.healthy")
                                    keys = field.split(".")
                                    value = data
                                    for key in keys:
                                        if isinstance(value, dict) and key in value:
                                            value = value[key]
                                        else:
                                            self.errors.append(
                                                f"{endpoint}: Missing required field '{field}'"
                                            )
                                            return False
                                elif field not in data:
                                    # Simple field check
                                    self.errors.append(
                                        f"{endpoint}: Missing required field '{field}'"
                                    )
                                    return False
                        except json.JSONDecodeError:
                            self.errors.append(f"{endpoint}: Invalid JSON response")
                            return False

                    # Text content validation
                    if content_checks.get("contains"):
                        text = response.text
                        for required_text in content_checks["contains"]:
                            if required_text not in text:
                                self.errors.append(
                                    f"{endpoint}: Response missing required text: '{required_text}'"
                                )
                                return False

                print(f"✅ {endpoint}: OK ({response.status_code})")
                return True

        except Exception as e:
            # Handle httpx-specific errors without referencing possibly-unavailable types
            if httpx is not None and isinstance(e, httpx.TimeoutException):
                self.errors.append(f"{endpoint}: Request timeout after {self.timeout}s")
                return False
            if httpx is not None and isinstance(e, httpx.ConnectError):
                self.errors.append(f"{endpoint}: Connection failed to {url}")
                return False
            self.errors.append(f"{endpoint}: Unexpected error: {e}")
            return False

    def validate_file_serving(self) -> bool:
        """Validate that expected output files are properly served."""
        if not self.config:
            self.warnings.append("No config provided, skipping file validation")
            return True

        success = True

        # Check calendar file
        if self.config.calendar_enabled:
            calendar_endpoint = "/calendar"
            if not self.validate_endpoint(
                calendar_endpoint,
                content_checks={"contains": ["BEGIN:VCALENDAR", "END:VCALENDAR"]},
            ):
                success = False

        # Check events JSON
        events_endpoint = "/events"
        if not self.validate_endpoint(
            events_endpoint,
            content_checks={
                "json": True,
                "required_fields": ["last_updated", "events"],
            },
        ):
            success = False

        return success

    def validate_health_status(self) -> bool:
        """Validate health and status endpoints."""
        success = True

        # Health endpoint
        if not self.validate_endpoint(
            "/health",
            content_checks={"json": True, "required_fields": ["status", "timestamp"]},
        ):
            success = False

        # Status endpoint (more detailed)
        if not self.validate_endpoint(
            "/status",
            content_checks={
                "json": True,
                "required_fields": ["service", "timestamp", "files"],
            },
        ):
            success = False

        return success

    def validate_api_docs(self) -> bool:
        """Validate API documentation endpoints."""
        success = True

        # OpenAPI/Swagger docs
        if not self.validate_endpoint(
            "/docs", content_checks={"contains": ["Swagger UI", "API"]}
        ):
            success = False

        # OpenAPI JSON schema
        if not self.validate_endpoint(
            "/openapi.json",
            content_checks={
                "json": True,
                "required_fields": ["openapi", "info", "paths"],
            },
        ):
            success = False

        return success


def validate_config(config: Any) -> bool:
    """Validate web server configuration."""
    errors = []

    if not config.web_enabled:
        print("⚠️  Web server is disabled in configuration")
        return False

    # Validate host
    host = config.web_host
    if not host:
        errors.append("web_server.host is required")
    elif (
        host not in ["0.0.0.0", "127.0.0.1", "localhost"]
        and not host.replace(".", "").replace("-", "").replace("_", "").isalnum()
    ):
        errors.append(f"web_server.host '{host}' appears invalid")

    # Validate port
    port = config.web_port
    if not isinstance(port, int) or port < 1 or port > 65535:
        errors.append(f"web_server.port must be integer 1-65535, got {port}")
    elif port < 1024:
        print(f"⚠️  Port {port} is privileged (< 1024), may require root access")

    # Validate external URL if provided
    external_url = config.web_external_url_base
    if external_url and not (
        external_url.startswith("http://") or external_url.startswith("https://")
    ):
        errors.append(
            "web_server.external_url_base must start with http:// or https://"
        )

    if errors:
        print("❌ Configuration validation errors:")
        for error in errors:
            print(f"  - {error}")
        return False

    print("✅ Web server configuration is valid")
    return True


def start_test_server(config: Any) -> Optional[Any]:
    """Start web server for testing (returns server instance or None)."""
    try:
        from twickenham_events.web.twickenham_server import TwickenhamWebServer

        server = TwickenhamWebServer(config)
        if server.start():
            print(f"✅ Test server started on {config.web_host}:{config.web_port}")
            time.sleep(2)  # Give server time to start
            return server
        else:
            print("❌ Failed to start test server")
            return None
    except Exception as e:
        print(f"❌ Error starting test server: {e}")
        return None


def main(argv: list[str]) -> int:
    """Main validation function."""
    args = parse_args().parse_args(argv)

    if not WEB_VALIDATION_AVAILABLE:
        print("❌ httpx library not available. Install with: poetry add httpx")
        return 1

    # Load configuration
    config = None
    if Config:
        try:
            config = Config.from_file(args.config)
            print(f"✅ Loaded configuration from {args.config}")
        except Exception as e:
            print(f"⚠️  Could not load config {args.config}: {e}")
            print("   Using command line arguments only")

    # Validate configuration if available
    if config and not validate_config(config):
        return 1

    # Determine base URL
    if args.external_url:
        base_url = args.external_url.rstrip("/")
        print(f"🔗 Using external URL: {base_url}")
    elif config and config.web_external_url_base:
        base_url = config.web_external_url_base.rstrip("/")
        print(f"🔗 Using configured external URL: {base_url}")
    else:
        # Use host and port from args or config
        host = args.host
        port = args.port
        if config:
            host = config.web_host if host == "localhost" else host
            port = config.web_port if port == 8080 else port
        base_url = f"http://{host}:{port}"
        print(f"🔗 Testing server at: {base_url}")

    # Start test server if requested
    test_server = None
    if args.start_server and config:
        test_server = start_test_server(config)
        if not test_server:
            return 1

    try:
        # Create validator
        validator = WebServerValidator(base_url, args.timeout, config)

        # Run validations
        all_success = True

        print("\n🔍 Validating endpoints...")
        for endpoint in args.endpoints:
            if not validator.validate_endpoint(endpoint):
                all_success = False

        print("\n🏥 Validating health endpoints...")
        if not validator.validate_health_status():
            all_success = False

        print("\n📚 Validating API documentation...")
        if not validator.validate_api_docs():
            all_success = False

        if args.check_files:
            print("\n📁 Validating file serving...")
            if not validator.validate_file_serving():
                all_success = False

        # Report results
        if validator.warnings:
            print("\n⚠️  Warnings:")
            for warning in validator.warnings:
                print(f"  - {warning}")

        if validator.errors:
            print("\n❌ Validation errors:")
            for error in validator.errors:
                print(f"  - {error}")

        if all_success and not validator.errors:
            print("\n✅ All web server validations passed!")
            return 0
        else:
            print("\n❌ Web server validation failed")
            return 1

    finally:
        # Stop test server if we started it
        if test_server:
            try:
                test_server.stop()
                print("🛑 Test server stopped")
            except Exception as e:
                print(f"⚠️  Error stopping test server: {e}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
