"""
Configuration management for Flights CLI.

Adapted from twickenham_events configuration system for flight-related functionality.
"""

import os
from pathlib import Path
import random
import string
from typing import Any, Optional

from dotenv import dotenv_values
import yaml

# Lazy one-time .env loading flag
_ENV_LOADED = False


def _load_env_once() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    # Load environment files with cascading precedence
    project_root = Path(__file__).parent.parent.parent
    workspace_env = project_root.parent / ".env"
    project_env = project_root / ".env"

    # Read dotenv files into dictionaries
    workspace_vals = dotenv_values(workspace_env) if workspace_env.exists() else {}
    project_vals = dotenv_values(project_env) if project_env.exists() else {}

    # Merge: project values override workspace defaults
    merged = {}
    merged.update({k: v for k, v in workspace_vals.items() if v is not None})
    merged.update({k: v for k, v in project_vals.items() if v is not None})

    # Apply merged values to environment only when not already defined by OS
    for k, v in merged.items():
        if k and v is not None and k not in os.environ:
            os.environ[k] = str(v)
    _ENV_LOADED = True


class Config:
    """Configuration class for Flights CLI."""
    
    def __init__(self, data: dict[str, Any]):
        self._data = data
        _load_env_once()
    
    @classmethod
    def from_file(cls, config_path: str) -> "Config":
        """Load configuration from YAML file."""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        
        return cls(data)
    
    @classmethod
    def from_defaults(cls) -> "Config":
        """Create a configuration with default values."""
        defaults = {
            "flights": {
                "api_enabled": True,
                "tracking_enabled": True,
                "alerts_enabled": False,
            },
            "mqtt": {
                "enabled": False,
                "broker": "localhost",
                "port": 1883,
                "topics": {
                    "status": "flights/status",
                    "departures": "flights/departures",
                    "arrivals": "flights/arrivals",
                    "alerts": "flights/alerts",
                }
            },
            "output": {
                "directory": "output",
                "formats": ["json", "csv"]
            }
        }
        return cls(defaults)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation."""
        keys = key.split(".")
        current = self._data
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        
        return current
    
    def get_mqtt_config(self) -> dict[str, Any]:
        """Get MQTT configuration for connection."""
        mqtt_config = {}
        
        # Basic connection settings
        mqtt_config["broker_host"] = self.get("mqtt.broker", "localhost")
        mqtt_config["broker_port"] = self.get("mqtt.port", 1883)
        
        # Authentication
        username = os.getenv("MQTT_USERNAME")
        password = os.getenv("MQTT_PASSWORD")
        if username and password:
            mqtt_config["username"] = username
            mqtt_config["password"] = password
        
        # TLS settings
        if self.get("mqtt.tls.enabled", False):
            mqtt_config["use_tls"] = True
            ca_cert = self.get("mqtt.tls.ca_cert")
            if ca_cert:
                mqtt_config["ca_cert_path"] = ca_cert
        
        return mqtt_config


def _generate_device_id() -> str:
    """Generate a unique device ID for MQTT discovery."""
    random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"flights_cli_{random_suffix}"