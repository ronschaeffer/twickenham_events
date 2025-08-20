"""
Simple test to validate the FastAPI web server functionality.
"""

import json
from pathlib import Path
import sys
import tempfile

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from twickenham_events.config import Config
from twickenham_events.web import TwickenhamEventsServer


def test_server_initialization():
    """Test that the server initializes correctly."""
    config = Config.from_defaults()

    with tempfile.TemporaryDirectory() as temp_dir:
        server = TwickenhamEventsServer(config, Path(temp_dir))

        assert server.app is not None
        assert server.base_path == Path(temp_dir)
        assert not server.is_running()


def test_server_routes_setup():
    """Test that all expected routes are configured."""
    config = Config.from_defaults()

    with tempfile.TemporaryDirectory() as temp_dir:
        server = TwickenhamEventsServer(config, Path(temp_dir))

        # Check that file routes are registered
        expected_routes = [
            "/calendar",
            "/twickenham_events.ics",
            "/events",
            "/upcoming_events.json",
            "/scrape-results",
        ]

        for route in expected_routes:
            assert route in server.file_routes


def test_file_serving_with_missing_files():
    """Test behavior when files don't exist."""
    config = Config.from_defaults()

    with tempfile.TemporaryDirectory() as temp_dir:
        server = TwickenhamEventsServer(config, Path(temp_dir))

        # Create test client
        from fastapi.testclient import TestClient

        client = TestClient(server.app)

        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

        # Test missing file
        response = client.get("/calendar")
        assert response.status_code == 404


def test_file_serving_with_existing_files():
    """Test serving actual files."""
    config = Config.from_defaults()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        server = TwickenhamEventsServer(config, temp_path)

        # Create test files
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:test
BEGIN:VEVENT
SUMMARY:Test Event
DTSTART:20250827T120000Z
DTEND:20250827T130000Z
END:VEVENT
END:VCALENDAR"""

        json_content = {
            "events": [
                {"title": "Test Event", "date": "2025-08-27", "venue": "Test Venue"}
            ]
        }

        # Write test files
        (temp_path / "twickenham_events.ics").write_text(ics_content)
        (temp_path / "upcoming_events.json").write_text(json.dumps(json_content))

        # Create test client
        from fastapi.testclient import TestClient

        client = TestClient(server.app)

        # Test ICS file serving
        response = client.get("/calendar")
        assert response.status_code == 200
        assert "BEGIN:VCALENDAR" in response.text

        # Test JSON file serving
        response = client.get("/events")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert len(data["events"]) == 1

        # Test status endpoint
        response = client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "twickenham_events"
        assert data["files"]["calendar"]["exists"] is True
        assert data["files"]["events"]["exists"] is True


if __name__ == "__main__":
    # Run a simple test
    test_server_initialization()
    test_server_routes_setup()
    print("✅ Basic server tests passed!")
