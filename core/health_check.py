#!/usr/bin/env python3
"""
Health check command for Twickenham Events
Usage: poetry run python -m core.health_check
"""

from datetime import datetime, timedelta
import json
from pathlib import Path
import sys

from core.config import Config


def check_health():
    """Comprehensive health check for monitoring systems."""
    health_status = {
        "timestamp": datetime.now().isoformat(),
        "status": "healthy",
        "checks": {},
        "warnings": [],
        "errors": [],
    }

    try:
        # Check 1: Configuration validity
        config = Config("config/config.yaml")
        health_status["checks"]["config"] = "ok"

        # Check 2: Recent data availability
        output_dir = Path(__file__).parent.parent / "output"
        events_file = output_dir / "upcoming_events.json"

        if events_file.exists():
            with open(events_file) as f:
                data = json.load(f)
                last_updated_str = data["last_updated"]

                # Parse datetime, handling timezone info
                try:
                    if last_updated_str.endswith("Z"):
                        last_updated_str = last_updated_str[:-1]
                    elif "+" in last_updated_str:
                        last_updated_str = last_updated_str.split("+")[0]

                    last_updated = datetime.fromisoformat(last_updated_str)
                    age_hours = (datetime.now() - last_updated).total_seconds() / 3600
                except ValueError:
                    health_status["checks"]["data_freshness"] = "error"
                    health_status["errors"].append(
                        "Invalid datetime format in data file"
                    )
                    health_status["status"] = "unhealthy"
                else:
                    if age_hours < 24:
                        health_status["checks"]["data_freshness"] = "ok"
                    elif age_hours < 48:
                        health_status["checks"]["data_freshness"] = "warning"
                        health_status["warnings"].append(
                            f"Data is {age_hours:.1f} hours old"
                        )
                    else:
                        health_status["checks"]["data_freshness"] = "error"
                        health_status["errors"].append(
                            f"Data is {age_hours:.1f} hours old"
                        )
                        health_status["status"] = "unhealthy"
        else:
            health_status["checks"]["data_freshness"] = "error"
            health_status["errors"].append("No data file found")
            health_status["status"] = "unhealthy"

        # Check 3: Error log status
        errors_file = output_dir / "event_processing_errors.json"
        if errors_file.exists():
            with open(errors_file) as f:
                error_data = json.load(f)
                if error_data.get("errors"):
                    health_status["warnings"].append(
                        f"{len(error_data['errors'])} processing errors"
                    )
                health_status["checks"]["error_log"] = "ok"

        # Check 4: MQTT connectivity (quick test)
        mqtt_enabled = config.get("mqtt.enabled", False)
        if mqtt_enabled:
            # Could add a quick MQTT connection test here
            health_status["checks"]["mqtt_config"] = "ok"
        else:
            health_status["checks"]["mqtt_config"] = "disabled"

    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["errors"].append(str(e))
        health_status["checks"]["overall"] = "error"

    # Output results
    print(json.dumps(health_status, indent=2))

    # Exit code for monitoring systems
    if health_status["status"] == "unhealthy":
        sys.exit(1)
    elif health_status["warnings"]:
        sys.exit(2)  # Warning state
    else:
        sys.exit(0)  # Healthy


if __name__ == "__main__":
    check_health()
