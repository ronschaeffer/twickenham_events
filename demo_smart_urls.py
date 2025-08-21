#!/usr/bin/env python3
"""
Demonstration of smart external URL detection for Docker deployments.
"""

from pathlib import Path
import sys

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from twickenham_events.config import Config
from twickenham_events.mqtt_client import _get_web_server_status
from twickenham_events.network_utils import (
    build_smart_external_url,
    get_local_ipv4,
    is_running_in_docker,
)


def demonstrate_smart_urls():
    """Demonstrate smart URL building for different scenarios."""
    print("🌐 Smart External URL Detection Demo")
    print("=" * 50)

    # Show environment detection
    local_ip = get_local_ipv4()
    in_docker = is_running_in_docker()

    print("🔍 Environment Detection:")
    print(f"   Local IPv4: {local_ip}")
    print(f"   In Docker: {in_docker}")
    print()

    # Test different scenarios
    scenarios = [
        {
            "name": "📱 Development (localhost binding)",
            "host": "localhost",
            "port": 8080,
            "external_url": None,
        },
        {
            "name": "🐳 Docker (0.0.0.0 binding, auto-detect)",
            "host": "0.0.0.0",
            "port": 8080,
            "external_url": None,
        },
        {
            "name": "☁️ Production (explicit external URL)",
            "host": "0.0.0.0",
            "port": 8080,
            "external_url": "https://twickenham.example.com",
        },
        {
            "name": "🏠 Home Network (0.0.0.0, auto LAN access)",
            "host": "0.0.0.0",
            "port": 9090,
            "external_url": None,
        },
    ]

    for scenario in scenarios:
        print(f"{scenario['name']}:")
        smart_url = build_smart_external_url(
            scenario["host"], scenario["port"], scenario["external_url"]
        )
        print(f"   Host: {scenario['host']}")
        print(f"   Port: {scenario['port']}")
        print(f"   External URL: {scenario['external_url']}")
        print(f"   → Smart URL: {smart_url}")
        print()

    # Test with actual config
    print("🔧 MQTT Status Integration:")
    print("-" * 30)

    config = Config.from_defaults()
    config._data["web_server"]["enabled"] = True
    config._data["web_server"]["host"] = "0.0.0.0"
    config._data["web_server"]["port"] = 8080

    print("Configuration:")
    print(f"   web_server.host: {config.web_host}")
    print(f"   web_server.port: {config.web_port}")
    print(f"   web_server.external_url_base: {config.web_external_url_base}")
    print()

    status = _get_web_server_status(config)
    if status:
        print("MQTT Status Payload (web_server section):")
        import json

        print(json.dumps(status, indent=2))
        print()

        print("🏠 Home Assistant Integration:")
        print("   Calendar URL:")
        print(f"     {status['home_assistant']['calendar_url']}")
        print("   Events JSON URL:")
        print(f"     {status['home_assistant']['events_json_url']}")
        print()

        print("💡 Benefits:")
        print("   ✅ Automatic IP detection for LAN access")
        print("   ✅ Works in Docker containers")
        print("   ✅ No manual configuration needed")
        print("   ✅ Other devices can reach the service")
        print("   ✅ Home Assistant auto-discovery ready")


if __name__ == "__main__":
    demonstrate_smart_urls()
