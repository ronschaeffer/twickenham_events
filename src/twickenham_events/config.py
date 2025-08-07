"""
Configuration management for Twickenham Events.

Provides a modern, type-safe configuration system with validation.
"""

import os
from pathlib import Path
from typing import Any, Optional

import yaml


class Config:
    """Configuration manager with validation and defaults."""

    def __init__(self, config_data: dict):
        """Initialize configuration from dictionary."""
        self._data = config_data
        self.config_path = None  # Will be set by from_file or from_defaults

    @classmethod
    def from_file(cls, config_path: str) -> "Config":
        """Load configuration from YAML file."""
        path = Path(config_path)

        if not path.exists():
            # Try relative to project root
            project_root = Path(__file__).parent.parent.parent
            path = project_root / config_path

            if not path.exists():
                raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(path) as f:
            data = yaml.safe_load(f)

        instance = cls(data)
        instance.config_path = str(path)
        return instance

    @classmethod
    def from_defaults(cls) -> "Config":
        """Create configuration with default values."""
        defaults = {
            "scraping": {
                "url": "https://www.twickenham-stadium.com/fixtures-and-events",
                "timeout": 30,
                "retries": 3,
            },
            "mqtt": {
                "enabled": False,
                "broker": "localhost",
                "port": 1883,
                "tls": False,
                "topics": {
                    "all_upcoming": "twickenham_events/events/all_upcoming",
                    "next": "twickenham_events/events/next",
                    "status": "twickenham_events/status",
                },
            },
            "calendar": {"enabled": True, "filename": "twickenham_events.ics"},
            "ai_processor": {
                "api_key": "${GEMINI_API_KEY}",
                "type_detection": {
                    "enabled": False,
                    "cache_enabled": True,
                    "cache_dir": "output/cache",
                    "model": "gemini-2.5-pro",
                },
                "shortening": {
                    "enabled": False,
                    "cache_enabled": True,
                    "model": "gemini-2.5-pro",
                    "max_length": 16,
                    "flags_enabled": False,
                    "standardize_spacing": True,
                    "prompt_template": "",
                },
            },
            "web_server": {"enabled": False, "host": "0.0.0.0", "port": 8080},
        }

        instance = cls(defaults)
        instance.config_path = "defaults"
        return instance

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation."""
        keys = key.split(".")
        value = self._data

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        # Environment variable override
        env_key = f"TWICK_{key.upper().replace('.', '_')}"
        env_value = os.getenv(env_key)
        if env_value is not None:
            # Basic type conversion
            if isinstance(value, bool):
                return env_value.lower() in ("true", "1", "yes", "on")
            elif isinstance(value, int):
                try:
                    return int(env_value)
                except ValueError:
                    pass
            elif isinstance(value, float):
                try:
                    return float(env_value)
                except ValueError:
                    pass
            return env_value

        # Handle ${VARIABLE} expansion in string values
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]  # Remove ${ and }
            expanded_value = os.getenv(env_var)
            if expanded_value is not None:
                return expanded_value
            # If env var not found, return the original value (so it fails gracefully)

        return value

    @property
    def scraping_url(self) -> str:
        """Get scraping URL."""
        return self.get("scraping.url", "")

    @property
    def scraping_timeout(self) -> int:
        """Get scraping timeout."""
        return self.get("scraping.timeout", 30)

    @property
    def scraping_retries(self) -> int:
        """Get scraping retries."""
        return self.get("scraping.retries", 3)

    @property
    def mqtt_enabled(self) -> bool:
        """Check if MQTT is enabled."""
        return self.get("mqtt.enabled", False)

    @property
    def mqtt_broker(self) -> str:
        """Get MQTT broker."""
        return self.get("mqtt.broker_url", "localhost")

    @property
    def mqtt_port(self) -> int:
        """Get MQTT port."""
        return self.get("mqtt.broker_port", 1883)

    @property
    def mqtt_tls(self) -> bool:
        """Check if MQTT TLS is enabled."""
        return self.get("mqtt.tls", False)

    @property
    def mqtt_username(self) -> Optional[str]:
        """Get MQTT username."""
        return self.get("mqtt.auth.username")

    @property
    def mqtt_password(self) -> Optional[str]:
        """Get MQTT password."""
        return self.get("mqtt.auth.password")

    @property
    def mqtt_client_id(self) -> str:
        """Get MQTT client ID."""
        return self.get("mqtt.client_id", "twickenham_events")

    @property
    def calendar_enabled(self) -> bool:
        """Check if calendar is enabled."""
        return self.get("calendar.enabled", True)

    @property
    def calendar_filename(self) -> str:
        """Get calendar filename."""
        return self.get("calendar.filename", "twickenham_events.ics")

    @property
    def ai_enabled(self) -> bool:
        """Check if AI processor shortening is enabled."""
        return self.get("ai_processor.shortening.enabled", False)

    @property
    def ai_model(self) -> str:
        """Get AI model for shortening."""
        return self.get("ai_processor.shortening.model", "gemini-2.5-pro")

    @property
    def ai_max_length(self) -> int:
        """Get AI max length for shortening."""
        return self.get("ai_processor.shortening.max_length", 16)

    @property
    def ai_api_key(self) -> Optional[str]:
        """Get AI API key."""
        return self.get("ai_processor.api_key") or os.getenv("GEMINI_API_KEY")

    @property
    def web_enabled(self) -> bool:
        """Check if web server is enabled."""
        return self.get("web_server.enabled", False)

    @property
    def web_host(self) -> str:
        """Get web server host."""
        return self.get("web_server.host", "0.0.0.0")

    @property
    def web_port(self) -> int:
        """Get web server port."""
        return self.get("web_server.port", 8080)

    def get_mqtt_topics(self) -> dict:
        """Get MQTT topics configuration."""
        return self.get("mqtt.topics", {})

    def get_mqtt_config(self) -> dict:
        """Get complete MQTT configuration for client."""
        config = {
            "broker_url": self.mqtt_broker,
            "broker_port": self.mqtt_port,
            "client_id": self.mqtt_client_id,
            "tls": self.mqtt_tls,
        }

        if self.mqtt_username:
            config["username"] = self.mqtt_username
        if self.mqtt_password:
            config["password"] = self.mqtt_password

        return config
