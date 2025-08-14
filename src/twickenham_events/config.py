"""
Configuration management for Twickenham Events.

Provides a modern, type-safe configuration system with validation.
"""

import os
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
import yaml

# Lazy one-time .env loading flag
_ENV_LOADED = False


def _load_env_once():
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    # Prefer project root .env if present
    project_root = Path(__file__).parent.parent.parent
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:  # fallback to default search (current working dir)
        load_dotenv()
    _ENV_LOADED = True


class Config:
    """Configuration manager with validation and defaults."""

    def __init__(self, config_data: dict):
        _load_env_once()
        """Initialize configuration from dictionary."""
        self._data = config_data
        self.config_path = None  # Will be set by from_file or from_defaults

    @classmethod
    def from_file(cls, config_path: str) -> "Config":
        _load_env_once()
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
        _load_env_once()
        """Create configuration with default values."""
        defaults = {
            "scraping": {
                "url": "https://www.twickenham-stadium.com/fixtures-and-events",
                "timeout": 30,
                "retries": 3,
            },
            "service": {
                "interval_seconds": 14400,  # 4 hours
                "enable_buttons": True,
                "discovery_prefix": "homeassistant",
                "systemd": {
                    "auto_launch": False,
                    "unit": "twickenham-events.service",
                    "user": True,
                    "delay_seconds": 2,
                },
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
                    "retry_minutes_on_quota": 10,
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
        # Support both new style (broker_url) and legacy (broker) keys, plus env overrides.
        primary = self.get("mqtt.broker_url", None)
        legacy = self.get("mqtt.broker", None)
        val = primary or legacy or "localhost"
        # Handle unexpanded ${VAR} placeholders by falling back to legacy or default
        if isinstance(val, str) and val.startswith("${"):
            val = legacy if legacy and not str(legacy).startswith("${") else "localhost"
        return val  # type: ignore[return-value]

    @property
    def mqtt_port(self) -> int:
        """Get MQTT port."""
        # Support both new style (broker_port) and legacy (port) keys.
        primary = self.get("mqtt.broker_port", None)
        legacy = self.get("mqtt.port", None)
        val = primary if primary is not None else legacy
        if val is None:
            return 1883
        if isinstance(val, str):
            if val.startswith("${") or not val.strip():
                # Try legacy if primary was placeholder
                if legacy and not str(legacy).startswith("${"):
                    val = legacy
                else:
                    return 1883
            try:
                return int(val)
            except ValueError:
                return 1883
        try:
            return int(val)  # type: ignore[arg-type]
        except Exception:
            return 1883

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

    # Service (daemon) settings
    @property
    def service_interval_seconds(self) -> int:
        return int(self.get("service.interval_seconds", 14400))

    @property
    def service_buttons_enabled(self) -> bool:
        return self.get("service.enable_buttons", True)

    @property
    def service_discovery_prefix(self) -> str:
        return self.get("service.discovery_prefix", "homeassistant")

    def get_mqtt_topics(self) -> dict:
        """Get MQTT topics configuration."""
        return self.get("mqtt.topics", {})

    def get_mqtt_config(self) -> dict:
        """Get complete MQTT configuration for MQTTPublisher (ha-mqtt-publisher)."""
        cfg = {
            "broker_url": self.mqtt_broker,
            "broker_port": self.mqtt_port,
            "client_id": self.mqtt_client_id,
            "security": self.get("mqtt.security", "none"),
            "max_retries": self.get("mqtt.max_retries", 3),
        }
        tls_cfg = self.get("mqtt.tls")
        if isinstance(tls_cfg, dict):  # allow dict TLS settings
            cfg["tls"] = tls_cfg
        if cfg["security"] == "username" and self.mqtt_username and self.mqtt_password:
            cfg["auth"] = {
                "username": self.mqtt_username,
                "password": self.mqtt_password,
            }
        last_will = self.get("mqtt.last_will")
        if isinstance(last_will, dict):
            cfg["last_will"] = last_will
        return cfg
